"""Logical agent roles.

Covener refers to agents by *logical role*. ``.covener/config.yaml`` maps each role to the name
of an agent definition in ``agents/``. Renaming an agent never changes the methodology.
"""

from __future__ import annotations

# role key -> default agent definition name (agents/<name>.md)
DEFAULT_AGENT_NAMES: dict[str, str] = {
    "product": "product",
    "planner": "planner",
    "engineer": "engineer",
    "qa": "qa",
    "reviewer": "reviewer",
}
ROLE_KEYS: tuple[str, ...] = tuple(DEFAULT_AGENT_NAMES)
