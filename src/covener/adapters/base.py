from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .. import frontmatter
from ..config import Config

IGNORED: frozenset[str] = frozenset({"README.MD", "TEMPLATE.MD"})
SKILL_FILE = "SKILL.md"
# The Agent Skills open standard: Codex, Cursor and Copilot read this repository location natively.
PORTABLE_SKILLS_DIR = Path(".agents") / "skills"


@dataclass
class AdapterResult:
    tool: str
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_junction(path: Path) -> bool:
    """Path.is_junction arrived in Python 3.12; on older versions there is nothing to detect."""
    checker = getattr(path, "is_junction", None)
    return bool(checker()) if checker is not None else False


def _points_into(link: Path, source_dir: Path) -> bool:
    """True when ``link`` resolves to ``source_dir`` or to something inside it."""
    try:
        resolved = link.resolve()
    except OSError:
        return False
    source = source_dir.resolve()
    return resolved == source or source in resolved.parents


class Adapter:
    """Expose the project's ``agents/`` and ``skills/`` where each tool looks for them.

    There is exactly one file per agent (``agents/<name>.md``) and one folder per skill
    (``skills/<name>/SKILL.md``). A tool directory such as ``.claude/agents`` or ``.claude/skills``
    is a real directory holding one symlink per entry, not a symlink to ours: Claude Code documents
    a skill entry that is a symlink to a directory elsewhere as supported, while a symlinked skills
    directory is not documented and has known discovery bugs. Per-entry links also leave room for
    the project's own agents and skills next to Covener's. Where the platform refuses symlinks
    (Windows without Developer Mode), entries are copied and the developer is told.
    """

    key = "base"
    title = "Base"

    def agents_dir(self, root: Path) -> Path:  # pragma: no cover - abstract
        raise NotImplementedError

    def skills_dir(self, root: Path) -> Path | None:
        """Where this tool reads skills, or None when the portable location covers it."""
        return None

    def detect(self, root: Path) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    # --- linking ------------------------------------------------------------------------
    @staticmethod
    def _symlink(link: Path, target: Path, is_dir: bool) -> bool:
        """Create a relative symlink; on Windows fall back to a junction for directories."""
        relative = os.path.relpath(target, link.parent)
        try:
            os.symlink(relative, link, target_is_directory=is_dir)
            return True
        except (OSError, NotImplementedError):
            pass
        if is_dir and sys.platform == "win32":
            try:
                import _winapi

                _winapi.CreateJunction(str(target.resolve()), str(link))
                return True
            except (OSError, AttributeError, ImportError):
                return False
        return False

    @staticmethod
    def _is_git_symlink_placeholder(path: Path, target: Path) -> bool:
        """A clone with core.symlinks=false turns a symlink into a small text file holding its target."""
        if not path.is_file() or path.stat().st_size > 512:
            return False
        try:
            content = path.read_text(encoding="utf-8").strip().replace("\\", "/")
        except (OSError, UnicodeDecodeError):
            return False
        return content == os.path.relpath(target, path.parent).replace("\\", "/")

    @staticmethod
    def _remove(path: Path) -> None:
        """Remove a link or an empty directory; directory links need rmdir on Windows."""
        if path.is_symlink() or path.is_file():
            try:
                path.unlink()
                return
            except (IsADirectoryError, PermissionError):
                pass
        os.rmdir(path)

    def _skill_dirs(self, source_dir: Path) -> list[Path]:
        """Skill folders that carry a SKILL.md, the Agent Skills open standard."""
        if not source_dir.is_dir():
            return []
        return sorted(p for p in source_dir.iterdir() if p.is_dir() and (p / SKILL_FILE).is_file())

    def _agent_files(self, source_dir: Path) -> list[Path]:
        if not source_dir.is_dir():
            return []
        files = []
        for path in sorted(source_dir.glob("*.md")):
            if path.name.upper() in IGNORED or not path.is_file():
                continue
            try:
                document = frontmatter.parse(path.read_text(encoding="utf-8"))
            except (frontmatter.FrontMatterError, UnicodeDecodeError):
                continue
            if document.has_front_matter and str(document.meta.get("name", "")).strip():
                files.append(path)
        return files

    def link_agents(self, root: Path, config: Config, dry_run: bool = False) -> AdapterResult:
        return self.link_dir(root, root / config.paths["agents"], self.agents_dir(root), config, dry_run)

    def link_dir(
        self,
        root: Path,
        source_dir: Path,
        target_dir: Path,
        config: Config,
        dry_run: bool = False,
        result: AdapterResult | None = None,
    ) -> AdapterResult:
        """Link every agent or skill of ours into ``target_dir``, one symlink per entry."""
        result = result or AdapterResult(tool=self.key)
        kind = "skills" if source_dir.name == config.paths["skills"] else "agents"
        target_rel = _rel(root, target_dir)
        source_rel = _rel(root, source_dir)

        # A directory-wide symlink is what Covener created before 0.5.0, and what Claude Code does
        # not document; replace it with a real directory of per-entry links.
        if target_dir.is_symlink() or (sys.platform == "win32" and _is_junction(target_dir)):
            if not _points_into(target_dir, source_dir):
                result.skipped.append(target_rel)
                result.notes.append(f"{target_rel} is a link to somewhere else; left untouched.")
                return result
            if dry_run:
                result.updated.append(f"{target_rel} (directory link replaced by per-entry links)")
            else:
                self._remove(target_dir)
                result.notes.append(
                    f"{target_rel} was a link to {source_rel}; replaced with one link per {kind[:-1]}, "
                    "which is the form every tool documents."
                )

        # git checked an old committed directory link out as a text file (core.symlinks=false).
        if not dry_run and self._is_git_symlink_placeholder(target_dir, source_dir):
            target_dir.unlink()

        if not target_dir.exists() and not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        if kind == "skills":
            sources = self._skill_dirs(source_dir)
            if not sources and dry_run:  # skills/ is not written yet in a dry run
                sources = [source_dir / name for name in ("frontend", "backend")]
        else:
            sources = self._agent_files(source_dir)
            if not sources and dry_run:  # agents/ is not written yet in a dry run
                sources = [source_dir / f"{name}.md" for name in config.active_agents().values()]

        for source in sources:
            link = target_dir / source.name
            link_rel = _rel(root, link)
            if link.is_symlink() or (sys.platform == "win32" and _is_junction(link)):
                if _points_into(link, source_dir):
                    result.unchanged.append(link_rel)
                else:
                    result.skipped.append(link_rel)
                    result.notes.append(f"{link_rel} links elsewhere; left untouched.")
                continue
            if self._is_git_symlink_placeholder(link, source):
                if not dry_run:
                    link.unlink()
                result.notes.append(
                    f"{link_rel} was a symlink placeholder left by git (core.symlinks=false); recreated the link. "
                    "Consider `git config core.symlinks true` before cloning."
                )
            elif link.exists():
                content = source.read_text(encoding="utf-8") if source.is_file() else None
                if link.is_file() and content is not None and link.read_text(encoding="utf-8") == content:
                    result.unchanged.append(link_rel)
                else:
                    result.skipped.append(link_rel)
                    result.notes.append(
                        f"{link_rel} is the project's own; left untouched. Remove it to let Covener link "
                        f"{_rel(root, source)} there."
                    )
                continue
            if dry_run:
                result.created.append(link_rel)
                continue
            if self._symlink(link, source, is_dir=source.is_dir()):
                result.created.append(link_rel)
                continue
            copy = shutil.copytree if source.is_dir() else shutil.copyfile
            copy(source, link)  # type: ignore[operator]
            result.created.append(link_rel)
            result.notes.append(
                f"{link_rel} was copied because symlinks are unavailable here; re-run `covener init` "
                f"after editing {kind}/."
            )

        # Dangling links into ours belong to renamed or deleted entries.
        for entry in sorted(target_dir.iterdir()) if target_dir.is_dir() else []:
            if not entry.is_symlink() or entry.exists():
                continue
            pointed = Path(os.path.normpath(entry.parent / os.readlink(entry)))
            if pointed == Path(os.path.normpath(source_dir / entry.name)):
                if not dry_run:
                    entry.unlink()
                result.removed.append(_rel(root, entry))
        return result

    def link_skills(self, root: Path, config: Config, dry_run: bool = False) -> AdapterResult:
        """Link the skills into this tool's directory and into the portable ``.agents/skills``."""
        result = AdapterResult(tool=self.key)
        source_dir = root / config.paths["skills"]
        targets = [root / PORTABLE_SKILLS_DIR]
        own = self.skills_dir(root)
        if own is not None:
            targets.insert(0, own)
        for target in targets:
            self.link_dir(root, source_dir, target, config, dry_run, result)
        return result

    def link_all(self, root: Path, config: Config, dry_run: bool = False) -> AdapterResult:
        """Link the agents and the skills this tool reads."""
        result = self.link_agents(root, config, dry_run=dry_run)
        skills = self.link_skills(root, config, dry_run=dry_run)
        for name in ("created", "updated", "removed", "unchanged", "skipped", "notes"):
            getattr(result, name).extend(getattr(skills, name))
        return result

    def install(self, root: Path, config: Config, dry_run: bool = False) -> AdapterResult:
        return self.link_all(root, config, dry_run=dry_run)
