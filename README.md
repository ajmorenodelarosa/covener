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

- **Specifications, bugs and tasks are files** with a status. What the product is, where it
  deviates, and what has to be done never mix and never grow.
- **Sprints hold the work**: one work log per item with a checklist, the agents' summaries,
  decisions and reviews, and your feedback. Closed sprints are archived; nothing is stored twice.
- **Approval is a rule in a file.** An item is `done` only when a human wrote `Approved: Yes` in its
  work log. `covener status --strict` fails CI when that rule, or any consistency rule, is broken.
- **Knowledge is evidence.** Regulations, contracts and procedures in `knowledge/` become a
  page-anchored corpus with a citation graph and an optional semantic graph; agents cite
  `file#page-N`, reviewers verify, and `status` flags dangling references.
- **Nothing runs a server, calls a model or needs the package** once initialised. Two commands for
  the method, one for knowledge, one to expose both as MCP tools.

## Why Covener

Spec-driven development already works: write the spec, let the agent implement it. What breaks at
scale, and in any environment with an auditor, is everything around the spec.

| The problem | What the field does | What Covener does |
|---|---|---|
| Agents forget between sessions; decisions live in chat | Constitution or steering files (spec-kit, Kiro) that describe conventions, not history | Every decision, review and human comment is logged in the sprint next to the item it belongs to. A new session starts from the log |
| "Done" means whatever the agent says | A review step in a prompt | `done` requires `Approved: Yes` written by a person; a script enforces it, so CI and auditors can rely on it |
| Numbered features and shared backlogs collide the moment two people branch | spec-kit numbers features; BMAD adds process; OpenSpec gets it right with one change per branch | OpenSpec's model applied to the whole repository: named sprints, one owner each, a derived backlog nobody edits, git does the isolation |
| Requirements from regulations get paraphrased into code | Nothing; at best a PDF pasted into context | A knowledge layer with page-anchored evidence and a citation graph built without a model, so nothing about a regulation can be hallucinated |
| Frameworks bury you in generated Markdown and roles | 8+ files per feature, 12+ agents | 2 files per item, 5 roles with explicit boundaries, and a folder layout you can explain in a minute |

Covener keeps what the field agreed on (one spec per feature, checklists, work separate from specs,
archive by date, `AGENTS.md`) and adds the three things nobody enforces: living specs with history,
human approval as a checkable rule, and evidence for domain knowledge.

## How it works

```bash
cd my-project
covener init          # links the agents into Claude Code and Cursor; never overwrites your files
```

Then talk to the team in your IDE:

> I want customers to connect their Stripe account and receive payments.

| Step | Role | What happens in the repository |
|---|---|---|
| 1 | product | Reads `specs/vision.md` and the existing specs, reports the impact, drafts `specs/stripe-connect.md` with acceptance criteria and, when a regulation applies, `references:` to the evidence. You set `status: approved`. |
| 2 | planner | Opens `sprints/payments-onboarding/` with the spec (and open bugs first) and writes the checklist in the work log. |
| 3 | engineer, qa, reviewer | Implement, test against the criteria, review architecture, security and compliance. Each writes its entry in the work log. |
| 4 | planner | Sets the sprint to `review` and tells you what to evaluate. |
| 5 | you | `Approved: No` with what to change, or `Approved: Yes`. |
| 6 | planner | Reworks until you approve, marks the spec `done`, archives the sprint. |

```bash
covener status        # backlog, sprints, inconsistencies, what to do next
```

## Repository layout

```
specs/vision.md                     product intent
specs/<id>.md                       what the product is: one living file per spec (draft -> approved -> done)
bugs/<id>.md                        what is wrong (open -> done)
tasks/<id>.md                       work that changes neither: migrations, refactors, upgrades (open -> done)
sprints/<name>/sprint.md            owner, status, specs, bugs and tasks in scope (active -> review -> closed)
sprints/<name>/<kind>s/<id>.md      the item's work log: checklist, summary, decisions, QA, review, feedback
sprints/archive/YYYY-MM-DD-<name>/  closed sprints
knowledge/                          optional: domain documents, their Markdown, INDEX.md, CITATIONS.md
agents/<name>.md                    one file per agent; .claude/agents and .cursor/agents link here
AGENTS.md                           a small block every coding agent reads (CLAUDE.md imports it)
.covener/config.yaml                role to agent mapping and tools; nothing else
```

