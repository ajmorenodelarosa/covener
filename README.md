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
- **Built for teams.** Each developer runs their own sprint with their own agents, in parallel,
  on their own branch; the layout is designed so they never collide. A lead reviews the sprint from
  its work logs and the reviewer agent's findings, and reads code where those point.
- **Approval is a rule in a file.** An item is `done` only when a human wrote `Approved: Yes` in its
  work log. `covener status --strict` fails CI when that rule, or any consistency rule, is broken.
- **Knowledge is evidence.** Regulations, contracts and procedures in `knowledge/` become a
  page-anchored corpus with a citation graph and an optional semantic graph; agents cite
  `file#page-N`, reviewers verify, and `status` flags dangling references.
- **The core runs no server and calls no model.** Once initialised, the repository works without
  the package. Two commands for the method; the knowledge layer and the MCP server are optional extras.

## Why Covener

Spec-driven development tools stop at the spec. spec-kit generates a pile of Markdown per feature
and numbers features so that two developers branching on the same day collide. Kiro writes
requirements, design and tasks, then treats them as launch documents that drift as soon as code
changes. BMAD answers the problem with a dozen personas and the process overhead that comes with
them. OpenSpec tracks changes well, but a spec is still just text an agent can declare done. None of
them keeps the decisions made while building, none makes human approval something a machine can
verify, and none can tell you which article of which regulation a requirement comes from.

Covener does all three. **Every decision, review and human comment is written next to the item it
belongs to**, so a new session starts from the record instead of from zero. **An item is done only
when a person wrote `Approved: Yes`**, and `covener status --strict` fails CI otherwise, which makes
the approval something an auditor can rely on rather than a line in a prompt. **Requirements that
come from regulations cite their evidence page by page**, backed by a citation graph built without a
model, so nothing about a law can be hallucinated.

And it is built for teams. When several developers drive agents, the volume of generated code
outgrows line-by-line review, and what actually happens is skimming. Covener gives the reviewer a
map instead: a work log per item that says what was built, what was decided, which test proves
which criterion, and what the independent reviewer flagged, with file and line, next to the
requirement it serves. The human reads the code where the map points. All of it with two files per
item, five roles with hard boundaries, and a layout you can explain in a minute.

## How it works

```bash
cd my-project
covener init          # links the agents into Claude Code and Cursor; never overwrites your files
```

Then talk to the team in your IDE. Take a bank:

> Customers must be able to close their account and have their personal data erased.

A naive agent deletes the customer. That breaks the law: GDPR grants the right to erasure, but EU
anti-money-laundering rules require the bank to keep identity and transaction records for five years
after the relationship ends, and GDPR itself exempts data kept to meet a legal obligation. This is
the kind of requirement Covener is built for.

| Step | Role | What happens in the repository |
|---|---|---|
| 1 | product | Asks the Knowledge Oracle, finds both obligations and the exemption, and drafts `specs/account-closure.md`: erase marketing, profiling and app data at once; keep KYC and transaction records for five years with restricted access, then erase them. Every criterion cites its article in `references:`. You set `status: approved`. |
| 2 | planner | Opens `sprints/account-closure/` with the spec (open bugs first) and writes the checklist in the work log. |
| 3 | engineer, qa, reviewer | Implement, test each criterion, and review architecture, security and compliance: the reviewer opens every cited page and checks the code against its wording. |
| 4 | planner | Sets the sprint to `review` and tells you what to evaluate. |
| 5 | you | `Approved: No` with what to change, or `Approved: Yes`. |
| 6 | planner | Reworks until you approve, marks the spec `done`, archives the sprint. Six months later an auditor asks why a closed customer's passport scan still exists: the spec, the citations, the review and your approval are all in the repository. |

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

Domain folders are fine: `specs/privacy/account-closure.md` has the id `privacy/account-closure`.

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
# account-closure

## Checklist
- [x] closure request endpoint with strong customer authentication
- [x] immediate erasure of marketing, profiling and app data
- [x] KYC and transaction records moved to restricted retention with a five-year expiry
- [x] scheduled erasure job at retention expiry
- [x] erasure notice to processors (GDPR Art. 19)
- [ ] customer-facing explanation of what is retained and why

