"""``covener init``: initialise an existing repository with the Covener structure.

Guarantees:

* never silently overwrites project-owned files (AGENTS.md, CLAUDE.md, agents/, vision, config);
* is idempotent: running it again reports what exists and only adds what is missing;
* leaves the repository fully functional without the package installed.
"""

from __future__ import annotations

import importlib.resources as resources
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as config_module
from .adapters import ADAPTERS, get_adapter
from .repo import is_git_repo
from .roles import DEFAULT_AGENT_NAMES

MCP_ENTRY: dict[str, object] = {"command": "covener", "args": ["serve"]}

MARK_START = "<!-- covener:start -->"
MARK_END = "<!-- covener:end -->"
BLOCK_RE = re.compile(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), re.DOTALL)

FRAMEWORK_FILES: tuple[tuple[str, str], ...] = (("framework/states.yaml", ".covener/states.yaml"),)

DETECTABLE: tuple[tuple[str, str], ...] = (
    ("AGENTS.md", "existing AGENTS.md (will be integrated, never overwritten)"),
    ("CLAUDE.md", "existing CLAUDE.md (Claude Code instructions)"),
    (".claude", "existing .claude/ directory (Claude Code configuration)"),
    (".claude/agents", "existing Claude Code subagents in .claude/agents/"),
    (".cursor", "existing .cursor/ directory (Cursor configuration)"),
    (".cursor/rules", "existing Cursor rules in .cursor/rules/"),
    (".cursor/agents", "existing Cursor subagents in .cursor/agents/"),
    (".cursorrules", "legacy .cursorrules file"),
    (".github/copilot-instructions.md", "GitHub Copilot instructions"),
    (".covener/config.yaml", "existing Covener configuration"),
)


@dataclass
class InitReport:
    root: Path
    git_repo: bool
    detected: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    dry_run: bool = False

    def render(self) -> str:
        lines = [f"Covener init{' (dry run)' if self.dry_run else ''}", f"  Repository: {self.root}"]
        lines.append(f"  Git: {'yes' if self.git_repo else 'no (.git not found; using this directory as root)'}")
        lines.append(f"  Tools: {', '.join(self.tools) if self.tools else 'none'}")
        sections = (
            ("Detected", "*", self.detected),
            ("Created", "+", self.created),
            ("Updated", "~", self.updated),
            ("Removed (dangling links to deleted or renamed agents)", "-", self.removed),
            ("Kept (already present, not overwritten)", "=", self.kept),
            ("Skipped (see notes)", "!", self.skipped),
        )
        for title, mark, items in sections:
            if items:
                lines += ["", title] + [f"  {mark} {item}" for item in items]
        if self.notes:
            lines += ["", "Notes"] + [f"  - {note}" for note in self.notes]
        lines += ["", "Next: open your IDE and talk to the Product agent. Run `covener status` any time."]
        return "\n".join(lines)


def read_resource(relative: str) -> str:
    return resources.files("covener.resources").joinpath(relative).read_text(encoding="utf-8")


def _write(root: Path, relative: str, content: str, report: InitReport) -> None:
    target = root / relative
    if target.exists():
        report.kept.append(relative)
        return
    if not report.dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    report.created.append(relative)


def _write_preserving_newlines(target: Path, text: str, raw: bytes) -> None:
    newline = "\r\n" if b"\r\n" in raw else "\n"
    target.write_bytes(text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8"))


def integrate_agents_md(root: Path, report: InitReport) -> None:
    """Create AGENTS.md or integrate the Covener block into an existing one, never overwriting.

    The block is delimited by HTML comment markers. If the markers in an existing file are
    unbalanced or duplicated, the file is left untouched and the developer is told.
    """
    target = root / "AGENTS.md"
    block = f"{MARK_START}\n{read_resource('framework/instructions.md').rstrip()}\n{MARK_END}"
    if not target.exists():
        if not report.dry_run:
            target.write_text(f"# AGENTS.md\n\n{block}\n", encoding="utf-8")
        report.created.append("AGENTS.md")
        return
    raw = target.read_bytes()
    existing = raw.decode("utf-8").replace("\r\n", "\n")
    starts, ends = existing.count(MARK_START), existing.count(MARK_END)
    if starts == 0 and ends == 0:
        merged = (existing.rstrip("\n") + "\n\n" if existing.strip() else "") + block + "\n"
        if not report.dry_run:
            _write_preserving_newlines(target, merged, raw)
        report.updated.append("AGENTS.md")
        report.notes.append(
            "Existing AGENTS.md detected. AGENTS.md has no include mechanism, so the Covener "
            "instructions were appended inside clearly marked comments; your original content is untouched."
        )
        return
    blocks = BLOCK_RE.findall(existing)
    if starts != 1 or ends != 1 or len(blocks) != 1:
        report.kept.append("AGENTS.md")
        report.notes.append(
            f"AGENTS.md contains unbalanced or repeated covener markers ({starts} start, {ends} end); "
            "left untouched. Fix the markers by hand and re-run init."
        )
        return
    if blocks[0] == block:
        report.kept.append("AGENTS.md")
        return
    merged = BLOCK_RE.sub(lambda _m: block, existing, count=1)
    if not report.dry_run:
        _write_preserving_newlines(target, merged, raw)
    report.updated.append("AGENTS.md")
    report.notes.append("Refreshed the Covener block inside the existing AGENTS.md; everything else untouched.")


def _merge_mcp_config(path: Path, with_type: bool, dry_run: bool) -> bool:
    """Add the covener MCP server to a JSON config, keeping everything else. True if it was added."""
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return False
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict) or "covener" in servers:
        return False
    servers["covener"] = ({"type": "stdio"} | MCP_ENTRY) if with_type else dict(MCP_ENTRY)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def register_mcp(root: Path, tools: list[str], report: InitReport) -> None:
    """Expose `status` and the Knowledge Oracle to the IDE as tools, when the mcp package is installed."""
    from .mcp_server import mcp_available

    if not mcp_available():
        report.notes.append(
            "MCP server not registered: install `covener[mcp]` and re-run init to expose `status` and "
            "`search_knowledge` as tools in your IDE (the CLI works without it)."
        )
        return
    targets = {"claude": (root / ".mcp.json", True), "cursor": (root / ".cursor" / "mcp.json", False)}
    for tool in tools:
        path, with_type = targets[tool]
        rel = path.relative_to(root).as_posix()
        if _merge_mcp_config(path, with_type, report.dry_run):
            report.created.append(rel)
        else:
            report.kept.append(rel)


