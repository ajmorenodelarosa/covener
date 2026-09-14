<div align="center">

# Covener

**Your AI coding agents, working as a team. You approve.**

Spec-driven development for Claude Code, Cursor and any tool that reads `AGENTS.md`.<br>
One file per spec, bug or task. Five agents. Human approval that CI can verify.<br>
Optional Knowledge Oracle: your regulations and contracts as a knowledge graph your agents can cite.

[![CI](https://github.com/ajmorenodelarosa/covener/actions/workflows/ci.yml/badge.svg)](https://github.com/ajmorenodelarosa/covener/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/covener.svg)](https://pypi.org/project/covener/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/covener/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

```bash
pip install covener && covener init
```

</div>

---

## The problem

AI coding agents are fast and forgetful. Every session starts from zero, decisions evaporate with
the chat, and nothing stops an agent from declaring a feature "done". The frameworks that try to
fix this either bury you in generated markdown or bring twelve agents and a process to learn.

Covener takes the opposite bet: **the repository is the source of truth, the conversation is the
interface, and a human decision is a line in a file that a script can check.**

## Sixty seconds

```bash
cd my-project
covener init          # links the agents into Claude Code and Cursor, never overwrites your files
```

Open your IDE and say what you want:

> I want customers to connect their Stripe account and receive payments.

| Step | Who | What happens |
|---|---|---|
| 1 | **product** | Reads the vision and existing specs, reports what is affected, drafts `specs/stripe-connect.md`. You set `status: approved`. |
| 2 | **planner** | Opens `sprints/payments-onboarding/` with the spec (open bugs first) and a checklist. |
| 3 | **engineer**, **qa**, **reviewer** | Implement, test, review. Every step is logged next to the checklist. |
| 4 | **planner** | Sets the sprint to `review` and asks for your feedback. |
| 5 | **you** | Write `Approved: No` with what to change, or `Approved: Yes`. |
| 6 | **planner** | Reworks until you approve, marks the spec `done`, archives the sprint. |

```bash
covener status        # backlog, sprints, what is inconsistent, what is next
```

## What you get

- **A team, not a chatbot.** Five roles with clear boundaries: product, planner, engineer, qa,
  reviewer. Each is one Markdown file you own and can edit, rename, disable or extend.
- **Three questions, three folders.** `specs/` is what the product is, `bugs/` is where it deviates,
  `tasks/` is work that changes neither (migrations, refactors, upgrades). None of them grows:
  everything that happened lives in the sprint, next to the checklist.
- **Approval you can enforce.** A spec cannot be `done` and a sprint cannot be `closed` without
  your `Approved: Yes` in the work log. `covener status --strict` fails CI otherwise.
- **Memory without a database.** Summaries, decisions, reviews and your feedback are plain
  Markdown in the repository. A new session picks up where the last one stopped.
- **Team-safe by construction.** No backlog file to fight over, sprints named by what they deliver
  instead of numbers that collide, one sprint per owner, one branch per sprint. Git does the rest.
- **Tool agnostic.** Agents use the format Claude Code and Cursor read natively; `.claude/agents`
  and `.cursor/agents` are links to `agents/`. Instructions live in the cross-tool `AGENTS.md`.
- **Nothing to learn.** Two commands for the method, one for knowledge, one to serve them to the
  IDE. No orchestration engine, no slash-command vocabulary, no profiles, no MCP requirement. The
  repository works even if you uninstall the package.
- **Governance-ready.** Drop your regulations, contracts and procedures in `knowledge/`; agents answer
  with evidence, cite page by page, and the reviewer checks compliance against what was cited.

## Layout

```
specs/vision.md                     product intent
specs/<id>.md                       what the product is: one living file per spec (draft -> approved -> done)
bugs/<id>.md                        what is wrong: one file per bug (open -> done)
tasks/<id>.md                       work that changes neither: migrations, refactors, upgrades (open -> done)
sprints/<name>/sprint.md            owner, status, specs, bugs and tasks in scope (active -> review -> closed)
sprints/<name>/<kind>s/<id>.md      an item's work log: checklist, summary, decisions, QA, review, feedback
sprints/archive/YYYY-MM-DD-<name>/  closed sprints
knowledge/                          optional: your domain documents (PDF, Markdown, text) and their index
agents/<name>.md                    one file per agent; .claude/agents and .cursor/agents link here
AGENTS.md                           a small block every coding agent reads (CLAUDE.md imports it)
.covener/config.yaml                role -> agent mapping and tools; nothing else
```

Domain folders are fine: `specs/payments/stripe-connect.md` has the id `payments/stripe-connect`.
There is no backlog file. The backlog is every open bug, approved spec and open task that is not in
an open sprint: bugs first, then everything by two optional fields, `priority` and `epic`.

Which folder? If in a year someone must read it to know what the product is, it is a spec. If it
describes something that is wrong today, it is a bug. If they only need to know it was done, it is a
task. Specs are living documents: to extend, change or remove a requirement you edit the spec, it
goes back to `draft`, you approve it again, and a sprint carries the change. Its history is the
sprints that touched it.

## The work log

`sprints/<name>/specs/<id>.md` (or `bugs/<id>.md`) is a chronological log. Agents add entries; you add one.

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

The last entry is the state: awaiting feedback, changes requested or approved. `covener status`
derives everything from this file. Nothing is stored twice.

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
    - spec stripe-connect: awaiting feedback, tasks 5/6
    - bug expired-tokens: approved, tasks 2/2

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

Errors are the rules that protect your authority: a spec, bug or task `done` without your
`Approved: Yes`; a sprint `closed` with unapproved work; an item in two open sprints; a draft spec,
a done item or an unknown id in an open sprint; an open sprint in the archive; invalid statuses or
unparsable files; a missing vision; a configured agent without a definition. Closed sprints are
history: only the approval rule applies to them, so a spec that later changes never breaks CI.
A second open sprint for the same owner is a warning, not an error: that is what a hotfix looks like.

## Bugs, tasks and hotfixes

A **bug** is a deviation from the product. A **fix** is the change that corrects it. A **hotfix**
is a fix that cannot wait. A **task** is work that leaves no requirement behind. Covener keeps the
words apart and the flow the same.

| Size | What happens |
|---|---|
| Trivial (one place, no design decision) | Say "fix this". The engineer fixes it with a test and tells you. No file, no sprint. |
| Worth tracking | Say "this is the problem". Product registers `bugs/<id>.md` (symptom, how to reproduce, cause if known, expected behaviour). It is `open` from the start: a bug is reported, not approved. It waits at the top of the backlog for the next sprint; an active sprint's scope does not change. |
| Hotfix | Same as above, but the planner opens a one-bug sprint right now (`sprints/hotfix-<slug>/`) and the cycle runs in an hour: regression test, fix, QA, review, your `Approved: Yes`, archive. |

| Technical work | Say "migrate to Postgres". The planner registers `tasks/<id>.md` (goal, why, scope, done-when, risk and rollback), `open` from the start. It takes its place in the backlog by priority and runs the same cycle; QA verifies the done-when and that no spec regressed. If the work leaves a durable requirement ("data lives in Postgres"), it is a spec instead. |

Specs stay what the product is. Bugs and tasks never touch them; if a bug reveals the spec was
wrong, or a task changes what the product promises, that is a separate change to the spec.

## Project Knowledge and the Knowledge Oracle

Regulated products live or die by documents nobody reads twice: laws, decrees, contracts,
procedures, internal standards. Covener makes them a first-class input with **traceable evidence**,
so an agent never writes "the regulation says" from memory.

```bash
pip install "covener[oracle]"        # or "covener[knowledge]" for the no-model layer only
mkdir knowledge && cp ~/regulations/*.pdf knowledge/
covener knowledge build              # run again whenever documents change; only changes are processed
```

Two layers, both optional, both outside the core:

| Layer | What it does | Needs |
|---|---|---|
| **Deterministic** | Converts every source to Markdown with `## Page N` headings next to it, writes `knowledge/INDEX.md`, and builds `knowledge/CITATIONS.md`: the graph of explicit cross-references between documents ("conforme al artículo 12 de la Ley 1437 de 2011"), resolved to documents in the corpus. No model, no network, nothing can be hallucinated. | `pypdf` |
| **Oracle** | A knowledge graph of entities and relationships plus vector retrieval, built with a frontier model and stored as local files (LightRAG: NetworkX graph, nano-vectordb, no server). One MCP tool, `search_knowledge`, returns **answer + relations + evidence** with `knowledge/<file>.md#page-N` references. Without evidence it says so instead of guessing. | `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY` |

```bash
covener knowledge ask "¿Cuándo opera el silencio administrativo positivo?"
```

```
El silencio administrativo positivo opera cuando la administración no responde en tres meses [ley-1437.md#page-1].

Evidence
  - knowledge/ley-1437.md#page-1: Artículo 12. El silencio administrativo positivo opera cuando ...
Relations
  - ley-1437 -> decreto-1082 (citation)
  - decreto-1082 -> ley-1437 (citation)
```

**How the team uses it.** Product asks the Oracle before drafting a governed spec and cites the
evidence in the spec's `references:` field. Engineer reads the cited pages before implementing.
Reviewer opens every citation, checks the implementation against the wording, and asks the Oracle
whether an uncited document contradicts the spec: a contradiction is a `fail`. `covener status`
warns when a reference points to a file that does not exist.

```yaml
# specs/silencio-administrativo.md
references: [knowledge/ley-1437.md#page-1, knowledge/decreto-1082.md#page-1]
```

**The `covener` MCP server.** The same capabilities the CLI gives people are given to the model as
tools, through one local server over stdio: `status`, `search_knowledge` and
`list_knowledge_sources`. Nothing that changes the repository on the model's behalf.

```bash
pip install "covener[mcp]"     # included in covener[oracle]
covener init                   # registers the server; re-run after installing the extra
```

- Claude Code reads `.mcp.json` (project scope, committed): open Claude Code in the repository,
  accept the project server when asked, and the tools appear. By hand:
  `claude mcp add --transport stdio covener --scope project -- covener serve`.
- Cursor reads `.cursor/mcp.json` (same server without `type`); enable it under Settings, MCP.
- Codex, Windsurf and others: point their MCP config at `covener serve` (stdio).
- Keys go in the environment of the IDE (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`), never in the
  repository. Without them `search_knowledge` still answers from the deterministic layer, marked
  `backend: grep`.

Where each thing lives, so nothing is registered twice:

| Level | For | How it is registered | Covener |
|---|---|---|---|
| CLI | people and CI | installed | `covener init`, `status`, `knowledge build`, `serve` |
| Instructions | the model, at session start | `AGENTS.md`, `agents/*.md` | when to use each tool or command |
| MCP tools | the model, any time | `.mcp.json`, `.cursor/mcp.json` (written by `init`) | `status`, `search_knowledge`, `list_knowledge_sources` |
| Chat commands | you, as shortcuts | `.claude/commands`, `.cursor/commands` | roadmap |

**Multilingual by design.** The Oracle uses `claude-sonnet-5` for extraction and answers and
`voyage-4-large` for retrieval, both multilingual; it answers in the language of the question.
The citation patterns cover Spanish-language public law (leyes, decretos, resoluciones, sentencias,
Constitución), Spain (Real Decreto, Ley N/AAAA) and EU regulations; unknown forms stay as text and
are never invented. Override models with `COVENER_LLM_MODEL` and `COVENER_EMBED_MODEL`
(`voyage-law-2` is tuned for legal text). The graph lives in `.covener/knowledge/` (ignored by git,
rebuildable); the Markdown and both index files are committed and reviewable.

**Cost and honesty.** Indexing with LightRAG costs cents to a few dollars per hundred documents,
not the thousands Microsoft GraphRAG needs. Quality of the semantic graph depends on the model;
the citation graph and the page-anchored evidence do not. The Oracle is for domain knowledge; it
does not replace your IDE's code index.

## Working in a team

Covener follows the team model OpenSpec proved at scale: **one sprint, one owner, one branch, one
pull request.** Git isolates parallel work; Covener makes the rules checkable.

- **Name sprints by what they deliver**, `payments-onboarding`, or by whatever convention your team
  likes. Never by number: sequential numbers collide the moment two people branch.
- **The owner is a field** in `sprint.md`. One open sprint per owner is the norm (a hotfix is the
  exception and shows as a warning); a spec or bug is in at most one open sprint, which is an error.
  `covener status` flags both after a merge.
- **Specs are one file each**, so two people rarely touch the same one. Approval is in the file.
- **The backlog is derived**, never written. Reprioritising is a one-line change in one spec.
- **History is the archive** of closed sprints plus `status: done` in the spec. Archive after the
  pull request merges. Everything is committed; nothing is personal or ignored.

## The team

| Agent | Responsibility | Model |
|---|---|---|
| product | vision changes, impact analysis, specifications, bug intake | strong |
| planner | sprint lead: registers tasks, picks from the backlog, briefs the team, asks for your feedback, closes | strong |
| engineer | implementation, fixes (regression test first), tasks, infrastructure, trivial fixes | balanced |
| qa | tests from acceptance criteria, acceptance verification | fast |
| reviewer | independent architecture, security and quality review, also on pull requests | strong |

Each agent is one Markdown file with YAML front matter, the format Claude Code and Cursor read
natively. The model is a property of the agent: a provider-level id both tools accept, or
`inherit`. Today: fast `claude-haiku-4-5`, balanced `claude-sonnet-5`, strong `claude-fable-5-1`.
The prompts follow the current Anthropic and OpenAI guidance for frontier coding models: clear
objective, just-in-time reads, explicit outputs, explicit human gates, no permission-seeking for
work already requested.

```yaml
# .covener/config.yaml
agents:
  reviewer: security-reviewer   # agents/security-reviewer.md
  qa: off
tools: [claude, cursor]
```

## How it compares

| | Covener | spec-kit | OpenSpec | Kiro | BMAD |
|---|---|---|---|---|---|
| Unit of work | sprint (named) | numbered feature + branch | change (named) + branch | spec + worktree | story |
| Human approval | file rule, CI-checkable | review step | review step | review step | review step |
| Team collisions | none by design | numbering collides | none by design | git | manual |
| Roles | 5 | 1 | 1 | 1 | 12+ |
| Commands to learn | 2 | 5+ | 4+ | IDE | many |
| Files per feature | 2 | 8+ | 4 | 3 | many |
| Living specs | yes | no | yes | no | no |
| Bugs and tasks | own files, same flow | feature | change | spec | story |
| Domain knowledge | graph + evidence, MCP | constitution file | none | steering files | none |

Covener keeps what these tools agree on, one spec per feature, checklists, work separate from
specs, archive by date, an `AGENTS.md` block, and removes what they are criticised for: the pile of
markdown to review, ceremony that ignores problem size, and orchestration that reproduces the
chaos of the team it models.

## Install

```bash
pip install covener            # or: uv tool install covener / pipx install covener
covener init                   # --tools claude,cursor  --dry-run  --install-agents
covener status                 # --json  --verbose  --strict
covener knowledge build        # --no-graph  --dry-run        (pip install "covener[knowledge]" or "[oracle]")
covener knowledge ask "..."    # --json
covener serve                  # MCP over stdio               (pip install "covener[mcp]")
```

Python 3.10+. One runtime dependency (PyYAML). No network. `-C <dir>` works on both commands.

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

## FAQ

**Do I need MCP, hooks or a server?** No. The repository provides the context. The optional
`covener serve` exposes `status` and the Knowledge Oracle as tools, locally over stdio, for IDEs
that prefer tools to shell commands.

**Can I use my own agents?** Yes. Drop a file in `agents/`; it is visible to every tool through
the links. Rename or disable roles in `.covener/config.yaml`.

**What if I uninstall the package?** Everything keeps working. The methodology is in the files;
`covener status` is only a checker.

**Does it work with Codex, Copilot or Windsurf?** They read `AGENTS.md`, so the instructions and
the layout work. Agent files are linked for Claude Code and Cursor today; other adapters are a few
lines each.

**Why not just a good CLAUDE.md?** A CLAUDE.md tells an agent how to behave. It does not keep
decisions between sessions, does not separate what must be true from what happened, and cannot
stop an agent from calling something done. Covener adds exactly those three things.

## Roadmap

- Codex and Windsurf link adapters.
- `/covener` slash commands for approving and requesting changes from the chat.
- A reviewer GitHub Action that posts the `## Review` entry on pull requests.
- Knowledge Oracle: DOCX and HTML sources, a second graph backend, compliance reports per spec.

## Contributing

Issues and pull requests are welcome. Run the checks before opening one:

```bash
pip install -e ".[dev]" && pytest && ruff check . && mypy
```

Standards used: [AGENTS.md](https://agents.md/), Claude Code
[subagents](https://code.claude.com/docs/en/sub-agents) and
[CLAUDE.md imports](https://code.claude.com/docs/en/memory), Cursor
[subagents](https://cursor.com/docs/agent/subagents) and [rules](https://cursor.com/docs/context/rules);
conventions from [OpenSpec](https://openspec.dev/docs/team-workflow),
[spec-kit](https://github.com/github/spec-kit) and [Kiro](https://kiro.dev/docs/specs/).

## License

MIT. Built by [@ajmorenodelarosa](https://github.com/ajmorenodelarosa).