Domain folders are fine: `specs/payments/stripe-connect.md` has the id `payments/stripe-connect`.

**Which folder?** If in a year someone must read it to know what the product is, it is a spec. If
it describes something that is wrong today, it is a bug. If they only need to know it was done, it
is a task. Specs are living documents: to extend, change or remove a requirement, edit the spec, it
goes back to `draft`, approve it again, and a sprint carries the change. Its history is the sprints
that touched it.

**No backlog file.** The backlog is every open bug, approved spec and open task that is not in an
open sprint: bugs first, then everything by two optional front matter fields, `priority` and `epic`.
Reprioritising is a one-line change in one file, so a team never fights over a list.

## The work log

`sprints/<name>/specs/<id>.md` (or `bugs/<id>.md`, `tasks/<id>.md`) is a chronological log. Agents
add entries; you add one.

```markdown
# stripe-connect

## Checklist
- [x] onboarding endpoint
- [x] token refresh
- [ ] operator docs

## Summary
Implemented in payments/onboarding.py; 6 tests in tests/test_onboarding.py.

## Decisions
- 2026-09-12 Store the Stripe account id, not the token; tokens are fetched on demand.

## QA
Verdict: pass
- AC1 test_onboarding_starts, AC2 test_reconnect_expired, AC3 manual check on staging.

## Review
Verdict: pass with notes
- medium: retry on 429 missing in payments/client.py:41; add backoff.

## Feedback
Approved: No
Also handle a revoked authorization, not only an expired one.

## Rework
Added revocation handling and a test.

## Feedback
Approved: Yes
```

The last entry is the state: awaiting feedback, changes requested or approved (the checklist does
not count). `covener status` derives everything from this file.

## `covener status`

```
Covener

Product
  Vision: OK

Specs
  Total: 4
  Draft: 1
  Approved: 2
  Done: 1

Bugs
  Total: 2
  Open: 2
  Done: 0

Tasks
  Total: 1
  Open: 1
  Done: 0

Backlog
  Items: 3
  [bugs]
    - wrong-currency (priority 1)
  [platform]
    - task migrate-postgres (priority 1)
  [payments]
    - spec refunds (priority 2)

Sprints
  payments-onboarding (review, alvaro): approved 1/2
    - spec stripe-connect: awaiting feedback, checklist 5/6
    - bug expired-tokens: approved, checklist 2/2

Done
  - spec reporting-api (2026-09-10-reporting-v1 2026-09-10)

Governance
  Pending human review: 1
  Pending spec approval: 1
  Errors: 0
  Warnings: 0

Next
  * Review and approve specs/ideas.md (draft)
  * Give feedback on spec stripe-connect in sprints/payments-onboarding/specs/stripe-connect.md
```

`--json` for machines, `--verbose` for warnings, `--strict` to fail CI on errors. No model is
involved; it only reads files.

Errors are the rules that protect your authority and the repository's consistency: an item `done`
without your `Approved: Yes`; a sprint `closed` with unapproved work; an item in two open sprints; a
draft spec, a done item or an unknown id in an open sprint; an open sprint in the archive; invalid
statuses or unparsable files; a missing vision; a configured agent without a definition. Closed
sprints are history: only the approval rule applies to them, so a spec that later changes never
breaks CI. A second open sprint for the same owner is a warning, not an error: that is what a
hotfix looks like.

## Working in a team

One sprint, one owner, one branch, one pull request. Git isolates parallel work; Covener makes the
rules checkable.

- Name sprints by what they deliver (`payments-onboarding`), never by number: sequential numbers
  collide the moment two people branch.