def detect_existing(root: Path) -> list[str]:
    return [label for relative, label in DETECTABLE if (root / relative).exists()]


def select_tools(root: Path, requested: list[str] | None) -> list[str]:
    if requested is not None:
        unknown = [tool for tool in requested if tool not in ADAPTERS]
        if unknown:
            raise ValueError(f"unknown tool(s): {', '.join(unknown)}; known: {', '.join(ADAPTERS)}")
        return list(dict.fromkeys(requested))
    detected = [key for key, adapter in ADAPTERS.items() if adapter().detect(root)]
    return detected or list(ADAPTERS)


def initialize(
    root: Path,
    *,
    tools: list[str] | None = None,
    dry_run: bool = False,
    install_agents: bool = False,
) -> InitReport:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")
    report = InitReport(root=root, git_repo=is_git_repo(root), dry_run=dry_run, detected=detect_existing(root))

    config_path = root / config_module.CONFIG_RELATIVE_PATH
    first_init = not config_path.exists()
    agents_existed = (root / config_module.PATHS["agents"]).is_dir()
    cfg = config_module.Config() if first_init else config_module.load(root)
    if not first_init:
        report.kept.append(config_module.CONFIG_RELATIVE_PATH.as_posix())
        report.notes.append("Repository already initialised; existing configuration honoured.")

    selected = select_tools(root, tools if tools is not None else (cfg.tools if not first_init else None))
    if not first_init and selected != cfg.tools:
        report.notes.append(
            f"Configured tools in .covener/config.yaml are {cfg.tools}; this run used {selected}. "
            "Edit `tools:` in the config to make it permanent."
        )
    cfg.tools = selected
    report.tools = selected
    paths = cfg.paths

    if not dry_run:
        for directory in (paths["specs"], paths["bugs"], paths["tasks"], paths["sprints"], paths["agents"], ".covener"):
            (root / directory).mkdir(parents=True, exist_ok=True)

    if first_init:
        _write(root, config_module.CONFIG_RELATIVE_PATH.as_posix(), cfg.render(), report)
    for resource, target in FRAMEWORK_FILES:
        _write(root, target, read_resource(resource), report)
    _write(root, paths["vision"], read_resource("templates/vision.md"), report)
    _write(root, f"{paths['specs']}/TEMPLATE.md", read_resource("templates/spec.md"), report)
    _write(root, f"{paths['bugs']}/TEMPLATE.md", read_resource("templates/bug.md"), report)
    _write(root, f"{paths['tasks']}/TEMPLATE.md", read_resource("templates/task.md"), report)
    _write(root, f"{paths['sprints']}/TEMPLATE/sprint.md", read_resource("templates/sprint.md"), report)
    _write(root, f"{paths['sprints']}/TEMPLATE/work.md", read_resource("templates/work.md"), report)

    # Agents: the default team on first install; afterwards only on request.
    default_role_by_name = {name: role for role, name in DEFAULT_AGENT_NAMES.items()}
    install_defaults = first_init or install_agents or not agents_existed
    roles_by_name: dict[str, list[str]] = {}
    for role_key, agent_name in cfg.active_agents().items():
        roles_by_name.setdefault(agent_name, []).append(role_key)
    for agent_name, role_keys in roles_by_name.items():
        target_rel = f"{paths['agents']}/{agent_name}.md"
        if (root / target_rel).exists():
            report.kept.append(target_rel)
            continue
        if not install_defaults:
            report.notes.append(
                f"{target_rel} is missing for role(s) {', '.join(role_keys)}. Re-run with --install-agents to "
                "install the default definition, map the role to another agent, or set the role to `off` "
                "in .covener/config.yaml."
            )
            continue
        source_role = default_role_by_name.get(agent_name, role_keys[0])
        default_name = DEFAULT_AGENT_NAMES[source_role]
        content = read_resource(f"agents/{default_name}.md")
        if agent_name != default_name:
            content = content.replace(f"name: {default_name}\n", f"name: {agent_name}\n", 1)
        if len(role_keys) > 1 or source_role not in role_keys:
            report.notes.append(
                f"{target_rel} serves role(s) {', '.join(role_keys)} and was installed from the packaged "
                f"'{default_name}' definition; adjust its prompt if those roles need different guidance."
            )
        _write(root, target_rel, content, report)

    integrate_agents_md(root, report)

    for tool in selected:
        adapter = get_adapter(tool)
        result = adapter.install(root, cfg, dry_run=dry_run)
        report.created += result.created
        report.updated += result.updated
        report.removed += result.removed
        report.kept += result.unchanged
        report.skipped += result.skipped
        report.notes += [f"[{adapter.title}] {note}" for note in result.notes]

    register_mcp(root, selected, report)

    if not report.git_repo:
        report.notes.append("No git repository detected; initialised the current directory. Run `git init` when ready.")
    return report
