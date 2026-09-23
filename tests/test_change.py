"""covener change: the unit of work, from the backlog to the archive."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import bug, change, spec, task
from covener import change as change_module
from covener import config
from covener.cli import main
from covener.status import compute


def cfg(root: Path) -> config.Config:
    return config.load(root)


def state(root: Path) -> str:
    return compute(root, cfg(root))[2].changes[0]["state"]


def errors(root: Path) -> set[str]:
    return {issue.code for issue in compute(root, cfg(root))[1].errors}


def actions(root: Path) -> list[str]:
    return compute(root, cfg(root))[1].actions


def test_start_scaffolds_the_change_and_takes_the_item(repo: Path) -> None:
    spec(repo, "billing/refunds")
    report = change_module.start(repo, cfg(repo), "refund-flow", specs=["billing/refunds"])
    assert report.created == ["changes/refund-flow/tasks.md"]  # the design and the record come later
    text = (repo / "changes" / "refund-flow" / "tasks.md").read_text()
    assert text.startswith("---\nstatus: draft\nitems:\n  - spec: billing/refunds\n---\n")
    # The item is taken: it leaves the backlog, so no other agent picks it up.
    _, report_, snapshot = compute(repo, cfg(repo))
    assert snapshot.backlog == [] and snapshot.changes[0]["name"] == "refund-flow"
    assert snapshot.changes[0]["state"] == "not_started" and report_.errors == []
    assert "Agents: plan change refund-flow in changes/refund-flow/tasks.md (design.md first if it needs one)" in (
        report_.actions
    )
    with pytest.raises(change_module.ChangeError, match="already in the open change"):
        change_module.start(repo, cfg(repo), "second", specs=["billing/refunds"])


def test_start_refuses_what_would_break_the_rules(repo: Path) -> None:
    spec(repo, "draft-spec", status="draft")
    bug(repo, "rounding")
    with pytest.raises(change_module.ChangeError, match="does not exist"):
        change_module.start(repo, cfg(repo), "ghost", specs=["nope"])
    with pytest.raises(change_module.ChangeError, match="a change only takes"):
        change_module.start(repo, cfg(repo), "too-early", specs=["draft-spec"])
    with pytest.raises(change_module.ChangeError, match="at least one item"):
        change_module.start(repo, cfg(repo), "empty")
    for name in ("Not A Name", "archive", "template"):  # the archive and template folders are not changes
        with pytest.raises(change_module.ChangeError, match="not a valid change name"):
            change_module.start(repo, cfg(repo), name, bugs=["rounding"])
    change_module.start(repo, cfg(repo), "fix-rounding", bugs=["rounding"])
    with pytest.raises(change_module.ChangeError, match="changes/fix-rounding already exists"):
        change_module.start(repo, cfg(repo), "fix-rounding", bugs=["rounding"])


def test_the_whole_cycle_from_backlog_to_archive(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    spec(repo, "privacy/account-closure", priority="high")
    task(repo, "upgrade-deps")
    items = ["spec: privacy/account-closure", "task: upgrade-deps"]
    assert (
        main(
            ["-C", str(repo), "change", "start", "account-closure"]
            + ["--spec", "privacy/account-closure", "--task", "upgrade-deps"]
        )
        == 0
    )
    assert "+ changes/account-closure/tasks.md" in capsys.readouterr().out
    assert state(repo) == "not_started"

    # The design comes first and stops: yours to read, edit and approve in its own front matter.
    change(repo, "account-closure", items=items, tasks="draft", body="", design="draft")
    _, report, snapshot = compute(repo, cfg(repo))
    assert snapshot.changes[0]["state"] == "awaiting_design" and snapshot.pending_human_review == 1
    assert (
        "Review the design of change account-closure: set status: approved in changes/account-closure/design.md"
        in report.actions
    )

    # Then the plan, approved the same way. Approving the tasks over a draft design is an error.
    plan = "## Tasks\n- [ ] a (AC1)\n- [ ] b (AC2)\n"
    change(repo, "account-closure", items=items, tasks="approved", body=plan, design="draft")
    assert "change.tasks-before-design" in errors(repo)
    change(repo, "account-closure", items=items, tasks="draft", body=plan, design="approved")
    _, report, snapshot = compute(repo, cfg(repo))
    assert snapshot.changes[0]["state"] == "awaiting_tasks" and snapshot.pending_human_review == 1
    assert any(a.startswith("Review the tasks of change account-closure") for a in report.actions)
    with pytest.raises(change_module.ChangeError, match="no implementation.md"):
        change_module.archive(repo, cfg(repo), "account-closure")

    # No code before the tasks are approved: a record that appears too early is an error, and an
    # approval written over a draft plan does not archive either.
    change(repo, "account-closure", items=items, tasks="draft", body=plan, design="approved", implementation="approved")
    assert "change.implementation-before-tasks" in errors(repo)
    with pytest.raises(change_module.ChangeError, match="tasks.md is 'draft', not 'approved'"):
        change_module.archive(repo, cfg(repo), "account-closure")

    def build(body: str, implementation: str, entries: str) -> None:
        change(
            repo,
            "account-closure",
            items=items,
            body=body,
            design="approved",
            implementation=implementation,
            entries=entries,
        )

    build(plan, "in-progress", "## Summary\nStarted.\n")
    assert state(repo) == "in_progress" and errors(repo) == set()

    # A failing verdict cannot reach you as a request for approval: it is an error, and the agents are told.
    ticked = "## Tasks\n- [x] a (AC1)\n- [x] b (AC2)\n"
    build(
        ticked, "review", "## Summary\nBuilt.\n\n## QA\nVerdict: fail\n- AC2 has no test\n\n## Review\nVerdict: pass\n"
    )
    _, report, snapshot = compute(repo, cfg(repo))
    assert {i.code for i in report.errors} == {"change.review-with-failing-verdict"}
    assert snapshot.changes[0]["verdicts"] == {"qa": "fail", "review": "pass"}
    assert snapshot.pending_human_review == 0  # nothing for you until the agents fix it
    assert not any(a.startswith("Review the implementation") for a in report.actions)
    assert any("failing verdict" in a for a in report.actions)

    # QA and review passed; the change waits for the only verdict that closes it.
    passing = "## Summary\nBuilt.\n\n## QA\nVerdict: pass\n\n## Review\nVerdict: pass\n"
    build(ticked, "review", passing)
    _, report, snapshot = compute(repo, cfg(repo))
    assert snapshot.changes[0]["state"] == "in_review" and snapshot.pending_human_review == 1
    assert (
        "Review the implementation of change account-closure: set status: approved in "
        "changes/account-closure/implementation.md, or add rework tasks to changes/account-closure/tasks.md"
    ) in report.actions
    assert main(["-C", str(repo), "change", "archive", "account-closure"]) == 2
    assert "not 'approved'" in capsys.readouterr().err

    # Rework is a task you add; nothing to log, and the change is in review again once it is ticked.
    rework = ticked + "\n## Rework\n- [ ] restrict retained records to compliance\n"
    build(rework, "review", passing)
    assert state(repo) == "in_progress"
    assert any(a.startswith("Agents: rework account-closure") for a in actions(repo))
    build(rework.replace("- [ ]", "- [x]"), "review", passing + "\n## Rework\nRestricted.\n")
    assert state(repo) == "in_review"

    # Your approval is a status in implementation.md; archive still refuses while a task is open.
    build(rework, "approved", passing)
    assert state(repo) == "approved"
    with pytest.raises(change_module.ChangeError, match="1 open task"):
        change_module.archive(repo, cfg(repo), "account-closure")
    assert not any(a.startswith("Archive") for a in actions(repo))
    assert any(a.startswith("Tick or remove the 1 open task") for a in actions(repo))
    build(rework.replace("- [ ]", "- [x]"), "approved", passing)
    assert "Archive account-closure: covener change archive account-closure" in actions(repo)
    report_ = change_module.archive(repo, cfg(repo), "account-closure", when="2026-09-21")
    assert report_.moved == ["changes/account-closure -> changes/archive/2026-09-21-account-closure"]
    archived = repo / "changes" / "archive" / "2026-09-21-account-closure"
    assert (archived / "design.md").is_file() and (archived / "implementation.md").is_file()
    assert "status: done" in (repo / "specs" / "privacy" / "account-closure.md").read_text()
    assert "status: done" in (repo / "tasks" / "upgrade-deps.md").read_text()

    _, report, snapshot = compute(repo, cfg(repo))
    assert report.errors == [] and snapshot.changes == [] and snapshot.specs["done"] == 1
    assert [(e["kind"], e["id"], e["change"], e["closed"]) for e in snapshot.done] == [
        ("spec", "privacy/account-closure", "2026-09-21-account-closure", "2026-09-21"),
        ("task", "upgrade-deps", "2026-09-21-account-closure", "2026-09-21"),
    ]
    with pytest.raises(change_module.ChangeError, match="already archived"):
        change_module.archive(repo, cfg(repo), "account-closure")
