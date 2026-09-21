"""Central state model. Code validates these; agents reason within them."""

from __future__ import annotations

# What the product is. A living document: editing a done spec sends it back to draft.
# ``approved`` is a human decision on the text; ``done`` means a change implemented it and a
# human approved that work.
SPEC_STATES: tuple[str, ...] = ("draft", "approved", "done")
SPEC_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("draft", "approved"), ("approved", "done")})

# Where the product deviates. Reported, not approved.
BUG_STATES: tuple[str, ...] = ("open", "done")
BUG_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("open", "done")})

# Work that changes neither what the product is nor fixes a deviation: migrations, refactors,
# upgrades, removals.
TASK_STATES: tuple[str, ...] = ("open", "done")
TASK_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("open", "done")})

# A change is the unit of work: one or a few items, its design, its work log and your verdict.
# ``open`` while agents work, ``review`` while the human evaluates, ``done`` once approved.
CHANGE_STATES: tuple[str, ...] = ("open", "review", "done")
CHANGE_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("review", "done")})

# Derived state of a change, computed from its work log and never stored.
WORK_STATES: tuple[str, ...] = (
    "not_started",  # no work entry yet (a checklist alone is not work)
    "in_progress",  # work entries, change still open
    "awaiting_feedback",  # change in review, no feedback after the latest work entry
    "changes_requested",  # latest entry is feedback with Approved: No
    "approved",  # latest feedback is Approved: Yes
)

KINDS: tuple[str, ...] = ("spec", "bug", "task")
ITEM_STATES: dict[str, tuple[str, ...]] = {"spec": SPEC_STATES, "bug": BUG_STATES, "task": TASK_STATES}
# What a change may take: an approved spec, an open bug, an open task.
READY_STATE: dict[str, str] = {"spec": "approved", "bug": "open", "task": "open"}
