"""covener status: the derived backlog, human authority, domains, and the CI exit codes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import bug, change, spec, write
from covener import config
from covener.cli import main
from covener.status import compute, render_json, render_text


def errors(root: Path) -> set[str]:
    return {issue.code for issue in compute(root, config.load(root))[1].errors}


def codes(root: Path) -> set[str]:
    return {issue.code for issue in compute(root, config.load(root))[1].issues}


def actions(root: Path) -> list[str]:
    return compute(root, config.load(root))[1].actions


def test_status_reports_the_backlog_the_changes_and_what_is_next(populated: Path) -> None:
    _, report, snapshot = compute(populated, config.load(populated))
    assert report.errors == []
    # Templates and the vision are not items: four specs, two bugs, one task were written.
    assert snapshot.specs == {"total": 4, "draft": 1, "approved": 2, "done": 1}
    assert snapshot.bugs == {"total": 2, "open": 2, "done": 0}
    assert snapshot.domains == {"aml": 2, "privacy": 2}
    # The backlog is derived, not a file: open bugs first, then by priority, nothing already in a change.
    assert [(e["kind"], e["id"]) for e in snapshot.backlog] == [
        ("bug", "wrong-currency"),
        ("spec", "privacy/consent"),
        ("task", "upgrade-deps"),
    ]
    assert [(c["name"], c["state"]) for c in snapshot.changes] == [
        ("account-closure", "in_review"),
        ("fix-rounding", "in_progress"),
    ]
    assert snapshot.changes[0]["items"] == ["spec privacy/account-closure"]
    assert snapshot.changes[0]["design"] == "approved" and snapshot.changes[1]["design"] is None
    assert snapshot.done == [
        {"kind": "spec", "id": "aml/audit-trail", "change": "2026-09-10-audit-trail", "closed": "2026-09-10"}
    ]
    assert snapshot.pending_human_review == 1 and snapshot.pending_spec_approval == 1
    for action in (
        "Review and approve specs/aml/monitoring.md (draft)",
        "Start a change for bug wrong-currency: covener change start <name> --bug wrong-currency",
        "Review the implementation of change account-closure: set status: approved in "
        "changes/account-closure/implementation.md, or add rework tasks to changes/account-closure/tasks.md",
    ):
        assert action in snapshot.actions, action
    # The rendered report is what a human and an agent both read.
    text = render_text(snapshot).splitlines()
    for line in (
        "  Domains: aml 2, privacy 2",
        "  - bug wrong-currency (priority 3)",
        "  account-closure: in review, tasks 2/2, design approved, qa pass, review pass",
        "  fix-rounding: in progress, tasks 1/2",
        "    - spec privacy/account-closure",
        "  - spec aml/audit-trail (2026-09-10-audit-trail 2026-09-10)",
    ):
        assert line in text, line
    data = json.loads(render_json(snapshot))
    assert data["changes"][1]["name"] == "fix-rounding" and data["backlog"][0]["kind"] == "bug"


def test_nothing_is_done_without_the_humans_approval(populated: Path) -> None:
    """The one rule no agent can route around: it is a check, not a request."""
    spec(populated, "privacy/account-closure", status="done", priority="high")
    assert "spec.done-without-approval" in errors(populated)
    # An archived change whose implementation you never approved is an error, wherever it sits.
    change(
        populated,
        "2026-09-21-account-closure",
        items=["spec: privacy/account-closure"],
        implementation="review",
        archived=True,
    )
    assert {"change.archived-without-approval", "spec.done-without-approval"} <= errors(populated)
    change(
        populated,
        "2026-09-21-account-closure",
        items=["spec: privacy/account-closure"],
        implementation="approved",
        archived=True,
    )
    assert not {code for code in errors(populated) if "approval" in code}
    # The approval lives in the archived record, nowhere else, and every file of an archived change is approved.
    change(
        populated,
        "2026-09-21-account-closure",
        items=["spec: privacy/account-closure"],
        tasks="draft",
        implementation="approved",
        archived=True,
    )
    assert "change.archived-without-approval" in errors(populated)
    (populated / "changes" / "archive" / "2026-09-21-account-closure" / "implementation.md").unlink()
    assert "change.archived-without-approval" in errors(populated)


def test_an_item_belongs_to_one_open_change_and_must_be_ready(populated: Path) -> None:
    """How two agents working in parallel find out they collided."""
    change(populated, "second-go", items=["spec: privacy/account-closure"])
    assert "spec.in-several-changes" in errors(populated)
    change(populated, "second-go", items=["spec: aml/monitoring", "bug: ghost", "nonsense"])
    assert {"change.item-not-ready", "change.unknown-item", "parse"} <= errors(populated)


def test_the_archive_keeps_history_even_when_the_item_moved_on(populated: Path) -> None:
    change(
        populated,
        "2026-09-10-audit-trail",
        items=["spec: aml/audit-trail", "spec: gone"],
        implementation="approved",
        archived=True,
    )
    # Approved work whose item nobody marked done is a warning, not a silent gap.
    spec(populated, "aml/audit-trail", status="approved")
    assert "spec.not-done" in codes(populated)
    # History survives an item that was renamed or deleted: the record stays readable.
    (populated / "specs" / "aml" / "audit-trail.md").unlink()
    assert not {code for code in errors(populated) if code.startswith("change.")}


def test_a_domain_view_shows_only_that_domains_work(populated: Path) -> None:
    change(populated, "monitoring", items=["spec: aml/monitoring"], tasks="draft", body="")  # aml, not planned yet
    spec(populated, "aml/monitoring")
    _, _, privacy = compute(populated, config.load(populated), domain="privacy")
    assert privacy.specs["total"] == 2 and privacy.domains == {"privacy": 2}
    assert not any("monitoring" in action for action in privacy.actions)
    assert [c["name"] for c in privacy.changes] == ["account-closure", "fix-rounding"]  # the bug names a privacy spec
    assert [(e["kind"], e["id"]) for e in privacy.backlog] == [("spec", "privacy/consent")]
    assert render_text(privacy).splitlines()[0] == "Covener (domain: privacy)"
    assert not any("aml/monitoring" in action for action in privacy.actions)
    _, _, aml = compute(populated, config.load(populated), domain="aml")
    assert [c["name"] for c in aml.changes] == ["monitoring"] and [e["id"] for e in aml.done] == ["aml/audit-trail"]
    assert any(action.startswith("Agents: plan change monitoring") for action in aml.actions)


def test_broken_files_are_reported_and_nothing_crashes(populated: Path) -> None:
    write(populated, "changes/no-tasks/design.md", "---\nstatus: draft\n---\n")  # a change is its tasks.md
    write(populated, "changes/no-front-matter/tasks.md", "## Tasks\n- [ ] a\n")
    change(populated, "no-items")
    change(populated, "bad-status", items=["task: upgrade-deps"], tasks="shipped")  # states the model does not have
    change(populated, "bad-design", items=["bug: wrong-currency"], design="ok", implementation="done")
    write(populated, "specs/broken.md", "---\ntitle: [\n---\n")
    write(populated, "agents/README.md", "# how this team works\n")  # not an agent definition
    spec(populated, "aml/weird", status="shipped")
    change(populated, "half-done", items=["task: upgrade-deps"], body="## Tasks\n- [ ] a\n", implementation="approved")
    (populated / "bugs" / "latin.md").write_bytes(b"---\ntitle: caf\xe9\nstatus: open\n---\n")
    bug(populated, "orphan", spec="privacy/ghost")
    (populated / "agents" / "qa.md").unlink()
    found = codes(populated)
    assert {
        "change.invalid-tasks-status",
        "change.invalid-design-status",
        "change.invalid-implementation-status",
    } <= found
    assert {"change.no-items", "parse", "bug.unknown-spec", "agent.missing"} <= found
    assert {"spec.invalid-status", "change.approved-with-open-tasks"} <= found
    problems = {issue.path for issue in compute(populated, config.load(populated))[1].errors if issue.code == "parse"}
    assert {"changes/no-tasks", "changes/no-front-matter/tasks.md", "specs/broken.md"} <= problems
    assert "agent.incomplete" not in found
    # Turning the role off is how a team of four stops being told about the fifth agent.
    cfg = config.Config()
    cfg.agents["qa"] = None
    write(populated, ".covener/config.yaml", cfg.render())
    assert "agent.missing" not in codes(populated)


def test_the_exit_codes_are_the_contract_with_ci(
    tmp_path: Path, populated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    assert main(["-C", str(fresh), "status"]) == 2  # not initialised
    assert main(["-C", str(fresh), "init", "--tools", "claude"]) == 0
    capsys.readouterr()
    assert main(["-C", str(fresh), "status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["product"]["vision"] == "TEMPLATE"
    assert main(["-C", str(populated), "status", "--strict"]) == 0
    spec(populated, "payouts", status="done")  # an agent closing a spec on its own
    assert main(["-C", str(populated), "status", "--strict"]) == 1
    assert main(["-C", str(populated), "status"]) == 0  # without --strict a report is still a report
