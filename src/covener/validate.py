"""Deterministic checks over a loaded :class:`~covener.repo.Repository`.

No model is involved. Errors protect traceability and human authority and fail
``covener status --strict``. Warnings are hygiene. Actions are what to do next.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import states
from .repo import SKILL_NAME_RE, Change, ItemKey, Repository
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
    # The items each action is about, so a domain view keeps only its own next steps.
    action_items: dict[str, list[ItemKey]] = field(default_factory=dict)

    def error(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("error", code, path, message))

    def warning(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("warning", code, path, message))

    def act(self, text: str, *items: ItemKey) -> None:
        self.actions.append(text)
        if items:
            self.action_items.setdefault(text, []).extend(items)

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


def _check_skills(repo: Repository, report: Report) -> None:
    """Skills follow the Agent Skills open standard: name matching the folder, and a description."""
    for skill in repo.skills:
        if not skill.has_skill_file:
            report.warning("skill.no-file", skill.path, "skill folder has no SKILL.md; agents will not see it")
            continue
        if not skill.name or not skill.description:
            report.error("skill.incomplete", skill.path, "SKILL.md needs 'name' and 'description' in its front matter")
            continue
        if skill.name != skill.folder:
            report.error(
                "skill.name-mismatch", skill.path, f"name {skill.name!r} must match the folder {skill.folder!r}"
            )
        if not SKILL_NAME_RE.match(skill.name):
            report.error("skill.invalid-name", skill.path, "name must be lowercase letters, numbers and hyphens")
        if len(skill.description) > 1024:
            report.error("skill.long-description", skill.path, "description must be at most 1024 characters")
        if any(marker in skill.body for marker in PLACEHOLDER_MARKERS):
            report.warning(
                "skill.placeholder", skill.path, "skill is still the template; fill in this project's conventions"
            )
            report.act(f"Fill in {skill.path} with this project's conventions")


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
            report.act(f"Review and approve {item.path} (draft)", item.key)
        if item.ready and any(marker in item.body for marker in PLACEHOLDER_MARKERS):
            report.warning(f"{item.kind}.placeholder", item.path, f"{item.kind} still contains template placeholders")
        if item.spec and ("spec", item.spec) not in repo.item_by_key:
            report.warning(f"{item.kind}.unknown-spec", item.path, f"spec {item.spec!r} does not exist")
        for reference in item.references:
            target = reference.split("#", 1)[0]
            if "/" in target and not target.startswith(("http://", "https://")) and not (repo.root / target).is_file():
                report.warning(
                    f"{item.kind}.reference-missing",
                    item.path,
                    f"references {reference!r} but that file does not exist",
                )
        open_changes = repo.changes_of(item.key, open_only=True)
        if len(open_changes) > 1:
            report.error(
                f"{item.kind}.in-several-changes",
                item.path,
                "listed in more than one open change: " + ", ".join(c.name for c in open_changes),
            )
        if item.status == "done" and not any(c.approved for c in repo.changes_of(item.key)):
            report.error(
                f"{item.kind}.done-without-approval",
                item.path,
                f"{item.kind} is 'done' but no change has an approved implementation for it",
            )
        if item.ready and not open_changes and item.kind == "bug":
            report.act(f"Start a change for bug {item.id}: covener change start <name> --bug {item.id}", item.key)


def _check_change_statuses(change: Change, report: Report) -> bool:
    """Each file of a change carries a status from the model; False when one does not."""
    checks = (
        (change.tasks_file, change.tasks, states.TASKS_STATES, "tasks"),
        (change.design_file, change.design, states.DESIGN_STATES, "design"),
        (change.implementation_file, change.implementation, states.IMPLEMENTATION_STATES, "implementation"),
    )
    valid = True
    for where, status, allowed, label in checks:
        if status is not None and status not in allowed:
            report.error(
                f"change.invalid-{label}-status",
                where,
                f"status {status or 'missing'!r} is not one of {', '.join(allowed)}",
            )
            valid = False
    return valid


def _check_changes(repo: Repository, report: Report) -> None:
    for change in repo.changes:
        if not _check_change_statuses(change, report):
            continue
        if not change.items:
            report.warning("change.no-items", change.tasks_file, "change lists no spec, bug or task")
        if change.archived:
            # History: only the approval rules apply; items may have moved on since.
            drafts = [
                (where, status)
                for where, status in (
                    (change.implementation_file, change.implementation),
                    (change.tasks_file, change.tasks),
                    (change.design_file, change.design),
                )
                if status != "approved" and (status is not None or where == change.implementation_file)
            ]
            if drafts:
                where, status = drafts[0]
                filename = where.rsplit("/", 1)[1]
                report.error(
                    "change.archived-without-approval",
                    where,
                    f"change is in the archive but {filename} is {status or 'missing'!r}, not 'approved'",
                )
                continue
            for key in change.items:
                item = repo.item_by_key.get(key)
                if item is not None and item.status != "done":
                    report.warning(
                        f"{key[0]}.not-done",
                        item.path,
                        f"implementation approved in change {change.name} but status is {item.status!r}",
                    )
            continue
        for key in change.items:
            kind, item_id = key
            item = repo.item_by_key.get(key)
            if item is None:
                report.error("change.unknown-item", change.tasks_file, f"lists unknown {kind} {item_id!r}")
                continue
            if not item.ready and item.status != "done":
                report.error(
                    "change.item-not-ready",
                    change.tasks_file,
                    f"{item.path} is {item.status!r}; a change only takes {states.READY_STATE[kind]} {kind}s",
                )
        # The order of the gates: design before tasks, tasks before code.
        if change.tasks == "approved" and change.design == "draft":
            report.error(
                "change.tasks-before-design",
                change.tasks_file,
                f"tasks are approved while {change.design_file} is still a draft",
            )
        if change.implementation is not None and change.tasks != "approved":
            report.error(
                "change.implementation-before-tasks",
                change.implementation_file,
                f"work started while {change.tasks_file} is still a draft: no code before the tasks are approved",
            )
        failing = [role for role, verdict in change.verdicts.items() if verdict == "fail"]
        if change.implementation == "review" and failing:
            report.error(
                "change.review-with-failing-verdict",
                change.implementation_file,
                f"in review while the latest {' and '.join(failing)} verdict is 'fail'",
            )
            report.act(
                f"Agents: {change.name} is in review with a failing verdict; fix it before asking", *change.items
            )
        if change.approved and change.open_tasks:
            report.warning(
                "change.approved-with-open-tasks",
                change.tasks_file,
                f"implementation approved with {change.open_tasks} open task(s); tick or remove them to archive",
            )
            report.act(
                f"Tick or remove the {change.open_tasks} open task(s) in {change.tasks_file} before archiving "
                f"{change.name}",
                *change.items,
            )
        state = change.state
        if state == "not_started":
            report.act(
                f"Agents: plan change {change.name} in {change.tasks_file} (design.md first if it needs one)",
                *change.items,
            )
        elif state == "awaiting_design":
            report.act(
                f"Review the design of change {change.name}: set status: approved in {change.design_file}",
                *change.items,
            )
        elif state == "awaiting_tasks":
            report.act(
                f"Review the tasks of change {change.name}: set status: approved in {change.tasks_file}", *change.items
            )
        elif state == "in_review" and not failing:
            report.act(
                f"Review the implementation of change {change.name}: set status: approved in "
                f"{change.implementation_file}, or add rework tasks to {change.tasks_file}",
                *change.items,
            )
        elif state == "in_progress" and change.implementation == "review":
            report.act(f"Agents: rework {change.name} from the open tasks in {change.tasks_file}", *change.items)
        elif state == "approved" and not change.open_tasks:
            report.act(f"Archive {change.name}: covener change archive {change.name}", *change.items)


def validate(repo: Repository) -> Report:
    report = Report()
    for problem in repo.problems:
        report.error("parse", problem.path, problem.message)
    _check_vision(repo, report)
    _check_agents(repo, report)
    _check_skills(repo, report)
    _check_items(repo, report)
    _check_changes(repo, report)
    report.actions = list(dict.fromkeys(report.actions))
    return report
