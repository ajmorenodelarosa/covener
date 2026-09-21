---
name: backend
description: This project's backend conventions for module layout, API contracts, data access and migrations, transactions, validation, errors, authorisation, logging and tests. Use when creating or changing server-side code, endpoints, jobs, database schemas or integrations.
---

# Backend conventions

<!-- TODO: replace every line below with how this project actually works. An empty template is
worse than no skill: agents will follow generic habits instead of yours. Keep this file under
100 lines and move long material into reference files next to it. -->

## Stack
Language, framework, database, queue and runtime, with the versions that matter.

## Where code goes
The layers this project uses (for example handler, service, repository), what may import what, and
one real path for each.

## API contracts
Style (REST, GraphQL, RPC), where the schema lives, how versions and breaking changes are handled,
and the shape of a successful and a failed response.

## Data and migrations
The ORM or query layer, how migrations are written and run, the rule about backfills, and what must
never happen in a migration.

## Transactions and consistency
Where a transaction starts and ends, what must be atomic, how retries and idempotency work.

## Validation and errors
Where input is validated, the error type hierarchy, which errors are returned to the client and
which are only logged.

## Authorisation
Where the check happens, how the current actor is obtained, and the rule for data scoped to a
tenant, an account or a role.

## Observability
What is logged, at which level, what must never appear in a log (personal data, secrets, tokens),
and the metrics or traces a new endpoint must emit.

## Tests
What is unit-tested, what needs the database, what is an integration test, and the command that
runs each set.

## Done checklist
- [ ] Input validated and authorisation checked at the documented layer
- [ ] Errors mapped to the documented response shape
- [ ] Migration reversible, or its irreversibility stated in the change's design
- [ ] No personal data or secrets in logs
- [ ] Tests added for the acceptance criteria this change covers
