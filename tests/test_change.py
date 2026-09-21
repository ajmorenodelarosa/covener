"""covener change: the unit of work, from the backlog to the archive."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import bug, change, spec, task, write
from covener import change as change_module
from covener import config
from covener.cli import main
from covener.status import compute


def cfg(root: Path) -> config.Config:
    return config.load(root)


def state(root: Path) -> str:
    return compute(root, cfg(root))[2].changes[0]["state"]


def test_start_scaffolds_the_change_and_takes_the_item(repo: Path) -> None:
    spec(repo, "billing/refunds")
    report = change_module.start(repo, cfg(repo), "refund-flow", specs=["billing/refunds"])
    assert report.created == [
        "changes/refund-flow/change.md",
        "changes/refund-flow/design.md",
        "changes/refund-flow/work.md",
    ]
    text = (repo / "changes" / "refund-flow" / "change.md").read_text()
    assert "status: open" in text and "  - spec: billing/refunds" in text and "opened: 20" in text
    # The item is taken: it leaves the backlog, so no other agent picks it up.
    _, _, snapshot = compute(repo, cfg(repo))
    assert snapshot.backlog == [] and snapshot.changes[0]["name"] == "refund-flow"
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
    with pytest.raises(change_module.ChangeError, match="not a valid change name"):
        change_module.start(repo, cfg(repo), "Not A Name", bugs=["rounding"])
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
    assert "+ changes/account-closure/change.md" in capsys.readouterr().out
    assert (repo / "changes" / "account-closure" / "design.md").is_file()  # the design lives in the change
    assert state(repo) == "not_started"

    # The design comes first and stops: it is yours to read, extend and approve before any code.
    write(repo, "changes/account-closure/work.md", "## Checklist\n- [ ] a\n\n## Design\nTwo tables, one endpoint.\n")
    _, report, snapshot = compute(repo, cfg(repo))
    assert snapshot.changes[0]["state"] == "awaiting_design" and snapshot.pending_human_review == 1
    assert "Review the design of change account-closure in changes/account-closure/design.md" in report.actions

    # An approval on a change that is still open approves the design, not the work.
    write(
        repo, "changes/account-closure/work.md", "## Design\nTwo tables, one endpoint.\n\n## Feedback\nApproved: Yes\n"
    )
    assert state(repo) == "in_progress"
    with pytest.raises(change_module.ChangeError, match="approval of the design"):
        change_module.archive(repo, cfg(repo), "account-closure")

    write(repo, "changes/account-closure/work.md", "## Checklist\n- [x] a\n\n## Summary\nBuilt.\n")
    assert state(repo) == "in_progress"

    # QA and review passed; the change waits for the only verdict that closes it.
    work = "## Checklist\n- [x] a\n\n## Summary\nBuilt.\n\n## QA\nVerdict: pass\n\n## Review\nVerdict: pass\n"
    change(repo, "account-closure", status="review", items=items, work=work)
    assert state(repo) == "awaiting_feedback"
    assert main(["-C", str(repo), "change", "archive", "account-closure"]) == 2
    assert "Approved: Yes" in capsys.readouterr().err

    write(repo, "changes/account-closure/work.md", work + "\n## Feedback\nApproved: No\nFix it.\n")
    assert state(repo) == "changes_requested"
    with pytest.raises(change_module.ChangeError, match="changes requested"):
        change_module.archive(repo, cfg(repo), "account-closure")
    assert any("rework account-closure" in action for action in compute(repo, cfg(repo))[1].actions)

    write(repo, "changes/account-closure/work.md", work + "\n## Rework\nFixed.\n\n## Feedback\nApproved: Yes\n")
    assert (
        "Close account-closure: your approval is in changes/account-closure/work.md"
        in compute(repo, cfg(repo))[1].actions
    )
    report = change_module.archive(repo, cfg(repo), "account-closure", when="2026-09-21")
    assert report.moved == ["changes/account-closure -> changes/archive/2026-09-21-account-closure"]
    archived = repo / "changes" / "archive" / "2026-09-21-account-closure"
    assert "status: done" in (archived / "change.md").read_text()
    assert "closed: 2026-09-21" in (archived / "change.md").read_text()
    assert (archived / "design.md").is_file()
    assert "status: done" in (repo / "specs" / "privacy" / "account-closure.md").read_text()
    assert "status: done" in (repo / "tasks" / "upgrade-deps.md").read_text()

    _, report_, snapshot = compute(repo, cfg(repo))
    assert report_.errors == [] and snapshot.changes == [] and snapshot.specs["done"] == 1
    assert [(e["kind"], e["id"], e["change"]) for e in snapshot.done] == [
        ("spec", "privacy/account-closure", "2026-09-21-account-closure"),
        ("task", "upgrade-deps", "2026-09-21-account-closure"),
    ]
    with pytest.raises(change_module.ChangeError, match="already archived"):
        change_module.archive(repo, cfg(repo), "account-closure")
