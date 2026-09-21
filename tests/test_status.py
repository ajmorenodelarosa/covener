"""covener status: parsing, derived backlog, changes, human authority, next actions."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import bug, change, spec, write
from covener import config
from covener.repo import parse_work
from covener.status import compute, render_json, render_text


def codes(root: Path) -> set[str]:
    return {issue.code for issue in compute(root, config.load(root))[1].issues}


def errors(root: Path) -> set[str]:
    return {issue.code for issue in compute(root, config.load(root))[1].errors}


def actions(root: Path) -> list[str]:
    return compute(root, config.load(root))[1].actions


def test_parse_work_is_chronological_and_feedback_carries_approval() -> None:
    entries = parse_work(
        "# x\n\n## Checklist\n- [ ] a\n\n## Summary\nDid X.\n\n## Feedback\n**Approved:** no\nFix Y.\n\n"
        "## Rework\nFixed.\n\n## Feedback: round 2\napproved: YES\n\n## Feedback\nno approved line\n"
    )
    assert [(e.kind, e.approved) for e in entries] == [
        ("checklist", None),
        ("work", None),
        ("feedback", False),
        ("work", None),
        ("feedback", True),
        ("feedback", False),
    ]
    assert entries[2].text == "**Approved:** no\nFix Y."


def test_snapshot_backlog_changes_and_actions(populated: Path) -> None:
    _, report, snapshot = compute(populated, config.load(populated))
    assert report.errors == []
    assert snapshot.specs == {"total": 4, "draft": 1, "approved": 2, "done": 1}
    assert snapshot.bugs == {"total": 2, "open": 2, "done": 0}
    assert snapshot.domains == {"aml": 2, "privacy": 2}
    # Derived backlog: open bugs first, then specs and tasks by priority; nothing in an open change.
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
    assert "Give feedback on change account-closure in changes/account-closure/work.md" in snapshot.actions
    assert "Review and approve specs/aml/monitoring.md (draft)" in snapshot.actions
    text = render_text(snapshot)
    for line in (
        "Covener",
        "  Domains: aml 2, privacy 2",
        "  - bug wrong-currency (priority 3)",
        "  account-closure (review): awaiting feedback, checklist 1/2, design",
        "    - spec privacy/account-closure",
        "  - spec aml/audit-trail (2026-09-10-audit-trail 2026-09-10)",
        "Next",
    ):
        assert line in text.splitlines(), line
    data = json.loads(render_json(snapshot))
    assert data["changes"][1]["name"] == "fix-rounding" and data["backlog"][0]["kind"] == "bug"


def test_nothing_is_done_without_human_approval(populated: Path) -> None:
    # An agent marking the spec done, or the change done, without feedback: both are errors.
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
    assert not {c for c in errors(populated) if c.endswith("done-without-approval")}
    # A later "No" after a "Yes" reopens it.
    change(
        populated,
        "account-closure",
        status="done",
        items=["spec: privacy/account-closure"],
        work="# w\n\n## Feedback\nApproved: Yes\n\n## Feedback\nApproved: No\n",
    )
    assert {"change.done-without-approval", "spec.done-without-approval"} <= errors(populated)


def test_change_lifecycle_actions(populated: Path) -> None:
    assert any("Give feedback on change account-closure" in a for a in actions(populated))
    write(populated, "changes/account-closure/work.md", "## Summary\nx\n\n## Feedback\nApproved: No\nFix it.\n")
    assert any("rework account-closure from the feedback" in a for a in actions(populated))
    write(
        populated, "changes/account-closure/work.md", "## Summary\nx\n\n## Feedback\nApproved: No\n\n## Rework\nDone.\n"
    )
    assert any("Give feedback on change account-closure" in a for a in actions(populated))
    write(populated, "changes/account-closure/work.md", "## Summary\nx\n\n## Feedback\nApproved: Yes\n")
    assert "Close account-closure: your approval is in changes/account-closure/work.md" in actions(populated)
    change(
        populated,
        "account-closure",
        status="done",
        items=["spec: privacy/account-closure"],
        work="## Summary\nx\n\n## Feedback\nApproved: Yes\n",
    )
    assert "Archive account-closure: covener change archive account-closure" in actions(populated)


def test_one_open_change_per_item_and_only_ready_items(populated: Path) -> None:
    change(populated, "second-go", items=["spec: privacy/account-closure"])
    assert "spec.in-several-changes" in errors(populated)
    change(populated, "second-go", items=["spec: aml/monitoring", "bug: ghost", "nonsense"])
    found = errors(populated)
    assert {"change.item-not-ready", "change.unknown-item", "parse"} <= found


def test_archive_rules(populated: Path) -> None:
    # An open change in the archive is an error; history survives an item that changed or vanished.
    change(populated, "2026-09-10-audit-trail", status="review", items=["spec: aml/audit-trail"], archived=True)
    assert "change.archived-open" in errors(populated)
    change(
        populated,
        "2026-09-10-audit-trail",
        status="done",
        items=["spec: aml/audit-trail", "spec: gone"],
        archived=True,
        closed="2026-09-10",
        work="## Summary\nx\n\n## Feedback\nApproved: Yes\n",
    )
    (populated / "specs" / "aml" / "audit-trail.md").unlink()
    assert not {c for c in errors(populated) if c.startswith("change.")}


def test_domain_filter(populated: Path) -> None:
    _, _, privacy = compute(populated, config.load(populated), domain="privacy")
    assert privacy.specs["total"] == 2 and privacy.domains == {"privacy": 2}
    assert [c["name"] for c in privacy.changes] == ["account-closure", "fix-rounding"]  # the bug names a privacy spec
    assert [(e["kind"], e["id"]) for e in privacy.backlog] == [("spec", "privacy/consent")]
    assert render_text(privacy).splitlines()[0] == "Covener (domain: privacy)"
    assert not any("aml/monitoring" in action for action in privacy.actions)
    _, _, aml = compute(populated, config.load(populated), domain="aml")
    assert aml.changes == [] and [e["id"] for e in aml.done] == ["aml/audit-trail"]


def test_hygiene_warnings_and_parse_errors(populated: Path) -> None:
    write(populated, "changes/no-log/change.md", "---\ntitle: t\nstatus: open\nitems: []\n---\n")
    write(populated, "specs/broken.md", "---\ntitle: [\n---\n")
    (populated / "bugs" / "latin.md").write_bytes(b"---\ntitle: caf\xe9\nstatus: open\n---\n")
    bug(populated, "orphan", spec="privacy/ghost")
    (populated / "agents" / "qa.md").unlink()
    found = codes(populated)
    assert {"change.no-work-log", "change.no-items", "parse", "bug.unknown-spec", "agent.missing"} <= found
    cfg = config.Config()
    cfg.agents["qa"] = None
    write(populated, ".covener/config.yaml", cfg.render())
    assert "agent.missing" not in codes(populated)


def test_templates_and_readmes_are_not_items(repo: Path) -> None:
    write(repo, "specs/README.md", "# specs\n")
    write(repo, "agents/README.md", "# agents\n")
    _, report, snapshot = compute(repo, config.load(repo))
    assert snapshot.specs["total"] == 0 and snapshot.bugs["total"] == 0 and report.errors == []


def test_bug_in_the_backlog_suggests_starting_a_change(repo: Path) -> None:
    bug(repo, "rounding")
    assert "Start a change for bug rounding: covener change start <name> --bug rounding" in actions(repo)
    change(repo, "fix-rounding", items=["bug: rounding"])
    assert not any("Start a change for bug" in a for a in actions(repo))
