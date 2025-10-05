"""Subset of utilities required for the repo map tests."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import git


class _BaseTemporaryDirectory(tempfile.TemporaryDirectory):
    """Temporary directory that cleans up aggressively on exit."""

    def __init__(self, suffix: str | None = None, prefix: str | None = None, dir: str | None = None):
        super().__init__(suffix=suffix, prefix=prefix, dir=dir)

    def __enter__(self) -> str:
        return super().__enter__()

    def cleanup(self) -> None:  # pragma: no cover - exercised in tests
        try:
            super().cleanup()
        except FileNotFoundError:
            pass


class GitTemporaryDirectory(_BaseTemporaryDirectory):
    """Temporary directory that tolerates git metadata lingering around."""

    def __enter__(self) -> str:
        path = super().__enter__()
        git.Repo.init(path)
        return path

    def cleanup(self) -> None:  # pragma: no cover - exercised in tests
        try:
            super().cleanup()
        except (PermissionError, OSError):
            # Retry with onerror handler to make Windows-style permissions happy.
            shutil.rmtree(self.name, ignore_errors=True)


class IgnorantTemporaryDirectory(_BaseTemporaryDirectory):
    """Temporary directory that ignores common deletion errors."""

    def cleanup(self) -> None:  # pragma: no cover - exercised in tests
        try:
            super().cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.name, ignore_errors=True)


def safe_abs_path(path: str | Path) -> str:
    return str(Path(path).resolve())


__all__ = [
    "GitTemporaryDirectory",
    "IgnorantTemporaryDirectory",
    "safe_abs_path",
]
