"""Expose :mod:`repomap_tool` as an MCP server."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Annotated, Iterable, Literal, Sequence

import anyio
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field
from mcp.types import ToolAnnotations

from ..service import RepoMapBuilder

RefreshMode = Literal["auto", "always", "files", "manual"]

_DEFAULT_ROOT: Path | None = None
_LOG_LEVELS: tuple[str, ...] = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")


# Guidance surfaced through ToolAnnotations to enrich MCP metadata presented to LLMs.
_SHARED_PARAMETER_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "root": {
        "summary": "Repository root directory.",
        "details": (
            "Absolute or relative path pointing at the repository to analyse."
            " Defaults to the server's configured root or the current working"
            " directory when omitted."
        ),
        "tips": "Set this when the conversation spans multiple repositories or sandboxes.",
    },
    "chat_files": {
        "summary": "Files already surfaced in the chat.",
        "details": (
            "Repository-relative paths that have appeared in the conversation."
            " The ranking engine boosts nearby files to extend the current thread."
        ),
        "tips": "Provide when follow-up questions refer to code previously pasted in the chat.",
    },
    "context": {
        "summary": "Inline natural-language context.",
        "details": (
            "Problem statements, stack traces, or user goals that should shape"
            " the generated map."
        ),
        "tips": "Keep concise but descriptive; long context can dilute the most relevant signals.",
    },
    "context_files": {
        "summary": "Paths to additional context files.",
        "details": (
            "Each file is read, concatenated, and fed to the ranking engine as"
            " supplementary context."
        ),
        "tips": "Useful for design docs or test logs that live alongside the code base.",
    },
    "mentioned_files": {
        "summary": "Explicitly referenced files.",
        "details": (
            "Repository-relative paths to emphasise. Files listed here receive"
            " a strong priority boost regardless of other signals."
        ),
        "tips": "Add files the user asked about even if they have not appeared in chat yet.",
    },
    "mentioned_identifiers": {
        "summary": "Important identifiers to prioritise.",
        "details": (
            "Fully qualified function, class, or constant names that should rank"
            " highly when present in the repository."
        ),
        "tips": "Match the repository's import style (for example `pkg.module.symbol`).",
    },
    "include_files": {
        "summary": "Restrict search scope with globs.",
        "details": (
            "List of repository-relative files or glob patterns that limit analysis"
            " to specific areas (for example `src/app/**`)."
        ),
        "tips": "Use when the task targets a subsystem and broader context would be noisy.",
    },
    "map_tokens": {
        "summary": "Token budget hint for the resulting map.",
        "details": (
            "Soft maximum number of tokens the map should consume. Helps balance"
            " breadth versus depth."
        ),
        "tips": "Lower the value when downstream prompts have strict token limits.",
    },
    "refresh": {
        "summary": "Cache refresh strategy.",
        "details": (
            "Choose between 'auto', 'always', 'files', or 'manual' to control"
            " how cached repository analysis is reused."
        ),
        "tips": "Use 'always' after large refactors; prefer 'files' when only a few files changed.",
    },
    "model_name": {
        "summary": "Preferred LLM profile for token heuristics.",
        "details": (
            "Adjusts token estimation for repositories tuned to a specific model"
            " (for example `gpt-4.1-mini`)."
        ),
        "tips": "Only set if the deployment's token accounting deviates from the default assumptions.",
    },
    "verbose": {
        "summary": "Toggle verbose diagnostic logging.",
        "details": "Enables additional logging in the MCP server for troubleshooting.",
        "tips": "Use sparingly; verbose logs can overwhelm limited transports like stdio.",
    },
}

_REPO_MAP_PARAMETER_DESCRIPTIONS: dict[str, dict[str, str]] = {
    **_SHARED_PARAMETER_DESCRIPTIONS,
    "force_refresh": {
        "summary": "Bypass cached analysis.",
        "details": "Force a rebuild of the repository map even if cached data appears fresh.",
        "tips": "Set to true after major dependency or configuration changes.",
    },
}

_RANKED_TAG_PARAMETER_DESCRIPTIONS: dict[str, dict[str, str]] = {
    **_SHARED_PARAMETER_DESCRIPTIONS,
    "limit": {
        "summary": "Maximum number of ranked entries to return.",
        "details": (
            "Truncate the ranked tag list to this many items. Useful for previews"
            " or when only the highest scoring symbols are needed."
        ),
        "tips": "Leave unset to receive the full ranking for downstream processing.",
    },
}


class RankedTag(BaseModel):
    """Structured representation of a ranked tag entry."""

    file: str = Field(description="Repository-relative path to the symbol's file.")
    absolute_file: str | None = Field(
        default=None, description="Absolute path to the symbol's file."
    )
    line: int | None = Field(
        default=None, description="Line number where the symbol occurs."
    )
    name: str | None = Field(
        default=None, description="Identifier that was ranked."
    )
    kind: str | None = Field(
        default=None, description="Symbol type emitted by the repo map engine."
    )


def _normalise_log_level(value: str | None) -> str:
    if value is None:
        return "INFO"

    candidate = value.upper()
    if candidate not in _LOG_LEVELS:
        raise ValueError(f"Invalid log level: {value}")
    return candidate


def _set_default_root(root: Path | None) -> None:
    global _DEFAULT_ROOT
    _DEFAULT_ROOT = root


def _resolve_root(root: str | Path | None) -> Path:
    if root is None:
        if _DEFAULT_ROOT is not None:
            candidate = _DEFAULT_ROOT
        else:
            candidate = Path.cwd()
    else:
        candidate = Path(root).expanduser() if not isinstance(root, Path) else root

    try:
        resolved = candidate.resolve()
    except FileNotFoundError as exc:  # pragma: no cover - mirrors pathlib behaviour
        raise ValueError(f"Repository root does not exist: {candidate}") from exc

    if not resolved.exists():
        raise ValueError(f"Repository root does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Repository root must be a directory: {resolved}")
    return resolved


def _normalise_refresh(value: str | None) -> RefreshMode:
    if value is None:
        return "auto"

    valid_modes: tuple[RefreshMode, ...] = ("auto", "always", "files", "manual")
    if value not in valid_modes:
        raise ValueError(f"Invalid refresh mode: {value}")
    return value  # type: ignore[return-value]


def _gather_context(
    inline_context: str | None,
    context_files: Sequence[str] | None,
    root: Path,
    ctx: Context | None,
) -> str | None:
    segments: list[str] = []

    if inline_context:
        segments.append(inline_context)

    for fname in context_files or []:
        file_path = Path(fname)
        if not file_path.is_absolute():
            file_path = (root / file_path).resolve()
        else:
            file_path = file_path.resolve()

        try:
            segments.append(file_path.read_text(encoding="utf-8"))
        except OSError as exc:
            message = f"Unable to read context file {file_path}: {exc}"
            if ctx is not None:
                ctx.warning(message)
                continue
            raise ValueError(message) from exc

    combined = "\n".join(segment for segment in segments if segment)
    return combined or None


def _create_builder(
    root: Path,
    map_tokens: int | None,
    refresh: RefreshMode,
    verbose: bool,
    model_name: str | None,
) -> RepoMapBuilder:
    return RepoMapBuilder(
        root=root,
        map_tokens=map_tokens,
        refresh=refresh,
        verbose=verbose,
        model_name=model_name,
    )


def generate_repo_map_tool(
    *,
    root: Annotated[
        str | None,
        Field(
            description=(
                "Absolute or relative path to the repository root. Defaults to the "
                "server's configured root or the current working directory."
            )
        ),
    ] = None,
    chat_files: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Paths to files already surfaced in the conversation. Helps the map "
                "builder prioritise nearby files."
            )
        ),
    ] = None,
    context: Annotated[
        str | None,
        Field(
            description=(
                "Inline context that should influence ranking (for example a problem "
                "statement or error message)."
            )
        ),
    ] = None,
    context_files: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Paths to files whose contents should be concatenated and supplied as "
                "additional context."
            )
        ),
    ] = None,
    mentioned_files: Annotated[
        Sequence[str] | None,
        Field(
            description="Explicitly referenced file paths that warrant higher priority."
        ),
    ] = None,
    mentioned_identifiers: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Fully-qualified identifiers that should be emphasised when building "
                "the map."
            )
        ),
    ] = None,
    include_files: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Restrict the map to these repository-relative paths. Supports glob "
                "patterns."
            )
        ),
    ] = None,
    map_tokens: Annotated[
        int | None,
        Field(
            ge=0,
            description=(
                "Soft cap on the number of tokens that should be allocated to the "
                "resulting map."
            ),
        ),
    ] = None,
    refresh: Annotated[
        str | None,
        Field(
            description=(
                "Cache refresh strategy. Accepts 'auto', 'always', 'files', or 'manual'."
            )
        ),
    ] = None,
    force_refresh: Annotated[
        bool,
        Field(
            description=(
                "Skip cached data and rebuild the map even if it appears up to date."
            )
        ),
    ] = False,
    model_name: Annotated[
        str | None,
        Field(
            description=(
                "Preferred LLM profile to use when estimating token budgets for the map."
            )
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Field(description="Emit verbose logging to aid troubleshooting."),
    ] = False,
    ctx: Context | None = None,
) -> str:
    """Generate a focused repository map for the requesting model.

    This tool mirrors the behaviour of the ``repomap-tool`` CLI. Provide a repository
    ``root`` and optional signals (chat history references, inline context, or
    explicit mentions) to guide the ranking engine. The response is a string that is
    ready to inject into a prompt without additional formatting.

    Example call::

        generate_repo_map(
            root="/workspace/project",
            chat_files=["src/app.py"],
            context="Investigating failing login tests",
            mentioned_identifiers=["auth.login"],
        )

    Returns:
        str: A condensed, human-readable repository map covering the most relevant
        files and symbols.
    """

    root_path = _resolve_root(root)
    builder = _create_builder(root_path, map_tokens, _normalise_refresh(refresh), verbose, model_name)
    gathered_context = _gather_context(context, context_files, root_path, ctx)

    repo_map = builder.generate_map(
        chat_files=list(chat_files or []),
        context=gathered_context,
        mentioned_fnames=list(mentioned_files or []),
        mentioned_identifiers=list(mentioned_identifiers or []),
        force_refresh=force_refresh,
        include_files=list(include_files or []),
    )

    if not repo_map:
        raise ValueError("No repository map could be generated for the requested repository.")

    return repo_map


def generate_ranked_tags_tool(
    *,
    root: Annotated[
        str | None,
        Field(
            description=(
                "Absolute or relative path to the repository root. Defaults to the "
                "server's configured root or the current working directory."
            )
        ),
    ] = None,
    chat_files: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Paths to files already surfaced in the conversation. Helps the tag "
                "ranker emphasise nearby files."
            )
        ),
    ] = None,
    context: Annotated[
        str | None,
        Field(
            description=(
                "Inline context that should influence scoring (for example a problem "
                "statement or error message)."
            )
        ),
    ] = None,
    context_files: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Paths to files whose contents should be concatenated and supplied as "
                "additional context."
            )
        ),
    ] = None,
    mentioned_files: Annotated[
        Sequence[str] | None,
        Field(description="Explicitly referenced file paths that warrant higher priority."),
    ] = None,
    mentioned_identifiers: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Fully-qualified identifiers that should be emphasised when ranking "
                "symbols."
            )
        ),
    ] = None,
    include_files: Annotated[
        Sequence[str] | None,
        Field(
            description=(
                "Restrict the ranking to these repository-relative paths. Supports glob "
                "patterns."
            )
        ),
    ] = None,
    map_tokens: Annotated[
        int | None,
        Field(
            ge=0,
            description=(
                "Soft cap on the number of tokens that should be allocated to the map "
                "produced from these tags."
            ),
        ),
    ] = None,
    refresh: Annotated[
        str | None,
        Field(
            description=(
                "Cache refresh strategy. Accepts 'auto', 'always', 'files', or 'manual'."
            )
        ),
    ] = None,
    model_name: Annotated[
        str | None,
        Field(
            description=(
                "Preferred LLM profile to use when estimating token budgets for the map."
            )
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Field(description="Emit verbose logging to aid troubleshooting."),
    ] = False,
    limit: Annotated[
        int | None,
        Field(
            ge=0,
            description=(
                "Optional maximum number of ranked entries to return. Useful for "
                "previews when the client only needs the highest scoring tags."
            ),
        ),
    ] = None,
    ctx: Context | None = None,
) -> list[RankedTag]:
    """Return structured ranked tags for advanced control over the repo map.

    Call this tool when you need machine-readable details (file paths, symbol names,
    and line numbers) describing the ranking that underpins ``generate_repo_map``.
    The parameters mirror the map generator so that both tools can be driven with the
    same signals.

    Example call::

        generate_ranked_tags(
            root="/workspace/project",
            mentioned_files=["src/auth.py"],
            limit=5,
        )

    Returns:
        list[RankedTag]: Each entry contains repository-relative and absolute file
        paths along with optional identifier metadata if it was available.
    """

    if limit is not None and limit < 0:
        raise ValueError("limit must be greater than or equal to zero")

    root_path = _resolve_root(root)
    builder = _create_builder(root_path, map_tokens, _normalise_refresh(refresh), verbose, model_name)
    gathered_context = _gather_context(context, context_files, root_path, ctx)

    tags = builder.generate_ranked_tags(
        chat_files=list(chat_files or []),
        context=gathered_context,
        mentioned_fnames=list(mentioned_files or []),
        mentioned_identifiers=list(mentioned_identifiers or []),
        include_files=list(include_files or []),
    )

    if limit is not None:
        tags = tags[:limit]

    serialised: list[RankedTag] = []
    for tag in tags:
        if hasattr(tag, "rel_fname"):
            serialised.append(
                RankedTag(
                    file=tag.rel_fname,
                    absolute_file=tag.fname,
                    line=tag.line,
                    name=tag.name,
                    kind=tag.kind,
                )
            )
            continue

        if isinstance(tag, Sequence) and not isinstance(tag, (str, bytes)) and tag:
            rel_fname = str(tag[0])
            file_path = Path(rel_fname)
            if not file_path.is_absolute():
                file_path = (builder.root / file_path).resolve()
            serialised.append(
                RankedTag(
                    file=rel_fname,
                    absolute_file=str(file_path),
                )
            )
            continue

        if ctx is not None:
            ctx.warning(
                "Encountered an unexpected ranked tag entry; omitting from response."
            )

    return serialised


def register_tools(server: FastMCP) -> FastMCP:
    """Attach repo map tools to *server* and return it."""

    server.tool(
        name="generate_repo_map",
        title="Generate repository map",
        description=(
            "Build a condensed repository map for the supplied project. Provide the "
            "repository root plus optional chat or context signals to focus the "
            "result on the current task."
        ),
        annotations=ToolAnnotations(
            title="Generate repository map",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
            callGuidance=(
                "Use when you need a ready-to-share textual overview of the current"
                " repository. Supply chat and context signals to steer the ranking"
                " toward the active issue, and prefer the ranked-tag tool if you"
                " require machine-readable symbol metadata."
            ),
            usageExamples=[
                {
                    "description": "Map the current repository using chat history",
                    "arguments": {
                        "chat_files": ["src/app.py"],
                        "context": "Investigating login failures",
                    },
                },
                {
                    "description": "Focus on a specific module",
                    "arguments": {
                        "mentioned_files": ["src/auth/login.py"],
                        "include_files": ["src/auth/**"],
                    },
                },
            ],
            parameterDescriptions=_REPO_MAP_PARAMETER_DESCRIPTIONS,
        ),
    )(generate_repo_map_tool)

    server.tool(
        name="generate_ranked_tags",
        title="Inspect ranked tags",
        description=(
            "Return the ranked identifiers used to construct the repository map. Use "
            "this when you need structured metadata like file paths, symbol names, "
            "and line numbers."
        ),
        annotations=ToolAnnotations(
            title="Inspect ranked tags",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
            callGuidance=(
                "Choose this tool when you need structured data about the ranked"
                " symbols behind the repository map, such as file paths, line"
                " numbers, or to drive custom visualisations. For a conversational"
                " overview, prefer 'generate_repo_map'."
            ),
            usageExamples=[
                {
                    "description": "Preview the top ranked symbols",
                    "arguments": {"limit": 5},
                },
                {
                    "description": "Filter rankings to files mentioned in the chat",
                    "arguments": {
                        "chat_files": ["src/api/routes.py"],
                        "mentioned_identifiers": ["api.routes.handle_request"],
                    },
                },
            ],
            parameterDescriptions=_RANKED_TAG_PARAMETER_DESCRIPTIONS,
        ),
        structured_output=True,
    )(generate_ranked_tags_tool)

    return server


def create_server(
    *,
    default_root: str | Path | None = None,
    log_level: str | None = None,
    **kwargs,
) -> FastMCP:
    """Create a :class:`FastMCP` server with the repo map tools registered."""

    if default_root is not None:
        resolved = _resolve_root(default_root)
    else:
        resolved = None
    _set_default_root(resolved)

    server = FastMCP(
        name="repomap-tool",
        instructions=(
            "Use repomap-tool to generate repository maps or inspect the ranked tags "
            "behind them. Call 'generate_repo_map' when you want a ready-to-share "
            "map string; call 'generate_ranked_tags' when you need structured "
            "metadata for downstream processing. Supply a repository root when "
            "working outside the default, and pass chat, context, or mention "
            "signals to focus the ranking on the current task."
        ),
        website_url="https://github.com/unixsysdev/repomap",
        log_level=_normalise_log_level(log_level),
        **kwargs,
    )
    return register_tools(server)


app = create_server()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Expose repomap-tool as a Model Context Protocol server.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport mechanism to use when serving the MCP tools.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host interface for SSE or HTTP transports (defaults to 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number for SSE or HTTP transports (defaults to 8000).",
    )
    parser.add_argument(
        "--mount-path",
        default=None,
        help="Optional mount path for the SSE transport (defaults to the configured mount path).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help=(
            "Repository root to use when tool requests omit the root parameter "
            "(defaults to the current working directory)."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        type=_normalise_log_level,
        choices=_LOG_LEVELS,
        help="Log level for MCP diagnostics (defaults to INFO).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable FastMCP debug mode (implies additional logging).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    server_kwargs = {}
    if args.host is not None:
        server_kwargs["host"] = args.host
    if args.port is not None:
        server_kwargs["port"] = args.port

    try:
        default_root = _resolve_root(args.root) if args.root is not None else None
    except ValueError as exc:
        parser.error(str(exc))

    server = create_server(
        default_root=default_root,
        log_level=args.log_level,
        debug=args.debug,
        **server_kwargs,
    )

    if args.transport == "stdio":
        message = "repomap-mcp awaiting MCP client handshake on stdio"
    elif args.transport == "sse":
        mount_path = args.mount_path or server.settings.mount_path
        message = (
            "repomap-mcp serving SSE transport at "
            f"http://{server.settings.host}:{server.settings.port}{mount_path}"
        )
    else:
        message = (
            "repomap-mcp serving streamable HTTP transport at "
            f"http://{server.settings.host}:{server.settings.port}{server.settings.streamable_http_path}"
        )
    if default_root is not None:
        message = f"{message} (default repository root: {default_root})"
    print(message, file=sys.stderr, flush=True)

    try:
        if args.transport == "stdio":
            anyio.run(server.run_stdio_async)
        elif args.transport == "sse":
            anyio.run(server.run_sse_async, args.mount_path)
        else:
            anyio.run(server.run_streamable_http_async)
    except KeyboardInterrupt:
        print("repomap-mcp interrupted by user", file=sys.stderr, flush=True)
        return 130

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

