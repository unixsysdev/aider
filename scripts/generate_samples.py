#!/usr/bin/env python3
"""Regenerate the sample repo map captures stored under ``samples/``.

The helper runs the same commands showcased in the README so the published
artifacts always match the current repository state.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_COMMANDS = {
    "repomap_self_full.txt": [
        "python",
        "-m",
        "repomap_tool.cli",
        "--root",
        ".",
        "--refresh",
        "always",
        "--map-tokens",
        "800",
    ],
    "repomap_self_context.txt": [
        "python",
        "-m",
        "repomap_tool.cli",
        "--root",
        ".",
        "--refresh",
        "files",
        "--map-tokens",
        "600",
        "--context",
        "Document repo map usage in README",
    ],
    "repomap_self_readme.txt": [
        "python",
        "-m",
        "repomap_tool.cli",
        "--root",
        ".",
        "--refresh",
        "files",
        "--map-tokens",
        "600",
        "--chat-file",
        "README.md",
    ],
}


def capture(
    dest: Path,
    command: Sequence[str],
    *,
    cwd: Path,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Execute ``command`` and write its stdout to ``dest``."""
    display_cmd = " ".join(command)
    prefix = "DRY-RUN" if dry_run else "RUN"
    print(f"[{prefix}] {display_cmd} -> {dest.relative_to(cwd.parent)}")
    if dry_run:
        return

    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    if verbose and result.stderr:
        print(result.stderr)
    dest.write_text(result.stdout)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to analyse (defaults to the project root).",
    )
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=None,
        help="Directory to store the captured outputs (defaults to <root>/samples).",
    )
    parser.add_argument(
        "--only",
        choices=sorted(DEFAULT_COMMANDS),
        action="append",
        help="Limit generation to specific sample names.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the commands that would run without executing them.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print stderr emitted by the commands.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    samples_dir = (
        args.samples_dir.resolve()
        if args.samples_dir is not None
        else root / "samples"
    )
    samples_dir.mkdir(parents=True, exist_ok=True)

    selected = args.only or sorted(DEFAULT_COMMANDS)
    for name in selected:
        command = DEFAULT_COMMANDS[name]
        capture(
            samples_dir / name,
            command,
            cwd=root,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
