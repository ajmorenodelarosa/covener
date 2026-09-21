"""covener change: start refuses items that are not ready, archive refuses without approval."""

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


def test_start_scaffolds_the_change(repo: Path) -> None:
    spec(repo, "billing/refunds")
    report = change_module.start(repo, cfg(repo), "refund-flow", specs=["billing/refunds"])
    assert report.created == [
        "changes/refund-flow/change.md",
        "changes/refund-flow/design.md",
        "changes/refund-flow/work.md",
    ]
    text = (repo / "changes" / "refund-flow" / "change.md").read_text()
    assert "status: open" in text and "  - spec: billing/refunds" in text and "opened: 20" in text
    assert "## Checklist" in (repo / "changes" / "refund-flow" / "work.md").read_text()
    # The item is now taken: it leaves the backlog and a second change is refused.
    _, _, snapshot = compute(repo, cfg(repo))
    assert snapshot.backlog == [] and snapshot.changes[0]["name"] == "refund-flow"
    with pytest.raises(change_module.ChangeError, match="already in the open change"):
        change_module.start(repo, cfg(repo), "second", specs=["billing/refunds"])


def test_start_refuses_bad_input(repo: Path) -> None:
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


def test_archive_needs_the_human_approval(repo: Path) -> None:
    spec(repo, "billing/refunds")
    task(repo, "upgrade-deps")
    change_module.start(repo, cfg(repo), "refund-flow", specs=["billing/refunds"], tasks=["upgrade-deps"])
    work = repo / "changes" / "refund-flow" / "work.md"
    with pytest.raises(change_module.ChangeError, match="does not end with a human 'Approved: Yes'"):
        change_module.archive(repo, cfg(repo), "refund-flow")
    work.write_text("## Summary\nDone.\n\n## Feedback\nApproved: No\nFix it.\n")
    with pytest.raises(change_module.ChangeError, match="changes requested"):
        change_module.archive(repo, cfg(repo), "refund-flow")
    work.write_text("## Summary\nDone.\n\n## Feedback\nApproved: Yes\n")
    report = change_module.archive(repo, cfg(repo), "refund-flow", when="2026-09-21")
    assert report.moved == ["changes/refund-flow -> changes/archive/2026-09-21-refund-flow"]
    archived = repo / "changes" / "archive" / "2026-09-21-refund-flow" / "change.md"
    assert "status: done" in archived.read_text() and "closed: 2026-09-21" in archived.read_text()
    assert "status: done" in (repo / "specs" / "billing" / "refunds.md").read_text()
    assert "status: done" in (repo / "tasks" / "upgrade-deps.md").read_text()
    # The repository stays consistent and the item shows up as done.
    _, report_, snapshot = compute(repo, cfg(repo))
    assert report_.errors == [] and snapshot.changes == []
    assert [(e["kind"], e["id"], e["change"]) for e in snapshot.done] == [
        ("spec", "billing/refunds", "2026-09-21-refund-flow"),
        ("task", "upgrade-deps", "2026-09-21-refund-flow"),
    ]
    with pytest.raises(change_module.ChangeError, match="already archived"):
        change_module.archive(repo, cfg(repo), "refund-flow")


def test_cli_change_commands(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    spec(repo, "billing/refunds")
    assert main(["-C", str(repo), "change", "start", "refund-flow", "--spec", "billing/refunds"]) == 0
    assert "+ changes/refund-flow/change.md" in capsys.readouterr().out
    assert main(["-C", str(repo), "change", "archive", "refund-flow"]) == 2
    assert "Approved: Yes" in capsys.readouterr().err
    write(repo, "changes/refund-flow/work.md", "## Summary\nx\n\n## Feedback\nApproved: Yes\n")
    assert main(["-C", str(repo), "change", "archive", "refund-flow"]) == 0
    assert "archived" in capsys.readouterr().out
    assert main(["-C", str(repo), "status", "--strict"]) == 0


def test_a_whole_change_cycle(repo: Path) -> None:
    """The flow a developer follows, with the checks that protect it."""
    spec(repo, "privacy/account-closure", priority="high")
    _, _, snapshot = compute(repo, cfg(repo))
    assert [(e["kind"], e["id"]) for e in snapshot.backlog] == [("spec", "privacy/account-closure")]

    change_module.start(repo, cfg(repo), "account-closure", specs=["privacy/account-closure"])
    folder = repo / "changes" / "account-closure"
    assert (folder / "design.md").is_file()
    _, _, snapshot = compute(repo, cfg(repo))
    assert snapshot.changes[0]["state"] == "not_started" and snapshot.backlog == []

    write(repo, "changes/account-closure/work.md", "## Checklist\n- [x] a\n\n## Summary\nBuilt.\n")
    _, _, snapshot = compute(repo, cfg(repo))
    assert snapshot.changes[0]["state"] == "in_progress"

    change(
        repo,
        "account-closure",
        status="review",
        items=["spec: privacy/account-closure"],
        work="## Checklist\n- [x] a\n\n## Summary\nBuilt.\n\n## QA\nVerdict: pass\n\n## Review\nVerdict: pass\n",
    )
    _, report, snapshot = compute(repo, cfg(repo))
    assert snapshot.changes[0]["state"] == "awaiting_feedback" and snapshot.pending_human_review == 1
    assert any("Give feedback on change account-closure" in a for a in report.actions)

    write(repo, "changes/account-closure/work.md", "## Summary\nBuilt.\n\n## Feedback\nApproved: Yes\n")
    change_module.archive(repo, cfg(repo), "account-closure", when="2026-09-21")
    _, report, snapshot = compute(repo, cfg(repo))
    assert report.errors == [] and snapshot.specs["done"] == 1 and snapshot.changes == []
    assert (repo / "changes" / "archive" / "2026-09-21-account-closure" / "design.md").is_file()