## Summary
Closure flow in accounts/closure.py; retention store in compliance/retention.py; nightly expiry job.
14 tests in tests/test_closure.py, one per acceptance criterion.

## Decisions
- 2026-09-14 Retention clock starts at the closure date, not the last transaction (AMLD Art. 40(1)).
- 2026-09-14 Retained records are readable only by the compliance role; every read is audited.

## QA
Verdict: pass
- AC1 test_marketing_data_erased_immediately, AC2 test_kyc_retained_five_years,
  AC3 test_retained_records_erased_at_expiry, AC4 test_processors_notified.

## Review
Verdict: pass with notes
- high: compliance/retention.py:88 lets the support role read retained records; restrict to compliance.
- Compliance: criteria match knowledge/gdpr.md#page-43 and knowledge/amld.md#page-31.

## Feedback
Approved: No
Restrict retained records as the review says, and show customers what is kept and until when.

## Rework
Support role removed from retention access; retention summary added to the closure confirmation.

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
    - erasure-skips-backups (priority 1)
  [aml]
    - task kyc-archive-eu-region (priority 1)
  [privacy]
    - spec consent-management (priority 2)

Sprints
  account-closure (review, ana): approved 1/2
    - spec account-closure: awaiting feedback, checklist 5/6
    - bug consent-default-on: approved, checklist 2/2

Done
  - spec audit-trail (2026-09-01-audit-trail 2026-09-01)

Governance
  Pending human review: 1
  Pending spec approval: 1
  Errors: 0
  Warnings: 0

Next
  * Review and approve specs/transaction-monitoring.md (draft)
  * Give feedback on spec account-closure in sprints/account-closure/specs/account-closure.md
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

## Teams and review

Agents make code cheap and review expensive. Covener answers with two things: a layout where
developers work in parallel without stepping on each other, and a unit of review that is not the
diff.

**In parallel, without collisions.**

- One sprint, one owner, one branch, one pull request. Git isolates the work; Covener makes the
  rules checkable.
- Sprints are named by what they deliver (`account-closure`), never numbered, so two people
  branching on the same day cannot collide.
- The owner is a field in `sprint.md`. One open sprint per owner is the norm; an item is in at most
  one open sprint. `covener status` flags both after a merge.
- Specs, bugs and tasks are one file each and there is no backlog file, so there is no shared list
  to fight over.
- Closed sprints are archived by date. Everything is committed.

**Review the work, then the code.** Each item in a sprint has one work log. A reviewer reads, in
order: the checklist (what was done), the summary (where), the decisions (why), the QA entry (which
test proves which acceptance criterion) and the reviewer agent's findings ordered by severity with
file and line. Critical and high findings, security, money and data are where you open the code.
The rest you check against the record. Your verdict goes in the same file as `## Feedback`, and
git records who wrote it and when.

**What a lead sees.** `covener status` across the repository: every open sprint, its owner, each
item's state and checklist progress, what is waiting for a human, what is inconsistent. It is the
stand-up, generated from the files.

**What the rule can and cannot do.** Nothing physically stops an agent from typing
`Approved: Yes`. The agent prompts forbid it, `status` makes every approval a visible line that CI
checks, and git blame tells you who wrote it. That is more than a review step in a prompt, and less
than a signature; treat it accordingly.

**Your reviewer in CI.** The reviewer agent is a file in your repository, so the same agent that
reviews in the IDE can review a pull request headlessly and publish its findings as the starting
point for the human reviewer. An example with Claude Code; adapt it to your CI and tool:

```yaml
- run: pip install covener && covener status --strict
- run: npm install -g @anthropic-ai/claude-code
- env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    claude -p --agent reviewer --allowedTools "Read" "Bash(git diff *)" "Bash(git log *)" \
      "Review this pull request against the work logs of the sprint it closes. Report findings \
       by severity with file and line, and compliance against cited references." \
      >> "$GITHUB_STEP_SUMMARY"
```

## Bugs, tasks and hotfixes

