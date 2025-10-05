"""Minimal Git repository helper used by the repo map toolkit."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Iterable, List, Optional

try:
    import git

    ANY_GIT_ERROR = (
        git.exc.ODBError,
        git.exc.GitError,
        git.exc.InvalidGitRepositoryError,
        git.exc.GitCommandNotFound,
    )
except ImportError:  # pragma: no cover - GitPython is an install dependency.
    git = None
    ANY_GIT_ERROR = ()

from .utils import safe_abs_path


class GitRepo:
    """Lightweight wrapper that exposes the bits of GitPython used by repo maps."""

    def __init__(
        self,
        io,
        fnames: Optional[Iterable[str]] = None,
        git_dname: Optional[str] = None,
        subtree_only: bool = False,
        git_commit_verify: bool = True,  # noqa: ARG002 - kept for API compatibility
        **_: object,
    ) -> None:
        if git is None:
            raise RuntimeError("GitPython is required to use GitRepo")

        self.io = io
        self.subtree_only = subtree_only

        if git_dname:
            candidates = [git_dname]
        elif fnames:
            candidates = list(fnames)
        else:
            candidates = ["."]

        repo_paths: List[str] = []
        for fname in candidates:
            path = Path(fname).resolve()
            if not path.exists() and path.parent.exists():
                path = path.parent
            try:
                repo = git.Repo(path, search_parent_directories=True)
                repo_paths.append(safe_abs_path(repo.working_dir))
            except ANY_GIT_ERROR:
                continue

        unique_paths = sorted(set(repo_paths))
        if not unique_paths:
            raise FileNotFoundError("Unable to locate a git repository from the provided paths")
        if len(unique_paths) > 1:
            self.io.tool_error("Files are in different git repositories.")
            raise FileNotFoundError("Multiple git repositories detected")

        self.repo = git.Repo(unique_paths[0], odbt=git.GitDB)
        self.root = safe_abs_path(self.repo.working_tree_dir)

        self._tree_cache: dict = {}

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def get_tracked_files(self) -> List[str]:
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            commit = None
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to list files in git repo: {err}")
            return []

        files = set()
        if commit:
            cached = self._tree_cache.get(commit)
            if cached is None:
                discovered = set()
                try:
                    for blob in commit.tree.traverse():
                        if getattr(blob, "type", None) == "blob":
                            discovered.add(blob.path)
                except ANY_GIT_ERROR as err:
                    self.io.tool_error(f"Unable to traverse git tree: {err}")
                    return []
                cached = {self._normalize_path(path) for path in discovered}
                self._tree_cache[commit] = cached
            files.update(cached)

        try:
            staged = {path for path, _ in self.repo.index.entries.keys()}
            files.update(self._normalize_path(path) for path in staged)
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to read staged files: {err}")

        return sorted(files)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_path(self, path: str) -> str:
        rel = Path(PurePosixPath((Path(self.root) / path).relative_to(self.root)))
        return rel.as_posix()


__all__ = ["GitRepo"]

