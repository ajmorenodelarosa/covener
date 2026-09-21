---
name: frontend
description: This project's frontend conventions for structure, state, data fetching, forms, styling, accessibility and component tests. Use when creating or changing anything a user sees or interacts with, including components, pages, styles, client-side state and API calls from the browser.
---

# Frontend conventions

<!-- TODO: replace every line below with how this project actually works. An empty template is
worse than no skill: agents will follow generic habits instead of yours. Keep this file under
100 lines and move long material into reference files next to it. -->

## Stack
Framework, language, build tool and package manager, with the versions that matter.

## Where code goes
The directories a component, a page, a hook and a shared utility belong in, with one real example
of each path.

## Composition
When to create a component, when to extend one, and which shared components must be reused instead
of rebuilt (forms, tables, modals, buttons).

## State and data
Local versus shared state, the state library and the one pattern to use it, how data is fetched and
cached, and how loading and error states are represented.

## Forms and validation
The form library, where the schema lives, and how server errors reach the field.

## Styling
The styling system, the spacing and colour tokens, and the rule about writing raw values.

## Accessibility
The non-negotiables: labels, focus order, keyboard paths, contrast, and what the component must do
with a screen reader.

## Tests
What is unit-tested, what is tested through the DOM, what needs a visual check, and the command
that runs them.

## Done checklist
- [ ] Every state handled: empty, loading, error, success, no permission
- [ ] Keyboard and screen-reader path verified
- [ ] Shared components reused, tokens used instead of raw values
- [ ] Tests added for the acceptance criteria this change covers
