"""Expose :mod:`repomap_tool` as an MCP server."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Literal, Sequence

import asyncio
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from ..service import RepoMapBuilder

RefreshMode = Literal["auto", "always", "files", "manual"]


class RankedTag(BaseModel):
    """Structured representation of a ranked tag entry."""

    file: str = Field(description="Repository-relative path to the symbol's file.")
    absolute_file: str = Field(description="Absolute path to the symbol's file.")
    line: int = Field(description="Line number where the symbol occurs.")
    name: str = Field(description="Identifier that was ranked.")
    kind: str = Field(description="Symbol type emitted by the repo map engine.")


def _resolve_root(root: str | None) -> Path:
    candidate = Path(root).expanduser() if root else Path.cwd()
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
    root: str | None = None,
    chat_files: Sequence[str] | None = None,
    context: str | None = None,
    context_files: Sequence[str] | None = None,
    mentioned_files: Sequence[str] | None = None,
    mentioned_identifiers: Sequence[str] | None = None,
    include_files: Sequence[str] | None = None,
    map_tokens: int | None = None,
    refresh: str | None = None,
    force_refresh: bool = False,
    model_name: str | None = None,
    verbose: bool = False,
    ctx: Context | None = None,
) -> str:
    """Generate a repository map identical to the aider workflow."""

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
    root: str | None = None,
    chat_files: Sequence[str] | None = None,
    context: str | None = None,
    context_files: Sequence[str] | None = None,
    mentioned_files: Sequence[str] | None = None,
    mentioned_identifiers: Sequence[str] | None = None,
    include_files: Sequence[str] | None = None,
    map_tokens: int | None = None,
    refresh: str | None = None,
    model_name: str | None = None,
    verbose: bool = False,
    limit: int | None = None,
    ctx: Context | None = None,
) -> list[RankedTag]:
    """Return the ranked tags that power the repo map."""

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

    return [
        RankedTag(
            file=tag.rel_fname,
            absolute_file=tag.fname,
            line=tag.line,
            name=tag.name,
            kind=tag.kind,
        )
        for tag in tags
    ]


def register_tools(server: FastMCP) -> FastMCP:
    """Attach repo map tools to *server* and return it."""

    server.tool(
        name="generate_repo_map",
        description="Build a condensed repository map for the supplied project.",
    )(generate_repo_map_tool)

    server.tool(
        name="generate_ranked_tags",
        description="Return the ranked identifiers used to construct the repository map.",
        structured_output=True,
    )(generate_ranked_tags_tool)

    return server


def create_server(**kwargs) -> FastMCP:
    """Create a :class:`FastMCP` server with the repo map tools registered."""

    server = FastMCP(
        name="repomap-tool",
        instructions=(
            "Generate repository maps and ranked tags using repomap-tool. "
            "Pass chat files, inline context, or explicit mentions to focus the output."
        ),
        website_url="https://github.com/unixsysdev/repomap",
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
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    server_kwargs = {}
    if args.host is not None:
        server_kwargs["host"] = args.host
    if args.port is not None:
        server_kwargs["port"] = args.port

    server = create_server(**server_kwargs)

    if args.transport == "stdio":
        asyncio.run(server.run_stdio_async())
    elif args.transport == "sse":
        asyncio.run(server.run_sse_async(args.mount_path))
    else:
        asyncio.run(server.run_streamable_http_async())

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

