"""covener init: structure, links, safe integration with existing files, roles."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from conftest import links_to, needs_symlinks, remove_link, write
from covener import config
from covener.init import MARK_END, MARK_START, initialize
from covener.roles import DEFAULT_AGENT_NAMES


def test_fresh_init_creates_structure_and_links(tmp_path: Path) -> None:
    report = initialize(tmp_path, tools=["claude", "cursor"])
    for relative in (
        ".covener/config.yaml",
        ".covener/states.yaml",
        "specs/vision.md",
        "specs/TEMPLATE.md",
        "bugs/TEMPLATE.md",
        "tasks/TEMPLATE.md",
        "sprints/TEMPLATE/sprint.md",
        "sprints/TEMPLATE/work.md",
        "AGENTS.md",
        "CLAUDE.md",
    ):
        assert (tmp_path / relative).is_file(), relative
    for name in DEFAULT_AGENT_NAMES.values():
        assert (tmp_path / "agents" / f"{name}.md").is_file()
    for tool in (".claude", ".cursor"):
        link = tmp_path / tool / "agents"
        assert links_to(link, tmp_path / "agents")
        if link.is_symlink():  # relative, so clones and moves keep working
            assert os.readlink(link).replace("\\", "/") == "../agents"
    assert "AGENTS.md" in report.created and not report.updated
    # Idempotent.
    again = initialize(tmp_path, tools=["claude", "cursor"])
    assert not again.created and not again.updated and not again.removed


def test_mcp_server_is_registered_when_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(tmp_path, ".mcp.json", '{"mcpServers": {"other": {"type": "stdio", "command": "x"}}}\n')
    report = initialize(tmp_path, tools=["claude", "cursor"])
    claude = json.loads((tmp_path / ".mcp.json").read_text())
    assert claude["mcpServers"]["other"]["command"] == "x"  # untouched
    assert claude["mcpServers"]["covener"] == {"type": "stdio", "command": "covener", "args": ["serve"]}
    cursor = json.loads((tmp_path / ".cursor" / "mcp.json").read_text())
    assert cursor["mcpServers"]["covener"] == {"command": "covener", "args": ["serve"]}
    assert ".mcp.json" in report.created and ".mcp.json" in initialize(tmp_path).kept
    # Without the mcp package nothing is registered and the developer is told.
    monkeypatch.setattr("covener.mcp_server.mcp_available", lambda: False)
    report = initialize(tmp_path / "bare", tools=["claude"]) if (tmp_path / "bare").mkdir() is None else None
    assert report is not None and not (tmp_path / "bare" / ".mcp.json").exists()
    assert any("covener[mcp]" in note for note in report.notes)


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    report = initialize(tmp_path, tools=["claude"], dry_run=True)
    assert "agents/qa.md" in report.created and ".claude/agents -> agents" in report.created
    assert list(tmp_path.iterdir()) == []
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    report = initialize(tmp_path, tools=["claude"], dry_run=True)
    assert ".claude/agents/qa.md" in report.created
    assert sorted(p.name for p in (tmp_path / ".claude" / "agents").iterdir()) == []


def test_existing_agents_md_is_preserved(tmp_path: Path) -> None:
    write(tmp_path, "AGENTS.md", "# My project\n\nRun `make test`.\n")
    report = initialize(tmp_path, tools=["cursor"])
    text = (tmp_path / "AGENTS.md").read_text()
    assert text.startswith("# My project\n\nRun `make test`.\n")
    assert text.count(MARK_START) == 1 and text.count(MARK_END) == 1
    assert "AGENTS.md" in report.updated
    assert "AGENTS.md" in initialize(tmp_path, tools=["cursor"]).kept
    # A stale block is refreshed in place; unbalanced markers are left alone.
    write(tmp_path, "AGENTS.md", f"# Mine\n\n{MARK_START}\nold\n{MARK_END}\n\n## After\nkeep me\n")
    initialize(tmp_path, tools=["cursor"])
    text = (tmp_path / "AGENTS.md").read_text()
    assert "old" not in text and text.endswith("## After\nkeep me\n")
    broken = f"# Mine\n\n{MARK_START}\npartial\n\n## Team rules\nnever delete me\n"
    write(tmp_path, "AGENTS.md", broken)
    report = initialize(tmp_path, tools=["cursor"])
    assert (tmp_path / "AGENTS.md").read_text() == broken and any("unbalanced" in n for n in report.notes)


def test_existing_claude_md_gets_one_import(tmp_path: Path) -> None:
    write(tmp_path, "CLAUDE.md", "# Claude notes\n\n```\n@AGENTS.md\n```\n")
    initialize(tmp_path, tools=["claude"])
    initialize(tmp_path, tools=["claude"])
    text = (tmp_path / "CLAUDE.md").read_text()
    assert text.startswith("# Claude notes\n") and text.count("@AGENTS.md") == 2  # one real, one in the fence
    write(tmp_path, "CLAUDE.md", "@./AGENTS.md\n")
    assert "CLAUDE.md" in initialize(tmp_path, tools=["claude"]).kept


@needs_symlinks
def test_existing_tool_directory_gets_per_file_links(tmp_path: Path) -> None:
    write(tmp_path, ".claude/agents/qa.md", "---\nname: qa\ndescription: mine\n---\nMy own QA agent.\n")
    report = initialize(tmp_path, tools=["claude"])
    agents = tmp_path / ".claude" / "agents"
    assert agents.is_dir() and not agents.is_symlink()
    assert links_to(agents / "engineer.md", tmp_path / "agents" / "engineer.md")
    assert (agents / "qa.md").read_text().endswith("My own QA agent.\n")
    assert ".claude/agents/qa.md" in report.skipped
    # Renaming an agent removes the dangling link.
    cfg = config.load(tmp_path)
    cfg.agents["reviewer"] = "code-reviewer"
    (tmp_path / ".covener" / "config.yaml").write_text(cfg.render())
    source = tmp_path / "agents" / "reviewer.md"
    target = tmp_path / "agents" / "code-reviewer.md"
    target.write_text(source.read_text().replace("name: reviewer\n", "name: code-reviewer\n", 1))
    source.unlink()
    os.symlink(os.path.join("..", "..", "elsewhere", "foo.md"), agents / "foo.md")  # dangling, not ours: kept
    report = initialize(tmp_path)
    assert ".claude/agents/reviewer.md" in report.removed
    assert links_to(agents / "code-reviewer.md", tmp_path / "agents" / "code-reviewer.md")
    assert (agents / "foo.md").is_symlink()


def test_symlink_failure_falls_back_to_copies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("symlinks not allowed")

    monkeypatch.setattr(os, "symlink", refuse)
    monkeypatch.setattr("covener.adapters.base.sys.platform", "linux")  # no junction fallback either
    report = initialize(tmp_path, tools=["claude"])
    copy = tmp_path / ".claude" / "agents" / "qa.md"
    assert copy.is_file() and not copy.is_symlink()
    assert any("symlinks unavailable" in note for note in report.notes)


def test_git_symlink_placeholder_is_repaired(tmp_path: Path) -> None:
    initialize(tmp_path, tools=["claude"])
    link = tmp_path / ".claude" / "agents"
    remove_link(link)
    link.write_text("../agents")  # what git writes with core.symlinks=false
    report = initialize(tmp_path)
    assert links_to(link, tmp_path / "agents") and any("core.symlinks" in note for note in report.notes)


def test_roles_rename_disable_alias_and_deleted_agents(tmp_path: Path) -> None:
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
    # A deleted agent is not resurrected unless asked.
    (tmp_path / "agents" / "product.md").unlink()
    report = initialize(tmp_path)
    assert not (tmp_path / "agents" / "product.md").exists() and any("--install-agents" in n for n in report.notes)
    assert "agents/product.md" in initialize(tmp_path, install_agents=True).created


def test_tool_selection(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    assert initialize(tmp_path).tools == ["cursor"]
    assert not (tmp_path / ".claude").exists()
    assert initialize(tmp_path, tools=[]).tools == []
    with pytest.raises(ValueError, match="unknown tool"):
        initialize(tmp_path, tools=["vim"])
    with pytest.raises(ValueError, match="not a directory"):
        initialize(tmp_path / "missing")
