"""Central state model. Code validates these; agents reason within them."""

from __future__ import annotations

# A specification describes the product and is a living document: editing a done spec sends it
# back to draft. ``approved`` is a human decision on the text; ``done`` is reached only when the
# work was approved by a human in a sprint work log.
SPEC_STATES: tuple[str, ...] = ("draft", "approved", "done")
SPEC_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("draft", "approved"), ("approved", "done")})

# A bug describes a deviation from the product. It is reported, not approved; ``done`` is reached
# only when the fix was approved by a human in a sprint work log.
BUG_STATES: tuple[str, ...] = ("open", "done")
BUG_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("open", "done")})

# A task is work that changes neither what the product is nor fixes a deviation: migrations,
# refactors, upgrades, removals. Decided, not approved; ``done`` after human approval of the work.
TASK_STATES: tuple[str, ...] = ("open", "done")
TASK_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("open", "done")})

# A sprint: agents work (active), then ask for feedback (review); the human approves every item's
# work or requests changes; the sprint closes only when everything is approved.
SPRINT_STATES: tuple[str, ...] = ("active", "review", "closed")
SPRINT_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("review", "closed")})

# Derived state of an item's work inside a sprint (computed from its work log, never stored).
WORK_STATES: tuple[str, ...] = (
    "not_started",  # no work entry yet (a checklist alone is not work)
    "in_progress",  # work entries, sprint still active
    "awaiting_feedback",  # sprint in review, no feedback after the latest work entry
    "changes_requested",  # latest entry is feedback with Approved: No
    "approved",  # latest feedback is Approved: Yes
)

KINDS: tuple[str, ...] = ("bug", "spec", "task")  # bugs first in the backlog; then by priority
ITEM_STATES: dict[str, tuple[str, ...]] = {"spec": SPEC_STATES, "bug": BUG_STATES, "task": TASK_STATES}
READY_STATE: dict[str, str] = {"spec": "approved", "bug": "open", "task": "open"}  # what a sprint may take
