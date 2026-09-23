"""The pieces everything else is built on: front matter, configuration, states, implementation records."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import write
from covener import config, frontmatter, states
from covener.repo import parse_entries
from covener.roles import ROLE_KEYS

STATES_YAML = Path(__file__).resolve().parents[1] / "src" / "covener" / "resources" / "framework" / "states.yaml"


def test_front_matter_parses_or_fails_loudly() -> None:
    """Specs, bugs, tasks, changes, agents and skills are all read this way."""
    document = frontmatter.parse("---\nname: qa\ndescription: Tests things\n---\n\nBody.\n")
    assert document.meta == {"name": "qa", "description": "Tests things"} and document.body.strip() == "Body."
    assert not frontmatter.parse("# Just markdown\n").has_front_matter
    assert not frontmatter.parse("\n---\nname: x\n---\n").has_front_matter  # must open the file
    for broken in ("---\nname: x\n", "---\n- a\n---\n"):
        with pytest.raises(frontmatter.FrontMatterError):
            frontmatter.parse(broken)


def test_config_maps_the_roles_and_refuses_nonsense(tmp_path: Path) -> None:
    cfg = config.Config()
    assert set(cfg.agents) == set(ROLE_KEYS) and cfg.tools == ["claude", "cursor"]
    cfg.agents["reviewer"] = "code-reviewer"
    cfg.agents["qa"] = None
    write(tmp_path, ".covener/config.yaml", cfg.render())
    loaded = config.load(tmp_path)
    assert loaded.agents["reviewer"] == "code-reviewer" and loaded.agents["qa"] is None
    # `off` drops a role; two roles may share one agent, which is how the team shrinks.
    assert config.from_dict({"agents": {"qa": "off", "planner": "engineer"}}).active_agents() == {
        "product": "product",
        "planner": "engineer",
        "engineer": "engineer",
        "reviewer": "reviewer",
    }
    for data, message in (
        ({"version": 2}, "unsupported config version"),
        ({"agents": {"wizard": "wizard"}}, "unknown agent role"),
        ({"agents": {"qa": "QA-"}}, "lowercase"),  # the harnesses require it
        ({"tools": "claude"}, "list of strings"),
        ({"workflow": {}}, "unknown configuration key"),
    ):
        with pytest.raises(config.ConfigError, match=message):
            config.from_dict(data)
    with pytest.raises(config.ConfigError, match="init"):
        config.load(tmp_path / "nowhere")


def test_states_yaml_matches_the_code() -> None:
    """Agents read .covener/states.yaml; if it drifts they follow rules the tool does not enforce."""
    data = yaml.safe_load(STATES_YAML.read_text(encoding="utf-8"))
    for kind, expected in (
        ("spec", states.SPEC_STATES),
        ("bug", states.BUG_STATES),
        ("task", states.TASK_STATES),
        ("change", states.CHANGE_STATES),
    ):
        assert data[kind]["states"] == list(expected), kind
    assert {tuple(t) for t in data["spec"]["human_gated"]} == set(states.SPEC_HUMAN_GATED)
    files = data["change"]["files"]
    for name, expected, gated in (
        ("design.md", states.DESIGN_STATES, states.DESIGN_HUMAN_GATED),
        ("tasks.md", states.TASKS_STATES, states.TASKS_HUMAN_GATED),
        ("implementation.md", states.IMPLEMENTATION_STATES, states.IMPLEMENTATION_HUMAN_GATED),
    ):
        assert files[name]["states"] == list(expected), name
        assert {tuple(t) for t in files[name]["human_gated"]} == set(gated), name


def test_the_implementation_record_is_chronological_and_the_verdicts_are_read() -> None:
    """The record is the audit trail: the latest QA and Review verdicts are what status shows."""
    entries = parse_entries(
        "# x\n\n## Summary\nDid X.\n\n## Decisions\n- one\n\n## QA\n**Verdict:** pass with notes\n\n"
        "## Review\nVerdict: FAIL\n- high: x\n\n## Rework\nFixed.\n\n## Review: round 2\nverdict: Pass\n"
    )
    assert [e.title for e in entries] == ["Summary", "Decisions", "QA", "Review", "Rework", "Review: round 2"]
    assert entries[0].text == "Did X." and entries[1].verdict is None
    assert [(e.role, e.verdict) for e in entries[2:4]] == [("qa", "pass with notes"), ("review", "fail")]
    assert (entries[5].role, entries[5].verdict) == ("review", "pass")
