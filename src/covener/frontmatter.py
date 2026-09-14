"""Minimal, deterministic YAML front matter reader/writer.

Front matter is the block between an opening ``---`` on the very first line and the
next ``---`` line. Everything after it is the body. This mirrors what Claude Code,
Cursor and the AGENTS.md ecosystem expect from agent and rule files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


class FrontMatterError(ValueError):
    """Raised when a front matter block cannot be parsed."""


@dataclass
class Document:
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    has_front_matter: bool = False


def parse(text: str) -> Document:
    """Parse ``text`` into a :class:`Document`.

    A file without a leading ``---`` line has no front matter and is returned as body only.
    """
    if not text.startswith("---"):
        return Document(body=text)
    first_line, _, rest = text.partition("\n")
    if first_line.strip() != "---":
        return Document(body=text)
    lines = rest.split("\n")
    for index, line in enumerate(lines):
        if line.strip() == "---":
            raw = "\n".join(lines[:index])
            body = "\n".join(lines[index + 1 :])
            try:
                loaded = yaml.safe_load(raw) if raw.strip() else {}
            except yaml.YAMLError as exc:  # pragma: no cover - message formatting only
                raise FrontMatterError(f"invalid YAML front matter: {exc}") from exc
            if loaded is None:
                loaded = {}
            if not isinstance(loaded, dict):
                raise FrontMatterError("front matter must be a YAML mapping")
            return Document(meta=loaded, body=body, has_front_matter=True)
    raise FrontMatterError("unterminated front matter block (missing closing '---')")
