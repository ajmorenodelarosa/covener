from __future__ import annotations

import os
import tempfile
import textwrap
from pathlib import Path

import pytest

from covener.init import initialize


def _can_symlink() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.symlink(os.path.join(tmp, "missing"), os.path.join(tmp, "link"))
        except (OSError, NotImplementedError):
            return False
    return True


CAN_SYMLINK = _can_symlink()
needs_symlinks = pytest.mark.skipif(not CAN_SYMLINK, reason="file symlinks are not permitted on this machine")


def links_to(link: Path, target: Path) -> bool:
    """True for a symlink or a Windows junction that resolves to ``target``."""
    return link.exists() and link.resolve() == target.resolve() and link != target


def remove_link(link: Path) -> None:
    """Remove a link; directory links (symlink or junction) need rmdir on Windows."""
    if os.name == "nt" and link.is_dir():
        os.rmdir(link)
    else:
        link.unlink()


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


def change(
    root: Path,
    name: str,
    status: str = "open",
    items: list[str] | None = None,
    work: str = "",
    closed: str = "",
    archived: bool = False,
    design: bool = False,
) -> None:
    """Write a change directory; ``items`` are references like ``spec: billing/refunds``."""
    folder = f"changes/archive/{name}" if archived else f"changes/{name}"
    listed = "\n".join(f"  - {reference}" for reference in (items or []))
    write(
        root,
        f"{folder}/change.md",
        f"---\ntitle: {name}\nstatus: {status}\nitems:\n{listed}\nopened: 2026-09-20\nclosed: {closed}\n---\n## Why\n",
    )
    write(root, f"{folder}/work.md", work or "# w\n\n## Checklist\n- [ ] step\n")
    if design:
        write(root, f"{folder}/design.md", "# Design\n\n## Approach\nx\n")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A freshly initialised repository with a real vision."""
    (tmp_path / ".git").mkdir()
    initialize(tmp_path, tools=["claude", "cursor"])
    write(tmp_path, "specs/vision.md", "# Vision\n\nWe help shops get paid.\n")
    return tmp_path


@pytest.fixture
def populated(repo: Path) -> Path:
    """Two open changes and one archived, in a consistent state.

    - account-closure (review): spec privacy/account-closure, awaiting the human's feedback
    - fix-rounding (open): bug rounding, in progress
    - archived 2026-09-10-audit-trail: spec aml/audit-trail, approved and done
    - backlog: bug wrong-currency, spec privacy/consent (approved), task upgrade-deps
    """
    spec(repo, "privacy/account-closure", priority="high")
    spec(repo, "privacy/consent")
    spec(repo, "aml/audit-trail", status="done")
    spec(repo, "aml/monitoring", status="draft")
    bug(repo, "rounding", spec="privacy/account-closure")
    bug(repo, "wrong-currency", priority="low")
    task(repo, "upgrade-deps")
    change(
        repo,
        "account-closure",
        status="review",
        items=["spec: privacy/account-closure"],
        design=True,
        work="# w\n\n## Checklist\n- [x] a\n- [ ] b\n\n## Summary\nDone.\n\n## QA\nVerdict: pass\n\n## Review\nVerdict: pass\n",
    )
    change(repo, "fix-rounding", items=["bug: rounding"], work="# w\n\n## Checklist\n- [x] test\n\n## Summary\nWIP.\n")
    change(
        repo,
        "2026-09-10-audit-trail",
        status="done",
        items=["spec: aml/audit-trail"],
        closed="2026-09-10",
        archived=True,
        work="# w\n\n## Summary\nx\n\n## Feedback\nApproved: Yes\n",
    )
    return repo
