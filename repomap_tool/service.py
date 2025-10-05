"""Standalone helpers for building repository maps and ranked tags."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

from ._backend import DEFAULT_MODEL_NAME, GitRepo, Model, RepoMap


class RepoMapConsoleIO:
    """Lightweight console IO adapter compatible with the underlying backend."""

    def __init__(self, verbose: bool = False, encoding: str = "utf-8") -> None:
        self.verbose = verbose
        self.encoding = encoding

    def tool_output(self, *messages, log_only: bool = False, bold: bool = False) -> None:  # noqa: ARG002
        if log_only:
            return
        if not self.verbose and bold is False:
            return
        text = " ".join(str(msg) for msg in messages if msg is not None)
        if text:
            print(text)

    def tool_warning(self, *messages) -> None:
        text = " ".join(str(msg) for msg in messages if msg is not None)
        if text:
            print(text, file=sys.stderr)

    def tool_error(self, *messages) -> None:
        text = " ".join(str(msg) for msg in messages if msg is not None)
        if text:
            print(text, file=sys.stderr)

    def read_text(self, fname: str) -> str:
        try:
            return Path(fname).read_text(encoding=self.encoding, errors="ignore")
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            return ""


@dataclass
class RepoMapInputs:
    chat_files: Set[str]
    other_files: List[str]
    mentioned_files: Set[str]
    mentioned_identifiers: Set[str]


@dataclass
class RepoMapBuilder:
    """High-level wrapper that produces repository maps identical to the chat workflow.

    The optional ``model_name`` (or ``main_model``) argument is still supported because
    the repo map engine sizes its output to the context window of the downstream model.
    The lightweight :class:`repomap_tool.models.Model` shim lets callers mirror the
    behaviour of their preferred LLM without pulling in the rest of aider.
    """

    root: Path | str | None = None
    model_name: Optional[str] = None
    map_tokens: Optional[int] = None
    refresh: str = "auto"
    verbose: bool = False
    main_model: Optional[Model] = None
    io: Optional[RepoMapConsoleIO] = None
    repo_map_kwargs: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.root = Path(self.root or Path.cwd()).resolve()
        self.io = self.io or RepoMapConsoleIO(verbose=self.verbose)

        if self.main_model is None:
            model_to_use = self.model_name or DEFAULT_MODEL_NAME
            self.main_model = Model(model_to_use, verbose=self.verbose)
        elif self.model_name is not None and self.main_model.name != self.model_name:
            raise ValueError("Provided main_model does not match model_name")

        if self.map_tokens is None:
            self.map_tokens = int(self.main_model.get_repo_map_tokens())

        repo_map_args = dict(
            map_tokens=self.map_tokens,
            root=str(self.root),
            main_model=self.main_model,
            io=self.io,
            verbose=self.verbose,
            refresh=self.refresh,
        )
        repo_map_args.update(self.repo_map_kwargs)
        self.repo_map = RepoMap(**repo_map_args)

        try:
            self.git_repo = GitRepo(
                io=self.io,
                fnames=[str(self.root)],
                git_dname=str(self.root),
                subtree_only=False,
                git_commit_verify=False,
                attribute_author=False,
                attribute_committer=False,
                attribute_commit_message_author=False,
                attribute_commit_message_committer=False,
            )
        except FileNotFoundError:
            self.git_repo = None
        except Exception:
            if self.verbose:
                self.io.tool_warning("Unable to open git repository; falling back to filesystem scan.")
            self.git_repo = None

        self._repo_file_cache: Optional[List[str]] = None

    def generate_map(
        self,
        chat_files: Optional[Sequence[str]] = None,
        context: Optional[str] = None,
        mentioned_fnames: Optional[Iterable[str]] = None,
        mentioned_identifiers: Optional[Iterable[str]] = None,
        force_refresh: bool = False,
        include_files: Optional[Sequence[str]] = None,
    ) -> str:
        inputs = self._prepare_inputs(
            chat_files=chat_files,
            context=context,
            mentioned_fnames=mentioned_fnames,
            mentioned_identifiers=mentioned_identifiers,
            include_files=include_files,
        )

        return self.repo_map.get_repo_map(
            inputs.chat_files,
            inputs.other_files,
            mentioned_fnames=inputs.mentioned_files,
            mentioned_idents=inputs.mentioned_identifiers,
            force_refresh=force_refresh,
        )

    def generate_ranked_tags(
        self,
        chat_files: Optional[Sequence[str]] = None,
        context: Optional[str] = None,
        mentioned_fnames: Optional[Iterable[str]] = None,
        mentioned_identifiers: Optional[Iterable[str]] = None,
        include_files: Optional[Sequence[str]] = None,
    ):
        inputs = self._prepare_inputs(
            chat_files=chat_files,
            context=context,
            mentioned_fnames=mentioned_fnames,
            mentioned_identifiers=mentioned_identifiers,
            include_files=include_files,
        )
        return self.repo_map.get_ranked_tags(
            inputs.chat_files,
            inputs.other_files,
            inputs.mentioned_files,
            inputs.mentioned_identifiers,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_inputs(
        self,
        chat_files: Optional[Sequence[str]] = None,
        context: Optional[str] = None,
        mentioned_fnames: Optional[Iterable[str]] = None,
        mentioned_identifiers: Optional[Iterable[str]] = None,
        include_files: Optional[Sequence[str]] = None,
    ) -> RepoMapInputs:
        chat_abs = self._normalize_abs_paths(chat_files or [])
        include_abs = self._normalize_abs_paths(include_files or [])
        repo_abs_files = set(self._get_repo_abs_files())

        all_abs_files = repo_abs_files | chat_abs | include_abs
        other_files = sorted(all_abs_files - chat_abs)

        chat_rel = {self._rel_path(path) for path in chat_abs}

        mentioned_files_set: Set[str] = set()
        if mentioned_fnames:
            mentioned_files_set.update(self._normalize_relative_set(mentioned_fnames))

        identifier_mentions = set()
        if mentioned_identifiers:
            identifier_mentions.update(mentioned_identifiers)

        if context:
            identifier_mentions.update(self._extract_identifiers(context))
            mentioned_files_set.update(self._extract_file_mentions(context, chat_rel))

        mentioned_files_set.update(self._match_identifiers_to_files(identifier_mentions))

        return RepoMapInputs(
            chat_files=chat_abs,
            other_files=other_files,
            mentioned_files=mentioned_files_set,
            mentioned_identifiers=identifier_mentions,
        )

    def _normalize_abs_paths(self, paths: Sequence[str]) -> Set[str]:
        normalized: Set[str] = set()
        for value in paths:
            if value is None:
                continue
            path = Path(value)
            if not path.is_absolute():
                path = (self.root / path).resolve()
            else:
                path = path.resolve()
            if path.is_file():
                normalized.add(str(path))
        return normalized

    def _normalize_relative_set(self, values: Iterable[str]) -> Set[str]:
        normalized: Set[str] = set()
        for value in values:
            if value is None:
                continue
            candidate = Path(value)
            if candidate.is_absolute():
                try:
                    rel_value = candidate.resolve().relative_to(self.root)
                    normalized.add(rel_value.as_posix())
                    continue
                except ValueError:
                    normalized.add(candidate.resolve().as_posix())
                    continue
            normalized.add(str(candidate).replace("\\", "/"))
        return normalized

    def _rel_path(self, path: str) -> str:
        try:
            return Path(path).resolve().relative_to(self.root).as_posix()
        except ValueError:
            return Path(path).resolve().as_posix()

    def _get_repo_abs_files(self) -> List[str]:
        if self._repo_file_cache is not None:
            return list(self._repo_file_cache)

        rel_paths: List[str]
        if self.git_repo and self.git_repo.repo:
            rel_paths = list(self.git_repo.get_tracked_files())
        else:
            rel_paths = []
            for path in self.root.rglob("*"):
                if path.is_file():
                    try:
                        rel_paths.append(path.relative_to(self.root).as_posix())
                    except ValueError:
                        continue

        abs_paths = sorted({str((self.root / rel).resolve()) for rel in rel_paths})
        self._repo_file_cache = abs_paths
        return list(abs_paths)

    def _extract_identifiers(self, text: str) -> Set[str]:
        identifiers = set(re.split(r"\W+", text))
        return {ident for ident in identifiers if ident}

    def _extract_file_mentions(self, text: str, existing_chat_rel: Set[str]) -> Set[str]:
        words = {word.rstrip(",.!;:?") for word in text.split()}
        quotes = "\"'`*_"
        words = {word.strip(quotes) for word in words if word}
        normalized_words = {word.replace("\\", "/") for word in words if word}

        repo_rel_files = {self._rel_path(abs_path) for abs_path in self._get_repo_abs_files()}
        mentioned: Set[str] = set()

        for rel in repo_rel_files:
            normalized_rel = rel.replace("\\", "/")
            if normalized_rel in normalized_words:
                mentioned.add(rel)

        fname_to_rel: dict[str, List[str]] = {}
        for rel in repo_rel_files:
            fname = os.path.basename(rel)
            if "/" in fname or "\\" in fname or "." in fname or "_" in fname or "-" in fname:
                fname_to_rel.setdefault(fname, []).append(rel)

        existing_basenames = {os.path.basename(rel) for rel in existing_chat_rel}

        for fname, rels in fname_to_rel.items():
            if fname in existing_basenames:
                continue
            if fname in normalized_words and len(rels) == 1:
                mentioned.add(rels[0])

        return mentioned

    def _match_identifiers_to_files(self, identifiers: Set[str]) -> Set[str]:
        if not identifiers:
            return set()

        repo_rel_files = {self._rel_path(abs_path) for abs_path in self._get_repo_abs_files()}
        basename_map: dict[str, Set[str]] = {}
        for rel in repo_rel_files:
            stem = Path(rel).stem.lower()
            if len(stem) < 5:
                continue
            basename_map.setdefault(stem, set()).add(rel)

        matches = set()
        for ident in identifiers:
            if len(ident) < 5:
                continue
            matches.update(basename_map.get(ident.lower(), set()))

        return matches


def build_repo_map(
    root: Path | str | None = None,
    chat_files: Optional[Sequence[str]] = None,
    context: Optional[str] = None,
    mentioned_fnames: Optional[Iterable[str]] = None,
    mentioned_identifiers: Optional[Iterable[str]] = None,
    model_name: Optional[str] = None,
    map_tokens: Optional[int] = None,
    refresh: str = "auto",
    include_files: Optional[Sequence[str]] = None,
    force_refresh: bool = False,
    verbose: bool = False,
) -> str:
    """Convenience wrapper to return the rendered repository map in one call."""

    builder = RepoMapBuilder(
        root=root,
        model_name=model_name,
        map_tokens=map_tokens,
        refresh=refresh,
        verbose=verbose,
    )
    return builder.generate_map(
        chat_files=chat_files,
        context=context,
        mentioned_fnames=mentioned_fnames,
        mentioned_identifiers=mentioned_identifiers,
        force_refresh=force_refresh,
        include_files=include_files,
    )
