from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .. import frontmatter
from ..config import Config

IGNORED: frozenset[str] = frozenset({"README.MD", "TEMPLATE.MD"})


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


def _points_into(link: Path, source_dir: Path) -> bool:
    """True when ``link`` is a symlink whose target lies inside ``source_dir``."""
    try:
        resolved = link.resolve()
    except OSError:
        return False
    return resolved == source_dir.resolve() or source_dir.resolve() in resolved.parents


class Adapter:
    """Expose the canonical ``agents/`` directory where a tool looks for subagents.

    There is exactly one file per agent, ``agents/<name>.md``. The tool directory
    (``.claude/agents`` or ``.cursor/agents``) is a symlink to ``agents/``. When that directory
    already exists with the project's own files, each agent is linked into it instead. When the
    platform refuses symlinks (Windows without Developer Mode), files are copied and the developer
    is told.
    """

    key = "base"
    title = "Base"

    def agents_dir(self, root: Path) -> Path:  # pragma: no cover - abstract
        raise NotImplementedError

    def detect(self, root: Path) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    # --- linking ------------------------------------------------------------------------
    @staticmethod
    def _symlink(link: Path, target: Path, is_dir: bool) -> bool:
        """Create a relative symlink; on Windows fall back to a directory junction (no privileges needed)."""
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
        result = AdapterResult(tool=self.key)
        source_dir = root / config.paths["agents"]
        target_dir = self.agents_dir(root)
        target_rel = _rel(root, target_dir)
        source_rel = _rel(root, source_dir)

        if target_dir.is_symlink() or (
            sys.platform == "win32" and target_dir.is_dir() and _points_into(target_dir, source_dir)
        ):
            if _points_into(target_dir, source_dir):
                result.unchanged.append(f"{target_rel} -> {source_rel}")
            else:
                result.skipped.append(target_rel)
                result.notes.append(f"{target_rel} is a symlink to somewhere else; left untouched.")
            return result

        if self._is_git_symlink_placeholder(target_dir, source_dir):
            # git checked the committed symlink out as a text file (core.symlinks=false); repair it.
            if not dry_run:
                target_dir.unlink()
            verb = "would recreate" if dry_run else "recreated"
            result.notes.append(
                f"{target_rel} was a symlink placeholder left by git (core.symlinks=false); {verb} the link. "
                "Consider `git config core.symlinks true` before cloning."
            )

        if not target_dir.exists():
            if dry_run:
                result.created.append(f"{target_rel} -> {source_rel}")
                return result
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            if self._symlink(target_dir, source_dir, is_dir=True):
                result.created.append(f"{target_rel} -> {source_rel}")
                return result
            result.notes.append(
                f"Could not create the symlink {target_rel} -> {source_rel} (symlinks unavailable on this "
                "platform). Files were copied instead; re-run `covener init` after editing agents/."
            )
            target_dir.mkdir(parents=True, exist_ok=True)

        # Existing real directory: link (or copy) each agent file into it.
        sources = self._agent_files(source_dir)
        if not sources and dry_run:  # agents/ is not written yet in a dry run
            sources = [source_dir / f"{name}.md" for name in config.active_agents().values()]
        for source in sources:
            link = target_dir / source.name
            link_rel = _rel(root, link)
            if link.is_symlink():
                if _points_into(link, source_dir):
                    result.unchanged.append(link_rel)
                else:
                    result.skipped.append(link_rel)
                    result.notes.append(f"{link_rel} links elsewhere; left untouched.")
                continue
            if link.exists():
                content = source.read_text(encoding="utf-8") if source.is_file() else None
                if link.is_file() and content is not None and link.read_text(encoding="utf-8") == content:
                    result.unchanged.append(link_rel)
                else:
                    result.skipped.append(link_rel)
                    result.notes.append(
                        f"{link_rel} is the project's own file; left untouched. Remove it to let Covener link "
                        f"{_rel(root, source)} there."
                    )
                continue
            if dry_run:
                result.created.append(link_rel)
                continue
            if self._symlink(link, source, is_dir=False):
                result.created.append(link_rel)
            else:
                shutil.copyfile(source, link)
                result.created.append(link_rel)
                result.notes.append(f"{link_rel} was copied because symlinks are unavailable here.")

        # Dangling links into agents/ belong to renamed or deleted agents.
        for entry in sorted(target_dir.iterdir()) if target_dir.is_dir() else []:
            if not entry.is_symlink() or entry.exists():
                continue
            pointed = Path(os.path.normpath(entry.parent / os.readlink(entry)))
            if pointed == Path(os.path.normpath(source_dir / entry.name)):
                if not dry_run:
                    entry.unlink()
                result.removed.append(_rel(root, entry))
        return result

    def install(self, root: Path, config: Config, dry_run: bool = False) -> AdapterResult:
        return self.link_agents(root, config, dry_run=dry_run)
