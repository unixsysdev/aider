"""Utility helpers for the standalone repository map toolkit."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import git


def safe_abs_path(path: str | Path) -> str:
    """Return a resolved absolute path using the platform's native separators."""

    return str(Path(path).resolve())


class _BaseTemporaryDirectory(tempfile.TemporaryDirectory):
    """Temporary directory that cleans up aggressively on exit."""

    def __enter__(self) -> str:  # pragma: no cover - exercised indirectly in tests
        return super().__enter__()

    def cleanup(self) -> None:  # pragma: no cover - exercised indirectly in tests
        try:
            super().cleanup()
        except FileNotFoundError:
            pass


class GitTemporaryDirectory(_BaseTemporaryDirectory):
    """Temporary directory that initialises an empty Git repository on entry."""

    def __enter__(self) -> str:  # pragma: no cover - exercised indirectly in tests
        path = super().__enter__()
        git.Repo.init(path)
        return path

    def cleanup(self) -> None:  # pragma: no cover - exercised indirectly in tests
        try:
            super().cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.name, ignore_errors=True)


class IgnorantTemporaryDirectory(_BaseTemporaryDirectory):
    """Temporary directory that swallows common deletion errors."""

    def cleanup(self) -> None:  # pragma: no cover - exercised indirectly in tests
        try:
            super().cleanup()
        except (PermissionError, OSError):
            shutil.rmtree(self.name, ignore_errors=True)


__all__ = [
    "safe_abs_path",
    "GitTemporaryDirectory",
    "IgnorantTemporaryDirectory",
]

