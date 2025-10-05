"""Command line tool for generating repository maps and ranked tags."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .service import RepoMapBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a repository map and ranked tags identical to the chat workflow.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (defaults to current working directory).",
    )
    parser.add_argument(
        "--map-tokens",
        type=int,
        default=None,
        help="Override the token budget for the repo map.",
    )
    parser.add_argument(
        "--refresh",
        choices=["auto", "always", "files", "manual"],
        default="auto",
        help="Choose the refresh strategy for cached repository maps.",
    )
    parser.add_argument(
        "--chat-file",
        dest="chat_files",
        action="append",
        default=None,
        help="File to treat as already in the chat (can be repeated).",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=None,
        help="Inline context string that should influence file ranking (can be repeated).",
    )
    parser.add_argument(
        "--context-file",
        action="append",
        default=None,
        help="Read additional context from file(s).",
    )
    parser.add_argument(
        "--mention",
        action="append",
        dest="mentions",
        default=None,
        help="Explicitly mention a repository path (relative or absolute).",
    )
    parser.add_argument(
        "--ident",
        action="append",
        dest="identifiers",
        default=None,
        help="Treat an identifier as mentioned when ranking files (can be repeated).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass cached repo maps.",
    )
    parser.add_argument(
        "--include",
        action="append",
        dest="include_files",
        default=None,
        help="Extra files to consider even if they are untracked.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print diagnostic information while building the map.",
    )
    return parser


def _gather_context_strings(args) -> str:
    segments: List[str] = []
    if args.context:
        segments.extend(args.context)
    if args.context_file:
        for fname in args.context_file:
            try:
                segments.append(Path(fname).read_text())
            except OSError as exc:
                print(f"Unable to read context file {fname}: {exc}", file=sys.stderr)
    return "\n".join(segments) if segments else ""


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    service = RepoMapBuilder(
        root=args.root,
        map_tokens=args.map_tokens,
        refresh=args.refresh,
        verbose=args.verbose,
    )

    context = _gather_context_strings(args)
    context_value = context or None

    repo_map = service.generate_map(
        chat_files=args.chat_files,
        context=context_value,
        mentioned_fnames=args.mentions,
        mentioned_identifiers=args.identifiers,
        force_refresh=args.force_refresh,
        include_files=args.include_files,
    )

    if repo_map:
        print(repo_map)
        return 0
    print("No repository map could be generated.", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
