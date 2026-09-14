"""Deterministic checks over a loaded :class:`~covener.repo.Repository`.

No model is involved. Errors protect traceability and human authority and fail
``covener status --strict``. Warnings are hygiene. Actions are what to do next.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import states
from .repo import Repository
from .roles import ROLE_KEYS

PLACEHOLDER_MARKERS: tuple[str, ...] = ("<!-- TODO", "TODO:", "{{")


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    code: str
    path: str
    message: str


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    def error(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("error", code, path, message))

    def warning(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("warning", code, path, message))

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    def count(self, *codes: str) -> int:
        wanted = set(codes)
        return sum(1 for issue in self.issues if issue.code in wanted)


def _check_vision(repo: Repository, report: Report) -> None:
    if not repo.vision_exists:
        report.error("vision.missing", repo.vision_path, "product vision file is missing")
    elif not repo.vision_text.strip():
        report.error("vision.empty", repo.vision_path, "product vision is empty")
    elif any(marker in repo.vision_text for marker in PLACEHOLDER_MARKERS):
        report.warning("vision.placeholder", repo.vision_path, "vision still contains template placeholders")
        report.actions.append(f"Fill in {repo.vision_path}")


def _check_agents(repo: Repository, report: Report) -> None:
    by_name = {agent.name for agent in repo.agents if agent.name}
    for agent in repo.agents:
        if not agent.name or not agent.description:
            report.error("agent.incomplete", agent.path, "agent definition needs 'name' and 'description'")
        elif not agent.body.strip():
            report.error("agent.empty", agent.path, "agent definition has an empty body (system prompt)")
    for role in ROLE_KEYS:
        name = repo.config.agents[role]
        if name is not None and name not in by_name:
            report.error(
                "agent.missing",
                f"{repo.config.paths['agents']}/{name}.md",
                f"config maps role '{role}' to agent '{name}' but no such definition exists",
            )


def _check_items(repo: Repository, report: Report) -> None:
    for item in repo.items:
        allowed = states.ITEM_STATES[item.kind]
        if item.status not in allowed:
            report.error(
                f"{item.kind}.invalid-status",
                item.path,
                f"status {item.status or 'missing'!r} is not one of {', '.join(allowed)}",
            )
            continue
        if item.kind == "spec" and item.status == "draft":
            report.actions.append(f"Review and approve {item.path} (draft)")
        if item.status == states.READY_STATE[item.kind] and any(m in item.body for m in PLACEHOLDER_MARKERS):
            report.warning(f"{item.kind}.placeholder", item.path, f"{item.kind} still contains template placeholders")
        open_ = repo.sprints_of(item.key, open_only=True)
        if len(open_) > 1:
            report.error(
                f"{item.kind}.in-several-sprints",
                item.path,
                "listed in more than one open sprint: " + ", ".join(s.id for s in open_),
            )
        for reference in item.references:
            target = reference.split("#", 1)[0]
            if "/" in target and not target.startswith(("http://", "https://")) and not (repo.root / target).is_file():
                report.warning(
                    f"{item.kind}.reference-missing",
                    item.path,
                    f"references {reference!r} but that file does not exist",
                )
        if item.status == "done" and not any(s.work_state(item.key) == "approved" for s in repo.sprints_of(item.key)):
            report.error(
                f"{item.kind}.done-without-approval",
                item.path,
                f"{item.kind} is 'done' but no sprint work log ends with 'Approved: Yes' for it",
            )


def _check_sprints(repo: Repository, report: Report) -> None:
    by_owner: dict[str, list[str]] = {}
    for sprint in repo.open_sprints():
        by_owner.setdefault(sprint.owner, []).append(sprint.id)
    for owner, ids in by_owner.items():
        if len(ids) > 1:
            who = f"owner '{owner}'" if owner else "no owner"
            report.warning(
                "sprint.multiple-open",
                repo.config.paths["sprints"],
                f"{len(ids)} open sprints with {who}: {', '.join(ids)} (fine for a hotfix; otherwise close one first)",
            )
    for sprint in repo.sprints:
        where = f"{sprint.path}/sprint.md"
        if sprint.status not in states.SPRINT_STATES:
            report.error(
                "sprint.invalid-status",
                where,
                f"status {sprint.status or 'missing'!r} is not one of {', '.join(states.SPRINT_STATES)}",
            )
            continue
        if not sprint.owner:
            report.warning("sprint.no-owner", where, "sprint has no 'owner'; needed to work in a team")
        if sprint.archived and sprint.status != "closed":
            report.error("sprint.archived-open", where, f"sprint is in the archive but its status is {sprint.status!r}")
        elif sprint.status == "closed" and not sprint.archived:
            report.actions.append(f"Move {sprint.path} to sprints/archive/<YYYY-MM-DD>-{sprint.id} (closed)")
        if not sprint.items:
            report.warning("sprint.empty", where, "sprint lists no specs, bugs or tasks")
        for key in sprint.items:
            kind, item_id = key
            work_file = sprint.work_file(key)
            state = sprint.work_state(key)
            if sprint.status == "closed":
                # History: only the approval rule applies; the item may have moved on since.
                if state != "approved":
                    report.error(
                        "sprint.closed-without-approval",
                        where,
                        f"sprint is closed but {kind} {item_id} was not approved in {work_file} "
                        f"(state: {state.replace('_', ' ')})",
                    )
                else:
                    item = repo.item_by_key.get(key)
                    if item is not None and item.status != "done":
                        report.warning(
                            f"{kind}.not-done",
                            item.path,
                            f"work approved in closed {sprint.id} but status is {item.status!r}",
                        )
                continue
            item = repo.item_by_key.get(key)
            if item is None:
                report.error("sprint.unknown-item", where, f"lists unknown {kind} {item_id!r}")
                continue
            ready = states.READY_STATE[kind]
            if item.status not in (ready, "done"):
                report.error(
                    "sprint.item-not-ready",
                    where,
                    f"{item.path} is {item.status!r}; a sprint only takes {ready} {kind}s",
                )
            if state == "awaiting_feedback":
                report.actions.append(f"Give feedback on {kind} {item_id} in {work_file}")
            elif state == "changes_requested":
                report.actions.append(f"Agents: rework {kind} {item_id} from the feedback in {work_file}")
            elif sprint.status == "review" and state in {"not_started", "in_progress"}:
                report.warning(
                    "sprint.review-without-work", where, f"sprint is in review but {kind} {item_id} has no work"
                )
        if sprint.status == "review" and sprint.items and all(sprint.work_state(k) == "approved" for k in sprint.items):
            report.actions.append(f"Close {sprint.id}: everything is approved")
        if sprint.status != "closed":
            for key in sprint.work:
                if key not in sprint.items:
                    report.warning(
                        "work.not-in-sprint",
                        sprint.work_files[key],
                        f"work log for {key[0]} {key[1]!r} but the sprint does not list it (carry-over?)",
                    )


def validate(repo: Repository) -> Report:
    report = Report()
    for problem in repo.problems:
        report.error("parse", problem.path, problem.message)
    _check_vision(repo, report)
    _check_agents(repo, report)
    _check_items(repo, report)
    _check_sprints(repo, report)
    report.actions = list(dict.fromkeys(report.actions))
    return report
