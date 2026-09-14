"""Read the Covener artefacts of a repository into plain data structures.

Everything here is deterministic file parsing. No LLM is involved.

Layout::

    specs/vision.md                 product intent
    specs/<id>.md                   what the product is        (title, status, epic, priority)
    bugs/<id>.md                    what is wrong              (title, status, epic, priority)
    tasks/<id>.md                   work that changes neither  (title, status, epic, priority)
    sprints/<name>/sprint.md        owner, status, specs: [...], bugs: [...], tasks: [...]
    sprints/<name>/<kind>s/<id>.md  work log of an item in that sprint: checklist, entries, feedback
    sprints/archive/YYYY-MM-DD-<name>/   closed sprints
    agents/<name>.md                one file per agent
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import frontmatter
from .config import CONFIG_RELATIVE_PATH, Config
from .states import KINDS, READY_STATE

ENTRY_HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
APPROVED_RE = re.compile(r"^(?:\*\*)?Approved(?:\*\*)?\s*:\s*(?:\*\*)?\s*(?P<value>[A-Za-z]+)", re.IGNORECASE)
TASK_RE = re.compile(r"^\s*[-*]\s+\[(?P<done>[ xX])\]\s+\S")
RESERVED_NAMES: frozenset[str] = frozenset({"vision", "template", "readme"})
IGNORED_AGENT_FILES: frozenset[str] = frozenset({"README.MD", "TEMPLATE.MD"})
ARCHIVE_DIR = "archive"
KINDS_IN_SPRINT_ORDER: tuple[str, ...] = ("spec", "bug", "task")
PRIORITY_WORDS: dict[str, int] = {"high": 1, "medium": 2, "normal": 2, "low": 3}

ItemKey = tuple[str, str]  # (kind, id)


def find_repo_root(start: Path | None = None) -> Path:
    """Nearest ancestor holding ``.covener/config.yaml``, then the nearest ``.git``, else ``start``."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / CONFIG_RELATIVE_PATH).exists():
            return candidate
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def is_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def _as_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [_as_str(item) for item in value if _as_str(item)]
    return [_as_str(value)]


def _priority(value: Any) -> int:
    if value is None or value == "" or isinstance(value, bool):
        return 2
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    return int(text) if text.isdigit() else PRIORITY_WORDS.get(text, 2)


@dataclass
class ParseProblem:
    path: str
    message: str


@dataclass
class WorkEntry:
    """A ``## ...`` section of a work log, in file order."""

    title: str
    kind: str  # "feedback" | "work" | "checklist"
    approved: bool | None = None  # feedback only
    text: str = ""


@dataclass
class Item:
    """A specification (what the product is) or a bug (what is wrong)."""

    kind: str  # "spec" | "bug" | "task"
    path: str  # repository-relative, posix
    id: str  # path under specs/ or bugs/ without .md
    title: str
    status: str
    epic: str = ""
    priority: int = 2
    references: list[str] = field(default_factory=list)  # knowledge/<file>.md#page-N, norm ids, URLs
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def key(self) -> ItemKey:
        return (self.kind, self.id)

    @property
    def label(self) -> str:
        return f"{self.kind} {self.id}"


@dataclass
class Sprint:
    path: str  # directory, repository-relative
    id: str  # directory name
    owner: str
    status: str
    goal: str = ""
    items: list[ItemKey] = field(default_factory=list)  # in sprint.md order: specs, bugs, tasks
    opened: str = ""
    closed: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    work: dict[ItemKey, list[WorkEntry]] = field(default_factory=dict)
    work_files: dict[ItemKey, str] = field(default_factory=dict)
    checklist: dict[ItemKey, tuple[int, int]] = field(default_factory=dict)  # (done, total) steps
    archived: bool = False

    def work_file(self, key: ItemKey) -> str:
        return self.work_files.get(key, f"{self.path}/{key[0]}s/{key[1]}.md")

    def work_state(self, key: ItemKey) -> str:
        """Derived state of an item's work in this sprint (see states.WORK_STATES)."""
        entries = [e for e in self.work.get(key, []) if e.kind != "checklist"]
        if not entries:
            return "not_started"
        last = entries[-1]
        if last.kind == "feedback":
            return "approved" if last.approved else "changes_requested"
        return "awaiting_feedback" if self.status == "review" else "in_progress"


@dataclass
class AgentDefinition:
    path: str
    name: str
    description: str
    meta: dict[str, Any]
    body: str


