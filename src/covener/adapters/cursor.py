"""Cursor adapter.

Cursor reads ``AGENTS.md`` from the project root natively, so no rule file is needed for the
shared instructions. Cursor subagents live in ``.cursor/agents/*.md`` (Markdown + YAML front
matter with ``name``, ``description``, ``model``); ``.cursor/agents`` is a symlink to ``agents/``.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from .base import Adapter, AdapterResult


class CursorAdapter(Adapter):
    key = "cursor"
    title = "Cursor"

    def agents_dir(self, root: Path) -> Path:
        return root / ".cursor" / "agents"

    def skills_dir(self, root: Path) -> Path:
        return root / ".cursor" / "skills"

    def detect(self, root: Path) -> bool:
        return (root / ".cursor").is_dir() or (root / ".cursorrules").is_file()

    def install(self, root: Path, config: Config, dry_run: bool = False) -> AdapterResult:
        result = self.link_all(root, config, dry_run=dry_run)
        if (root / ".cursorrules").is_file():
            result.notes.append(
                "A legacy .cursorrules file exists. Cursor also reads AGENTS.md; consider moving "
                "project rules to .cursor/rules/*.mdc or AGENTS.md so there is one source of truth."
            )
        return result
