"""Load and validate ``.covener/config.yaml``. Deliberately small."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .roles import DEFAULT_AGENT_NAMES, ROLE_KEYS

CONFIG_VERSION = 1
CONFIG_RELATIVE_PATH = Path(".covener") / "config.yaml"
# Claude Code and Cursor both document subagent names as lowercase letters and hyphens.
AGENT_NAME_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*$")
DISABLED_VALUES: frozenset[str] = frozenset({"off", "none", "disabled"})

# The fixed Covener layout.
PATHS: dict[str, str] = {
    "vision": "specs/vision.md",
    "specs": "specs",
    "bugs": "bugs",
    "tasks": "tasks",
    "changes": "changes",
    "agents": "agents",
}


class ConfigError(ValueError):
    """Raised when the configuration is missing or invalid."""


@dataclass
class Config:
    version: int = CONFIG_VERSION
    # role -> agent definition name, or None when the project disabled the role.
    agents: dict[str, str | None] = field(default_factory=lambda: dict(DEFAULT_AGENT_NAMES))
    tools: list[str] = field(default_factory=lambda: ["claude", "cursor"])

    @property
    def paths(self) -> dict[str, str]:
        return dict(PATHS)

    def active_agents(self) -> dict[str, str]:
        """Roles that are enabled, mapped to their agent name."""
        return {role: name for role, name in self.agents.items() if name}

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "agents": dict(self.agents), "tools": list(self.tools)}

    def render(self) -> str:
        header = (
            "# Covener configuration. This configures the methodology, not your application.\n"
            "# - agents: logical role -> agent definition (agents/<name>.md).\n"
            "#   Two roles may share one agent. Set a role to `off` to disable it.\n"
            "# - tools: IDE integrations linked by `covener init` (claude, cursor)\n"
        )
        return header + yaml.safe_dump(self.to_dict(), sort_keys=False)


def _expect_mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"'{label}' must be a mapping")
    return value


def from_dict(data: dict[str, Any]) -> Config:
    config = Config()
    version = data.get("version", CONFIG_VERSION)
    if version != CONFIG_VERSION:
        raise ConfigError(f"unsupported config version {version!r}; expected {CONFIG_VERSION}")

    agents = _expect_mapping(data.get("agents"), "agents")
    for role, name in agents.items():
        if role not in ROLE_KEYS:
            raise ConfigError(f"unknown agent role {role!r}; known roles: {', '.join(ROLE_KEYS)}")
        if name is None or name is False or (isinstance(name, str) and name.lower() in DISABLED_VALUES):
            config.agents[role] = None
            continue
        if not isinstance(name, str) or not AGENT_NAME_RE.match(name):
            raise ConfigError(
                f"agent name for role {role!r} must be lowercase letters and hyphens (or `off` to disable the role)"
            )
        config.agents[role] = name

    tools = data.get("tools", config.tools)
    if not isinstance(tools, list) or not all(isinstance(tool, str) for tool in tools):
        raise ConfigError("'tools' must be a list of strings")
    config.tools = tools

    unknown = set(data) - {"version", "agents", "tools"}
    if unknown:
        raise ConfigError(f"unknown configuration key(s): {', '.join(sorted(unknown))}")
    return config


def load(root: Path) -> Config:
    path = root / CONFIG_RELATIVE_PATH
    if not path.exists():
        raise ConfigError(f"{CONFIG_RELATIVE_PATH} not found; run `covener init` first")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{CONFIG_RELATIVE_PATH}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{CONFIG_RELATIVE_PATH}: top level must be a mapping")
    return from_dict(data)
