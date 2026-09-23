"""Read the Covener artefacts of a repository into plain data structures.

Everything here is deterministic file parsing. No LLM is involved.

Layout::

    specs/vision.md                     product intent
    specs/[<domain>/]<name>.md          what the product is  (title, status, priority)
    bugs/<id>.md                        what is wrong        (title, status, priority, spec)
    tasks/<id>.md                       work that changes neither (title, status, priority, spec)
    changes/<name>/tasks.md             the unit of work: the items it covers and the plan (status, items)
    changes/<name>/design.md            how it will be built (optional, dies with the change; status)
    changes/<name>/implementation.md    what happened: summary, decisions, QA, review, rework (status)
    changes/archive/YYYY-MM-DD-<name>/  finished changes
    agents/<name>.md                    one file per agent
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
VERDICT_RE = re.compile(r"^(?:\*\*)?Verdict(?:\*\*)?\s*:\s*(?:\*\*)?\s*(?P<value>[A-Za-z][A-Za-z ]*)", re.IGNORECASE)
# Implementation entries whose verdict `status` reads: the title prefix names the role.
VERDICT_ROLES: tuple[str, ...] = ("qa", "review")
CHECK_RE = re.compile(r"^\s*[-*]\s+\[(?P<done>[ xX])\]\s+\S")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_FILE = "SKILL.md"
ITEM_REF_RE = re.compile(r"^(?P<kind>spec|bug|task)\s*[:/]\s*(?P<id>\S+)$", re.IGNORECASE)
RESERVED_NAMES: frozenset[str] = frozenset({"vision", "template", "readme"})
IGNORED_AGENT_FILES: frozenset[str] = frozenset({"README.MD", "TEMPLATE.MD"})
ARCHIVE_DIR = "archive"
TASKS_FILE = "tasks.md"
DESIGN_FILE = "design.md"
IMPLEMENTATION_FILE = "implementation.md"
ARCHIVED_NAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<name>.+)$")
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
    """Read a YAML value as a list of references.

    Accepts ``[a, b]``, ``"a, b"`` and the mapping form YAML produces for
    ``- spec: billing/refunds`` (a one-key dict per entry), which is how a change lists its items.
    """
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, dict):
        return [f"{key}: {_as_str(item)}" for key, item in value.items()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, dict):
                result += [f"{key}: {_as_str(inner)}" for key, inner in item.items()]
            elif _as_str(item):
                result.append(_as_str(item))
        return result
    return [_as_str(value)]


def _priority(value: Any) -> int:
    if value is None or value == "" or isinstance(value, bool):
        return 2
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    return int(text) if text.isdigit() else PRIORITY_WORDS.get(text, 2)


def domain_of_spec_id(spec_id: str) -> str:
    """The domain of a spec is its first folder under specs/ (``billing/refunds`` -> ``billing``)."""
    return spec_id.split("/", 1)[0] if "/" in spec_id else ""


def normalise_ref(reference: str, directory: str) -> str:
    """``specs/billing/x.md``, ``billing/x.md`` and ``billing/x`` all mean the id ``billing/x``."""
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


def parse_item_ref(reference: str, paths: dict[str, str]) -> ItemKey | None:
    """Read ``spec: billing/refunds``, ``bug/rounding`` or ``specs/billing/refunds.md`` as an item key."""
    text = reference.strip()
    match = ITEM_REF_RE.match(text)
    if match:
        kind = match.group("kind").lower()
        return (kind, normalise_ref(match.group("id"), paths[f"{kind}s"]))
    plain = text.replace("\\", "/").lstrip("./").strip("/")
    for kind in KINDS:
        prefix = paths[f"{kind}s"].strip("/") + "/"
        if plain.startswith(prefix):
            return (kind, normalise_ref(plain, paths[f"{kind}s"]))
    return None


@dataclass
class ParseProblem:
    path: str
    message: str


@dataclass
class Entry:
    """A ``## ...`` section of an implementation record, in file order."""

    title: str
    verdict: str | None = None  # QA and Review entries: "pass", "pass with notes" or "fail"
    text: str = ""

    @property
    def role(self) -> str:
        """Which agent's entry this is, for the entries whose verdict counts (``qa`` or ``review``)."""
        lowered = self.title.lower()
        return next((role for role in VERDICT_ROLES if lowered.startswith(role)), "")


@dataclass
class Item:
    """A spec (what the product is), a bug (what is wrong) or a task (work with no requirement)."""

    kind: str
    path: str  # repository-relative, posix
    id: str  # path under its folder without .md
    title: str
    status: str
    priority: int = 2
    spec: str = ""  # bugs and tasks: the spec they relate to, which gives them its domain
    references: list[str] = field(default_factory=list)  # knowledge/<file>.md#page-N, URLs
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def key(self) -> ItemKey:
        return (self.kind, self.id)

    @property
    def label(self) -> str:
        return f"{self.kind} {self.id}"

    @property
    def ready(self) -> bool:
        return self.status == READY_STATE[self.kind]


