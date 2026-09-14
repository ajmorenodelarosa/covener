# Changelog

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
- `covener status` (`--json`, `--verbose`, `--strict`): derived backlog by epic and priority, open
  sprints with work states and task progress, done list, consistency errors that protect human
  approval, and what to do next.
- Five-agent default team (product, planner, engineer, qa, reviewer), one Markdown file each.
- One file per spec, bug or task; living specs (editing a done spec reopens it); sprints with one work
  log per item (checklist, entries, human feedback); bugs first in the backlog, then priority; hotfix as
  a one-bug sprint; closed sprints archived by date.
