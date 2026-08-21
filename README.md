# Vitae

A production-grade MVP of a personal health agent. You spend about a minute a day chatting with
Vitae; it turns messy natural language into structured, typed health data, builds a private
longitudinal record, finds people with similar journeys, and surfaces evidence-based patterns and
interventions grounded in your own data.

This is a portfolio project built as a learning-by-building curriculum. Every architectural choice
is justified from first principles and recorded as an ADR. It is not a medical device; safety and
guardrails are a first-class module, not an afterthought.

## What it does (MVP capabilities)

1. **Structured capture** - free-text daily chat becomes validated, typed health data.
2. **Longitudinal storage** - a private, append-only-ish record that accumulates over time.
3. **Similarity** - find users with similar symptom profiles ("people like you").
4. **Insight** - surface correlations and patterns, cited back to the user's own check-ins.
5. **Action** - propose short, measurable intervention trials and track their effect.

## Stack

The backend is Python; the frontend is Next.js. Each app keeps its own toolchain and lockfile.

| Concern           | Choice                | Notes                                                        |
|-------------------|-----------------------|--------------------------------------------------------------|
| Repo layout       | Monorepo (ADR-0003)   | `apps/api` (FastAPI) + `apps/web` (Next.js), shared `docs/`. |
| API tooling       | uv (ADR-0001)         | Python version, venv, deps, and lockfile in one tool.        |
| Web framework     | FastAPI               | Async-native, type-driven, auto OpenAPI docs.                |
| Validation        | Pydantic v2           | Runtime validation from the same hints `ty` checks.          |
| Config            | pydantic-settings     | Typed config from env; missing config fails at startup.      |
| Type checker      | ty                    | Static type checking for Python, from astral.                |
| Lint + format     | ruff                  | Replaces flake8, isort, black.                               |
| Tests (api)       | pytest                | Fixtures model dependency injection; isolated runs.          |
| Frontend          | Next.js + React       | App Router, server components, streaming UI.                 |
| Frontend tooling  | pnpm                  | Workspace manager for the web app.                           |
| Module structure  | Domain-first (ADR-0002) | Vertical slices: each domain owns its router/model/repo.   |

Choices deliberately left open and decided in the milestone that needs them (each gets an ADR):
datastore, persistence style, LLM provider, vector approach, external data sources, background
processing, containerization, CI, and deployment target. See `docs/PROGRESS.md` for the schedule.

## Architecture at a glance

```
Browser -> Next.js web app (apps/web) -> FastAPI (apps/api) -> domain modules
                                                                     |
                     checkins / insights / similarity / knowledge / agent / auth / health
                                                                     |
                              persistence (repos)  |  AI layer  |  queue + worker
```

Storage, LLM provider, and external sources sit behind interfaces, so those choices can be made
late and swapped without rewriting domain code. Full diagram and rationale in `docs/PROGRESS.md`.

## Repository layout

```
apps/
  api/          FastAPI backend (uv, src/vitae/ layout)   [scaffolded in M1]
  web/          Next.js frontend (pnpm)                   [added later]
docs/
  PROGRESS.md   Single source of truth: milestones, DoD, quality gate
  adr/          Architecture Decision Records
  notes/        Per-milestone learning journal
```

Only `docs/` exists today. `apps/` is created milestone by milestone.

## Getting started

Prerequisites: [uv](https://docs.astral.sh/uv/). The Node/pnpm toolchain is added when `apps/web`
lands.

```bash
uv --version          # confirm the toolchain (M0)
```

The API app is scaffolded in M1. Once it exists:

```bash
cd apps/api
uv sync                                   # reproduce the environment from the lockfile
uv run fastapi dev src/vitae/main.py      # serve the API
uv run ruff check && uv run ty check      # lint + types
uv run pytest                             # tests
```

## Quality gate

Every milestone must pass this before it counts as done (full list in `docs/PROGRESS.md`):

- `uv run ruff check` and `uv run ruff format --check` pass.
- `uv run ty check` passes; any `type: ignore` is justified inline.
- `uv run pytest` passes; new behavior has new tests.
- No secret is hardcoded or logged; config comes from settings.
- No silent failure; errors surface rather than being swallowed.
- Every real decision is captured as an ADR, and each milestone has a note in `docs/notes/`.

## Documentation

- `docs/PROGRESS.md` - the build plan, milestones M0-M12, and the quality gate.
- `docs/adr/` - why each decision was made, with alternatives and consequences.
- `docs/notes/` - the learning journal, one note per milestone.
