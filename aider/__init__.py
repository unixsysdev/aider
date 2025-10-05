"""Compatibility shims for legacy aider imports."""

from .models import Model, DEFAULT_MODEL_NAME
from .repomap import RepoMap

__all__ = ["Model", "RepoMap", "DEFAULT_MODEL_NAME"]
