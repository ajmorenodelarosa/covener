"""Claude Code adapter.

Claude Code loads project subagents from ``.claude/agents/*.md`` (Markdown + YAML front matter
with ``name`` and ``description``) and instructions from ``CLAUDE.md``, which can import other
files with ``@path`` syntax. ``.claude/agents`` is a symlink to the project's ``agents/`` and
``CLAUDE.md`` imports ``AGENTS.md``, so there is one source of truth for both.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..config import Config
from .base import Adapter, AdapterResult

CLAUDE_IMPORT_LINE = "@AGENTS.md"
MARK_START = "<!-- covener:start -->"
MARK_END = "<!-- covener:end -->"
IMPORT_RE = re.compile(r"^\s*@(?:\./)?AGENTS\.md\s*$")


def _code_lines(lines: list[str]) -> set[int]:
    """Indices of lines inside closed ``` / ~~~ fences (an unclosed fence is not a fence)."""
    inside: set[int] = set()
    opener: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if opener is None:
                opener = index
            else:
                inside.update(range(opener, index + 1))
                opener = None
    return inside


def _has_agents_import(text: str, root: Path) -> bool:
    """True when CLAUDE.md already imports AGENTS.md (code blocks do not count)."""
    if MARK_START in text and MARK_END in text and CLAUDE_IMPORT_LINE in text:
        return True
    absolute = (root / "AGENTS.md").resolve().as_posix()
    lines = text.splitlines()
    code = _code_lines(lines)
    for index, line in enumerate(lines):
        if index in code or line.startswith("    ") or line.startswith("\t"):
            continue
        if IMPORT_RE.match(line):
            return True
        stripped = line.strip()
        if stripped.startswith("@") and Path(stripped[1:]).expanduser().as_posix() == absolute:
            return True
    return False


class ClaudeAdapter(Adapter):
    key = "claude"
    title = "Claude Code"

    def agents_dir(self, root: Path) -> Path:
        return root / ".claude" / "agents"

    def skills_dir(self, root: Path) -> Path:
        return root / ".claude" / "skills"

    def detect(self, root: Path) -> bool:
        return (root / ".claude").is_dir() or (root / "CLAUDE.md").is_file()

    def install(self, root: Path, config: Config, dry_run: bool = False) -> AdapterResult:
        result = self.link_all(root, config, dry_run=dry_run)
        claude_md = root / "CLAUDE.md"
        block = f"{MARK_START}\n{CLAUDE_IMPORT_LINE}\n{MARK_END}\n"
        if not claude_md.exists():
            content = (
                "# Claude Code instructions\n\n"
                "Project-wide instructions for every coding agent live in AGENTS.md. "
                "Claude Code imports it below; add Claude-specific notes after the import.\n\n"
                f"{block}"
            )
            if not dry_run:
                claude_md.write_text(content, encoding="utf-8")
            result.created.append("CLAUDE.md")
            result.notes.append("Created CLAUDE.md that imports AGENTS.md (Claude Code `@path` import).")
            return result
        raw = claude_md.read_bytes()
        existing = raw.decode("utf-8")
        if _has_agents_import(existing, root):
            result.unchanged.append("CLAUDE.md")
            return result
        newline = "\r\n" if b"\r\n" in raw else "\n"
        appended = existing.rstrip("\r\n") + newline * 2 + block.replace("\n", newline)
        if not dry_run:
            claude_md.write_bytes(appended.encode("utf-8"))
        result.updated.append("CLAUDE.md")
        result.notes.append(
            "Existing CLAUDE.md kept; appended an `@AGENTS.md` import block so Claude Code reads "
            "the shared instructions."
        )
        return result
