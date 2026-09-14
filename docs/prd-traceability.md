# PRD traceability

Where each section of the product requirement document (`docs/prd.pdf`) lives in Covener, including the
simplifications the product owner asked for after the PRD (five roles, work log per specification and sprint,
approval at the end of the sprint, links instead of copies, one sprint one owner, derived backlog).

| PRD section | Covener |
|---|---|
| 1 Product vision | `specs/vision.md`; README |
| 2 Core development model | vision -> spec -> backlog -> sprint -> work -> review -> feedback -> done; no mandatory intermediate layers (`tasks/` is an optional item kind, not a decomposition of specs) |
| 3 Repository as source of truth | `init.py`; fixed structure: `specs/`, `sprints/`, `agents/`, `.covener/` |
| 4 Specifications | `specs/TEMPLATE.md`; living documents (`done -> draft` on change); `agents/product.md` |
| 5 Product-to-spec cascade | `agents/product.md` impact report before any edit |
| 6 Backlog | derived by `covener status`: open bugs then approved specs not in an open sprint (`epic`, `priority`); `agents/planner.md` |
| 7 Sprint model | `sprints/<name>/sprint.md` (owner, specs, bugs) + one work log per item under `specs/` and `bugs/`; `sprints/archive/` |
| 8 Agent team | `roles.py`: product, planner, engineer, qa, reviewer; `agents:` mapping in config |
| 9 Agent definitions | Markdown + YAML front matter read natively by Claude Code and Cursor |
| 10 Responsibilities | one file per agent under `agents/` |
| 11 Human-in-the-loop | `states.py`; `validate.py`: `spec.done-without-approval`, `sprint.closed-without-approval` |
| 12 Human feedback loop | `## Feedback` entries in the work log; `repo.parse_work` |
| 13 Agent reviews | `agents/reviewer.md` and `agents/qa.md` log `## Review` / `## QA` before feedback is requested |
| 14 CI/CD governance | `covener status --strict`; reviewer usable on pull requests; `.github/workflows/ci.yml` |
| 15 AGENTS.md | `resources/framework/instructions.md` (small block) |
| 16 Existing AGENTS.md | `init.integrate_agents_md` (marked block, informs); `adapters/claude.py` (`@AGENTS.md`) |
| 17 Claude, Cursor compatibility | `adapters/`: links to `agents/`; conventions verified 2026-09-12 |
| 18 Configuration | `config.py`: `agents` and `tools` only |
| 19 CLI | `cli.py`: `init` and `status` |
| 20 No update command | none; `init` only adds what is missing |
| 21 Installation model | `pyproject.toml`; repository works without the package |
| 22 No mandatory MCP | nothing requires MCP; the optional Knowledge Oracle ships one local stdio server |
| 23 Design principles | `specs/vision.md` |
| 24 Developer experience | README, section Five minutes |
| 25 Initial scope | this package, version 0.1.0 |

Added after the PRD on the product owner's request: `bugs/` as a first-class item kind with its own lifecycle (`open -> done`), hotfix as a one-bug sprint, trivial fixes outside the framework.

Added after the PRD on the product owner's request: Project Knowledge (`knowledge/`, deterministic index and citation graph) and the Knowledge Oracle (graph backend replaceable, LightRAG first, one MCP tool `search_knowledge` returning answer + relations + evidence), kept outside the core as an optional extra.

Also added: `tasks/` for work that leaves no requirement behind (same cycle as bugs), living specs, and `## Checklist` as the work log's step list.
