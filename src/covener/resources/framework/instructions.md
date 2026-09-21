## Covener

This repository uses Covener: spec-driven development with an AI agent team. The repository is the
source of truth, the conversation is the interface, and humans approve.

- Product vision: `specs/vision.md`
- Specifications, what the product is: `specs/<domain>/<name>.md`, one clean living file each,
  grouped by domain folder (`billing/`, `user-management/`); the path is the id
  (`status: draft | approved | done`; editing a done spec sends it back to draft)
- Bugs, what is wrong: `bugs/<id>.md` (`status: open | done`; `spec:` names the affected spec)
- Tasks, work that changes neither what the product is nor fixes a bug (migrations, refactors,
  upgrades, removals): `tasks/<id>.md` (`status: open | done`)
- Changes, the unit of work: `changes/<name>/` with `change.md` (status and the items it touches),
  `design.md` (how it will be built; optional, dies with the change) and `work.md`
  (checklist, summaries, decisions, QA, review and human feedback, chronological).
  Finished changes live in `changes/archive/`
- Backlog: not a file. Approved specs, open bugs and open tasks that are not in an open change;
  the `status` tool lists it, for the whole repository or one domain
- Project knowledge, when present: `knowledge/` (regulations, contracts, procedures) with
  `knowledge/INDEX.md` and `knowledge/CITATIONS.md`; ask the `search_knowledge` tool when it is
  configured, otherwise read the index. Cite evidence as `knowledge/<file>.md#page-N` in `references:`
- Agents: `agents/` (one file per agent; `.claude/agents` and `.cursor/agents` link here)
- Skills, this project's conventions: `skills/<name>/SKILL.md` in the Agent Skills open standard
  (`.claude/skills`, `.cursor/skills` and `.agents/skills` link here). Read the skill for the layer
  you are touching before writing code; `frontend` and `backend` ship as templates to fill in
- State model: `.covener/states.yaml`; role mapping: `.covener/config.yaml`

Rules for every agent:

1. Work happens inside a change. Start one with `covener change start <name> --spec <id>` (or
   `--bug`, `--task`); it refuses an item that is not ready or is already in an open change.
2. Implementation, tests and reviews happen only for the items the open change lists. A spec that is
   approved, in a change or done is not edited: changes to it are proposed to the Product agent.
3. Record what you did, decided and found in the change's `work.md`. Put the design in `design.md`
   before writing code. Short and useful; never chat logs.
4. Agents never write `## Feedback` entries. When the work is complete and reviewed, set the change to
   `status: review` and tell the human what to evaluate.
5. After the human writes `Approved: Yes`, close the change with `covener change archive <name>`:
   it marks the items done and moves the change to the archive. It refuses without that approval.
6. A trivial fix (one place, no design decision) needs no bug file and no change: do it, test it, say so.
7. Never state what a regulation or document says without evidence from `knowledge/`; if there is
   none, say so. Items that depend on such a statement cite it in `references:`.
8. The `status` tool (or `covener status`) lists the backlog, the open changes, the skills, what is
   next and what is inconsistent; use it before starting work and after changing statuses.
9. When a review finds the same problem twice, the fix is a line in the relevant skill, proposed to the
   human. Skills are how this project's conventions accumulate.
