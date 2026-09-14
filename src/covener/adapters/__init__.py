"""Tool-specific adapters.

The canonical agent definitions live in ``agents/``. Adapters project them into the
locations and dialects each IDE reads. They never become the source of truth.
"""

from __future__ import annotations

from .base import Adapter, AdapterResult
from .claude import ClaudeAdapter
from .cursor import CursorAdapter

ADAPTERS: dict[str, type[Adapter]] = {
    ClaudeAdapter.key: ClaudeAdapter,
    CursorAdapter.key: CursorAdapter,
}


def get_adapter(key: str) -> Adapter:
    try:
        return ADAPTERS[key]()
    except KeyError as exc:
        raise ValueError(f"unknown tool adapter {key!r}; known: {', '.join(ADAPTERS)}") from exc


__all__ = ["ADAPTERS", "Adapter", "AdapterResult", "ClaudeAdapter", "CursorAdapter", "get_adapter"]
