"""Front matter, configuration, state model and CLI exit codes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from conftest import spec, write
from covener import config, frontmatter, states
from covener.cli import main
from covener.roles import ROLE_KEYS

STATES_YAML = Path(__file__).resolve().parents[1] / "src" / "covener" / "resources" / "framework" / "states.yaml"


def test_front_matter_round_trip_and_errors() -> None:
    document = frontmatter.parse("---\nname: qa\ndescription: Tests things\n---\n\nBody.\n")
    assert document.meta == {"name": "qa", "description": "Tests things"} and document.body.strip() == "Body."
    assert not frontmatter.parse("# Just markdown\n").has_front_matter
    assert not frontmatter.parse("\n---\nname: x\n---\n").has_front_matter
    with pytest.raises(frontmatter.FrontMatterError):
        frontmatter.parse("---\nname: x\n")
    with pytest.raises(frontmatter.FrontMatterError):
        frontmatter.parse("---\n- a\n---\n")


def test_config_defaults_render_and_validation(tmp_path: Path) -> None:
    cfg = config.Config()
    assert set(cfg.agents) == set(ROLE_KEYS) and cfg.tools == ["claude", "cursor"]
    cfg.agents["reviewer"] = "code-reviewer"
    cfg.agents["qa"] = None
    write(tmp_path, ".covener/config.yaml", cfg.render())
    loaded = config.load(tmp_path)
    assert loaded.agents["reviewer"] == "code-reviewer" and loaded.agents["qa"] is None
    assert config.from_dict({"agents": {"qa": "off", "planner": "engineer"}}).active_agents() == {
        "product": "product",
        "planner": "engineer",
        "engineer": "engineer",
        "reviewer": "reviewer",
    }
    for data, message in (
        ({"version": 2}, "unsupported config version"),
        ({"agents": {"wizard": "wizard"}}, "unknown agent role"),
        ({"agents": {"qa": "QA-"}}, "lowercase"),
        ({"tools": "claude"}, "list of strings"),
        ({"workflow": {}}, "unknown configuration key"),
    ):
        with pytest.raises(config.ConfigError, match=message):
            config.from_dict(data)
    with pytest.raises(config.ConfigError, match="init"):
        config.load(tmp_path / "nowhere")


def test_states_yaml_matches_code() -> None:
    data = yaml.safe_load(STATES_YAML.read_text(encoding="utf-8"))
    assert data["spec"]["states"] == list(states.SPEC_STATES)
    assert data["sprint"]["states"] == list(states.SPRINT_STATES)
    assert data["bug"]["states"] == list(states.BUG_STATES)
    assert data["task"]["states"] == list(states.TASK_STATES)
    assert "draft" in data["spec"]["transitions"]["done"]
    assert data["work"]["states"] == list(states.WORK_STATES)
    assert {tuple(t) for t in data["sprint"]["human_gated"]} == set(states.SPRINT_HUMAN_GATED)
    assert {tuple(t) for t in data["spec"]["human_gated"]} == set(states.SPEC_HUMAN_GATED)


def test_cli_exit_codes(tmp_path: Path, populated: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    tmp_path = tmp_path / "fresh"
    tmp_path.mkdir()
    assert main(["-C", str(tmp_path), "status"]) == 2  # not initialised
    assert main(["-C", str(tmp_path / "nope"), "init"]) == 2
    assert main(["-C", str(tmp_path), "init", "--tools", "emacs"]) == 2
    assert main(["-C", str(tmp_path), "init", "--tools", "claude"]) == 0
    capsys.readouterr()
    assert main(["-C", str(tmp_path), "status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["product"]["vision"] == "TEMPLATE"
    broken = tmp_path.parent / "broken"
    write(broken, ".cursor/agents", "a file where a directory should be")
    assert main(["-C", str(broken), "init", "--tools", "cursor"]) == 2
    assert "error:" in capsys.readouterr().err
    assert main(["-C", str(populated), "status", "--strict"]) == 0
    spec(populated, "payouts", status="done", epic="payments")
    assert main(["-C", str(populated), "status", "--strict"]) == 1
    assert main(["-C", str(populated), "status"]) == 0
