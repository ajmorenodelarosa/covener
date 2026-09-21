"""covener init checks first: it refuses a directory that belongs to something else."""

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
        initialize(tmp_path, tools=["claude"], dry_run=True)
    message = str(raised.value)
    assert "specs/ holds openapi.yaml, payments.md" in message
    assert "tasks/ holds build.sh" in message and "covener init --adopt" in message
    assert sorted(p.name for p in tmp_path.iterdir()) == ["specs", "tasks"]  # nothing written
    # --adopt shares the directories: their files stay, Covener's are added next to them.
    report = initialize(tmp_path, tools=["claude"], adopt=True)
    assert (tmp_path / "specs" / "openapi.yaml").is_file() and (tmp_path / "specs" / "TEMPLATE.md").is_file()
    assert any("sharing specs/ with 2 entries" in note for note in report.notes)


def test_content_shaped_like_covener_is_adopted_without_asking(tmp_path: Path) -> None:
    """Their agent, spec, change and skill are already what Covener expects: no conflict, nothing lost."""
    write(tmp_path, "agents/reviewer.md", "---\nname: reviewer\ndescription: ours\n---\nOur reviewer.\n")
    write(tmp_path, "specs/billing/refunds.md", "---\ntitle: Refunds\nstatus: approved\n---\n## Objective\n")
    write(tmp_path, "changes/some-work/change.md", "---\ntitle: t\nstatus: open\nitems: []\n---\n")
    write(tmp_path, "skills/house-style/SKILL.md", "---\nname: house-style\ndescription: ours\n---\nOurs.\n")
    assert preflight(tmp_path, config.Config()) == []
    report = initialize(tmp_path, tools=["claude"])
    assert (tmp_path / "agents" / "reviewer.md").read_text().endswith("Our reviewer.\n")
    assert "agents/reviewer.md" in report.kept
    assert (tmp_path / ".claude" / "skills" / "house-style" / "SKILL.md").is_file()


def test_tool_files_and_a_second_init_never_block(tmp_path: Path) -> None:
    write(tmp_path, ".claude/agents/mine.md", "---\nname: mine\ndescription: mine\n---\nMine.\n")
    write(tmp_path, ".cursor/rules/style.mdc", "---\nalwaysApply: true\n---\nStyle.\n")
    write(tmp_path, "AGENTS.md", "# Ours\n\nUse pnpm.\n")
    initialize(tmp_path, tools=["claude", "cursor"])
    assert (tmp_path / ".claude" / "agents" / "mine.md").read_text().endswith("Mine.\n")
    assert (tmp_path / "AGENTS.md").read_text().startswith("# Ours\n\nUse pnpm.\n")
    # An initialised repository is ours: files added later never trigger the check again.
    write(tmp_path, "specs/openapi.yaml", "openapi: 3.1.0\n")
    report = initialize(tmp_path, tools=["claude"])
    assert not report.created and not any("adopt" in note for note in report.notes)


def test_the_cli_refuses_with_exit_code_2_and_adopts_on_request(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/python/requirements.txt", "flask\n")
    assert main(["-C", str(tmp_path), "init"]) == 2
    error = capsys.readouterr().err
    assert "covener init: this repository already uses directories" in error and "skills/ holds python" in error
    assert main(["-C", str(tmp_path), "init", "--adopt"]) == 0
    assert (tmp_path / "skills" / "frontend" / "SKILL.md").is_file()
