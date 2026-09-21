"""Deterministic checks over a loaded :class:`~covener.repo.Repository`.

No model is involved. Errors protect traceability and human authority and fail
``covener status --strict``. Warnings are hygiene. Actions are what to do next.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import states
from .repo import SKILL_NAME_RE, ItemKey, Repository
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
                f"{item.kind} is 'done' but no change work log ends with 'Approved: Yes' for it",
            )
        if item.ready and not open_changes and item.kind == "bug":
            report.act(f"Start a change for bug {item.id}: covener change start <name> --bug {item.id}", item.key)


def _check_changes(repo: Repository, report: Report) -> None:
    seen: dict[str, str] = {}
    for change in repo.changes:
        where = f"{change.path}/change.md"
        if change.name in seen:
            report.error("change.duplicate-name", where, f"another change is already called {change.name!r}")
        seen[change.name] = change.path
        if change.status not in states.CHANGE_STATES:
            report.error(
                "change.invalid-status",
                where,
                f"status {change.status or 'missing'!r} is not one of {', '.join(states.CHANGE_STATES)}",
            )
            continue
        if change.archived and change.status != "done":
            report.error("change.archived-open", where, f"change is in the archive but its status is {change.status!r}")
        elif change.status == "done" and not change.archived:
            report.act(f"Archive {change.name}: covener change archive {change.name}", *change.items)
        if not change.items:
            report.warning("change.no-items", where, "change lists no spec, bug or task")
        if not change.has_work_log:
            report.error("change.no-work-log", change.path, "change has no work.md")
        state = change.state
        if change.status == "done":
            # History: only the approval rule applies; items may have moved on since.
            if not change.approved:
                report.error(
                    "change.done-without-approval",
                    where,
                    f"change is 'done' but {change.work_file} does not end with 'Approved: Yes' "
                    f"(state: {state.replace('_', ' ')})",
                )
            else:
                for key in change.items:
                    item = repo.item_by_key.get(key)
                    if item is not None and item.status != "done":
                        report.warning(
                            f"{key[0]}.not-done",
                            item.path,
                            f"work approved in change {change.name} but status is {item.status!r}",
                        )
            continue
        for key in change.items:
            kind, item_id = key
            item = repo.item_by_key.get(key)
            if item is None:
                report.error("change.unknown-item", where, f"lists unknown {kind} {item_id!r}")
                continue
            if not item.ready and item.status != "done":
                report.error(
                    "change.item-not-ready",
                    where,
                    f"{item.path} is {item.status!r}; a change only takes {states.READY_STATE[kind]} {kind}s",
                )
        if state == "awaiting_design":
            report.act(f"Review the design of change {change.name} in {change.path}/design.md", *change.items)
        elif state == "awaiting_feedback":
            report.act(f"Give feedback on change {change.name} in {change.work_file}", *change.items)
        elif state == "changes_requested":
            report.act(f"Agents: rework {change.name} from the feedback in {change.work_file}", *change.items)
        elif state == "approved" and change.status != "done":
            report.act(f"Close {change.name}: your approval is in {change.work_file}", *change.items)
        elif change.status == "review" and state in {"not_started", "in_progress"}:
            report.warning("change.review-without-work", where, "change is in review but its work log has no entry")


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
