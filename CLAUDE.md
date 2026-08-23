# Vitae - project instructions

This file extends the global user instructions for this repo. Where this file and the global rules
disagree, this file wins. Where it is silent, the global rules apply.

## What this project is

Vitae is a learning-by-building portfolio project: a personal health agent with a FastAPI backend
and a Next.js frontend. It is built milestone by milestone as a curriculum. The human is preparing
for a technical interview and uses this project as the study vehicle, so the reasoning behind each
choice matters as much as the code.

`docs/PROGRESS.md` is the single source of truth for scope, milestones (M0-M12), Definition of Done,
and the global quality gate. Read it before proposing work. Do not start milestone M(n+1) until
M(n)'s DoD is fully checked.

## How to work here

- Follow the milestone in progress. Do not build ahead of the current milestone or pull in a
  decision (datastore, LLM provider, vectors, etc.) that PROGRESS.md defers to a later one.
- When a milestone forces a real architectural choice, write an ADR in `docs/adr/` (copy
  `0000-template.md`), weigh at least two real alternatives, and get it accepted before the code
  lands. Numbered sequentially.
- At the end of each milestone, write a self-contained learning note in `docs/notes/` (one per
  milestone). These notes are the interview study material, so they must reconstruct the reasoning,
  not just list what was done.
- Teaching mode: explain from first principles, map concepts from the human's TypeScript/Node
  background, and challenge weak answers instead of validating them. Coding challenges must come
  from the real work of the current milestone, never disconnected toy problems.

## Toolchains (two, kept separate)

- `apps/api` is Python, owned entirely by **uv**. Run everything through `uv run ...`. Never use
  pip, poetry, or a system Python directly.
- `apps/web` is TypeScript, owned by **pnpm** (never npm or yarn).
- The API exposes an OpenAPI contract; the web app consumes it through a generated typed client, so
  the contract is shared as generated types, never hand-copied.

## Backend code standards (Python)

The global code standards are written for TypeScript. They map to this Python backend as follows,
and still hold in spirit:

- Type hints everywhere. `ty` is our `tsc`; it must pass with no unjustified ignores. A `type:
  ignore` needs an inline reason, the same way an `any` would.
- Validate at boundaries, trust the core. Untrusted input (users, LLM output, external APIs) is
  parsed into Pydantic models at the edge. The LLM is just another untrusted boundary.
- Functional and immutable by default, early returns, small functions, named constants over magic
  values. Readability over cleverness.
- Explicit over implicit: dependencies and config are injected (app factory + `Depends`), not
  reached for as module globals.
- Fail fast and loud. Missing config crashes at startup. No silent fallbacks, no bare `except` that
  swallows errors.
- Default to zero comments; add one only when the WHY is non-obvious. No docstrings except to
  document a public API contract.

## Structure (domain-first, ADR-0002)

`src/vitae/` is organized as vertical slices. Each domain module (`checkins`, `insights`,
`similarity`, `agent`, `auth`, `health`, ...) owns its own router, models, schemas, repository, and
service. Cross-cutting concerns live in `core/` (settings, app factory, db, logging). A domain must
not import another domain's internals; lift shared behavior into `core/` or a narrow public
interface. Keep the storage model separate from the API request/response schema; never leak
internals.

The concrete house style (slice anatomy, naming, repository and router patterns, where operational
tooling lives) is in `docs/CONVENTIONS.md`. Follow it and the exemplar (the `conversations` slice);
new code should look like it.

## Quality gate (every milestone, non-negotiable)

Before a milestone is done, all of these pass. Do not claim done without running them:

- `uv run ruff check` and `uv run ruff format --check`
- `uv run ty check` (no unjustified ignores)
- `uv run pytest` (new behavior has new tests; from M4 on, no feature merges without tests)
- No secret hardcoded or logged; config via settings
- No silent failure
- Endpoint appears correctly in `/docs`
- ADR written for any real decision; learning note written for the milestone

## Commits and worktrees

- Conventional commits in English. Commit only when explicitly asked.
- Never use em dashes anywhere (prose, code, commits, docs). Use regular dashes or commas.
- Touching 3+ files or committing: ask about using a worktree first.
- If on `main`, branch before committing.
