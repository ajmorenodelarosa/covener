"""covener init: it adds the structure, links one file per agent, and destroys nothing."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from conftest import links_to, needs_symlinks, remove_link, write
from covener import config
from covener.init import MARK_END, MARK_START, initialize
from covener.roles import DEFAULT_AGENT_NAMES


def test_fresh_init_creates_the_structure_and_links_each_agent(tmp_path: Path) -> None:
    report = initialize(tmp_path, tools=["claude", "cursor"])
    assert "AGENTS.md" in report.created and not report.updated
    for relative in (
        ".covener/config.yaml",
        ".covener/states.yaml",
        "specs/vision.md",
        "specs/TEMPLATE.md",
        "bugs/TEMPLATE.md",
        "tasks/TEMPLATE.md",
        "changes/TEMPLATE/change.md",
        "changes/TEMPLATE/design.md",
        "changes/TEMPLATE/work.md",
        "AGENTS.md",
        "CLAUDE.md",
    ):
        assert (tmp_path / relative).is_file(), relative
    for name in DEFAULT_AGENT_NAMES.values():
        assert (tmp_path / "agents" / f"{name}.md").is_file()
    # One file per agent, one link per agent: the form every harness documents.
    for tool in (".claude", ".cursor"):
        directory = tmp_path / tool / "agents"
        assert directory.is_dir() and not directory.is_symlink()
        link = directory / "engineer.md"
        assert links_to(link, tmp_path / "agents" / "engineer.md")
        if link.is_symlink():  # relative, so clones and moved checkouts keep working
            assert os.readlink(link).replace("\\", "/") == "../../agents/engineer.md"
    assert initialize(tmp_path, tools=["claude", "cursor"]).created == []  # idempotent


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    report = initialize(tmp_path, tools=["claude"], dry_run=True)
    assert {"agents/qa.md", ".claude/agents/qa.md", ".claude/skills/frontend", ".agents/skills/frontend"} <= set(
        report.created
    )
    assert list(tmp_path.iterdir()) == []


def test_existing_instructions_are_integrated_never_overwritten(tmp_path: Path) -> None:
    write(tmp_path, "AGENTS.md", "# My project\n\nRun `make test`.\n")
    write(tmp_path, "CLAUDE.md", "# Claude notes\n\n```\n@AGENTS.md\n```\n")
    report = initialize(tmp_path, tools=["claude"])
    text = (tmp_path / "AGENTS.md").read_text()
    assert text.startswith("# My project\n\nRun `make test`.\n")
    assert text.count(MARK_START) == 1 and text.count(MARK_END) == 1
    assert "AGENTS.md" in report.updated and "AGENTS.md" in initialize(tmp_path).kept
    # CLAUDE.md gets the import once, and an @AGENTS.md inside a code fence does not count as one.
    claude = (tmp_path / "CLAUDE.md").read_text()
    assert claude.startswith("# Claude notes\n") and claude.count("@AGENTS.md") == 2
    assert "CLAUDE.md" in initialize(tmp_path).kept

    # A stale block is refreshed in place; everything around it survives.
    write(tmp_path, "AGENTS.md", f"# Mine\n\n{MARK_START}\nSTALE\n{MARK_END}\n\n## Team rules\nkeep me\n")
    initialize(tmp_path)
    text = (tmp_path / "AGENTS.md").read_text()
    assert "STALE" not in text and text.endswith("## Team rules\nkeep me\n")
    # Markers a human broke by hand: leave the file alone rather than guess where the block ends.
    broken = f"# Mine\n\n{MARK_START}\npartial\n\n## Team rules\nnever delete me\n"
    write(tmp_path, "AGENTS.md", broken)
    report = initialize(tmp_path)
    assert (tmp_path / "AGENTS.md").read_text() == broken
    assert any("unbalanced" in note for note in report.notes)


@needs_symlinks
def test_the_projects_own_agents_live_next_to_ours(tmp_path: Path) -> None:
    write(tmp_path, ".claude/agents/qa.md", "---\nname: qa\ndescription: mine\n---\nMy own QA agent.\n")
    report = initialize(tmp_path, tools=["claude"])
    agents = tmp_path / ".claude" / "agents"
    assert links_to(agents / "engineer.md", tmp_path / "agents" / "engineer.md")
    assert (agents / "qa.md").read_text().endswith("My own QA agent.\n")  # theirs wins
    assert ".claude/agents/qa.md" in report.skipped
    # Renaming a role removes the link it left behind; links that are not ours are never touched.
    cfg = config.load(tmp_path)
    cfg.agents["reviewer"] = "code-reviewer"
    write(tmp_path, ".covener/config.yaml", cfg.render())
    source = tmp_path / "agents" / "reviewer.md"
    (tmp_path / "agents" / "code-reviewer.md").write_text(
        source.read_text().replace("name: reviewer", "name: code-reviewer", 1)
    )
    source.unlink()
    os.symlink(os.path.join("..", "..", "elsewhere", "foo.md"), agents / "foo.md")
    report = initialize(tmp_path)
    assert ".claude/agents/reviewer.md" in report.removed
    assert links_to(agents / "code-reviewer.md", tmp_path / "agents" / "code-reviewer.md")
    assert (agents / "foo.md").is_symlink()


@needs_symlinks
def test_links_left_by_an_older_version_or_by_git_are_repaired(tmp_path: Path) -> None:
    """Covener 0.1 linked the whole directory, and git with core.symlinks=false writes text files."""
    initialize(tmp_path, tools=["claude"])
    agents = tmp_path / ".claude" / "agents"
    for entry in agents.iterdir():
        entry.unlink()
    agents.rmdir()
    os.symlink("../agents", agents, target_is_directory=True)
    report = initialize(tmp_path)
    assert not agents.is_symlink() and any("one link per agent" in note for note in report.notes)
    assert links_to(agents / "engineer.md", tmp_path / "agents" / "engineer.md")

    link = agents / "engineer.md"
    remove_link(link)
    link.write_text("../../agents/engineer.md")  # what git checks out without symlink support
    report = initialize(tmp_path)
    assert links_to(link, tmp_path / "agents" / "engineer.md")
    assert any("core.symlinks" in note for note in report.notes)


def test_entries_are_copied_where_symlinks_are_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows without Developer Mode: the team still gets the agents and the skills."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("symlinks not allowed")

    monkeypatch.setattr(os, "symlink", refuse)
    monkeypatch.setattr("covener.adapters.base.sys.platform", "linux")  # no junction fallback either
    report = initialize(tmp_path, tools=["claude"])
    agent = tmp_path / ".claude" / "agents" / "qa.md"
    skill = tmp_path / ".claude" / "skills" / "frontend" / "SKILL.md"
    assert agent.is_file() and not agent.is_symlink() and skill.is_file()
    assert any("symlinks are unavailable" in note for note in report.notes)


def test_roles_can_be_renamed_disabled_or_shared(tmp_path: Path) -> None:
    cfg = config.Config()
    cfg.agents["reviewer"] = "code-reviewer"
    cfg.agents["qa"] = None
    cfg.agents["planner"] = "engineer"
    write(tmp_path, ".covener/config.yaml", cfg.render())
    report = initialize(tmp_path, tools=["claude"])
    assert (tmp_path / "agents" / "code-reviewer.md").read_text().startswith("---\nname: code-reviewer\n")
    assert not (tmp_path / "agents" / "qa.md").exists()
    assert "You are the Engineer" in (tmp_path / "agents" / "engineer.md").read_text()
    assert any("serves role(s) planner, engineer" in note for note in report.notes)
    # An agent the team deleted stays deleted unless it is asked for again.
    (tmp_path / "agents" / "product.md").unlink()
    report = initialize(tmp_path)
    assert not (tmp_path / "agents" / "product.md").exists()
    assert any("--install-agents" in note for note in report.notes)
    assert "agents/product.md" in initialize(tmp_path, install_agents=True).created


def test_tools_are_detected_selected_or_rejected(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    assert initialize(tmp_path).tools == ["cursor"]  # only what the repository already uses
    assert not (tmp_path / ".claude").exists()
    assert initialize(tmp_path, tools=[]).tools == []
    with pytest.raises(ValueError, match="unknown tool"):
        initialize(tmp_path, tools=["vim"])
    with pytest.raises(ValueError, match="not a directory"):
        initialize(tmp_path / "missing")


def test_the_mcp_server_is_registered_beside_the_projects_own(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(tmp_path, ".mcp.json", '{"mcpServers": {"other": {"type": "stdio", "command": "x"}}}\n')
    report = initialize(tmp_path, tools=["claude", "cursor"])
    claude = json.loads((tmp_path / ".mcp.json").read_text())
    assert claude["mcpServers"]["other"]["command"] == "x"  # untouched
    assert claude["mcpServers"]["covener"] == {"type": "stdio", "command": "covener", "args": ["serve"]}
    cursor = json.loads((tmp_path / ".cursor" / "mcp.json").read_text())
    assert cursor["mcpServers"]["covener"] == {"command": "covener", "args": ["serve"]}
    assert ".mcp.json" in report.created and ".mcp.json" in initialize(tmp_path).kept
    # Without the extra there is nothing to register, and the developer is told how to get it.
    monkeypatch.setattr("covener.mcp_server.mcp_available", lambda: False)
    plain = tmp_path / "plain"
    plain.mkdir()
    report = initialize(plain, tools=["claude"])
    assert not (plain / ".mcp.json").exists()
    assert any("covener[mcp]" in note for note in report.notes)