@dataclass
class Repository:
    root: Path
    config: Config
    vision_path: str
    vision_exists: bool = False
    vision_text: str = ""
    items: list[Item] = field(default_factory=list)
    sprints: list[Sprint] = field(default_factory=list)
    agents: list[AgentDefinition] = field(default_factory=list)
    problems: list[ParseProblem] = field(default_factory=list)

    @property
    def item_by_key(self) -> dict[ItemKey, Item]:
        return {item.key: item for item in self.items}

    def of_kind(self, kind: str) -> list[Item]:
        return [item for item in self.items if item.kind == kind]

    def open_sprints(self) -> list[Sprint]:
        return [sprint for sprint in self.sprints if sprint.status != "closed"]

    def sprints_of(self, key: ItemKey, open_only: bool = False) -> list[Sprint]:
        return [s for s in self.sprints if key in s.items and (not open_only or s.status != "closed")]

    def backlog(self) -> list[Item]:
        """Ready items not in an open sprint: open bugs first, then specs and tasks by priority."""
        taken = {key for sprint in self.open_sprints() for key in sprint.items}
        available = [i for i in self.items if i.status == READY_STATE[i.kind] and i.key not in taken]
        return sorted(available, key=lambda i: (i.kind != "bug", i.priority, i.epic, KINDS.index(i.kind), i.id))


