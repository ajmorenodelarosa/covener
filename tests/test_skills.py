"""Skills: the Agent Skills open standard, linked to every tool that reads it."""

from __future__ import annotations

from pathlib import Path

import yaml

from conftest import links_to, write
from covener import config
from covener.init import STARTER_SKILLS, initialize
from covener.status import compute, render_text

RESOURCES = Path(__file__).resolve().parents[1] / "src" / "covener" / "resources"


def front_matter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


def test_packaged_agents_and_skills_have_valid_front_matter() -> None:
    """A colon in a description silently breaks the YAML and the IDE ignores the file."""
    files = sorted(RESOURCES.glob("agents/*.md")) + sorted(RESOURCES.glob("skills/*/SKILL.md"))
    assert len(files) == 7
    for path in files:
        meta = front_matter(path)
        assert meta.get("name"), path
        assert meta.get("description"), path
        assert len(meta["description"]) <= 1024, path
        assert meta["name"] == meta["name"].lower().replace(" ", "-"), path
        if path.name == "SKILL.md":
            assert meta["name"] == path.parent.name, path


def test_init_installs_the_starter_skills_and_links_them(repo: Path) -> None:
    for name in STARTER_SKILLS:
        assert (repo / "skills" / name / "SKILL.md").is_file()
    assert (repo / "skills" / "README.md").is_file()
    # One link per skill, which is the form Claude Code documents as supported. Claude Code reads
    # .claude/skills; Cursor, Codex and Copilot read the portable .agents/skills.
    for directory in (".claude/skills", ".agents/skills"):
        assert (repo / directory).is_dir() and not (repo / directory).is_symlink(), directory
        for name in STARTER_SKILLS:
            assert links_to(repo / directory / name, repo / "skills" / name), f"{directory}/{name}"
    assert not (repo / ".cursor" / "skills").exists()  # Cursor reads .agents/skills natively
    # Editing a skill is visible through every link, and adding one needs a re-run for the links.
    write(repo, "skills/frontend/SKILL.md", "---\nname: frontend\ndescription: ours\n---\nUse tokens.\n")
    assert "Use tokens." in (repo / ".claude" / "skills" / "frontend" / "SKILL.md").read_text()
    write(repo, "skills/api-design/SKILL.md", "---\nname: api-design\ndescription: ours\n---\nREST.\n")
    report = initialize(repo)
    assert ".agents/skills/api-design" in report.created
    assert (repo / ".claude" / "skills" / "api-design" / "SKILL.md").is_file()


def test_a_directory_link_from_an_older_version_is_replaced(repo: Path) -> None:
    """0.4.0 linked the whole directory; Claude Code only documents per-skill links."""
    import os

    for directory in (".claude/skills", ".agents/skills"):
        for name in STARTER_SKILLS:
            (repo / directory / name).unlink()
        (repo / directory).rmdir()
        os.symlink("../skills", repo / directory, target_is_directory=True)
    report = initialize(repo)
    assert any("replaced with one link per skill" in note for note in report.notes)
    for directory in (".claude/skills", ".agents/skills"):
        assert not (repo / directory).is_symlink()
        assert links_to(repo / directory / "frontend", repo / "skills" / "frontend")


def test_init_does_not_resurrect_a_deleted_skill(repo: Path) -> None:
    (repo / "skills" / "backend" / "SKILL.md").unlink()
    (repo / "skills" / "backend").rmdir()
    report = initialize(repo)
    assert not (repo / "skills" / "backend").exists()
    assert any("--install-agents" in note for note in report.notes)
    report = initialize(repo, install_agents=True)
    assert "skills/backend/SKILL.md" in report.created


def test_status_lists_skills_and_flags_templates(repo: Path) -> None:
    _, report, snapshot = compute(repo, config.load(repo))
    assert snapshot.skills == [
        {"name": "backend", "template": True},
        {"name": "frontend", "template": True},
    ]
    assert "Skills: backend (template), frontend (template)" in render_text(snapshot).splitlines()
    assert {i.code for i in report.warnings if i.code.startswith("skill")} == {"skill.placeholder"}
    assert "Fill in skills/frontend/SKILL.md with this project's conventions" in report.actions
    # Filled in: no warning, no action.
    for name in STARTER_SKILLS:
        write(repo, f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: ours\n---\nOur rules.\n")
    _, report, snapshot = compute(repo, config.load(repo))
    assert snapshot.skills == [{"name": "backend", "template": False}, {"name": "frontend", "template": False}]
    assert not [i for i in report.issues if i.code.startswith("skill")]


def test_status_reports_broken_skills(repo: Path) -> None:
    write(repo, "skills/frontend/SKILL.md", "---\nname: front-end\ndescription: ours\n---\nx\n")
    write(repo, "skills/backend/SKILL.md", "---\nname: backend\n---\nno description\n")
    (repo / "skills" / "empty").mkdir()
    write(repo, "skills/shouty/SKILL.md", "---\nname: Shouty\ndescription: ours\n---\nx\n")
    _, report, _ = compute(repo, config.load(repo))
    codes = {i.code for i in report.issues}
    assert {"skill.name-mismatch", "skill.incomplete", "skill.no-file", "skill.invalid-name"} <= codes
