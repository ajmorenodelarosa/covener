"""``covener change``: start a change, and archive it once you have approved the implementation.

Both are deterministic file operations with the rules enforced, not merely reported:
``start`` refuses an item that is not ready or is already in an open change, and ``archive``
refuses a change whose ``implementation.md`` you did not set to ``approved``, or with an open task.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .config import Config
from .init import read_resource
from .repo import ARCHIVE_DIR, IMPLEMENTATION_FILE, TASKS_FILE, ItemKey, load_repository

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_CHANGE_NAMES: frozenset[str] = frozenset({ARCHIVE_DIR, "template"})


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
) -> ChangeReport:
    """Create ``changes/<name>/tasks.md`` (a draft listing the given items) and nothing else."""
    if not NAME_RE.match(name) or name in RESERVED_CHANGE_NAMES:
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
    item_lines = "\n".join(f"  - {kind}: {item_id}" for kind, item_id in wanted)
    tasks_md = read_resource("templates/tasks.md").replace("items: []", f"items:\n{item_lines}")
    (directory / TASKS_FILE).write_text(tasks_md, encoding="utf-8")
    report.created.append(f"{directory.relative_to(root).as_posix()}/{TASKS_FILE}")
    report.notes.append(
        "Engineer: write design.md if the change needs one (changes/TEMPLATE/design.md) and stop; once the "
        "human sets it approved, write the tasks and stop again. No code before tasks.md is approved."
    )
    return report


def archive(root: Path, config: Config, name: str, when: str = "") -> ChangeReport:
    """Mark the change's items done and move it to ``changes/archive/<date>-<name>/``.

    Refuses unless ``implementation.md`` is ``approved`` by the human, and while a task is open.
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
    if change.implementation is None:
        raise ChangeError(
            f"{change.path} has no {IMPLEMENTATION_FILE} (state: {change.state.replace('_', ' ')}); "
            "nothing is archived without your approval of the implementation"
        )
    if not change.approved:
        raise ChangeError(
            f"{change.implementation_file} is {change.implementation!r}, not 'approved' "
            f"(state: {change.state.replace('_', ' ')}); nothing is archived without your approval"
        )
    for where, status in ((change.design_file, change.design), (change.tasks_file, change.tasks)):
        if status is not None and status != "approved":
            raise ChangeError(
                f"{where} is {status!r}, not 'approved': the implementation was approved over a draft; "
                "approve the file or fix it before archiving"
            )
    if change.open_tasks:
        raise ChangeError(
            f"{change.tasks_file} still has {change.open_tasks} open task(s); tick or remove them before archiving"
        )

    report = ChangeReport(action="archived", name=name)
    stamp = when or date.today().isoformat()
    source = root / change.path
    target = root / config.paths["changes"] / ARCHIVE_DIR / f"{stamp}-{name}"
    if target.exists():
        raise ChangeError(f"{target.relative_to(root).as_posix()} already exists")

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
