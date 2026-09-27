---
status: draft
---

# Design

<!-- How this change will be built, written by the engineer first and approved by the human
before the tasks are written: they edit it, ask for changes in the conversation and set
`status: approved`. When `.covener/config.yaml` says `approvals: {design: reviewer}`, the reviewer
approves it instead and adds `approved-by: reviewer`. It belongs to the change, not to the
product: when the change is archived, this file stays with it as history. A change too small for a
design has no design.md. A design is read in five minutes: the approach, the flows, the interfaces,
the decisions with their reason, the risks. No tests, no lists of files, no line numbers: the tests
go in tasks.md, one per criterion, and the evidence in the QA entry of implementation.md. Longer
than the spec it serves is a sign that something here belongs elsewhere. -->

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
