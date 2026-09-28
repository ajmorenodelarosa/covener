---
status: draft
---

# Design

<!-- How this change will be built, written by the engineer first and approved by the human
before the tasks are written: they edit it, ask for changes in the conversation and set
`status: approved`. When `.covener/config.yaml` says `approvals: {design: reviewer}`, the reviewer
approves it instead and adds `approved-by: reviewer`. It belongs to the change, not to the
product: when the change is archived, this file stays with it as history. A change too small for a
design has no design.md, and a bug usually has none: one is written when the fix carries a real
choice (more than one reasonable approach, a change to the shape of the system, or a pattern the
same class of bug will follow), and opens with one line saying which. A
design names components, boundaries and decisions with their reason, and stops there: behaviour
rules, validation tables, error handling, parameter parsing, ports, flags, signatures, file lists,
line numbers and tests belong to tasks.md, one per criterion, to the code and to the QA entry of
implementation.md. Adding a check to CI is a design decision; what it does when its port is taken
is not. It is read in five minutes, and longer than the spec it serves is a sign that something
here belongs elsewhere. -->

## Approach
The shape of the solution in a few sentences.

## Flows
The steps, states and error paths a user or a system goes through.

## Data and interfaces
Schemas, endpoints, events, migrations.

## Alternatives considered
What was rejected and why.

## Risks
What can go wrong, and how it is detected or undone.
