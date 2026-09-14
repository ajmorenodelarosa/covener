# Changelog

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