A **bug** is a deviation from the product. A **fix** is the change that corrects it. A **hotfix** is
a fix that cannot wait. A **task** is work that leaves no requirement behind. The words stay apart;
the flow stays the same.

| Situation | Flow |
|---|---|
| Trivial fix (one place, no design decision) | "Fix this." The engineer fixes it with a test and tells you. No file, no sprint. |
| Bug worth tracking | "This is the problem." Product registers `bugs/<id>.md` (symptom, reproduction, cause if known, expected behaviour), `open` from the start: a bug is reported, not approved. It waits at the top of the backlog for the next sprint; an active sprint's scope does not change. |
| Hotfix | Same, but the planner opens a one-bug sprint now (`sprints/hotfix-<slug>/`) and the cycle runs in an hour: regression test, fix, QA, review, your `Approved: Yes`, archive. |
| Technical work | "Move the KYC archive to an EU region." The planner registers `tasks/<id>.md` (goal, why, scope, done-when, risk and rollback), `open` from the start. Same cycle; QA verifies the done-when and that no spec regressed. If the work leaves a durable requirement ("customer data never leaves the EU"), it is a spec instead. |

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
`knowledge/<file>.md#page-N` references. The evidence list is the part to trust: when retrieval
finds nothing, it is empty and the answer is instructed to say so.

```bash
covener knowledge ask "A customer closes their account and asks us to delete everything. What must we erase and what must we keep?"
```

```
Erase personal data without undue delay once it is no longer necessary [gdpr.md#page-43], except
data you must keep to comply with a legal obligation [gdpr.md#page-44]. Customer due diligence
documents and transaction records must be retained for five years after the end of the business
relationship [amld.md#page-31] and deleted afterwards [amld.md#page-31]. Recipients of the data
must be told about the erasure [gdpr.md#page-45].

Evidence
  - knowledge/gdpr.md#page-43: Article 17(1) ... the controller shall have the obligation to erase ...
  - knowledge/gdpr.md#page-44: Article 17(3)(b) ... for compliance with a legal obligation ...
  - knowledge/amld.md#page-31: Article 40 ... for a period of five years after the end of the business relationship ...
  - knowledge/gdpr.md#page-45: Article 19 ... communicate any rectification or erasure ...
Relations
  - data-retention-policy -> gdpr (citation)
  - data-retention-policy -> amld (citation)
  - personal data -> customer due diligence (graph)
```

**How the team uses it.** Product asks the Oracle before drafting a governed spec and cites the
evidence in `references:`. Engineer reads the cited pages before implementing. Reviewer opens every
citation, checks the implementation against the wording, and asks the Oracle whether an uncited
document contradicts the spec: a contradiction is a `fail`. `covener status` warns when a reference
points to a file that does not exist.

```yaml
# specs/account-closure.md
references: [knowledge/gdpr.md#page-43, knowledge/gdpr.md#page-44, knowledge/amld.md#page-31]
```

Models: `claude-sonnet-5` for extraction and answers, `voyage-4-large` for retrieval, both
multilingual; the Oracle answers in the language of the question. Override with `COVENER_LLM_MODEL`
and `COVENER_EMBED_MODEL` (`voyage-law-2` is tuned for legal text). Keys (`ANTHROPIC_API_KEY`,
`VOYAGE_API_KEY`) live in the environment, never in the repository. Indexing is incremental and
costs on the order of a few dollars per hundred documents, depending on model and document length.
The graph lives in `.covener/knowledge/` (ignored by git, rebuildable); the Markdown and both index
files are committed and reviewable.

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
engineers with three prompts. Keep `agents/` for boundaries and your tool's skills directory for
expertise.

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

- Codex and Windsurf link adapters, and skills linked like agents.
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
conventions from [OpenSpec](https://openspec.dev/docs/team-workflow),
[spec-kit](https://github.com/github/spec-kit) and [Kiro](https://kiro.dev/docs/specs/);
[LightRAG](https://github.com/HKUDS/LightRAG) and [Voyage AI](https://docs.voyageai.com/) for the Oracle.

## License

MIT. Built by [@ajmorenodelarosa](https://github.com/ajmorenodelarosa).
