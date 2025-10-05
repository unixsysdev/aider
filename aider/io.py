"""Minimal IO implementation used by the repomap tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class InputOutput:
    """Lightweight stand-in for the chat IO helper."""

    def __init__(self, verbose: bool = False, encoding: str = "utf-8") -> None:
        self.verbose = verbose
        self.encoding = encoding

    def tool_output(self, *messages: Any, log_only: bool = False, bold: bool = False) -> None:  # noqa: D401,ARG002
        if log_only:
            return
        if not self.verbose and not bold:
            return
        text = " ".join(str(msg) for msg in messages if msg is not None)
        if text:
            print(text)

    def tool_warning(self, *messages: Any) -> None:  # noqa: D401
        text = " ".join(str(msg) for msg in messages if msg is not None)
        if text:
            print(text)

    def tool_error(self, *messages: Any) -> None:  # noqa: D401
        text = " ".join(str(msg) for msg in messages if msg is not None)
        if text:
            print(text)

    def read_text(self, fname: str) -> str:
        try:
            return Path(fname).read_text(encoding=self.encoding, errors="ignore")
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            return ""


__all__ = ["InputOutput"]