def _read(path: Path, rel: str, problems: list[ParseProblem]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        problems.append(ParseProblem(rel, f"file is not valid UTF-8 ({exc.reason} at byte {exc.start})"))
        return None


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _document(path: Path, rel: str, problems: list[ParseProblem]) -> frontmatter.Document | None:
    text = _read(path, rel, problems)
    if text is None:
        return None
    try:
        return frontmatter.parse(text)
    except frontmatter.FrontMatterError as exc:
        problems.append(ParseProblem(rel, str(exc)))
        return None


def _first_heading(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def count_tasks(text: str) -> tuple[int, int]:
    """Count GitHub-style task list items (``- [ ]`` / ``- [x]``) anywhere in a work log."""
    done = total = 0
    for line in text.splitlines():
        match = TASK_RE.match(line)
        if match:
            total += 1
            done += match.group("done").lower() == "x"
    return done, total


def parse_work(text: str) -> list[WorkEntry]:
    """Parse a work log: ``## ...`` entries in order. ``## Feedback`` entries are human decisions
    and carry ``Approved: Yes|No``; ``## Checklist`` (or ``## Tasks``) is the checklist; everything
    else is agent work."""
    entries: list[WorkEntry] = []
    current: WorkEntry | None = None
    lines: list[str] = []

    def flush() -> None:
        nonlocal current, lines
        if current is not None:
            current.text = "\n".join(lines).strip()
            if current.kind == "feedback":
                for line in lines:
                    match = APPROVED_RE.match(line.strip())
                    if match:
                        current.approved = match.group("value").lower() in {"yes", "true", "approved"}
                if current.approved is None:
                    current.approved = False
            entries.append(current)
        current, lines = None, []

    for line in text.splitlines():
        heading = ENTRY_HEADING_RE.match(line)
        if heading:
            flush()
            title = heading.group("title")
            lowered = title.lower()
            if lowered.startswith("feedback"):
                kind = "feedback"
            elif lowered.startswith(("checklist", "tasks")):
                kind = "checklist"
            else:
                kind = "work"
            current = WorkEntry(title=title, kind=kind)
            continue
        if line.startswith("# "):
            flush()
            continue
        if current is not None:
            lines.append(line.rstrip())
    flush()
    return entries


def normalise_ref(reference: str, directory: str) -> str:
    """``specs/payments/x.md``, ``payments/x.md`` and ``payments/x`` all mean the id ``payments/x``."""
    text = reference.strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    text = text.strip("/")
    if text.endswith(".md"):
        text = text[:-3]
    prefix = directory.strip("/") + "/"
    if text.startswith(prefix):
        text = text[len(prefix) :]
    return text


def load_items(root: Path, kind: str, directory: Path, problems: list[ParseProblem]) -> list[Item]:
    """One file per item; the path under the directory without ``.md`` is the id."""
    items: list[Item] = []
    if not directory.is_dir():
        return items
    for path in sorted(directory.rglob("*.md")):
        relative = path.relative_to(directory)
        if any(part.startswith(".") for part in relative.parts) or path.stem.lower() in RESERVED_NAMES:
            continue
        rel = _rel(root, path)
        document = _document(path, rel, problems)
        if document is None:
            continue
        if not document.has_front_matter:
            problems.append(ParseProblem(rel, f"{kind} has no front matter (title/status)"))
            continue
        meta = document.meta
        item_id = relative.with_suffix("").as_posix()
        items.append(
            Item(
                kind=kind,
                path=rel,
                id=item_id,
                title=_as_str(meta.get("title")) or _first_heading(document.body) or item_id,
                status=_as_str(meta.get("status")),
                epic=_as_str(meta.get("epic")),
                priority=_priority(meta.get("priority")),
                references=_as_list(meta.get("references")),
                meta=meta,
                body=document.body,
            )
        )
    return items


def _sprint_dirs(sprints_dir: Path) -> list[tuple[Path, bool]]:
    if not sprints_dir.is_dir():
        return []
    result: list[tuple[Path, bool]] = []
    for directory in sorted(p for p in sprints_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if directory.name.upper() == "TEMPLATE":
            continue
        if directory.name == ARCHIVE_DIR:
            result += [(p, True) for p in sorted(directory.iterdir()) if p.is_dir() and not p.name.startswith(".")]
            continue
        result.append((directory, False))
    return result


def load_sprints(root: Path, config: Config, problems: list[ParseProblem]) -> list[Sprint]:
    sprints: list[Sprint] = []
    for directory, archived in _sprint_dirs(root / config.paths["sprints"]):
        rel = _rel(root, directory)
        sprint_file = directory / "sprint.md"
        if not sprint_file.is_file():
            problems.append(ParseProblem(rel, "sprint directory has no sprint.md"))
            continue
        document = _document(sprint_file, f"{rel}/sprint.md", problems)
        if document is None:
            continue
        if not document.has_front_matter:
            problems.append(ParseProblem(f"{rel}/sprint.md", "sprint.md has no front matter (owner/status/items)"))
            continue
        meta = document.meta
        items: list[ItemKey] = []
        for kind in KINDS_IN_SPRINT_ORDER:
            for ref in _as_list(meta.get(f"{kind}s")):
                items.append((kind, normalise_ref(ref, config.paths[f"{kind}s"])))
        sprint = Sprint(
            path=rel,
            id=directory.name,
            owner=_as_str(meta.get("owner")),
            status=_as_str(meta.get("status")),
            goal=_as_str(meta.get("goal")),
            items=items,
            opened=_as_str(meta.get("opened")),
            closed=_as_str(meta.get("closed")),
            meta=meta,
            archived=archived,
        )
        for kind in KINDS_IN_SPRINT_ORDER:
            work_dir = directory / f"{kind}s"
            if not work_dir.is_dir():
                continue
            for work_file in sorted(work_dir.rglob("*.md")):
                inner = work_file.relative_to(work_dir)
                if any(part.startswith(".") for part in inner.parts):
                    continue
                key = (kind, inner.with_suffix("").as_posix())
                text = _read(work_file, _rel(root, work_file), problems)
                if text is not None:
                    sprint.work[key] = parse_work(text)
                    sprint.work_files[key] = _rel(root, work_file)
                    sprint.checklist[key] = count_tasks(text)
        sprints.append(sprint)
    sprints.sort(key=lambda s: (s.opened or "", s.id))
    return sprints


def load_agents(root: Path, agents_dir: Path, problems: list[ParseProblem]) -> list[AgentDefinition]:
    agents: list[AgentDefinition] = []
    if not agents_dir.is_dir():
        return agents
    for path in sorted(agents_dir.glob("*.md")):
        if path.name.upper() in IGNORED_AGENT_FILES:
            continue
        rel = _rel(root, path)
        document = _document(path, rel, problems)
        if document is None:
            continue
        agents.append(
            AgentDefinition(
                path=rel,
                name=_as_str(document.meta.get("name")),
                description=_as_str(document.meta.get("description")),
                meta=document.meta,
                body=document.body,
            )
        )
    return agents


def load_repository(root: Path, config: Config) -> Repository:
    problems: list[ParseProblem] = []
    vision = root / config.paths["vision"]
    repository = Repository(
        root=root, config=config, vision_path=config.paths["vision"], vision_exists=vision.is_file(), problems=problems
    )
    if vision.is_file():
        repository.vision_text = _read(vision, config.paths["vision"], problems) or ""
    repository.items = [
        item
        for kind in KINDS_IN_SPRINT_ORDER
        for item in load_items(root, kind, root / config.paths[f"{kind}s"], problems)
    ]
    repository.sprints = load_sprints(root, config, problems)
    repository.agents = load_agents(root, root / config.paths["agents"], problems)
    return repository
