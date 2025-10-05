"""Minimal model shim supplying token estimation for repo map generation."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Mapping, Sequence

DEFAULT_MODEL_NAME = "repomap-default"
DEFAULT_MAX_INPUT_TOKENS = 16_384
DEFAULT_TOKENS_PER_CHAR = 0.25


class Model:
    """Lightweight stand-in that mimics the bits the repo map expects."""

    def __init__(
        self,
        name: str = DEFAULT_MODEL_NAME,
        *,
        token_counter: Callable[[Any], int] | None = None,
        max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
        tokens_per_char: float = DEFAULT_TOKENS_PER_CHAR,
        verbose: bool = False,
    ) -> None:
        self.name = name or DEFAULT_MODEL_NAME
        self.verbose = verbose
        self._token_counter = token_counter
        self._tokens_per_char = max(tokens_per_char, 0.05)
        self._max_input_tokens = max(int(max_input_tokens), 1024)

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------
    def token_count(self, payload: Any) -> int:
        if self._token_counter is not None:
            try:
                return int(self._token_counter(payload))
            except Exception:
                # Fall back to heuristic below if the custom counter fails.
                pass

        text = self._normalise_payload(payload)
        # Cheap heuristic that mirrors the original fallback behaviour.
        estimated = int(len(text) * self._tokens_per_char)
        return max(1, estimated)

    def _normalise_payload(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            try:
                return json.dumps(list(payload))
            except TypeError:
                return "\n".join(self._normalise_payload(item) for item in payload)
        if isinstance(payload, Mapping):
            try:
                return json.dumps(payload)
            except TypeError:
                return "\n".join(f"{key}:{self._normalise_payload(value)}" for key, value in payload.items())
        if isinstance(payload, Iterable) and not isinstance(payload, (bytes, bytearray)):
            return "\n".join(self._normalise_payload(item) for item in payload)
        return str(payload)

    def get_repo_map_tokens(self) -> int:
        """Return a conservative token budget for repo map generation."""

        return max(1024, min(self._max_input_tokens // 8, 4096))


__all__ = ["DEFAULT_MODEL_NAME", "Model"]