- The owner is a field in `sprint.md`. One open sprint per owner is the norm; an item is in at most
  one open sprint. `covener status` flags both after a merge.
- Specs, bugs and tasks are one file each, so two people rarely touch the same one. Approval is in
  the file.
- History is the archive of closed sprints plus `status: done` in the item. Archive after the pull
  request merges. Everything is committed; nothing is personal or ignored.

## Bugs, tasks and hotfixes

A **bug** is a deviation from the product. A **fix** is the change that corrects it. A **hotfix** is
a fix that cannot wait. A **task** is work that leaves no requirement behind. The words stay apart;
the flow stays the same.

| Situation | Flow |
|---|---|
| Trivial fix (one place, no design decision) | "Fix this." The engineer fixes it with a test and tells you. No file, no sprint. |
| Bug worth tracking | "This is the problem." Product registers `bugs/<id>.md` (symptom, reproduction, cause if known, expected behaviour), `open` from the start: a bug is reported, not approved. It waits at the top of the backlog for the next sprint; an active sprint's scope does not change. |
| Hotfix | Same, but the planner opens a one-bug sprint now (`sprints/hotfix-<slug>/`) and the cycle runs in an hour: regression test, fix, QA, review, your `Approved: Yes`, archive. |
| Technical work | "Migrate to Postgres." The planner registers `tasks/<id>.md` (goal, why, scope, done-when, risk and rollback), `open` from the start. Same cycle; QA verifies the done-when and that no spec regressed. If the work leaves a durable requirement ("data lives in Postgres"), it is a spec instead. |

Bugs and tasks never touch a spec. If a bug reveals the spec was wrong, or a task changes what the
product promises, that is a separate change to the spec.

## Project Knowledge

Regulated products depend on documents nobody reads twice: laws, contracts, procedures, internal
standards. Covener makes them a first-class input with evidence, so an agent never writes "the
regulation says" from memory.

```bash
pip install "covener[oracle]"        # "covener[knowledge]" for the deterministic layer only
cp ~/regulations/*.pdf knowledge/
covener knowledge build              # incremental: only new or changed documents are processed
```

**Deterministic layer**, no model, no network. Every source becomes Markdown with `## Page N`
headings next to it; `knowledge/INDEX.md` lists the corpus; `knowledge/CITATIONS.md` is the graph of
explicit cross-references between documents, resolved to the documents in the corpus. Patterns cover
EU regulations and directives and Spanish-language public law today; adding a jurisdiction is one
regular expression. Nothing in this layer can be hallucinated.

**Knowledge Oracle**, optional. A graph of entities and relationships plus vector retrieval over the
same Markdown, built with a frontier model and stored as local files (LightRAG: NetworkX graph,
nano-vectordb, no server). One tool, `search_knowledge`, returns answer, relations and evidence with
`knowledge/<file>.md#page-N` references. Without evidence it says so instead of guessing.

```bash
covener knowledge ask "What must happen when a customer asks us to delete their data?"
```

```
Personal data must be erased without undue delay when the data subject withdraws consent or the
data is no longer necessary [gdpr.md#page-43]; the controller must inform recipients of the erasure
[gdpr.md#page-44].

Evidence
  - knowledge/gdpr.md#page-43: Article 17 ... the controller shall have the obligation to erase ...
  - knowledge/gdpr.md#page-44: Article 19 ... communicate any rectification or erasure ...
Relations
  - gdpr -> data-retention-policy (citation)
  - data-retention-policy -> gdpr (citation)
```

**How the team uses it.** Product asks the Oracle before drafting a governed spec and cites the
evidence in `references:`. Engineer reads the cited pages before implementing. Reviewer opens every
citation, checks the implementation against the wording, and asks the Oracle whether an uncited
document contradicts the spec: a contradiction is a `fail`. `covener status` warns when a reference
points to a file that does not exist.

```yaml
# specs/data-erasure.md
references: [knowledge/gdpr.md#page-43, knowledge/data-retention-policy.md#page-2]
```

