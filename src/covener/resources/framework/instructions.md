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
- Changes, the unit of work: `changes/<name>/` with three files, each with its own `status`:
  `design.md` (how it will be built; `draft | approved`; optional), `tasks.md` (the items it covers
  and the plan, one checkbox per step; `draft | approved`) and `implementation.md` (what happened:
  summary, decisions, QA, review, rework; `in-progress | review | approved`; agents only).
  Finished changes live in `changes/archive/`
- Backlog: not a file. Approved specs, open bugs and open tasks that are not in an open change;
  the `status` tool lists it, for the whole repository or one domain
- Project knowledge, when present: `knowledge/` (regulations, contracts, procedures) with
  `knowledge/INDEX.md` and `knowledge/CITATIONS.md`; ask the `search_knowledge` tool when it is
  configured, otherwise read the index. Cite evidence as `knowledge/<file>.md#page-N` in `references:`
- Agents: `agents/` (one file per agent; `.claude/agents` and `.cursor/agents` link here)
- Skills, this project's conventions: `skills/<name>/SKILL.md` in the Agent Skills open standard
  (`.claude/skills` and `.agents/skills` hold one link per skill). Read the skill for the layer you
  are touching before writing code, and `skills/architecture/SKILL.md` before designing: it holds
  the shape of the system and the decisions every change must respect. `frontend`, `backend` and
  `architecture` ship as templates to fill in
- State model: `.covener/states.yaml`; role mapping and who approves each gate: `.covener/config.yaml`

Rules for every agent:

1. Work happens inside a change. Start one with `covener change start <name> --spec <id>` (or
   `--bug`, `--task`); it refuses an item that is not ready or is already in an open change.
2. Implementation, tests and reviews happen only for the items the open change lists. A spec that is
   approved, in a change or done is not edited: changes to it are proposed to the Product agent.
   Code delivered by another open change is edited only where this change's own item requires it,
   said in `design.md` and recorded in `implementation.md`; rework of the other change is not this
   change's to do and keeps waiting for the human's review.
3. Design before tasks, tasks before code. A change delivers its item whole: every acceptance
   criterion, in every layer it touches, and the plan has as many steps as that takes. The engineer
   writes `design.md` as a draft and stops; the human edits it, asks for changes in the conversation
   and sets `status: approved`. Then the engineer writes the plan in `tasks.md` and stops again until
   the human approves it. A change too small for a design has no `design.md`, and a bug usually has
   none: its spec already says what the behaviour must be, so one is written when the fix carries a
   real choice (more than one reasonable approach, a change to the shape of the system, or a pattern
   the same class of bug will follow), opening with one line saying which.
   A design names components, boundaries and decisions with their reason, and stops there: behaviour
   rules, validation tables, parsing, error handling, file lists and tests belong to `tasks.md` and
   the code, and a design carrying them goes back unread. Feedback is given in
   the conversation and incorporated in the file, never logged, and `design.md` carries no open
   questions: engineering decisions are the engineer's to take and write down. `approvals:` in
   `.covener/config.yaml` may delegate the design gate, the tasks gate or both to the reviewer: the
   engineer then hands the file to the reviewer, who approves it with `status: approved` and
   `approved-by: reviewer` or asks for changes, and escalates to the human only when
   `skills/architecture/SKILL.md` is still the template, after two rounds without agreement, or when
   the item itself contradicts another item. The implementation is approved by the human, unless
   `approvals: {implementation: off}` removes that gate (rule 6).
4. Agents never set `status: approved` on any file, except the reviewer on a gate `approvals:`
   delegates to it, signed `approved-by: reviewer`. Record what you did, decided and found in the
   change's `implementation.md`, short and useful, never chat logs; tick tasks as you finish them.
5. When every task is ticked and QA and the reviewer pass, set `implementation.md` to
   `status: review`, commit the change (code, tests and its three files, one commit named after
   the change) and tell the human what to evaluate. Rework the human asks for goes into
   `tasks.md` as tasks under `## Rework`; the change is back in review, with a new commit, once
   they are ticked. Nothing waits for review uncommitted: the reviewer reads the commit's diff,
   and a `git checkout` must not be able to lose a day's work.
6. After the human sets `implementation.md` to `status: approved`, close the change with
   `covener change archive <name>`: it marks the items done and moves the change to the archive. It
   refuses without that approval, and while a task is open. Commit the archive. With
   `approvals: {implementation: off}` no one approves the implementation: once the change is in
   review and committed, the engineer runs `covener change archive <name>` right away. It closes
   the change only when every task is ticked, the design and the plan are approved, the latest QA
   and review verdicts pass and nothing is uncommitted, and it leaves `status: review` with
   `approval: off` in `implementation.md`, so the record never claims an approval that did not
   happen. With the gate off, a verdict is what closes the change: what needs fixing is a `fail`,
   and what needs a person is escalated, never left as a note.
7. A trivial fix (one place, no design decision) needs no bug file and no change: do it, test it, say so.
8. Never state what a regulation or document says without evidence from `knowledge/`; if there is
   none, say so. Items that depend on such a statement cite it in `references:`.
9. The `status` tool (or `covener status`) lists the backlog, the open changes, the skills, what is
   next and what is inconsistent; use it before starting work and after changing statuses.
10. When a review finds the same problem twice, the fix is a line in the relevant skill, proposed to the
    human. A decision that outlives its change becomes a line under Decisions in
    `skills/architecture/SKILL.md`, in that same change. Skills are how this project's conventions
    and its architecture accumulate.

Unattended runs. When the human asks for the backlog to be run without them and `approvals:`
delegates the design and the tasks to the reviewer, the agents take every routine decision
themselves and record it under `## Decisions` in `implementation.md`, which the human reads when
they approve the implementation: that is the only human gate left, and with
`approvals: {implementation: off}` there is none: each change is archived as soon as it passes,
nothing stacks, and the human reads the archive when they choose. The planner takes the first
item of the ordered backlog, never skips one, and moves to the next as soon as a change is in
review or archived. The run works on one branch, with one commit per change when it reaches review and one
per rework; a branch per change is for the flow the human drives, since rework on a stacked change
would mean rebasing every change above it. The run stops when the reviewer escalates, when QA or
the reviewer fail the same change twice, when the backlog is empty, or when as many changes as the
human allowed are waiting for
them ("until three changes wait for me"; no number means no cap). Every change waiting unapproved
is code the next one builds on and the human may still send back: approve and archive early. No
agent reads the files of other changes, open or archived; what outlived them is in the skills.
