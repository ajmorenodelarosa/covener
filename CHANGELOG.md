# Changelog

## [0.9.3] - 2026-09-27

Upgrading no longer means re-editing the agents, and the rest of what a second unattended run turned up.

### Added
- `covener init --update-defaults` replaces each agent prompt and each file in `changes/TEMPLATE/`
  with the packaged version, keeping the agent's own front matter: the `model` and `effort` you
  chose survive the upgrade, and git shows what changed in the prompts. Without the flag `init`
  only says which ones differ, and it now compares the prompt body, so a changed model is not a
  customised agent. The change templates get the same notice; they were silently kept before.

### Changed
- AGENTS.md rule 2: code delivered by another open change is edited only where this change's item
  requires it, said in `design.md` and recorded in `implementation.md`; the other change's rework
  keeps waiting for the human. The reviewer treats anything beyond that as unrequested behaviour.
- `tasks.md` holds engineering steps only: asking QA and the reviewer is not a task. The engineers
  kept listing it, and a plan showed 30 of 31 while QA worked.
- QA and the reviewer reread `implementation.md` right before writing and append at the end, since
  0.9.2 lets them run at the same time.

### Fixed
- `{{` no longer marks a file as a template: a skill that documents Django, Jinja or Handlebars
  syntax was reported as unfilled. Only `<!-- TODO` and `TODO:` do.

### Upgrading
```bash
pip install -U covener          # uv: uv tool install --reinstall --refresh "covener[mcp]"
covener init                    # states.yaml and the AGENTS.md block; says what else differs
covener init --update-defaults  # take the packaged prompts and templates, keeping your models
```
Then add `approvals:` to `.covener/config.yaml` by editing the file (the key must appear once):
```yaml
approvals:
  design: reviewer
  tasks: reviewer
```

## [0.9.2] - 2026-09-27

Prompt and template fixes from an unattended run where a design took twenty minutes to write and
three files repeated the same tests. No change to the checker or the gates.

### Changed
- `design.md` is bounded: approach, flows, interfaces, decisions with their reason, risks; read in
  five minutes. No tests, no lists of files, no line numbers: the tests go in `tasks.md` and the
  evidence in the QA entry. The template, the engineer and the reviewer say so, and a design that
  does the plan's work goes back for that, not for more detail.
- With both gates delegated, the engineer hands `design.md` and `tasks.md` together and the
  reviewer judges them in one pass, each approved in its own front matter.
- QA and the reviewer are independent and can work at the same time; the reviewer reads the QA entry
  when it exists and does not wait for it.
- The reviewer's verification depth follows the risk of the change: a library's source for
  authentication, money and personal data, lighter where a mistake costs little.
- No agent reads the files of other changes, open or archived; what outlived them is in the skills.
  The planner's briefing is the item and its references, not a reading list.
- Unattended runs also stop when as many changes as the human allowed are waiting for them
  ("until three changes wait for me"); AGENTS.md says why stacking unapproved changes costs.
- `covener init` says when an `agents/<name>.md` differs from the definition packaged with the
  installed version, with the two ways to take the new one. Agents are still never overwritten.

### Upgrading from 0.8 or 0.9.0
`pip install -U covener && covener init` refreshes `.covener/states.yaml` and the Covener block in
`AGENTS.md`, and leaves the configuration alone (no `approvals:` means every gate is yours). The
agent definitions are the project's and are not refreshed: for each one you did not customise,
delete it and run `covener init --install-agents`; merge the others by hand from the note `init`
prints.

## [0.9.1] - 2026-09-27

Prompt fixes from a first unattended run, where the chain broke at the design. No CLI change.

### Changed
- A change delivers its item whole: every acceptance criterion, in every layer it touches, and the
  plan has as many steps as that takes (AGENTS.md rule 3, engineer, reviewer). A design that
  leaves a layer for later is incomplete.
- `design.md` carries no open questions. Engineering decisions are the engineer's to take and
  write, with the reason; what it assumed and could not confirm goes under `## Decisions` in
  `implementation.md`, which the human reads when approving the implementation. The engineer's
  recap ends with what to look at first, not with what the human must decide.
- The reviewer sends back a design with a question in it instead of escalating it, and escalates
  only when the architecture skill is still the template, after two rounds without agreement, or
  when the item itself contradicts another item or a cited source.
- The planner never skips an item: it takes the first of the ordered backlog, and an item too big
  for one change goes to the product agent instead of being sliced. It keeps going while a change
  waits for the human's review of its implementation; before, any open change stopped it.
- An engineer facing a layer skill that is still the template follows the existing code and
  records the convention it assumed, and asks the human only when they are in the conversation.
