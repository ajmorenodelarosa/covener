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
    assert [(c["name"], c["status"], c["state"]) for c in snapshot.changes] == [
        ("account-closure", "review", "awaiting_feedback"),
        ("fix-rounding", "open", "in_progress"),
    ]
    assert snapshot.changes[0]["items"] == ["spec privacy/account-closure"] and snapshot.changes[0]["design"]
    assert snapshot.done == [
        {"kind": "spec", "id": "aml/audit-trail", "change": "2026-09-10-audit-trail", "closed": "2026-09-10"}
    ]
    assert snapshot.pending_human_review == 1 and snapshot.pending_spec_approval == 1
    for action in (
        "Review and approve specs/aml/monitoring.md (draft)",
        "Start a change for bug wrong-currency: covener change start <name> --bug wrong-currency",
        "Give feedback on change account-closure in changes/account-closure/work.md",
    ):
        assert action in snapshot.actions, action
    # The rendered report is what a human and an agent both read.
    text = render_text(snapshot).splitlines()
    for line in (
        "  Domains: aml 2, privacy 2",
        "  - bug wrong-currency (priority 3)",
        "  account-closure (review): awaiting feedback, checklist 1/2, design",
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
    change(populated, "account-closure", status="done", items=["spec: privacy/account-closure"])
    assert "change.done-without-approval" in errors(populated)
    change(
        populated,
        "account-closure",
        status="done",
        items=["spec: privacy/account-closure"],
        work="# w\n\n## Summary\nx\n\n## Feedback\nApproved: Yes\n",
    )
    assert not {code for code in errors(populated) if code.endswith("done-without-approval")}
    # A later "No" is the verdict that counts: the change is open again.
    change(
        populated,
        "account-closure",
        status="done",
        items=["spec: privacy/account-closure"],
        work="# w\n\n## Feedback\nApproved: Yes\n\n## Feedback\nApproved: No\n",
    )
    assert {"change.done-without-approval", "spec.done-without-approval"} <= errors(populated)


def test_an_item_belongs_to_one_open_change_and_must_be_ready(populated: Path) -> None:
    """How two agents working in parallel find out they collided."""
    change(populated, "second-go", items=["spec: privacy/account-closure"])
    assert "spec.in-several-changes" in errors(populated)
    change(populated, "second-go", items=["spec: aml/monitoring", "bug: ghost", "nonsense"])
    assert {"change.item-not-ready", "change.unknown-item", "parse"} <= errors(populated)


def test_the_archive_keeps_history_even_when_the_item_moved_on(populated: Path) -> None:
    change(populated, "2026-09-10-audit-trail", status="review", items=["spec: aml/audit-trail"], archived=True)
    assert "change.archived-open" in errors(populated)  # an archive holds finished work only
    change(
        populated,
        "2026-09-10-audit-trail",
        status="done",
        items=["spec: aml/audit-trail", "spec: gone"],
        closed="2026-09-10",
        archived=True,
        work="## Summary\nx\n\n## Feedback\nApproved: Yes\n",
    )
    # Approved work whose item nobody marked done is a warning, not a silent gap.
    spec(populated, "aml/audit-trail", status="approved")
    assert "spec.not-done" in codes(populated)
    # History survives an item that was renamed or deleted: the record stays readable.
    (populated / "specs" / "aml" / "audit-trail.md").unlink()
    assert not {code for code in errors(populated) if code.startswith("change.")}


def test_a_domain_view_shows_only_that_domains_work(populated: Path) -> None:
    _, _, privacy = compute(populated, config.load(populated), domain="privacy")
    assert privacy.specs["total"] == 2 and privacy.domains == {"privacy": 2}
    assert [c["name"] for c in privacy.changes] == ["account-closure", "fix-rounding"]  # the bug names a privacy spec
    assert [(e["kind"], e["id"]) for e in privacy.backlog] == [("spec", "privacy/consent")]
    assert render_text(privacy).splitlines()[0] == "Covener (domain: privacy)"
    assert not any("aml/monitoring" in action for action in privacy.actions)
    _, _, aml = compute(populated, config.load(populated), domain="aml")
    assert aml.changes == [] and [e["id"] for e in aml.done] == ["aml/audit-trail"]


def test_broken_files_are_reported_and_nothing_crashes(populated: Path) -> None:
    write(populated, "changes/no-log/change.md", "---\ntitle: t\nstatus: open\nitems: []\n---\n")
    write(populated, "specs/broken.md", "---\ntitle: [\n---\n")
    write(populated, "agents/README.md", "# how this team works\n")  # not an agent definition
    spec(populated, "aml/weird", status="shipped")  # a state the model does not have
    change(populated, "empty-review", status="review", items=["task: upgrade-deps"], work="# nothing yet\n")
    (populated / "bugs" / "latin.md").write_bytes(b"---\ntitle: caf\xe9\nstatus: open\n---\n")
    bug(populated, "orphan", spec="privacy/ghost")
    (populated / "agents" / "qa.md").unlink()
    found = codes(populated)
    assert {"change.no-work-log", "change.no-items", "parse", "bug.unknown-spec", "agent.missing"} <= found
    assert {"spec.invalid-status", "change.review-without-work"} <= found
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
