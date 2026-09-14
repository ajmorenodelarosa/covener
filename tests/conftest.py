from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from covener.init import initialize


def write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return path


def spec(root: Path, name: str, status: str = "approved", **fields: str) -> None:
    extra = "".join(f"{key}: {value}\n" for key, value in fields.items())
    write(root, f"specs/{name}.md", f"---\ntitle: {name}\nstatus: {status}\n{extra}---\n## Objective\n")


def bug(root: Path, name: str, status: str = "open", **fields: str) -> None:
    extra = "".join(f"{key}: {value}\n" for key, value in fields.items())
    write(root, f"bugs/{name}.md", f"---\ntitle: {name}\nstatus: {status}\n{extra}---\n## Symptom\n")


def task(root: Path, name: str, status: str = "open", **fields: str) -> None:
    extra = "".join(f"{key}: {value}\n" for key, value in fields.items())
    write(root, f"tasks/{name}.md", f"---\ntitle: {name}\nstatus: {status}\n{extra}---\n## Goal\n")


def sprint(
    root: Path,
    name: str,
    owner: str,
    status: str,
    specs: list[str],
    bugs: list[str] | None = None,
    closed: str = "",
    tasks: list[str] | None = None,
) -> None:
    write(
        root,
        f"sprints/{name}/sprint.md",
        f"---\nowner: {owner}\nstatus: {status}\ngoal: g\nspecs: [{', '.join(specs)}]\n"
        f"bugs: [{', '.join(bugs or [])}]\ntasks: [{', '.join(tasks or [])}]\nopened: 2026-09-12\nclosed: {closed}\n---\n",
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A freshly initialised repository with a real vision."""
    (tmp_path / ".git").mkdir()
    initialize(tmp_path, tools=["claude", "cursor"])
    write(tmp_path, "specs/vision.md", "# Vision\n\nWe help shops get paid.\n")
    return tmp_path


@pytest.fixture
def populated(repo: Path) -> Path:
    """Two people, one sprint each, consistent state.

    - payments-onboarding (review, alvaro): spec stripe-connect approved by the human;
      spec payouts awaiting feedback; bug expired-tokens awaiting feedback
    - reporting-v1 (active, maria): spec reporting-api in progress
    - backlog: bug wrong-currency (open), spec refunds (approved); spec ideas is draft
    """
    spec(repo, "stripe-connect", epic="payments", priority="high")
    spec(repo, "payouts", epic="payments")
    spec(repo, "reporting-api", epic="reports")
    spec(repo, "refunds", epic="payments", priority="low")
    spec(repo, "ideas", status="draft")
    bug(repo, "expired-tokens", epic="payments")
    bug(repo, "wrong-currency", epic="payments", priority="low")
    sprint(repo, "payments-onboarding", "alvaro", "review", ["stripe-connect", "payouts"], ["expired-tokens"])
    sprint(repo, "reporting-v1", "maria", "active", ["reporting-api"])
    write(
        repo,
        "sprints/payments-onboarding/specs/stripe-connect.md",
        """
        # stripe-connect

        ## Checklist
        - [x] onboarding endpoint
        - [x] token refresh
        - [ ] docs

        ## Summary
        Implemented onboarding in payments/onboarding.py; 4 tests.

        ## Review
        Verdict: pass

        ## Feedback
        Approved: No
        Handle expired tokens.

        ## Rework
        Added token refresh.

        ## Feedback
        Approved: Yes
        """,
    )
    write(
        repo,
        "sprints/payments-onboarding/specs/payouts.md",
        "# payouts\n\n## Summary\nDone.\n\n## Review\nVerdict: pass\n",
    )
    write(
        repo,
        "sprints/payments-onboarding/bugs/expired-tokens.md",
        "# b\n\n## Summary\nFixed.\n\n## Review\nVerdict: pass\n",
    )
    write(repo, "sprints/reporting-v1/specs/reporting-api.md", "# reporting-api\n\n## Summary\nHalf done.\n")
    return repo
