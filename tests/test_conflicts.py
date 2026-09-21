"""covener init checks first: it refuses to move into a directory that belongs to something else."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import write
from covener import config
from covener.cli import main
from covener.init import ConflictError, initialize, preflight


def test_a_foreign_directory_blocks_init_and_writes_nothing(tmp_path: Path) -> None:
    write(tmp_path, "specs/openapi.yaml", "openapi: 3.1.0\n")
    write(tmp_path, "specs/payments.md", "# Payments API\n\nOur REST contract.\n")
    write(tmp_path, "tasks/build.sh", "#!/bin/sh\necho build\n")
    with pytest.raises(ConflictError) as raised:
        initialize(tmp_path, tools=["claude"])
    message = str(raised.value)
    assert "specs/ holds openapi.yaml, payments.md" in message
    assert "tasks/ holds build.sh" in message
    assert "covener init --adopt" in message
    assert sorted(p.name for p in tmp_path.iterdir()) == ["specs", "tasks"]


def test_adopt_shares_the_directories_and_keeps_their_files(tmp_path: Path) -> None:
    write(tmp_path, "specs/openapi.yaml", "openapi: 3.1.0\n")
    report = initialize(tmp_path, tools=["claude"], adopt=True)
    assert (tmp_path / "specs" / "openapi.yaml").is_file()
    assert (tmp_path / "specs" / "TEMPLATE.md").is_file()
    assert any("sharing specs/ with 1 entry" in note for note in report.notes)


def test_covener_shaped_content_is_adopted_without_asking(tmp_path: Path) -> None:
    """Their own agent, spec and skill are the shape Covener expects: no conflict, nothing lost."""
    write(tmp_path, "agents/reviewer.md", "---\nname: reviewer\ndescription: ours\n---\nOur reviewer.\n")
    write(tmp_path, "specs/billing/refunds.md", "---\ntitle: Refunds\nstatus: approved\n---\n## Objective\n")
    write(tmp_path, "skills/house-style/SKILL.md", "---\nname: house-style\ndescription: ours\n---\nOurs.\n")
    write(tmp_path, "changes/some-work/change.md", "---\ntitle: t\nstatus: open\nitems: []\n---\n")
    assert preflight(tmp_path, config.Config()) == []
    report = initialize(tmp_path, tools=["claude"])
    assert (tmp_path / "agents" / "reviewer.md").read_text().endswith("Our reviewer.\n")
    assert "agents/reviewer.md" in report.kept
    assert (tmp_path / ".claude" / "skills" / "house-style" / "SKILL.md").is_file()


def test_tool_directories_and_instructions_never_block(tmp_path: Path) -> None:
    write(tmp_path, ".claude/agents/mine.md", "---\nname: mine\ndescription: mine\n---\nMine.\n")
    write(tmp_path, ".claude/skills/mine/SKILL.md", "---\nname: mine\ndescription: mine\n---\nMine.\n")
    write(tmp_path, ".cursor/rules/style.mdc", "---\nalwaysApply: true\n---\nStyle.\n")
    write(tmp_path, "AGENTS.md", "# Ours\n\nUse pnpm.\n")
    write(tmp_path, "CLAUDE.md", "# Ours\n")
    report = initialize(tmp_path, tools=["claude", "cursor"])
    assert (tmp_path / ".claude" / "agents" / "mine.md").read_text().endswith("Mine.\n")
    assert (tmp_path / ".claude" / "skills" / "mine" / "SKILL.md").is_file()
    assert (tmp_path / "AGENTS.md").read_text().startswith("# Ours\n\nUse pnpm.\n")
    assert "AGENTS.md" in report.updated


def test_a_covener_repository_is_never_blocked(tmp_path: Path) -> None:
    initialize(tmp_path, tools=["claude"])
    write(tmp_path, "specs/openapi.yaml", "openapi: 3.1.0\n")  # added later, after init
    report = initialize(tmp_path, tools=["claude"])
    assert not report.created and not any("adopt" in note for note in report.notes)


def test_dry_run_reports_the_conflict_without_writing(tmp_path: Path) -> None:
    write(tmp_path, "changes/CHANGELOG.md", "# Changelog\n\n## 1.0.0\n")
    with pytest.raises(ConflictError, match="changes/ holds CHANGELOG.md"):
        initialize(tmp_path, tools=["claude"], dry_run=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["changes"]


def test_cli_exit_code_and_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "skills/python/requirements.txt", "flask\n")
    assert main(["-C", str(tmp_path), "init"]) == 2
    error = capsys.readouterr().err
    assert "covener init: this repository already uses directories" in error
    assert "skills/ holds python" in error
    assert main(["-C", str(tmp_path), "init", "--adopt"]) == 0
    assert (tmp_path / "skills" / "frontend" / "SKILL.md").is_file()
