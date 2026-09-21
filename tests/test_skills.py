"""Skills: the Agent Skills open standard, one folder per skill, linked where each harness reads it."""

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


def test_the_packaged_agents_and_skills_are_valid_for_every_harness() -> None:
    """A colon in a description silently breaks the YAML and the harness ignores the file."""
    files = sorted(RESOURCES.glob("agents/*.md")) + sorted(RESOURCES.glob("skills/*/SKILL.md"))
    assert [path.stem if path.name != "SKILL.md" else path.parent.name for path in files] == [
        "engineer",
        "planner",
        "product",
        "qa",
        "reviewer",
        "architecture",
        "backend",
        "frontend",
    ]
    for path in files:
        meta = front_matter(path)
        assert meta.get("name") and meta.get("description"), path
        assert len(meta["description"]) <= 1024, path
        assert meta["name"] == meta["name"].lower().replace(" ", "-"), path
        if path.name == "SKILL.md":
            assert meta["name"] == path.parent.name, path


def test_skills_are_linked_where_each_harness_reads_them(repo: Path) -> None:
    for name in STARTER_SKILLS:
        assert (repo / "skills" / name / "SKILL.md").is_file()
    # Claude Code reads .claude/skills; Cursor, Codex and Copilot read the portable .agents/skills.
    for directory in (".claude/skills", ".agents/skills"):
        assert (repo / directory).is_dir() and not (repo / directory).is_symlink(), directory
        for name in STARTER_SKILLS:
            assert links_to(repo / directory / name, repo / "skills" / name), f"{directory}/{name}"
    assert not (repo / ".cursor" / "skills").exists()  # Cursor reads .agents/skills natively
    # One copy to edit: the change is visible through every link. A new skill is linked on the next run.
    write(repo, "skills/frontend/SKILL.md", "---\nname: frontend\ndescription: ours\n---\nUse tokens.\n")
    assert "Use tokens." in (repo / ".claude" / "skills" / "frontend" / "SKILL.md").read_text()
    write(repo, "skills/api-design/SKILL.md", "---\nname: api-design\ndescription: ours\n---\nREST.\n")
    report = initialize(repo)
    assert ".agents/skills/api-design" in report.created
    assert (repo / ".claude" / "skills" / "api-design" / "SKILL.md").is_file()
    # A skill the team deleted stays deleted unless it is asked for again.
    (repo / "skills" / "backend" / "SKILL.md").unlink()
    (repo / "skills" / "backend").rmdir()
    assert any("skills/backend/SKILL.md is missing" in note for note in initialize(repo).notes)
    assert "skills/backend/SKILL.md" in initialize(repo, install_agents=True).created


def test_status_flags_the_template_and_the_broken_skills(repo: Path) -> None:
    _, report, snapshot = compute(repo, config.load(repo))
    assert snapshot.skills == [{"name": name, "template": True} for name in ("architecture", "backend", "frontend")]
    assert (
        "Skills: architecture (template), backend (template), frontend (template)" in render_text(snapshot).splitlines()
    )
    assert "Fill in skills/frontend/SKILL.md with this project's conventions" in report.actions
    # Filled in: no warning, no action left.
    for name in STARTER_SKILLS:
        write(repo, f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: ours\n---\nOur rules.\n")
    _, report, snapshot = compute(repo, config.load(repo))
    assert snapshot.skills == [{"name": name, "template": False} for name in ("architecture", "backend", "frontend")]
    assert not [issue for issue in report.issues if issue.code.startswith("skill")]
    # What the standard requires: a name matching the folder, lowercase, with a description and a file.
    write(repo, "skills/frontend/SKILL.md", "---\nname: front-end\ndescription: ours\n---\nx\n")
    write(repo, "skills/backend/SKILL.md", "---\nname: backend\n---\nno description\n")
    write(repo, "skills/shouty/SKILL.md", "---\nname: Shouty\ndescription: ours\n---\nx\n")
    (repo / "skills" / "empty").mkdir()
    _, report, _ = compute(repo, config.load(repo))
    codes = {issue.code for issue in report.issues}
    assert {"skill.name-mismatch", "skill.incomplete", "skill.no-file", "skill.invalid-name"} <= codes