- AGENTS.md gains a short *Unattended runs* paragraph: routine decisions are the agents' and are
  recorded, the implementation is the only human gate when both others are delegated, and the run
  stops on an escalation, two failed verdicts on one change, or an empty backlog. The README says
  what "run the backlog unattended" then means.

## [0.9.0] - 2026-09-27

You can hand the design gate, the plan gate or both to the reviewer and read only the result. The
implementation is always yours.

### Added
- `approvals:` in `.covener/config.yaml`: `design` and `tasks`, each `human` (the default, also when
  absent) or `reviewer`. `init` writes both gates as `human` in a new configuration and never
  touches an existing one. `reviewer` on a gate while the reviewer role is `off` is a configuration error.
- `approved-by:` in the front matter of `design.md` and `tasks.md`: the reviewer signs
  `approved-by: reviewer` when it approves a delegated gate; a person approving a delegated gate
  writes `approved-by: human`. A gate that is yours carries no signature.
- Checks: `change.approval-not-delegated` (signed by the reviewer on a gate the configuration keeps
  for you), `change.approver-missing` (a delegated gate approved with no signature),
  `change.invalid-approver` and `change.approver-on-draft`. Archived changes are only checked for a
  valid value, since the configuration may have changed since.
- `covener status` counts only your gates in *Pending human review*, tells the reviewer what to
  approve on a delegated gate, prints `design approved by reviewer` and `tasks approved by
  reviewer`, and the JSON carries `approvers` per change.

### Changed
- The reviewer is the team's architect and most senior engineer: its identity says so, it is
  invoked for designs and plans as well as finished changes, and a section tells it how to approve a
  delegated gate (which checks apply before there is code, the bar for a design, when to escalate:
  the architecture skill still a template, two rounds without agreement, a decision that is the
  product's or yours). The only status it ever sets is `approved` on a delegated gate.
- The engineer hands a delegated design or plan to the reviewer instead of stopping for you, and
  records what changed after the reviewer's or your objections under `## Decisions` when the reason
  matters later.
- The planner is no longer described as optional: it is who you ask what is most important now, and
  the agent that runs the backlog unattended when the first two gates are delegated.
- Default models: Opus for the engineer and QA, Fable for product, planner and reviewer.
- The AGENTS.md block, `.covener/states.yaml` and the `design.md` and `tasks.md` templates describe
  the delegated gate.

## [0.8.1] - 2026-09-23

### Fixed
- `covener init` refreshes `.covener/states.yaml` when the packaged one changed, so upgrading the
  package upgrades the state model the agents read. It is Covener's file, not the project's; the
  configuration, the agents and the vision are still never overwritten.
- `covener init` says so when `changes/TEMPLATE/` still holds `change.md` or `work.md` from 0.7.

## [0.8.0] - 2026-09-23

The change cycle now follows what OpenSpec, Spec Kit and Kiro settled on, and every human approval is
a status in the file being approved, the way a spec is approved.

### Changed
- A change is three files, each with its own `status` in front matter: `design.md` (how;
  `draft | approved`; optional), `tasks.md` (the items it covers and the plan, one checkbox per step;
  `draft | approved`) and `implementation.md` (what happened; `in-progress | review | approved`).
  `change.md` and `work.md` are gone: the items and the checklist moved to `tasks.md`, the agents'
  entries (summary, decisions, QA, review, rework) to `implementation.md`, and `opened`, `closed`,
  `title` and the change's own `status` were redundant with the folder, the archive date and the
  three files.
- Three gates in order, design before tasks and tasks before code, all crossed the same way: the
  engineer writes the file and stops, you edit it, ask for changes in the conversation and set
  `status: approved`. `## Feedback` entries and `Approved: Yes | No` no longer exist; feedback is
  incorporated in the file, and rework after review is a task you add under `## Rework` in
  `tasks.md`, which reopens the change until it is ticked.
- The state of a change is derived from the three files and never stored: `not_started`,
  `awaiting_design`, `awaiting_tasks`, `in_progress`, `in_review`, `approved`, `done`.
  *Pending human review* counts the three gates.
- `covener change start` creates only `tasks.md`, as a draft listing the items; the engineer adds
  `design.md` from `changes/TEMPLATE/` when the change needs one. `--title` is gone.
- `covener change archive` refuses unless `implementation.md` is `approved` and every task is
  ticked, and no longer writes a `closed` date: the archive folder carries it.
- New checks: `change.tasks-before-design`, `change.implementation-before-tasks`,
  `change.archived-without-approval`, one `invalid-<file>-status` per file, and a warning when an
  approved implementation still has open tasks. `change.no-work-log`, `change.review-without-work`,
  `change.done-without-approval`, `change.archived-open`, `change.invalid-status` and
  `change.duplicate-name` are gone with the files they checked.
- `status` prints `tasks 5/6` and `design approved` instead of `checklist 5/6` and `design`; the
  JSON carries `tasks`, `design` and `implementation` per change instead of `status`, `checklist`
  and `design`.
- The engineer prompt states that the plan is the engineer's to write (the planner only chooses the
  item, and there is no architect role: `skills/architecture` is what an architect would carry);
  QA and the reviewer record their verdicts in `implementation.md`; the AGENTS.md block,
  `.covener/states.yaml` and the templates carry the new cycle.

