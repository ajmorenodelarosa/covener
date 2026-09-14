"""covener status: parsing, derived backlog, team rules, human authority, next actions."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import bug, spec, sprint, task, write
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
        "# x\n\n## Checklist\n- [ ] a\n\n## Summary\nDid X.\n\n## Feedback\n**Approved:** no\nFix Y.\n\n## Rework\nFixed.\n\n"
        "## Feedback: round 2\napproved: YES\n\n## Feedback\nno approved line\n"
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


def test_snapshot_backlog_sprints_and_actions(populated: Path) -> None:
    _, report, snapshot = compute(populated, config.load(populated))
    assert report.errors == []
    assert snapshot.vision == "OK"
    assert snapshot.specs == {"total": 5, "draft": 1, "approved": 4, "done": 0}
    assert snapshot.bugs == {"total": 2, "open": 2, "done": 0}
    # Backlog is derived: open bugs first, then approved specs, none in an open sprint.
    assert [(e["kind"], e["id"]) for e in snapshot.backlog] == [("bug", "wrong-currency"), ("spec", "refunds")]
    states = {(s["id"], e["kind"], e["id"]): e["state"] for s in snapshot.sprints for e in s["items"]}
    assert states == {
        ("payments-onboarding", "spec", "stripe-connect"): "approved",
        ("payments-onboarding", "spec", "payouts"): "awaiting_feedback",
        ("payments-onboarding", "bug", "expired-tokens"): "awaiting_feedback",
        ("reporting-v1", "spec", "reporting-api"): "in_progress",
    }
    assert snapshot.pending_human_review == 2
    assert (
        "Give feedback on bug expired-tokens in sprints/payments-onboarding/bugs/expired-tokens.md" in snapshot.actions
    )
    assert "Review and approve specs/ideas.md (draft)" in snapshot.actions
    text = render_text(snapshot)
    for line in (
        "Covener",
        "Bugs",
        "  Open: 2",
        "  - bug wrong-currency (priority 3)",
        "  payments-onboarding (review, alvaro): approved 1/3",
        "    - spec stripe-connect: approved, checklist 2/3",
        "    - bug expired-tokens: awaiting feedback",
        "Next",
    ):
        assert line in text.splitlines(), line
    assert json.loads(render_json(snapshot))["backlog"][0]["kind"] == "bug"


def test_backlog_orders_bugs_first_then_specs_and_tasks_by_priority(populated: Path) -> None:
    spec(populated, "b-mid")
    spec(populated, "a-top", priority="1")
    bug(populated, "late-bug", priority="3")
    task(populated, "migrate-postgres", priority="1")
    task(populated, "upgrade-deps", priority="3")
    ids = [(i.kind, i.id) for i in compute(populated, config.load(populated))[0].backlog()]
    assert ids == [
        ("bug", "late-bug"),
        ("bug", "wrong-currency"),
        ("spec", "a-top"),
        ("task", "migrate-postgres"),
        ("spec", "b-mid"),
        ("spec", "refunds"),
        ("task", "upgrade-deps"),
    ]
    text = render_text(compute(populated, config.load(populated))[2])
    assert "Tasks" in text.splitlines() and "  - task migrate-postgres (priority 1)" in text.splitlines()


def test_tasks_follow_the_same_cycle_and_specs_are_living(populated: Path) -> None:
    task(populated, "migrate-postgres")
    sprint(populated, "reporting-v1", "maria", "review", ["reporting-api"], tasks=["migrate-postgres"])
    write(
        populated,
        "sprints/reporting-v1/tasks/migrate-postgres.md",
        "## Checklist\n- [x] a\n\n## Summary\nx\n\n## Feedback\nApproved: Yes\n",
    )
    write(populated, "sprints/reporting-v1/specs/reporting-api.md", "## Summary\nx\n\n## Feedback\nApproved: Yes\n")
    assert "Close reporting-v1: everything is approved" in actions(populated)
    task(populated, "migrate-postgres", status="done")
    assert "task.done-without-approval" not in errors(populated)
    task(populated, "orphan", status="done")
    assert "task.done-without-approval" in errors(populated)
    # A done spec goes back to draft when its requirements change and simply re-enters the cycle.
    spec(populated, "reporting-api", status="draft")
    assert "Review and approve specs/reporting-api.md (draft)" in actions(populated)


def test_domains_come_from_spec_folders_and_filter_status(repo: Path) -> None:
    spec(repo, "billing/invoices")
    spec(repo, "billing/refunds", priority="1")
    spec(repo, "user-management/signup")
    spec(repo, "flat-spec")
    bug(repo, "rounding", spec="billing/invoices")
    bug(repo, "login-typo", spec="user-management/signup")
    task(repo, "ledger-migration", spec="specs/billing/refunds.md")
    bug(repo, "orphan", spec="billing/ghost")
    sprint(repo, "billing-q4", "ana", "active", ["billing/invoices"], ["rounding"])
    _, report, whole = compute(repo, config.load(repo))
    assert whole.domains == {"billing": 2, "user-management": 1}
    assert "  Domains: billing 2, user-management 1" in render_text(whole).splitlines()
    assert "bug.unknown-spec" in {i.code for i in report.warnings}
    _, _, billing = compute(repo, config.load(repo), domain="billing")
    assert billing.specs["total"] == 2 and billing.domains == {"billing": 2}
    # The orphan bug names a billing spec that does not exist: it still belongs to billing, and status warns.
    assert [(e["kind"], e["id"]) for e in billing.backlog] == [
        ("bug", "orphan"),
        ("spec", "billing/refunds"),
        ("task", "ledger-migration"),
    ]
    assert [s["id"] for s in billing.sprints] == ["billing-q4"]
    assert render_text(billing).splitlines()[0] == "Covener (domain: billing)"
    spec(repo, "user-management/draft-thing", status="draft")
    _, _, billing = compute(repo, config.load(repo), domain="billing")
    assert not any("user-management" in action for action in billing.actions)
    _, _, users = compute(repo, config.load(repo), domain="user-management")
    assert [(e["kind"], e["id"]) for e in users.backlog] == [("bug", "login-typo"), ("spec", "user-management/signup")]
    assert users.sprints == []


def test_templates_vision_and_readme_are_not_items_or_agents(repo: Path) -> None:
    write(repo, "specs/README.md", "# specs\n")
    write(repo, "agents/README.md", "# agents\n")
    _, report, snapshot = compute(repo, config.load(repo))
    assert snapshot.specs["total"] == 0 and snapshot.bugs["total"] == 0 and report.errors == []


def test_tasks_alone_is_not_started_and_path_refs_are_normalised(populated: Path) -> None:
    spec(populated, "payments/refund-api")
    bug(populated, "ui/typo")
    sprint(
        populated,
        "reporting-v1",
        "maria",
        "active",
        ["reporting-api", "specs/payments/refund-api.md"],
        ["bugs/ui/typo"],
    )
    write(populated, "sprints/reporting-v1/specs/payments/refund-api.md", "# r\n\n## Tasks\n- [ ] a\n")
    repo_, report, snapshot = compute(populated, config.load(populated))
    states = {
        (e["kind"], e["id"]): e["state"] for s in snapshot.sprints if s["id"] == "reporting-v1" for e in s["items"]
    }
    assert states[("spec", "payments/refund-api")] == "not_started" and states[("bug", "ui/typo")] == "not_started"
    assert ("spec", "payments/refund-api") not in [(i.kind, i.id) for i in repo_.backlog()]
    assert "work.not-in-sprint" not in {i.code for i in report.issues}


def test_done_requires_final_human_approval_for_specs_and_bugs(populated: Path) -> None:
    spec(populated, "payouts", status="done")
    bug(populated, "expired-tokens", status="done")
    assert {"spec.done-without-approval", "bug.done-without-approval"} <= errors(populated)
    write(populated, "sprints/payments-onboarding/specs/payouts.md", "## Summary\nx\n\n## Feedback\nApproved: Yes\n")
    write(
        populated, "sprints/payments-onboarding/bugs/expired-tokens.md", "## Summary\nx\n\n## Feedback\nApproved: Yes\n"
    )
    assert not {c for c in errors(populated) if c.endswith("done-without-approval")}
    write(
        populated,
        "sprints/payments-onboarding/specs/payouts.md",
        "## Feedback\nApproved: Yes\n\n## Feedback\nApproved: No\n",
    )
    assert "spec.done-without-approval" in errors(populated)


def test_sprint_cannot_close_with_unapproved_work_and_history_survives(populated: Path) -> None:
    sprint(
        populated,
        "payments-onboarding",
        "alvaro",
        "closed",
        ["stripe-connect", "payouts"],
        ["expired-tokens"],
        closed="2026-09-13",
    )
    _, report, _ = compute(populated, config.load(populated))
    blocked = [i.message for i in report.errors if i.code == "sprint.closed-without-approval"]
    assert len(blocked) == 2 and not any("stripe-connect" in m for m in blocked)
    sprint(populated, "payments-onboarding", "alvaro", "closed", ["stripe-connect"], [], closed="2026-09-13")
    assert "spec.not-done" in codes(populated)
    spec(populated, "stripe-connect", status="done")
    _, report, snapshot = compute(populated, config.load(populated))
    assert snapshot.done == [
        {"kind": "spec", "id": "stripe-connect", "sprint": "payments-onboarding", "closed": "2026-09-13"}
    ]
    assert any(a.startswith("Move sprints/payments-onboarding to sprints/archive/") for a in report.actions)
    # Archived: same data, no more action; an open sprint in the archive is an error.
    (populated / "sprints" / "archive").mkdir()
    (populated / "sprints" / "payments-onboarding").rename(
        populated / "sprints" / "archive" / "2026-09-13-payments-onboarding"
    )
    _, report, snapshot = compute(populated, config.load(populated))
    assert snapshot.done[0]["sprint"] == "2026-09-13-payments-onboarding" and not any(
        "Move" in a for a in report.actions
    )
    sprint(populated, "archive/2026-09-13-payments-onboarding", "alvaro", "review", ["stripe-connect"])
    assert "sprint.archived-open" in errors(populated)
    # History survives an item moving on or disappearing.
    sprint(
        populated,
        "archive/2026-09-13-payments-onboarding",
        "alvaro",
        "closed",
        ["stripe-connect", "gone"],
        closed="2026-09-13",
    )
    write(
        populated,
        "sprints/archive/2026-09-13-payments-onboarding/specs/gone.md",
        "## Summary\nx\n\n## Feedback\nApproved: Yes\n",
    )
    (populated / "specs" / "stripe-connect.md").unlink()
    assert not {c for c in errors(populated) if c.startswith("sprint.")}


def test_team_rules(populated: Path) -> None:
    # A second open sprint for the same owner is a warning (hotfix); an item in two open sprints is an error.
    sprint(populated, "hotfix-refunds", "alvaro", "active", [], ["wrong-currency"])
    assert "sprint.multiple-open" in codes(populated) and "sprint.multiple-open" not in errors(populated)
    sprint(populated, "hotfix-refunds", "pedro", "active", ["payouts"], ["expired-tokens"])
    found = errors(populated)
    assert "sprint.multiple-open" not in found
    assert {"spec.in-several-sprints", "bug.in-several-sprints"} <= found


def test_rework_loop_actions_and_close_suggestion(populated: Path) -> None:
    write(
        populated, "sprints/payments-onboarding/bugs/expired-tokens.md", "## Summary\nx\n\n## Feedback\nApproved: Yes\n"
    )
    write(
        populated,
        "sprints/payments-onboarding/specs/payouts.md",
        "## Summary\nx\n\n## Feedback\nApproved: No\nWrong currency.\n",
    )
    assert any("rework spec payouts" in a for a in actions(populated))
    write(
        populated,
        "sprints/payments-onboarding/specs/payouts.md",
        "## Summary\nx\n\n## Feedback\nApproved: No\n\n## Rework\nFixed.\n",
    )
    assert any("Give feedback on spec payouts" in a for a in actions(populated))
    write(populated, "sprints/payments-onboarding/specs/payouts.md", "## Summary\nx\n\n## Feedback\nApproved: Yes\n")
    assert "Close payments-onboarding: everything is approved" in actions(populated)


def test_consistency_errors_and_warnings(populated: Path) -> None:
    sprint(populated, "reporting-v1", "maria", "review", ["ideas", "ghost", "reporting-api"], ["wrong-currency"])
    bug(populated, "wrong-currency", status="done")
    spec(populated, "bad", status="shipped")
    bug(populated, "worse", status="fixed")
    write(populated, "sprints/reporting-v1/specs/refunds.md", "## Summary\nsneaky\n")
    write(populated, "specs/broken.md", "---\ntitle: [\n---\n")
    (populated / "bugs" / "latin.md").write_bytes(b"---\ntitle: caf\xe9\nstatus: open\n---\n")
    (populated / "agents" / "qa.md").unlink()
    found = codes(populated)
    assert {
        "sprint.item-not-ready",
        "sprint.unknown-item",
        "spec.invalid-status",
        "bug.invalid-status",
        "parse",
        "agent.missing",
        "work.not-in-sprint",
        "sprint.review-without-work",
        "bug.done-without-approval",
    } <= found
    cfg = config.Config()
    cfg.agents["qa"] = None
    write(populated, ".covener/config.yaml", cfg.render())
    assert "agent.missing" not in codes(populated)