Models: `claude-sonnet-5` for extraction and answers, `voyage-4-large` for retrieval, both
multilingual; the Oracle answers in the language of the question. Override with `COVENER_LLM_MODEL`
and `COVENER_EMBED_MODEL` (`voyage-law-2` is tuned for legal text). Keys (`ANTHROPIC_API_KEY`,
`VOYAGE_API_KEY`) live in the environment, never in the repository. Indexing costs cents to a few
dollars per hundred documents. The graph lives in `.covener/knowledge/` (ignored by git,
rebuildable); the Markdown and both index files are committed and reviewable.

## Tools: CLI and MCP

The same implementation has two doors: the CLI for people and CI, and a local MCP server for the
model. `AGENTS.md` tells the agents when to use which.

| Level | For | Registered in | Covener |
|---|---|---|---|
| CLI | people, CI | installed | `covener init`, `status`, `knowledge build`, `knowledge ask`, `serve` |
| Instructions | the model, at session start | `AGENTS.md`, `agents/*.md` | when to use each tool or command |
| MCP tools | the model, any time | `.mcp.json`, `.cursor/mcp.json`, written by `init` | `status`, `search_knowledge`, `list_knowledge_sources` |
| Chat commands | you, as shortcuts | `.claude/commands`, `.cursor/commands` | roadmap |

```bash
pip install "covener[mcp]"     # included in covener[oracle]
covener init                   # registers the server; re-run after installing the extra
```

Claude Code reads `.mcp.json` (project scope, committed) and asks you to accept the server once.
Cursor reads `.cursor/mcp.json`; enable it under Settings, MCP. Codex, Windsurf and others: point
their MCP config at `covener serve` (stdio). The server exposes nothing that changes the repository.

## The agents

Five roles with explicit boundaries, one Markdown file each in `agents/`, in the front matter
format Claude Code and Cursor read natively. `init` links `.claude/agents` and `.cursor/agents` to
that folder, so there is exactly one copy of each agent and editing it is editing the file.

| Role | Owns | Never |
|---|---|---|
| product | vision, impact analysis, specs, bug intake, evidence in `references:` | code, approving its own specs |
| planner | tasks, sprint scope, briefs, feedback requests, closing and archiving | code, writing `## Feedback`, marking `done` without approval |
| engineer | implementation, fixes (regression test first), tasks, infrastructure | editing specs, expanding scope |
| qa | tests from acceptance criteria, acceptance verification, regressions | changing application code |
| reviewer | architecture, security, quality, compliance against citations; also on pull requests | editing anything |

The prompts follow current Anthropic and OpenAI guidance for frontier coding models: clear objective,
just-in-time reads, explicit outputs, explicit human gates, no permission-seeking for work already
requested. The model is a property of the agent (`model: claude-sonnet-5` or `inherit`); defaults are
a fast model for QA, a balanced one for the engineer, a strong one for the rest.

**Extending the team.** Roles are the contract; agents are files. Rename or disable a role in
`.covener/config.yaml`; add an agent by adding a file (a `frontend-engineer.md` next to
`engineer.md` is visible to every tool through the links). For stack-specific know-how, prefer
skills over more roles: Claude Code and Cursor load a skill only when the task needs it, so one
engineer with `frontend`, `backend` and `infra` skills stays cheaper and more consistent than three
engineers with three prompts. Keep `agents/` for boundaries and `skills/` for expertise.

```yaml
# .covener/config.yaml
agents:
  reviewer: security-reviewer   # agents/security-reviewer.md
  qa: off
tools: [claude, cursor]
```

## Install

```bash
pip install covener            # or: uv tool install covener / pipx install covener
covener init                   # --tools claude,cursor  --dry-run  --install-agents
covener status                 # --json  --verbose  --strict
covener knowledge build        # --no-graph  --dry-run        (covener[knowledge] or [oracle])
covener knowledge ask "..."    # --json
covener serve                  # MCP over stdio               (covener[mcp])
```