### Migrating a repository from 0.7
For each change, open or archived: create `tasks.md` with a front matter holding `status: approved`
and the `items:` list copied from `change.md`, and move the checklist from `work.md` under it;
rename `work.md` to `implementation.md` and give it a front matter with `status: approved` for an
archived change, `in-progress` or `review` for an open one; give `design.md` a front matter with
`status: approved`; delete `change.md`. Without `tasks.md` a change is not read, and an archived
change without its `items:` leaves the specs it closed as `done` with no approving change, which is
an error. Delete `changes/TEMPLATE/change.md` and `changes/TEMPLATE/work.md`; `init` adds the new
templates next to them but never removes files.

## [0.7.0] - 2026-09-21

### Added
- The design is a human gate. The engineer writes `design.md`, logs a `## Design` entry in the
  change's work log and stops; `covener status` reports the change as `awaiting design`, counts it
  in *Pending human review* and points at the file to read. You extend the design, reject it with
  `Approved: No`, or approve it with `Approved: Yes`, and only then is code written.
- `## Design` is a work-log entry kind of its own, next to `## Feedback` and the agents' entries.
- `skills/architecture/SKILL.md` ships as a third starter skill: the shape of the system, its
  boundaries, patterns, data ownership and the decisions every change must respect. `design.md`
  describes one change; this file is what outlives it. The engineer reads it before designing, the
  reviewer judges the design against it, and a decision that constrains future changes is added to
  it in the same change.
- The QA and Review verdicts are read by the checker. `Verdict: pass | pass with notes | fail` in
  `## QA` and `## Review` shows up in `covener status` next to the change, and a change in `review`
  whose latest verdict is `fail` is an error (`change.review-with-failing-verdict`): you are never
  asked to approve work an agent failed, and the agents are told to fix it first.

### Changed
- An `Approved: Yes` on a change that is still `open` approves the design, not the work: only a
  change in `review` (or already archived) counts as approved. This also closes a loophole, since
  `covener change archive` used to accept an approval written before the change ever reached review.
- `covener change archive` says which of the two approvals is missing instead of reporting a generic
  one.
- The engineer prompt, the AGENTS.md block, `.covener/states.yaml` and the `work.md` and `design.md`
  templates carry the gate; a change too small for a design skips it and says so, and a human who
  wants no design review for a change (an unattended run) says so and the `## Design` entry records it.
- QA and the reviewer treat a spec that was already `done` as its delta: they diff it against the
  last archived change that touched it, so editing one line of a living spec is reviewed as one line.

## [0.6.0] - 2026-09-21

### Added
- `covener init` runs a preflight check and refuses, writing nothing, when one of its directories
  already belongs to something else (a `specs/` of OpenAPI files, a `tasks/` of scripts, a
  `changes/` holding a changelog). The message names every clashing path and what was found.
- `covener init --adopt` shares those directories instead: your files stay, Covener's are added.
- Content already in Covener's shape is adopted without asking: your `agents/*.md` with `name` and
  `description`, your `specs/*.md` with `title` and `status`, your `skills/<name>/SKILL.md`.
- A repository that already has `.covener/config.yaml` is never blocked, so re-running `init` is
  still idempotent.

## [0.5.0] - 2026-09-21

### Changed
- Agents and skills are linked one entry at a time instead of by linking the whole directory.
  Claude Code documents a skill entry that is a symlink to a directory elsewhere as supported, while
  a symlinked skills directory is undocumented and has open discovery bugs. `covener init` replaces
  the directory links created by 0.4.0 and reports it.
- Skills now reach every harness through two locations: `.claude/skills/` (Claude Code, and Copilot)
  and `.agents/skills/` (Cursor, Codex, Copilot). The redundant `.cursor/skills/` is gone, since
  Cursor reads `.agents/skills/` natively.
- Existing tool directories keep their own agents and skills; Covener only adds its own links.

## [0.4.0] - 2026-09-21

