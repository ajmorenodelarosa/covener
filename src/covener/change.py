"""``covener change``: start a change, and archive it once you approved the work.

Both are deterministic file operations with the rules enforced, not merely reported:
``start`` refuses an item that is not ready or is already in an open change, and ``archive``
refuses a change whose work log does not end with your ``Approved: Yes``.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .config import Config
from .init import read_resource
from .repo import ARCHIVE_DIR, CHANGE_FILE, DESIGN_FILE, WORK_FILE, ItemKey, load_repository

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ChangeError(ValueError):
    """Raised when a change cannot be started or archived."""


@dataclass
class ChangeReport:
    action: str
    name: str
    created: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"Change {self.name}: {self.action}"]
        lines += [f"  + {path}" for path in self.created]
        lines += [f"  > {path}" for path in self.moved]
        lines += [f"  ~ {path}" for path in self.updated]
        lines += [f"  - {note}" for note in self.notes]
        return "\n".join(lines)


def _items_from(specs: list[str], bugs: list[str], tasks: list[str]) -> list[ItemKey]:
    return [("spec", i) for i in specs] + [("bug", i) for i in bugs] + [("task", i) for i in tasks]


def start(
    root: Path,
    config: Config,
    name: str,
    specs: list[str] | None = None,
    bugs: list[str] | None = None,
    tasks: list[str] | None = None,
    title: str = "",
) -> ChangeReport:
    """Create ``changes/<name>/`` with change.md, design.md and work.md for the given items."""
    if not NAME_RE.match(name):
        raise ChangeError(f"{name!r} is not a valid change name: lowercase words separated by hyphens")
    wanted = _items_from(specs or [], bugs or [], tasks or [])
    if not wanted:
        raise ChangeError("a change needs at least one item: --spec, --bug or --task")

    directory = root / config.paths["changes"] / name
    if directory.exists():
        raise ChangeError(f"{directory.relative_to(root).as_posix()} already exists")

    repo = load_repository(root, config)
    by_key = repo.item_by_key
    for key in wanted:
        kind, item_id = key
        item = by_key.get(key)
        if item is None:
            raise ChangeError(f"{kind} {item_id!r} does not exist ({config.paths[f'{kind}s']}/{item_id}.md)")
        if not item.ready:
            raise ChangeError(
                f"{item.path} is {item.status!r}; a change only takes {kind}s that are "
                f"{'approved' if kind == 'spec' else 'open'}"
            )
        open_change = next((c for c in repo.changes_of(key, open_only=True)), None)
        if open_change is not None:
            raise ChangeError(f"{kind} {item_id} is already in the open change {open_change.name!r}")

    report = ChangeReport(action="started", name=name)
    directory.mkdir(parents=True)
    heading = title or ", ".join(by_key[key].title for key in wanted)
    item_lines = "\n".join(f"  - {kind}: {item_id}" for kind, item_id in wanted)
    change_md = (
        read_resource("templates/change.md")
        .replace("<title>", heading)
        .replace("status: open\nitems: []", f"status: open\nitems:\n{item_lines}")
        .replace("opened: <YYYY-MM-DD>", f"opened: {date.today().isoformat()}")
    )
    (directory / CHANGE_FILE).write_text(change_md, encoding="utf-8")
    (directory / DESIGN_FILE).write_text(
        read_resource("templates/design.md").replace("<title>", heading), encoding="utf-8"
    )
    (directory / WORK_FILE).write_text(read_resource("templates/work.md").replace("<title>", heading), encoding="utf-8")
    report.created += [f"{directory.relative_to(root).as_posix()}/{f}" for f in (CHANGE_FILE, DESIGN_FILE, WORK_FILE)]
    report.notes.append(
        "Write design.md and log `## Design` in work.md: the human approves the design before any code. "
        "Delete design.md if the change does not need one."
    )
    return report


def archive(root: Path, config: Config, name: str, when: str = "") -> ChangeReport:
    """Mark the change and its items done and move it to ``changes/archive/<date>-<name>/``.

    Refuses unless the work log ends with a human ``Approved: Yes``.
    """
    repo = load_repository(root, config)
    change = next((c for c in repo.changes if c.name == name and not c.archived), None)
    if change is None:
        archived = next(
            (c for c in repo.changes if c.archived and (c.name == name or c.name.endswith(f"-{name}"))), None
        )
        if archived is not None:
            raise ChangeError(f"change {name!r} is already archived in {archived.path}")
        raise ChangeError(f"change {name!r} does not exist")
    last = next((entry for entry in reversed(change.work) if entry.kind != "checklist"), None)
    if not change.approved and change.status == "open" and last is not None and last.approved:
        raise ChangeError(
            f"{change.work_file} ends with an approval of the design, not of the work: when the work is "
            f"complete, set `status: review` in {change.path}/{CHANGE_FILE} and ask for your verdict"
        )
    if not change.approved:
        raise ChangeError(
            f"{change.work_file} does not end with a human 'Approved: Yes' "
            f"(state: {change.state.replace('_', ' ')}); nothing is archived without your approval"
        )

    report = ChangeReport(action="archived", name=name)
    stamp = when or date.today().isoformat()
    source = root / change.path
    target = root / config.paths["changes"] / ARCHIVE_DIR / f"{stamp}-{name}"
    if target.exists():
        raise ChangeError(f"{target.relative_to(root).as_posix()} already exists")

    change_file = source / CHANGE_FILE
    text = change_file.read_text(encoding="utf-8")
    text = re.sub(r"^status:.*$", "status: done", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^closed:.*$", f"closed: {stamp}", text, count=1, flags=re.MULTILINE)
    change_file.write_text(text, encoding="utf-8")
    report.updated.append(f"{change.path}/{CHANGE_FILE} (status: done)")

    for kind, item_id in change.items:
        item = repo.item_by_key.get((kind, item_id))
        if item is None:
            report.notes.append(f"{kind} {item_id} no longer exists; left alone")
            continue
        path = root / item.path
        item_text = path.read_text(encoding="utf-8")
        updated = re.sub(r"^status:.*$", "status: done", item_text, count=1, flags=re.MULTILINE)
        if updated != item_text:
            path.write_text(updated, encoding="utf-8")
            report.updated.append(f"{item.path} (status: done)")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    report.moved.append(f"{change.path} -> {target.relative_to(root).as_posix()}")
    return report
