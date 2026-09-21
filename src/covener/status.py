"""``covener status``: a deterministic overview of the repository, ending with what to do next."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import states
from .config import Config
from .repo import ItemKey, Repository, load_repository
from .validate import PLACEHOLDER_MARKERS as PLACEHOLDERS
from .validate import Report, validate


@dataclass
class StatusSnapshot:
    root: str
    vision: str
    specs: dict[str, int]  # status -> count
    domains: dict[str, int]  # spec count per domain folder
    skills: list[dict[str, Any]]  # name, template (still the shipped template)
    bugs: dict[str, int]
    tasks: dict[str, int]
    backlog: list[dict[str, Any]]  # kind, id, domain, priority
    changes: list[dict[str, Any]]  # open changes: name, status, state, items, checklist, design
    done: list[dict[str, str]]  # kind, id, change, closed
    pending_human_review: int
    pending_spec_approval: int
    errors: int
    warnings: int
    actions: list[str] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)
    domain: str | None = None  # set when the snapshot is filtered to one domain

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "domain": self.domain,
            "product": {"vision": self.vision},
            "specs": self.specs,
            "domains": self.domains,
            "skills": self.skills,
            "bugs": self.bugs,
            "tasks": self.tasks,
            "backlog": self.backlog,
            "changes": self.changes,
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


def _counts(repo: Repository, kind: str, keep: Any) -> dict[str, int]:
    allowed = states.ITEM_STATES[kind]
    items = [i for i in repo.of_kind(kind) if keep(i.key)]
    counter = Counter(i.status if i.status in allowed else "invalid" for i in items)
    result = {"total": len(items)}
    result.update({state: counter.get(state, 0) for state in allowed})
    if counter.get("invalid"):
        result["invalid"] = counter["invalid"]
    return result


def build_snapshot(repo: Repository, report: Report, domain: str | None = None) -> StatusSnapshot:
    def keep(key: ItemKey) -> bool:
        return domain is None or repo.domain_of(key) == domain

    vision_state = "OK"
    if not repo.vision_exists:
        vision_state = "MISSING"
    elif not repo.vision_text.strip():
        vision_state = "EMPTY"
    elif report.count("vision.placeholder"):
        vision_state = "TEMPLATE"

    changes: list[dict[str, Any]] = []
    awaiting = 0
    for change in repo.open_changes():
        if domain is not None and change.items and not any(keep(key) for key in change.items):
            continue
        awaiting += change.state in {"awaiting_feedback", "awaiting_design"}
        changes.append(
            {
                "name": change.name,
                "status": change.status,
                "state": change.state,
                "items": [f"{kind} {item_id}" for kind, item_id in change.items],
                "checklist": list(change.checklist),
                "design": change.has_design,
            }
        )

    done: list[dict[str, str]] = []
    for item in repo.items:
        if item.status == "done" and keep(item.key):
            approving = [c for c in repo.changes_of(item.key) if c.approved]
            last = approving[-1] if approving else None
            done.append(
                {
                    "kind": item.kind,
                    "id": item.id,
                    "change": last.name if last else "",
                    "closed": last.closed if last else "",
                }
            )

    specs = _counts(repo, "spec", keep)
    return StatusSnapshot(
        root=str(repo.root),
        vision=vision_state,
        specs=specs,
        domains={d: n for d, n in repo.domains().items() if domain is None or d == domain},
        skills=[
            {"name": skill.name or skill.folder, "template": any(m in skill.body for m in PLACEHOLDERS)}
            for skill in repo.skills
        ],
        bugs=_counts(repo, "bug", keep),
        tasks=_counts(repo, "task", keep),
        backlog=[
            {"kind": i.kind, "id": i.id, "domain": repo.domain_of(i.key), "priority": i.priority}
            for i in repo.backlog()
            if keep(i.key)
        ],
        changes=changes,
        done=done,
        pending_human_review=awaiting,
        pending_spec_approval=specs.get("draft", 0),
        errors=len(report.errors),
        warnings=len(report.warnings),
        actions=[
            action
            for action in report.actions
            if domain is None
            or not report.action_items.get(action)
            or any(keep(key) for key in report.action_items[action])
        ],
        issues=[{"level": i.level, "code": i.code, "path": i.path, "message": i.message} for i in report.issues],
        domain=domain,
    )


def _count_lines(title: str, counts: dict[str, int]) -> list[str]:
    return [title] + [f"  {key.capitalize()}: {value}" for key, value in counts.items()]


def render_text(snapshot: StatusSnapshot, verbose: bool = False) -> str:
    lines: list[str] = ["Covener" + (f" (domain: {snapshot.domain})" if snapshot.domain else "")]
    lines += ["", "Product", f"  Vision: {snapshot.vision}", ""]
    lines += _count_lines("Specs", snapshot.specs)
    if snapshot.domains:
        lines.append("  Domains: " + ", ".join(f"{d} {n}" for d, n in snapshot.domains.items()))
    for title, counts in (("Bugs", snapshot.bugs), ("Tasks", snapshot.tasks)):
        if counts["total"]:
            lines += [""] + _count_lines(title, counts)
    if snapshot.skills:
        marks = ", ".join(f"{s['name']}{' (template)' if s['template'] else ''}" for s in snapshot.skills)
        lines += ["", f"Skills: {marks}"]
    lines += ["", "Backlog", f"  Items: {len(snapshot.backlog)}"]
    for entry in snapshot.backlog:
        lines.append(f"  - {entry['kind']} {entry['id']} (priority {entry['priority']})")
    lines += ["", "Changes"]
    if snapshot.changes:
        for change in snapshot.changes:
            done_n, total = change["checklist"]
            progress = f", checklist {done_n}/{total}" if total else ""
            design = ", design" if change["design"] else ""
            lines.append(
                f"  {change['name']} ({change['status']}): {change['state'].replace('_', ' ')}{progress}{design}"
            )
            for item in change["items"]:
                lines.append(f"    - {item}")
    else:
        lines.append("  Open: none")
    if snapshot.done:
        lines += ["", "Done"]
        for entry in snapshot.done:
            when = f" {entry['closed']}" if entry["closed"] else ""
            where = f"{entry['change']}{when}" if entry["change"] else "no approving change"
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


def compute(root: Path, config: Config, domain: str | None = None) -> tuple[Repository, Report, StatusSnapshot]:
    repo = load_repository(root, config)
    report = validate(repo)
    return repo, report, build_snapshot(repo, report, domain)