@dataclass
class Change:
    """A unit of work: a folder whose three files carry their own status.

    ``tasks.md`` (always) lists the items and the plan; ``design.md`` (optional) says how it will be
    built; ``implementation.md`` says what happened. The human approves each in its front matter;
    the change's state is derived from the three and never stored.
    """

    path: str  # directory, repository-relative
    name: str
    items: list[ItemKey] = field(default_factory=list)
    tasks: str = ""  # status of tasks.md
    design: str | None = None  # status of design.md, None when the change has none
    implementation: str | None = None  # status of implementation.md, None until the work starts
    checklist: tuple[int, int] = (0, 0)  # (ticked, total) tasks in tasks.md
    entries: list[Entry] = field(default_factory=list)  # ## sections of implementation.md
    meta: dict[str, Any] = field(default_factory=dict)  # front matter of tasks.md
    archived: bool = False

    @property
    def tasks_file(self) -> str:
        return f"{self.path}/{TASKS_FILE}"

    @property
    def design_file(self) -> str:
        return f"{self.path}/{DESIGN_FILE}"

    @property
    def implementation_file(self) -> str:
        return f"{self.path}/{IMPLEMENTATION_FILE}"

    @property
    def closed(self) -> str:
        """The date an archived change was filed under; empty for an open one."""
        match = ARCHIVED_NAME_RE.match(self.name) if self.archived else None
        return match.group("date") if match else ""

    @property
    def open_tasks(self) -> int:
        ticked, total = self.checklist
        return total - ticked

    @property
    def approved(self) -> bool:
        """The human approved the implementation: the only approval that closes a change."""
        return self.implementation == "approved"

    @property
    def state(self) -> str:
        """Derived state (see states.CHANGE_STATES)."""
        if self.archived:
            return "done"
        if self.design == "draft":
            return "awaiting_design"
        if self.tasks != "approved":
            return "awaiting_tasks" if self.checklist[1] else "not_started"
        if self.approved:
            return "approved"
        # Rework tasks added after review reopen the change until they are ticked.
        if self.implementation == "review" and not self.open_tasks:
            return "in_review"
        return "in_progress"

    @property
    def verdicts(self) -> dict[str, str]:
        """The latest QA and Review verdicts in the record, in that order, when the entries carry one."""
        latest = {entry.role: entry.verdict for entry in self.entries if entry.role and entry.verdict}
        return {role: latest[role] for role in VERDICT_ROLES if role in latest}


@dataclass
class Skill:
    """A folder in ``skills/`` with a SKILL.md, in the Agent Skills open standard."""

    path: str  # repository-relative path of SKILL.md (or of the folder when it is missing)
    folder: str
    name: str = ""
    description: str = ""
    body: str = ""
    has_skill_file: bool = False


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
    changes: list[Change] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    agents: list[AgentDefinition] = field(default_factory=list)
    problems: list[ParseProblem] = field(default_factory=list)

    @property
    def item_by_key(self) -> dict[ItemKey, Item]:
        return {item.key: item for item in self.items}

    def of_kind(self, kind: str) -> list[Item]:
        return [item for item in self.items if item.kind == kind]

    def open_changes(self) -> list[Change]:
        return [change for change in self.changes if not change.archived]

    def changes_of(self, key: ItemKey, open_only: bool = False) -> list[Change]:
        return [c for c in self.changes if key in c.items and (not open_only or not c.archived)]

    def backlog(self) -> list[Item]:
        """Ready items not in an open change: open bugs first, then specs and tasks by priority."""
        taken = {key for change in self.open_changes() for key in change.items}
        available = [i for i in self.items if i.ready and i.key not in taken]
        return sorted(available, key=lambda i: (i.kind != "bug", i.priority, KINDS.index(i.kind), i.id))

    def domain_of(self, key: ItemKey) -> str:
        """A spec's domain is its folder; a bug or task takes the domain of the spec it names."""
        kind, item_id = key
        if kind == "spec":
            return domain_of_spec_id(item_id)
        item = self.item_by_key.get(key)
        return domain_of_spec_id(item.spec) if item and item.spec else ""

    def domains(self) -> dict[str, int]:
        """Spec count per domain folder, in name order."""
        counts: dict[str, int] = {}
        for item in self.of_kind("spec"):
            domain = domain_of_spec_id(item.id)
            if domain:
                counts[domain] = counts.get(domain, 0) + 1
        return dict(sorted(counts.items()))


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


def count_checklist(text: str) -> tuple[int, int]:
    """Count task-list items (``- [ ]`` / ``- [x]``) anywhere in tasks.md."""
    done = total = 0
    for line in text.splitlines():
        match = CHECK_RE.match(line)
        if match:
            total += 1
            done += match.group("done").lower() == "x"
    return done, total


