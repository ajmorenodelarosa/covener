# Changelog

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
