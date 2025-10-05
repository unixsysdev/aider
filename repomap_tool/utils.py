"""Utility helpers for the standalone repository map toolkit."""

from __future__ import annotations

from pathlib import Path


def safe_abs_path(path: str | Path) -> str:
    """Return a resolved absolute path using the platform's native separators."""

    return str(Path(path).resolve())


__all__ = ["safe_abs_path"]

