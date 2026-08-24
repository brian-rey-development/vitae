# Architecture Decision Records

An ADR is a short record of a hard-to-reverse choice. It says what forced the decision, what we picked, and what we gave up. If someone later asks why the system is built this way, the answer should be here.

## When to write one

Write one when any of these is true.

- The decision is expensive or painful to reverse (database, framework, auth, provider).
- It rules out an alternative someone would otherwise try.
- It changes the shape of the code across many modules.

Skip it for local, reversible choices. A variable name or where a helper lives does not need an ADR.

## Format

Copy `0000-template.md`, number it sequentially, and keep it to about a page. Status moves from Proposed to Accepted, and to Superseded if a later ADR replaces it.