Python 3.10+. One runtime dependency (PyYAML). No network. `-C <dir>` works on every command.

**Existing files are safe.** An existing `AGENTS.md` keeps its content and gets the Covener block
between `<!-- covener:start -->` and `<!-- covener:end -->`; an existing `CLAUDE.md` gets an
`@AGENTS.md` import; existing `.claude/agents/` or `.cursor/agents/` directories keep their files
and get per-agent links; a legacy `.cursorrules` is reported.

**Windows.** Links become directory junctions when symlinks are not permitted. Clone with
`git config core.symlinks true`, or run `covener init` after cloning to repair the links.

**CI.**

```yaml
- run: pip install covener && covener status --strict
```

## How it compares

| | Covener | spec-kit | OpenSpec | Kiro | BMAD |
|---|---|---|---|---|---|
| Unit of work | sprint (named) | numbered feature + branch | change (named) + branch | spec + worktree | story |
| Human approval | file rule, CI-checkable | review step | review step | review step | review step |
| Team collisions | none by design | numbering collides | none by design | git | manual |
| Living specs | yes | no | yes | no | no |
| Bugs and tasks | own files, same flow | feature | change | spec | story |
| Domain knowledge | citation graph + evidence, MCP | constitution file | none | steering files | none |
| Roles | 5, extensible | 1 | 1 | 1 | 12+ |
| Files per feature | 2 | 8+ | 4 | 3 | many |
| Commands to learn | 2 (+1 knowledge, +1 serve) | 5+ | 4+ | IDE | many |

## What Covener does not do

No project-management UI. No orchestration engine. No MCP requirement. No autonomous deployment.
No user stories, requirement layers or profiles. Updating the package never touches your files. The
repository works without the package installed.

## FAQ

**Do I need MCP, hooks or a server?** No. The repository provides the context. `covener serve` is
optional and runs locally over stdio, for IDEs that prefer tools to shell commands.

**Can I use my own agents or skills?** Yes. Drop a file in `agents/`; it is visible to every tool
through the links. Rename or disable roles in `.covener/config.yaml`. Put stack-specific expertise
in skills rather than in more roles.

**What if I uninstall the package?** Everything keeps working. The method is in the files;
`covener status` is only a checker.

**Does it work with Codex, Copilot or Windsurf?** They read `AGENTS.md`, so the instructions and
the layout work. Agent files are linked for Claude Code and Cursor today; other adapters are a few
lines each.

**Why not just a good CLAUDE.md?** A CLAUDE.md tells an agent how to behave. It does not keep
decisions between sessions, does not separate what must be true from what happened, cannot stop an
agent from calling something done, and cannot cite a regulation with a page number. Covener adds
exactly those four things.

## Roadmap

- Codex and Windsurf link adapters; `skills/` linked like `agents/`.
- `/covener` chat commands for approving and requesting changes from the conversation.
- A reviewer GitHub Action that posts the `## Review` entry on pull requests.
- Knowledge Oracle: DOCX and HTML sources, more citation jurisdictions, compliance reports per spec.

## Contributing

Issues and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
pip install -e ".[dev]" && pytest && ruff check . && mypy
```

Standards used: [AGENTS.md](https://agents.md/), Claude Code
[subagents](https://code.claude.com/docs/en/sub-agents) and
[CLAUDE.md imports](https://code.claude.com/docs/en/memory), Cursor
[subagents](https://cursor.com/docs/agent/subagents) and [rules](https://cursor.com/docs/context/rules);
conventions from [OpenSpec](https://openspec.dev/docs/team-workflow),
[spec-kit](https://github.com/github/spec-kit) and [Kiro](https://kiro.dev/docs/specs/);
[LightRAG](https://github.com/HKUDS/LightRAG) and [Voyage AI](https://docs.voyageai.com/) for the Oracle.

## License

MIT. Built by [@ajmorenodelarosa](https://github.com/ajmorenodelarosa).
