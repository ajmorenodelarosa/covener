<div align="center">

# Covener

**Spec-driven development for AI agent teams.**<br>
Governance for regulated domains and large projects: traceable, auditable, human-approved.

[![CI](https://github.com/ajmorenodelarosa/covener/actions/workflows/ci.yml/badge.svg)](https://github.com/ajmorenodelarosa/covener/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/covener.svg)](https://pypi.org/project/covener/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/covener/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

```bash
pip install covener && covener init
```

</div>

---

Covener is a repository layout, a deterministic checker and a set of agent definitions that turn
Claude Code, Cursor or any tool that reads `AGENTS.md` into a development team you can govern.

- **Specs are the source of truth.** `specs/<domain>/<name>.md` says what the product must do,
  grouped by domain so an agent reads a whole domain before changing it. Bugs and tasks are one file
  each. None of them holds design, history or chat.
- **The change is the unit of work.** `covener change start account-closure --spec privacy/account-closure`
  creates a folder for three files: `design.md` (how), `tasks.md` (the plan) and `implementation.md`
  (what happened). One change, one branch, one pull request; an item is in at most one open change.
  No sprints and no iteration ceremony: you go item by item.
- **You approve the design, then the plan, before there is code.** The engineer writes `design.md`
  and stops; you edit it, ask for changes and set it `approved`. Then it writes the tasks and stops
  again. Each file carries its own status, the way a spec does, and `covener status` says which one
  is waiting for you. The design belongs to the change and is archived with it.
- **Approval is a rule that code enforces.** `covener change archive <name>` refuses unless you set
  `implementation.md` to `approved`, and while a task is open; then it marks the items done and
  files the change under `changes/archive/`. `covener status --strict` fails CI on that rule and
  every consistency rule.
- **The backlog is derived, never written.** Approved specs, open bugs and open tasks that are not in
  an open change, bugs first, then by priority. Nothing to maintain, nothing for a team to collide on.
- **Skills carry your conventions.** `skills/<name>/SKILL.md` in the Agent Skills open standard,
  linked one by one into `.claude/skills` (Claude Code) and `.agents/skills` (Cursor, Codex,
  Copilot). `frontend`, `backend` and `architecture` ship as templates to fill in; a convention
  broken twice becomes a line in one of them, and a decision that outlives its change becomes a line
  in `architecture`.
- **Knowledge is evidence.** Regulations and contracts in `knowledge/` become a page-anchored corpus
  with a citation graph; specs cite `file#page-N`, the reviewer verifies, and `status` flags dangling
  references.
- **The core runs no server and calls no model.** Once initialised, the repository works without the
  package. Three commands; the knowledge layer and the MCP server are optional extras.

## Why Covener

Spec-driven development tools agree on the cycle: a spec, a design, a task list the agent ticks.
Spec Kit, Kiro and OpenSpec all arrive there, and Covener keeps that cycle rather than inventing
another. What they leave to the conversation is what a regulated project cannot leave there. The
spec drifts as soon as code changes. Human approval is a "looks good" in a chat that nothing
verifies. The decisions made while building vanish with the session. And nobody can say which
article of which regulation a requirement comes from. BMAD answers with a dozen personas and the
process overhead that comes with them.

Covener adds four things to the cycle. **Specs are living documents**: editing a done spec reopens
it, a change carries the edit, and the archived changes are its history. **Every design, plan,
decision and review is written in the change that produced it**, so a new session starts from the
record instead of from zero. **An item is done only when a person set its implementation to
`approved`**, and the command that closes a change refuses without it, which makes the approval
something an auditor can rely on rather than a line in a prompt. **Requirements that come from
regulations cite their evidence page by page**, backed by a citation graph built without a model,
so nothing about a law can be hallucinated.

And it is built for teams. When several developers drive agents, the volume of generated code outgrows
line-by-line review, and what actually happens is skimming. Covener gives the reviewer a map instead:
one change, one plan you approved, one record that says what was built, what was decided, which test
proves which criterion, and what the independent reviewer flagged, with file and line. The human
reads the code where the map points. All of it with three files per change, five roles with hard
boundaries, and a layout you can explain in a minute.

## How it works

```bash
cd my-project
covener init          # links the agents into Claude Code and Cursor; never overwrites your files
```

Then talk to the team in your IDE. Take a bank:

> Customers must be able to close their account and have their personal data erased.

A naive agent deletes the customer. That breaks the law: GDPR grants the right to erasure, but EU
anti-money-laundering rules require the bank to keep identity and transaction records for five years
after the relationship ends, and GDPR itself exempts data kept to meet a legal obligation. This is the
kind of requirement Covener is built for.

| Step | Who | What happens in the repository |
|---|---|---|
| 1 | product | Reads every spec in `specs/privacy/`, asks the Knowledge Oracle, finds both obligations and the exemption, and drafts `specs/privacy/account-closure.md` with acceptance criteria and `references:` to the evidence. You set `status: approved`. |
| 2 | you (or planner) | `covener change start account-closure --spec privacy/account-closure`. The planner is optional: it reads the backlog and proposes the next item when you want it to. |
| 3 | engineer | Writes `design.md` (approach, flows, retention schedule, alternatives) and stops. |
| 4 | you | Read it, edit it, add the constraint the agent could not know, ask for changes in the conversation. When it is right, set `status: approved`. |
| 5 | engineer | Writes the plan in `tasks.md`, one checkbox per step naming the criterion it serves, and stops. You approve it the same way; only then is code written. |
| 6 | engineer, qa, reviewer | The code and the tests, ticking tasks and recording decisions in `implementation.md`. QA maps each criterion to a test; the reviewer checks architecture, security and every cited page. Both record their verdict there, and the engineer sets it to `review`. |
| 7 | you | Read the record, then the code where it points. Rework is a task you add under `## Rework`; when the result is right, set `implementation.md` to `approved`. |
| 8 | anyone | `covener change archive account-closure`: refused without that approval; with it, the spec becomes `done` and the change is filed by date. Six months later an auditor asks why a closed customer's passport scan still exists: the spec, the citations, the design, the plan, the review and your approval are all in the repository. |

```bash
covener status        # backlog, open changes, inconsistencies, what to do next
```

## Repository layout

```
specs/vision.md                     product intent
specs/<domain>/<name>.md            what the product is (draft -> approved -> done)
bugs/<id>.md                        what is wrong (open -> done); spec: names the affected spec
tasks/<id>.md                       work that changes neither: migrations, refactors, upgrades
changes/<name>/design.md            how it will be built (draft -> approved); optional
changes/<name>/tasks.md             the items it covers and the plan (draft -> approved)
changes/<name>/implementation.md    what happened: summary, decisions, QA, review (in-progress -> review -> approved)
changes/archive/YYYY-MM-DD-<name>/  finished changes: the history of the product
knowledge/                          optional: domain documents, their Markdown, INDEX.md, CITATIONS.md
skills/<name>/SKILL.md              this project's conventions; .claude/skills and .agents/skills link to each skill
agents/<name>.md                    one file per agent; .claude/agents and .cursor/agents link to each file
AGENTS.md                           a small block every coding agent reads (CLAUDE.md imports it)
.covener/config.yaml                role to agent mapping and tools; nothing else
.covener/states.yaml                the states and the human gates, as the agents read them
```

**Which file?** If in a year someone must read it to know what the product is, it is a spec. If it
describes something that is wrong today, it is a bug. If they only need to know it was done, it is a
task. How you are going to build it is none of those: it is the design of a change, and the steps
to build it are its tasks.

**Domains.** The first folder under `specs/` is the domain: `specs/privacy/account-closure.md` has the
id `privacy/account-closure`. The Product agent reads the whole domain before writing, which is how
contradictions and duplicates are caught before they reach code, and the reviewer checks a change
against its sibling specs. Bugs and tasks stay flat; their `spec:` field puts them in a domain.
`covener status --domain privacy` shows only that domain. Small projects can keep `specs/` flat.

**Living specs.** To extend, change or remove a requirement you edit the spec; it goes back to
`draft`, you approve it again, and a change carries it. Its history is the archived changes that
touched it, and that is what the delta is measured against: QA and the reviewer diff the spec since
the last archived change, so an edit of one line is reviewed as one line, not as the whole spec.

## The change

A change is a folder with three files, each with its own status and its own approval. `design.md`
says how it will be built, `tasks.md` which items it covers and the plan, `implementation.md` what
happened.

```bash
covener change start account-closure --spec privacy/account-closure   # --bug, --task, repeatable
covener change archive account-closure                                # only with your approval
```

`start` creates `tasks.md` as a draft listing the items, and nothing else; it refuses an item that
does not exist, is not ready (a draft spec, a done bug) or is already in another open change.
`archive` refuses a change whose `implementation.md` you did not set to `approved`, one whose design
or tasks are still a draft, and one with an open task; once everything is approved and every task
is ticked, it sets the items to `done` and moves the folder to `changes/archive/<date>-<name>/`.
The rule is executed, not merely reported.

**Three gates, one mechanism.** Design before tasks, tasks before code, and you approve each in the
file itself, the way you approve a spec.

| File | Written by | Status | You |
|---|---|---|---|
| `design.md` | engineer | `draft`, `approved` | edit it, ask for changes, set it `approved`. Optional: a change too small for a design has none. |
| `tasks.md` | engineer | `draft`, `approved` | approve the plan: one checkbox per step, each naming the criterion it serves. |
| `implementation.md` | agents only | `in-progress`, `review`, `approved` | approve the result once the engineer has set it to `review`. |

Feedback goes in the conversation and ends up in the file: the engineer revises `design.md` until
you approve it, and rework after review is a task you add, or ask for, under `## Rework` in
`tasks.md`, which puts the change back in progress until it is ticked. Your part is three status
lines, one per file, and git records who wrote each one.

**Where architecture lives.** `design.md` describes one change and is archived with it. What every
change must respect, the shape of the system, its boundaries, the patterns it uses and the decisions
already taken, lives in `skills/architecture/SKILL.md`: the engineer reads it before designing, the
reviewer judges the design against it, and a decision that outlives a change is added to it in that
same change, so the next engineer inherits it instead of digging through the archive.

`tasks.md` after your approval, and `implementation.md` once the engineer has asked for your review:

```markdown
---
status: approved
items:
  - spec: privacy/account-closure
---

## Tasks
- [x] closure endpoint with strong customer authentication (AC1)
- [x] immediate erasure of marketing and profiling data (AC2)
- [x] KYC records moved to restricted retention with a five-year expiry (AC3)
- [x] customer-facing explanation of what is retained (AC4)

## Rework
- [ ] restrict retained records to the compliance role
```

```markdown
---
status: review
---

## Summary
Closure flow in accounts/closure.py; retention store in compliance/retention.py. 14 tests.

## Decisions
- 2026-09-20 Retention clock starts at the closure date, not the last transaction (AMLD Art. 40(1)).

## QA
Verdict: pass
- AC1 test_marketing_data_erased_immediately, AC2 test_kyc_retained_five_years.

## Review
Verdict: pass with notes
- high: compliance/retention.py:88 lets the support role read retained records; restrict to compliance.
```

The state of a change is derived from the three files and never stored: not started, awaiting
design, awaiting tasks, in progress, in review, approved. The rework task above is why this change is
in progress rather than in review; once it is ticked (the engineer also records a `## Rework` entry),
it is in review again, and your `status: approved` is what `change archive` checks.

## `covener status`

```
Covener

Product
  Vision: OK

Specs
  Total: 5
  Draft: 1
  Approved: 3
  Done: 1
  Domains: aml 2, payments 1, privacy 2

Bugs
  Total: 1
  Open: 1
  Done: 0

Tasks
  Total: 1
  Open: 1
  Done: 0

Skills: architecture, backend, frontend

Backlog
  Items: 4
  - bug erasure-skips-backups (priority 1)
  - task kyc-archive-eu-region (priority 1)
  - spec privacy/consent-management (priority 2)
  - spec payments/sepa-transfers (priority 3)

Changes
  account-closure: in review, tasks 5/5, design approved, qa pass, review pass with notes
    - spec privacy/account-closure

Done
  - spec aml/audit-trail (2026-09-10-audit-trail 2026-09-10)

Governance
  Pending human review: 1
  Pending spec approval: 1
  Errors: 0
  Warnings: 0

Next
  * Review and approve specs/aml/transaction-monitoring.md (draft)
  * Start a change for bug erasure-skips-backups: covener change start <name> --bug erasure-skips-backups
  * Review the implementation of change account-closure: set status: approved in changes/account-closure/implementation.md, or add rework tasks to changes/account-closure/tasks.md
```

*Pending human review* counts the three gates: a design, a plan or an implementation waiting for
you. `--domain <name>` to focus on one domain, `--json` for machines, `--verbose` for warnings,
`--strict` to fail CI on errors. No model is involved; it only reads files.

Errors are the rules that protect your authority and the repository's consistency: an item `done`
or a change archived without your approval of its implementation; tasks approved over a draft
design, or an implementation started over draft tasks; an item in two open changes; a draft spec or
an unknown id in a change; a change with no `tasks.md`; invalid statuses or unparsable files; a
change in `review` whose latest QA or review verdict is `fail`, so you are never asked to approve
work an agent failed; a missing vision; a configured agent without a definition; a skill that
breaks the standard (its `name` not matching its folder, or no description). Archived changes are
history: only the approval rules apply to them, so a spec that later changes never breaks CI.

## Teams and review

Agents make code cheap and review expensive. Covener answers with two things: a layout where
developers work in parallel without stepping on each other, and a unit of review that is not the diff.

**In parallel, without collisions.**

- One change, one branch, one pull request. Git isolates the work; Covener makes the rules checkable.
- Changes are named by what they deliver (`account-closure`, `fix-token-refresh`), never numbered, so
  two people branching on the same day cannot collide.
- An item is in at most one open change; `covener status` flags a second one after a merge, and
  `change start` refuses it in the first place.
- Specs, bugs and tasks are one file each and there is no backlog file, so there is no shared list to
  fight over.
- Finished changes are archived by date. Everything is committed.

**You look three times, and the first two are cheap.** The design and the plan, before the code
exists, are where an agent about to build the wrong thing well gets caught; the record is where you
check what it actually built.

**Review the work, then the code.** A reviewer reads one change: the tasks (what was done), the
summary (where), the decisions (why), the design it followed, the QA entry (which test proves which
criterion) and the reviewer agent's findings ordered by severity with file and line. Critical and
high findings, security, money and data are where you open the code. The rest you check against the
record. Your verdict is the status of `implementation.md`, and git records who set it and when.

**What a lead sees.** `covener status` across the repository: every open change, its state, task
progress and the QA and reviewer verdicts, what is waiting for a human, what is inconsistent. A
domain lead runs `covener status --domain billing`. It is the stand-up, generated from the files.

**What the rule can and cannot do.** Nothing physically stops an agent from typing
`status: approved`. The agent prompts forbid it, `status` makes every approval a visible line that
CI checks, `change archive` refuses without it, and git blame tells you who wrote it. That is more
than a review step in a prompt, and less than a signature; treat it accordingly.

**Your reviewer in CI.** The reviewer agent is a file in your repository, so the same agent that
reviews in the IDE can review a pull request headlessly and publish its findings as the starting point
for the human reviewer. An example with Claude Code; adapt it to your CI and tool:

```yaml
- run: pip install covener && covener status --strict
- run: npm install -g @anthropic-ai/claude-code
- env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    claude -p "Review this pull request against the tasks and the implementation record of the change it closes. Report \
      findings by severity with file and line, and compliance against cited references." \
      --agent reviewer --allowed-tools "Read" "Bash(git diff *)" "Bash(git log *)" \
      >> "$GITHUB_STEP_SUMMARY"
```

## Bugs, tasks and hotfixes

A **bug** is a deviation from the product. A **fix** is the change that corrects it. A **hotfix** is a
fix that cannot wait. A **task** is work that leaves no requirement behind. The words stay apart; the
flow stays the same.

| Situation | Flow |
|---|---|
| Trivial fix (one place, no design decision) | "Fix this." The engineer fixes it with a test and tells you. No file, no change. |
| Bug worth tracking | "This is the problem." Product registers `bugs/<id>.md` (symptom, reproduction, cause if known, expected behaviour, affected spec), `open` from the start: a bug is reported, not approved. It goes to the top of the backlog until someone starts a change for it. |
| Hotfix | The same, without waiting: `covener change start fix-token-refresh --bug token-refresh` right now. The cycle runs in an hour instead of a week, and nothing else has to pause, because there is no sprint to interrupt. |
| Technical work | "Move the KYC archive to an EU region." You or the planner register `tasks/<id>.md` with goal, why, scope, done-when, risk and rollback. Same cycle. If the work leaves a durable requirement ("customer data never leaves the EU"), it is a spec instead. |

Bugs and tasks never touch a spec. If a bug reveals the spec was wrong, or a task changes what the
product promises, that is a separate edit to the spec.

## Project Knowledge

Regulated products depend on documents nobody reads twice: laws, contracts, procedures, internal
standards. Covener makes them a first-class input with evidence, so an agent never writes "the
regulation says" from memory.

```bash
pip install "covener[oracle]"        # "covener[knowledge]" for the deterministic layer only
cp ~/regulations/*.pdf knowledge/
covener knowledge build              # incremental: only new or changed documents are processed
```

**Deterministic layer**, no model, no network. Every source becomes Markdown with `## Page N` headings
next to it; `knowledge/INDEX.md` lists the corpus; `knowledge/CITATIONS.md` is the graph of explicit
cross-references between documents, resolved to the documents in the corpus. Patterns cover EU
regulations and directives and Spanish-language public law today; adding a jurisdiction is one regular
expression. Nothing in this layer can be hallucinated.

**Knowledge Oracle**, optional. A graph of entities and relationships plus vector retrieval over the
same Markdown, built with a frontier model and stored as local files (LightRAG: NetworkX graph,
nano-vectordb, no server). One tool, `search_knowledge`, returns answer, relations and evidence with
`knowledge/<file>.md#page-N` references. The evidence list is the part to trust: when retrieval finds
nothing, it is empty and the answer is instructed to say so.

```bash
covener knowledge ask "A customer closes their account and asks us to delete everything. What must we erase and what must we keep?"
```

```
Erase personal data without undue delay once it is no longer necessary [gdpr.md#page-43], except data
you must keep to comply with a legal obligation [gdpr.md#page-44]. Customer due diligence documents
and transaction records must be retained for five years after the end of the business relationship
[amld.md#page-31] and deleted afterwards [amld.md#page-31]. Recipients of the data must be told about
the erasure [gdpr.md#page-45].

Evidence
  - knowledge/gdpr.md#page-43: Article 17(1) ... the controller shall have the obligation to erase ...
  - knowledge/gdpr.md#page-44: Article 17(3)(b) ... for compliance with a legal obligation ...
  - knowledge/amld.md#page-31: Article 40 ... for a period of five years after the end of the business relationship ...
  - knowledge/gdpr.md#page-45: Article 19 ... communicate any rectification or erasure ...
Relations
  - data-retention-policy -> gdpr (citation)
  - data-retention-policy -> amld (citation)
  - personal data -> customer due diligence (graph)

(backend: oracle)
```

With no API key the same question is answered by a deterministic search over the same Markdown, in
the same shape and with the same evidence references (`backend: grep`). There is no mode in which
either backend answers without evidence: it returns none and says so.

**How the team uses it.** Product asks the Oracle before drafting a governed spec and cites the
evidence in `references:`. Engineer reads the cited pages before designing. Reviewer opens every
citation, checks the implementation against the wording, and asks the Oracle whether an uncited
document contradicts the spec: a contradiction is a `fail`. `covener status` warns when a reference
points to a file that does not exist.

```yaml
# specs/privacy/account-closure.md
references: [knowledge/gdpr.md#page-43, knowledge/gdpr.md#page-44, knowledge/amld.md#page-31]
```

Models: `claude-sonnet-5` for extraction and answers, `voyage-4-large` for retrieval, both
multilingual; the Oracle answers in the language of the question. Override with `COVENER_LLM_MODEL`
and `COVENER_EMBED_MODEL` (`voyage-law-2` is tuned for legal text). Keys (`ANTHROPIC_API_KEY`,
`VOYAGE_API_KEY`) live in the environment, never in the repository. Indexing is incremental and costs
on the order of a few dollars per hundred documents, depending on model and document length. The graph
lives in `.covener/knowledge/` (ignored by git, rebuildable); the Markdown and both index files are
committed and reviewable.

## Skills: your conventions, not generic advice

An agent already knows React and Postgres. What it does not know is that your forms use one wrapper,
that your migrations never backfill in the same deploy, or that raw hex colours are banned. That is
what a skill is for.

```
skills/frontend/SKILL.md      structure, state, data fetching, forms, styling, accessibility, tests
skills/backend/SKILL.md       layout, API contracts, data and migrations, errors, authorisation, logs
skills/architecture/SKILL.md  shape, boundaries, patterns, data ownership, the decisions every change respects
skills/<yours>/SKILL.md       api-design, data-migrations, mobile, whatever your stack needs
skills/<name>/reference/…     longer material the agent reads only when it needs it
skills/<name>/scripts/…       scripts it runs instead of writing code
```

Skills follow the [Agent Skills](https://agentskills.io) open standard: a folder with a `SKILL.md`
whose front matter carries `name` (matching the folder) and `description`. There is one copy of each
skill, and `covener init` links it where every harness looks:

| Harness | Reads | How Covener covers it |
|---|---|---|
| Claude Code | `.claude/skills/` only | a symlink per skill in `.claude/skills/`, the form the docs document as supported |
| Cursor | `.agents/skills/`, `.cursor/skills/`, `.claude/skills/` | natively through `.agents/skills/` |
| Codex CLI | `.agents/skills/`, `.codex/skills/` | natively through `.agents/skills/` |
| GitHub Copilot | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | natively through either |

The links are per skill, not one link for the whole directory: Claude Code documents "a
`<skill-name>` entry ... can be a symlink to a directory elsewhere on disk", while a symlinked
skills directory is undocumented and has open discovery bugs. Per-entry links also mean your own
skills can sit in `.claude/skills/` next to Covener's, untouched. Agents are linked the same way,
one file at a time. Where symlinks are unavailable (Windows without Developer Mode) the entries are
copied and `init` says so; re-run it after editing.

`frontend`, `backend` and `architecture` ship as templates with the sections that matter and a done
checklist.
Until you fill them in, `covener status` marks them `(template)` and tells you to, because an empty
skill is worse than none: the agent falls back on generic habits.

Adding a skill is creating the folder and running `covener init` once, so the links exist for every
tool. Editing one needs nothing: the link points at your file.

**How the team uses them.** The engineer reads `architecture` before designing and the skill for
the layer it is touching before writing code, and follows their checklists. QA takes its test
expectations from the same file. The reviewer checks the change against them, and when a convention
is broken twice, the finding comes with one proposed line for the skill. That is how a project's
conventions accumulate instead of being re-explained every session.

Writing one that actually fires: the description is a routing rule in the third person, saying what
it covers **and** when to use it; one job per skill; `SKILL.md` short, with detail in `reference/`;
your practice, not best practice.

## Tools: CLI and MCP

The same implementation has two doors: the CLI for people and CI, and a local MCP server for the
model. `AGENTS.md` tells the agents when to use which.

| Level | For | Registered in | Covener |
|---|---|---|---|
| CLI | people, CI | installed | `covener init`, `status`, `change start`, `change archive`, `knowledge`, `serve` |
| Instructions | the model, at session start | `AGENTS.md`, `agents/*.md` | when to use each tool or command |
| MCP tools | the model, any time | `.mcp.json`, `.cursor/mcp.json`, written by `init` | `status` (optionally for one domain), `search_knowledge`, `list_knowledge_sources` |
| Chat commands | you, as shortcuts | `.claude/commands`, `.cursor/commands` | roadmap |

```bash
pip install "covener[mcp]"     # included in covener[oracle]
covener init                   # registers the server; re-run after installing the extra
```

Claude Code reads `.mcp.json` (project scope, committed) and asks you to accept the server once.
Cursor reads `.cursor/mcp.json`; enable it under Settings, MCP. Codex, Windsurf and others: point
their MCP config at `covener serve` (stdio). The server exposes nothing that changes the repository.

## The agents

Five roles with explicit boundaries, one Markdown file each in `agents/`, in the front matter format
Claude Code and Cursor read natively. `init` puts one link per agent in `.claude/agents` and
`.cursor/agents`, so there is exactly one copy of each agent and editing it is editing the file.

| Role | Owns | Never |
|---|---|---|
| product | vision, impact analysis, specs by domain, bug intake, evidence in `references:` | code, design, approving its own specs |
| engineer | the design, the plan, the implementation, fixes (regression test first), the record | editing specs, setting anything to `approved` |
| qa | tests from acceptance criteria, acceptance verification, regressions | changing application code, ticking tasks |
| reviewer | consistency with the domain, architecture, security, quality, compliance against citations | editing anything |
| planner (optional) | what to work on next, and starting the change for it | the design or the plan of a change; anything once it is open |

There is no architect role. The engineer designs and plans every change, and what an architect
would carry in their head lives in `skills/architecture/SKILL.md`, which the engineer reads before
designing and the reviewer judges the design against.

The planner exists for autonomous or batch runs, and for the days you would rather be told what is
next. Turn it off (`planner: off`) and nothing else changes: you start the change yourself.

The prompts follow current Anthropic and OpenAI guidance for frontier coding models: clear objective,
just-in-time reads, explicit outputs, explicit human gates, no permission-seeking for work already
requested. The model is a property of the agent (`model: claude-sonnet-5` or `inherit`); defaults are a
fast model for QA, a balanced one for the engineer, a strong one for the rest.

**Extending the team.** Roles are the contract; agents are files. Rename or disable a role in
`.covener/config.yaml`; add an agent by adding a file and running `covener init` once to link it (a
`frontend-engineer.md` next to `engineer.md` is then visible to every tool). For stack-specific
know-how, prefer a skill over another role: skills load only when the task needs them, so one
engineer with `frontend`, `backend` and `infra` skills stays cheaper and more consistent than three
engineers with three prompts. Keep `agents/` for boundaries and `skills/` for expertise.

```yaml
# .covener/config.yaml
agents:
  reviewer: security-reviewer   # agents/security-reviewer.md
  planner: off
tools: [claude, cursor]
```

## Install

```bash
pip install covener            # or: uv tool install covener / pipx install covener
covener init                   # --tools claude,cursor  --dry-run  --adopt  --install-agents
covener status                 # --domain <name>  --json  --verbose  --strict
covener change start <name>    # --spec ID  --bug ID  --task ID
covener change archive <name>
covener knowledge build        # --no-graph  --dry-run        (covener[knowledge] or [oracle])
covener knowledge ask "..."    # --json
covener serve                  # MCP over stdio               (covener[mcp])
```

Python 3.10+. One runtime dependency (PyYAML). No network. `-C <dir>` works on every command.

**`init` checks before it writes.** It looks at the directories it needs and, if one of them already
belongs to something else, it refuses and writes nothing:

```
$ covener init
covener init: this repository already uses directories Covener needs, so nothing was written:

  specs/ holds openapi.yaml, payments.md
    Covener expects specifications: Markdown with `title` and `status` in front matter there.
  tasks/ holds build.sh
    Covener expects task files: Markdown with `title` and `status` in front matter there.

Either move that content elsewhere, or run `covener init --adopt` to share the directories:
Covener adds its own files, leaves yours alone, and `covener status` reports the ones it
cannot read as specs, bugs or tasks.
```

`--adopt` shares the folder: your files stay untouched, Covener's are added, and non-Markdown files
are simply ignored by `status`. A repository that already has `.covener/config.yaml` is Covener's,
so re-running `init` never blocks.

Content already in Covener's shape is adopted without asking. If your `agents/` holds Markdown with
`name` and `description`, or your `specs/` holds Markdown with `title` and `status`, they are your
agents and your specs: Covener uses them, adds only what is missing, and a role you already define
keeps your file.

**Your instructions and tool directories are never a conflict.** An existing `AGENTS.md` keeps its
content and gets the Covener block between `<!-- covener:start -->` and `<!-- covener:end -->`;
re-running `init` refreshes only that block. If your `AGENTS.md` carries stack conventions, they
belong in `skills/`, which agents load only when relevant, and `init` says so when it finds one. An
existing `CLAUDE.md` gets an `@AGENTS.md` import. Existing `.claude/agents/`, `.claude/skills/`,
`.cursor/agents/` and `.agents/skills/` keep their own entries and gain one link per Covener agent
or skill. A legacy `.cursorrules` is reported.

**Windows.** Without Developer Mode, skill folders become directory junctions and agent files are
copied; `init` says which. Clone with `git config core.symlinks true`, or run `covener init` after
cloning to repair the links.

**CI.**

```yaml
- run: pip install covener && covener status --strict
```

## What Covener does not do

No project-management UI. No orchestration engine. No sprints, iterations or velocity. No MCP
requirement. No autonomous deployment. No user stories or requirement layers. Updating the package
never touches your files. The repository works without the package installed.

## FAQ

**Why no sprints?** Because agents do not need them. A sprint exists to batch work for people who
estimate together; with agents you go item by item, and what matters is that each change is designed,
planned, built, reviewed and approved. The archive gives you the history a sprint used to give you.

**Does approving the design and the plan slow me down?** Each approval is one status line in the
file, and the design gate exists only when there is a design: a small change goes straight to the
tasks. You can also edit `design.md` or `tasks.md` yourself and approve your own version. They are
the cheapest places to catch an agent that understood the task differently.

**Do I need the planner?** No. Set `planner: off` and start changes yourself. It earns its place when
you want the backlog triaged for you, or when you run agents unattended.

**Do I need MCP, hooks or a server?** No. The repository provides the context. `covener serve` is
optional and runs locally over stdio, for IDEs that prefer tools to shell commands.

**Can I use my own agents or skills?** Yes. Drop a file in `agents/` or a folder in `skills/` and run
`covener init` once so every tool gets its link; editing one afterwards needs nothing, because the
link points at your file. Rename or disable roles in `.covener/config.yaml`. Put stack-specific
expertise in skills rather than in more roles.

**What if I uninstall the package?** Everything keeps working. The method is in the files; `status` and
`change` are only a checker and a scaffold.

**Does it work with Codex, Copilot or Windsurf?** They read `AGENTS.md`, so the instructions and the
layout work. Agent files are linked for Claude Code and Cursor today; other adapters are a few lines
each.

**Why not just a good CLAUDE.md?** A CLAUDE.md tells an agent how to behave. It does not keep decisions
between sessions, does not separate what must be true from what happened, cannot stop an agent from
calling something done, and cannot cite a regulation with a page number. Covener adds exactly those
four things.

**How close is this to OpenSpec, Spec Kit and Kiro?** Deliberately close. The change folder with a
design, a task list and a dated archive is OpenSpec's; design then tasks, each explicitly approved
before the next, is Kiro's; the plan as a checklist the agent ticks is what all three do. Covener
adds the four things above: specs that live on after the change, the record of what happened kept
with the change, an approval that is a status in the file and that the archive command checks, and
requirements that cite their evidence.

## Roadmap

- Codex and Windsurf link adapters.
- `/covener` chat commands for approving and requesting changes from the conversation.
- Knowledge Oracle: DOCX and HTML sources and more citation jurisdictions.

## Contributing

Issues and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
pip install -e ".[dev]" && pytest && ruff check . && mypy
```

Standards used: [AGENTS.md](https://agents.md/), Claude Code
[subagents](https://code.claude.com/docs/en/sub-agents) and
[CLAUDE.md imports](https://code.claude.com/docs/en/memory), Cursor
[subagents](https://cursor.com/docs/agent/subagents) and [rules](https://cursor.com/docs/context/rules);
the change-centric workflow follows [OpenSpec](https://openspec.dev/docs/team-workflow), with
conventions from [spec-kit](https://github.com/github/spec-kit) and [Kiro](https://kiro.dev/docs/specs/);
[LightRAG](https://github.com/HKUDS/LightRAG) and [Voyage AI](https://docs.voyageai.com/) for the Oracle.

## License

MIT. Built by [@ajmorenodelarosa](https://github.com/ajmorenodelarosa).
