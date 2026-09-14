---
owner: <your name or handle>
status: active
goal: <one sentence>
specs: [<spec-id>]
bugs: [<bug-id>]
tasks: [<task-id>]
opened: <YYYY-MM-DD>
closed:
---

Only the scope lives here. Every item in `specs:`, `bugs:` and `tasks:` gets a work log next to this
file: `specs/<id>.md`, `bugs/<id>.md`, `tasks/<id>.md` (a nested id like `payments/stripe` becomes
`payments/stripe.md`). `active` while agents work, `review` while the human evaluates, `closed` when
everything here is approved; a closed sprint moves to `sprints/archive/<YYYY-MM-DD>-<name>/`.
Name the sprint by what it delivers (`payments-onboarding`, `hotfix-stripe-tokens`), not by number.
One sprint, one owner, one branch.