def parse_entries(text: str) -> list[Entry]:
    """Parse an implementation record: ``## ...`` entries in order. ``## QA`` and ``## Review``
    carry ``Verdict: pass|pass with notes|fail``; everything else is the agents' account."""
    entries: list[Entry] = []
    current: Entry | None = None
    lines: list[str] = []

    def flush() -> None:
        nonlocal current, lines
        if current is not None:
            current.text = "\n".join(lines).strip()
            if current.role:
                for line in lines:
                    match = VERDICT_RE.match(line.strip())
                    if match:
                        value = match.group("value").lower()
                        if value.startswith("fail"):
                            current.verdict = "fail"
                        elif value.startswith("pass"):
                            current.verdict = "pass with notes" if "note" in value else "pass"
            entries.append(current)
        current, lines = None, []

    for line in text.splitlines():
        heading = ENTRY_HEADING_RE.match(line)
        if heading:
            flush()
            current = Entry(title=heading.group("title"))
            continue
        if line.startswith("# "):
            flush()
            continue
        if current is not None:
            lines.append(line.rstrip())
    flush()
    return entries


def load_items(
    root: Path, kind: str, directory: Path, paths: dict[str, str], problems: list[ParseProblem]
) -> list[Item]:
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
                priority=_priority(meta.get("priority")),
                spec=normalise_ref(_as_str(meta.get("spec")), paths["specs"]) if kind != "spec" else "",
                references=_as_list(meta.get("references")),
                meta=meta,
                body=document.body,
            )
        )
    return items


def _change_dirs(changes_dir: Path) -> list[tuple[Path, bool]]:
    if not changes_dir.is_dir():
        return []
    result: list[tuple[Path, bool]] = []
    for directory in sorted(p for p in changes_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if directory.name.upper() == "TEMPLATE":
            continue
        if directory.name == ARCHIVE_DIR:
            result += [(p, True) for p in sorted(directory.iterdir()) if p.is_dir() and not p.name.startswith(".")]
            continue
        result.append((directory, False))
    return result


def _status_of(
    directory: Path, filename: str, rel: str, problems: list[ParseProblem]
) -> tuple[frontmatter.Document, str] | None:
    """The front-matter document and ``status`` of one change file; None when it is absent or broken."""
    path = directory / filename
    if not path.is_file():
        return None
    document = _document(path, f"{rel}/{filename}", problems)
    if document is None:
        return None
    if not document.has_front_matter:
        problems.append(ParseProblem(f"{rel}/{filename}", f"{filename} has no front matter (status)"))
        return None
    return document, _as_str(document.meta.get("status"))


def load_changes(root: Path, config: Config, problems: list[ParseProblem]) -> list[Change]:
    changes: list[Change] = []
    paths = config.paths
    for directory, archived in _change_dirs(root / paths["changes"]):
        rel = _rel(root, directory)
        if not (directory / TASKS_FILE).is_file():
            problems.append(ParseProblem(rel, f"change directory has no {TASKS_FILE}"))
            continue
        loaded = _status_of(directory, TASKS_FILE, rel, problems)
        if loaded is None:
            continue
        document, tasks_status = loaded
        items: list[ItemKey] = []
        for reference in _as_list(document.meta.get("items")):
            key = parse_item_ref(reference, paths)
            if key is None:
                problems.append(
                    ParseProblem(
                        f"{rel}/{TASKS_FILE}",
                        f"item {reference!r} is not a spec, bug or task reference "
                        "(use `spec: billing/refunds`, `bug: rounding` or `task: kyc-archive`)",
                    )
                )
                continue
            items.append(key)
        change = Change(
            path=rel,
            name=directory.name,
            items=items,
            tasks=tasks_status,
            checklist=count_checklist(document.body),
            meta=document.meta,
            archived=archived,
        )
        design = _status_of(directory, DESIGN_FILE, rel, problems)
        if design is not None:
            change.design = design[1]
        implementation = _status_of(directory, IMPLEMENTATION_FILE, rel, problems)
        if implementation is not None:
            change.implementation = implementation[1]
            change.entries = parse_entries(implementation[0].body)
        changes.append(change)
    changes.sort(key=lambda c: (c.archived, c.name))
    return changes


def load_skills(root: Path, skills_dir: Path, problems: list[ParseProblem]) -> list[Skill]:
    skills: list[Skill] = []
    if not skills_dir.is_dir():
        return skills
    for directory in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        skill_file = directory / SKILL_FILE
        if not skill_file.is_file():
            skills.append(Skill(path=_rel(root, directory), folder=directory.name))
            continue
        rel = _rel(root, skill_file)
        document = _document(skill_file, rel, problems)
        if document is None:
            continue
        skills.append(
            Skill(
                path=rel,
                folder=directory.name,
                name=_as_str(document.meta.get("name")),
                description=_as_str(document.meta.get("description")),
                body=document.body,
                has_skill_file=True,
            )
        )
    return skills


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
    paths = config.paths
    vision = root / paths["vision"]
    repository = Repository(
        root=root, config=config, vision_path=paths["vision"], vision_exists=vision.is_file(), problems=problems
    )
    if vision.is_file():
        repository.vision_text = _read(vision, paths["vision"], problems) or ""
    repository.items = [
        item for kind in KINDS for item in load_items(root, kind, root / paths[f"{kind}s"], paths, problems)
    ]
    repository.changes = load_changes(root, config, problems)
    repository.skills = load_skills(root, root / paths["skills"], problems)
    repository.agents = load_agents(root, root / paths["agents"], problems)
    return repository
