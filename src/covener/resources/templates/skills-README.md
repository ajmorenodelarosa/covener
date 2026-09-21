# Skills

Skills are how this project teaches its agents *its* conventions. Each skill is a folder with a
`SKILL.md` in the [Agent Skills](https://agentskills.io) open standard, so the same file works in
Claude Code, Cursor, Codex and other tools. `covener init` links this folder to
`.claude/skills`, `.cursor/skills` and `.agents/skills`, so there is one copy.

```
skills/<name>/SKILL.md        required: front matter `name` (matching the folder) and `description`
skills/<name>/reference/…     optional: longer material the agent reads only when needed
skills/<name>/scripts/…       optional: scripts the agent runs instead of writing code
```

Rules that make a skill actually fire:

- The `description` is a routing rule, in the third person: what it does **and** when to use it.
  "This project's frontend conventions ... Use when creating or changing anything a user sees" beats
  "helps with frontend".
- One job per skill. Split rather than cover two workflows in one file.
- Keep `SKILL.md` short (a hundred lines is plenty) and move detail into `reference/`.
- Write your practice, not best practice. Generic advice is what the model already does.
- Update a skill when a review finds the same problem twice; that is the point of having one.

`frontend` and `backend` ship as templates: fill them in, delete what does not apply, and add the
skills your stack needs (`api-design`, `data-migrations`, `mobile`).
