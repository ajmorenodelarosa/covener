---
name: architecture
description: This project's architecture. The shape of the system, its boundaries, the patterns it uses and the decisions every change must respect. Use before designing a change, when reviewing a design, and when a decision taken in a change must outlive it.
---

# Architecture

<!-- TODO: replace every line below with how this system is actually built. A change's design.md
describes that change; this file describes what every change must respect. Keep it under 100 lines
and move diagrams and long material into reference files next to it. -->

## Shape
The parts of the system (services, apps, packages), what each one owns, and how they talk: calls,
events, a shared database, files.

## Boundaries
What may depend on what, what must never call what, and where a request may cross a boundary. One
real example of each.

## Patterns
The ones this project uses and where (event sourcing in accounts, an outbox for events, a cache in
front of the catalogue), and the ones it deliberately avoids.

## Data ownership
Which part owns which data, who may write it, and how the others read it.

## Cross-cutting
Authentication, authorisation, tenancy, configuration, feature flags, observability: where each is
handled, so no change reinvents it.

## Decisions
Decisions that constrain future changes, newest last, one line each with the date and the change
that took it. The engineer adds the line in the same change, before it goes to review.
- 2026-09-20 (account-closure) Retained KYC records live in a restricted store that only compliance reads.

## Design checklist
- [ ] The design names the parts it touches and crosses no boundary listed above
- [ ] New data has an owner
- [ ] A decision that outlives the change is added under Decisions
