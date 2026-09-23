"""Central state model. Code validates these; agents reason within them."""

from __future__ import annotations

# What the product is. A living document: editing a done spec sends it back to draft.
# ``approved`` is a human decision on the text; ``done`` means a change implemented it and a
# human approved that implementation.
SPEC_STATES: tuple[str, ...] = ("draft", "approved", "done")
SPEC_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("draft", "approved"), ("approved", "done")})

# Where the product deviates. Reported, not approved.
BUG_STATES: tuple[str, ...] = ("open", "done")
BUG_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("open", "done")})

# Work that changes neither what the product is nor fixes a deviation: migrations, refactors,
# upgrades, removals.
TASK_STATES: tuple[str, ...] = ("open", "done")
TASK_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("open", "done")})

# A change is a folder with three files, each approved by the human in its own front matter:
# ``design.md`` (how; optional), ``tasks.md`` (the plan, and the items the change covers) and
# ``implementation.md`` (what happened; agents write it, the human approves the result).
DESIGN_STATES: tuple[str, ...] = ("draft", "approved")
DESIGN_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("draft", "approved")})
TASKS_STATES: tuple[str, ...] = ("draft", "approved")
TASKS_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("draft", "approved")})
IMPLEMENTATION_STATES: tuple[str, ...] = ("in-progress", "review", "approved")
IMPLEMENTATION_HUMAN_GATED: frozenset[tuple[str, str]] = frozenset({("review", "approved")})

# Derived state of a change, computed from those three files and never stored.
CHANGE_STATES: tuple[str, ...] = (
    "not_started",  # tasks.md is a draft with no task yet: the engineer has not planned it
    "awaiting_design",  # design.md is a draft: the human reads it and sets it approved, before the tasks
    "awaiting_tasks",  # tasks.md is a draft with tasks: the human approves the plan, before any code
    "in_progress",  # tasks approved; work until every task is ticked and the record is in review
    "in_review",  # every task ticked and implementation.md in review: the human evaluates the result
    "approved",  # implementation.md approved by the human: archive it
    "done",  # in changes/archive/
)

KINDS: tuple[str, ...] = ("spec", "bug", "task")
ITEM_STATES: dict[str, tuple[str, ...]] = {"spec": SPEC_STATES, "bug": BUG_STATES, "task": TASK_STATES}
# What a change may take: an approved spec, an open bug, an open task.
READY_STATE: dict[str, str] = {"spec": "approved", "bug": "open", "task": "open"}
