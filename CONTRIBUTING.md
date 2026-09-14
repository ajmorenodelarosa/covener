# Contributing to Covener

Thanks for your interest. Covener is deliberately small; the best contributions keep it that way.

## Ground rules

- One spec per feature, one work log per spec per sprint, five agents, two commands. A change that
  adds an option, a file agents must read, or a command needs a strong reason.
- Follow what the ecosystem already settled (AGENTS.md, Claude Code and Cursor subagent format,
  OpenSpec's team model) instead of inventing a convention.
- Human approval stays a checkable rule in a file.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check . && mypy
```

Tests live in `tests/` and are kept minimal: one behaviour, one test. Please add one for any bug you fix.

## Pull requests

- Describe the behaviour, not the diff.
- Update `README.md` if the user-visible behaviour changes.
- Keep `CHANGELOG.md` current.
