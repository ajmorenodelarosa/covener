"""``covener status``: a deterministic overview of the repository, ending with what to do next."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import states
from .config import Config
from .repo import Repository, load_repository
from .validate import Report, validate


@dataclass
class StatusSnapshot:
    root: str
    vision: str
    specs: dict[str, int]  # status -> count
    bugs: dict[str, int]
    tasks: dict[str, int]
    backlog: list[dict[str, Any]]  # kind, id, epic, priority
    sprints: list[dict[str, Any]]  # open sprints: id, owner, status, items [{kind, id, state, tasks}]
    done: list[dict[str, str]]  # kind, id, sprint, closed
    pending_human_review: int
    pending_spec_approval: int
    errors: int
    warnings: int
    actions: list[str] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "product": {"vision": self.vision},
            "specs": self.specs,
            "bugs": self.bugs,
            "tasks": self.tasks,
            "backlog": self.backlog,
            "sprints": self.sprints,
            "done": self.done,
            "governance": {
                "pending_human_review": self.pending_human_review,
                "pending_spec_approval": self.pending_spec_approval,
                "errors": self.errors,
                "warnings": self.warnings,
            },
            "actions": self.actions,
            "issues": self.issues,
        }


def _counts(repo: Repository, kind: str) -> dict[str, int]:
    allowed = states.ITEM_STATES[kind]
    counter = Counter(i.status if i.status in allowed else "invalid" for i in repo.of_kind(kind))
    result = {"total": len(repo.of_kind(kind))}
    result.update({state: counter.get(state, 0) for state in allowed})
    if counter.get("invalid"):
        result["invalid"] = counter["invalid"]
    return result


def build_snapshot(repo: Repository, report: Report) -> StatusSnapshot:
    vision_state = "OK"
    if not repo.vision_exists:
        vision_state = "MISSING"
    elif not repo.vision_text.strip():
        vision_state = "EMPTY"
    elif report.count("vision.placeholder"):
        vision_state = "TEMPLATE"

    sprints: list[dict[str, Any]] = []
    awaiting = 0
    for sprint in repo.open_sprints():
        entries = [
            {
                "kind": k,
                "id": i,
                "state": sprint.work_state((k, i)),
                "checklist": list(sprint.checklist.get((k, i), (0, 0))),
            }
            for k, i in sprint.items
        ]
        awaiting += sum(1 for e in entries if e["state"] == "awaiting_feedback")
        sprints.append({"id": sprint.id, "owner": sprint.owner, "status": sprint.status, "items": entries})

    done: list[dict[str, str]] = []
    for item in repo.items:
        if item.status == "done":
            approving = [s for s in repo.sprints_of(item.key) if s.work_state(item.key) == "approved"]
            last = approving[-1] if approving else None
            done.append(
                {
                    "kind": item.kind,
                    "id": item.id,
                    "sprint": last.id if last else "",
                    "closed": last.closed if last else "",
                }
            )

    specs = _counts(repo, "spec")
    return StatusSnapshot(
        root=str(repo.root),
        vision=vision_state,
        specs=specs,
        bugs=_counts(repo, "bug"),
        tasks=_counts(repo, "task"),
        backlog=[{"kind": i.kind, "id": i.id, "epic": i.epic, "priority": i.priority} for i in repo.backlog()],
        sprints=sprints,
        done=done,
        pending_human_review=awaiting,
        pending_spec_approval=specs.get("draft", 0),
        errors=len(report.errors),
        warnings=len(report.warnings),
        actions=list(report.actions),
        issues=[{"level": i.level, "code": i.code, "path": i.path, "message": i.message} for i in report.issues],
    )


def _count_lines(title: str, counts: dict[str, int]) -> list[str]:
    lines = [title]
    for key, value in counts.items():
        lines.append(f"  {key.capitalize()}: {value}")
    return lines


def render_text(snapshot: StatusSnapshot, verbose: bool = False) -> str:
    lines: list[str] = ["Covener", "", "Product", f"  Vision: {snapshot.vision}", ""]
    lines += _count_lines("Specs", snapshot.specs) + [""] + _count_lines("Bugs", snapshot.bugs)
    if snapshot.tasks["total"]:
        lines += [""] + _count_lines("Tasks", snapshot.tasks)
    lines += ["", "Backlog", f"  Items: {len(snapshot.backlog)}"]
    group = None
    for entry in snapshot.backlog:
        label = "bugs" if entry["kind"] == "bug" else f"{entry['epic'] or 'no epic'}"
        if label != group:
            group = label
            lines.append(f"  [{label}]")
        kind = "" if entry["kind"] == "bug" else f"{entry['kind']} "
        lines.append(f"    - {kind}{entry['id']} (priority {entry['priority']})")
    lines += ["", "Sprints"]
    if snapshot.sprints:
        for sprint in snapshot.sprints:
            approved = sum(1 for e in sprint["items"] if e["state"] == "approved")
            owner = f", {sprint['owner']}" if sprint["owner"] else ""
            lines.append(f"  {sprint['id']} ({sprint['status']}{owner}): approved {approved}/{len(sprint['items'])}")
            for entry in sprint["items"]:
                done_n, total = entry["checklist"]
                progress = f", checklist {done_n}/{total}" if total else ""
                lines.append(f"    - {entry['kind']} {entry['id']}: {entry['state'].replace('_', ' ')}{progress}")
    else:
        lines.append("  Open: none")
    if snapshot.done:
        lines += ["", "Done"]
        for entry in snapshot.done:
            when = f" {entry['closed']}" if entry["closed"] else ""
            where = f"{entry['sprint']}{when}" if entry["sprint"] else "no approving sprint"
            lines.append(f"  - {entry['kind']} {entry['id']} ({where})")
    lines += ["", "Governance"]
    lines.append(f"  Pending human review: {snapshot.pending_human_review}")
    lines.append(f"  Pending spec approval: {snapshot.pending_spec_approval}")
    lines.append(f"  Errors: {snapshot.errors}")
    lines.append(f"  Warnings: {snapshot.warnings}")
    if snapshot.actions:
        lines += ["", "Next"] + [f"  * {action}" for action in snapshot.actions]
    shown = [issue for issue in snapshot.issues if verbose or issue["level"] == "error"]
    if shown:
        lines += ["", "Issues"]
        lines += [f"  {i['level'].upper():7} {i['code']:30} {i['path']}: {i['message']}" for i in shown]
        hidden = len(snapshot.issues) - len(shown)
        if hidden:
            lines.append(f"  ({hidden} warning(s) hidden; use --verbose to show them)")
    return "\n".join(lines)


def render_json(snapshot: StatusSnapshot) -> str:
    return json.dumps(snapshot.to_dict(), indent=2)


def compute(root: Path, config: Config) -> tuple[Repository, Report, StatusSnapshot]:
    repo = load_repository(root, config)
    report = validate(repo)
    return repo, report, build_snapshot(repo, report)