### Added
- Skills: `skills/<name>/SKILL.md` in the Agent Skills open standard, linked into `.claude/skills`
  (Claude Code), `.cursor/skills` (Cursor) and `.agents/skills` (portable), the same way agents are.
- `frontend` and `backend` starter skills with the sections that matter and a done checklist.
  `covener status` lists the skills, marks the ones still in template form and says to fill them in.
- `status` reports broken skills: missing SKILL.md, missing name or description, a name that does not
  match its folder, an invalid name, a description over 1024 characters.
- The engineer reads the skill for the layer it touches, QA takes test expectations from it, and the
  reviewer proposes a line for it when a convention is broken twice.

### Fixed
- Two agent descriptions contained a colon, which broke their own YAML front matter and made the IDE
  ignore the file. A test now validates the front matter of every packaged agent and skill.

## [0.3.0] - 2026-09-21

### Added
- Changes as the unit of work: `changes/<name>/` with `change.md` (status and the items it touches),
  `design.md` (how it will be built, archived with the change) and `work.md` (checklist, summaries,
  decisions, QA, review, human feedback). Finished changes go to `changes/archive/YYYY-MM-DD-<name>/`.
- `covener change start <name> --spec|--bug|--task <id>` scaffolds a change and refuses an item that
  does not exist, is not ready, or is already in another open change.
- `covener change archive <name>` refuses unless the work log ends with a human `Approved: Yes`, then
  marks the change and its items done and files it by date. The approval rule is now executed, not
  only reported.

### Removed
- Sprints. Work goes item by item; the archive of changes is the history.
- The planner is now optional: it picks the next item from the backlog and starts the change, and does
  nothing once a change is open.

### Changed
- `covener status` lists open changes with their state, checklist progress and design, and the items
  each one touches.
- Agent prompts rewritten for the change flow: the engineer writes the design before the code, and no
  agent writes `## Feedback` or closes a change.

## [0.2.0] - 2026-09-14

### Added
- Domains: the first folder under `specs/` is the spec's domain (`specs/billing/refunds.md`).
  `covener status` counts specs per domain, and `--domain <name>` (also on the MCP `status` tool)
  shows only that domain: its specs, the bugs and tasks that name them, its sprints and next actions.
- `spec:` field on bugs and tasks links them to a spec and its domain; `status` warns when it names a
  spec that does not exist.
- Product reads the whole domain before writing a spec; the reviewer checks changes against sibling specs.

### Removed
- The `epic` field. Grouping is by domain folder; ordering is by `priority`. Existing `epic:` lines are
  ignored.

## [0.1.2] - 2026-09-14

### Changed
- README: clearer team review section, explicit limits of the approval rule, no unverifiable claims.

## [0.1.1] - 2026-09-14

### Changed
- README rewritten around governance, with a regulated example (bank account closure under GDPR and
  EU anti-money-laundering retention rules), and a section on team review: review the work log and the
  reviewer's findings instead of every generated line, including the reviewer agent in CI.
- `covener status` shows "checklist n/m" for work log progress.

### Fixed
- Citation graph recognises English references such as "Article 40 of Directive (EU) 2015/849".
- Link tests pass on Windows (symlinks or junctions).

## [0.1.0] - 2026-09-12

### Added
- Project Knowledge (`covener knowledge build | ask | serve`): sources in `knowledge/` converted to
  page-anchored Markdown, `INDEX.md`, a deterministic citation graph (`CITATIONS.md`), and the optional
  Knowledge Oracle (LightRAG graph + vectors, Claude + Voyage) served as one MCP tool, `search_knowledge`,
  returning answer, relations and evidence. `references:` field on specs and bugs, validated by `status`.
- `covener serve`: one local MCP server exposing `status`, `search_knowledge` and `list_knowledge_sources`
  to Claude Code, Cursor and any MCP client; registered by `init` when the `mcp` extra is installed.
- `covener init` (`--tools`, `--dry-run`, `--install-agents`): the Covener structure, the default
  team, `AGENTS.md` integration that never overwrites, `CLAUDE.md` import, and `.claude/agents` /
  `.cursor/agents` as links to `agents/` (junctions or copies where symlinks are unavailable).
- `covener status` (`--json`, `--verbose`, `--strict`): derived backlog by priority, open
  sprints with work states and task progress, done list, consistency errors that protect human
  approval, and what to do next.
- Five-agent default team (product, planner, engineer, qa, reviewer), one Markdown file each.
- One file per spec, bug or task; living specs (editing a done spec reopens it); sprints with one work
  log per item (checklist, entries, human feedback); bugs first in the backlog, then priority; hotfix as
  a one-bug sprint; closed sprints archived by date.
