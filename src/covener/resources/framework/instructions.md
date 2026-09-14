## Covener

This repository uses Covener: spec-driven development with an AI agent team. The repository is the
source of truth, the conversation is the interface, and humans approve.

- Product vision: `specs/vision.md`
- Specifications, what the product is: `specs/<id>.md`, one clean living file each
  (`status: draft | approved | done`; editing a done spec sends it back to draft)
- Bugs, what is wrong: `bugs/<id>.md` (`status: open | done`)
- Tasks, work that changes neither what the product is nor fixes a bug (migrations, refactors,
  upgrades, removals): `tasks/<id>.md` (`status: open | done`)
- Sprints: `sprints/<name>/sprint.md` (owner, scope: `specs:`, `bugs:`, `tasks:`; `active -> review -> closed`)
  with one work log per item next to it, `sprints/<name>/<kind>s/<id>.md`: checklist, agent summaries,
  decisions, QA, reviews and human feedback, chronological. One sprint, one owner, one branch.
  Closed sprints live in `sprints/archive/`
- Backlog: not a file. Open bugs first, then approved specs and open tasks by priority, none in an
  open sprint; the `status` tool lists it
- Project knowledge, when present: `knowledge/` (regulations, contracts, procedures) with
  `knowledge/INDEX.md` and `knowledge/CITATIONS.md`; ask the `search_knowledge` tool when it is
  configured, otherwise read the index. Cite evidence as `knowledge/<file>.md#page-N` in `references:`
- Agents: `agents/` (one file per agent; `.claude/agents` and `.cursor/agents` link here)
- State model: `.covener/states.yaml`; role mapping: `.covener/config.yaml`

Rules for every agent:

1. Implementation, tests and reviews happen only for an approved spec, an open bug or an open task
   inside an open sprint. The Product agent writes specs and registers bugs; the Planner registers
   tasks and runs sprints.
2. A spec in an open sprint is not edited; changes are proposed to the Product agent. A sprint's
   scope does not change once active: new work waits for the next sprint; a hotfix is its own sprint.
3. Record what you did, decided and found in the item's work log of the current sprint.
   Short and useful; never chat logs.
4. Agents never write `## Feedback` entries. `status: done` on an item and `status: closed` on a
   sprint are applied by the Planner only after the human's `Approved: Yes` is in the work log.
5. A trivial fix (one place, no design decision) needs no bug file: do it, test it, say so.
6. Never state what a regulation or document says without evidence from `knowledge/`; if there is
   none, say so. Items that depend on such a statement cite it in `references:`.
7. The `status` tool (or `covener status` in the shell) lists the backlog, what is next and what is
   inconsistent; use it before planning and after changing statuses. `search_knowledge` is the tool for
   the project knowledge; without tools, run `covener knowledge ask "..."` or read `knowledge/INDEX.md`.
