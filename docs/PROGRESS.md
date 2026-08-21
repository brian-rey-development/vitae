# Vitae - Build Plan and Progress

Vitae is a production-grade MVP of a personal health agent (an Atlas-style app). You log a
short daily check-in, and the system turns messy natural language into structured health data,
finds people with similar journeys, and surfaces evidence-based patterns and interventions.

This document is the single source of truth for what we are building, why, and how far along we
are. It is written as a learning-by-building curriculum for a senior-quality portfolio project.
Every decision is justified from first principles, not by "this is how tutorials do it".

## How to use this document

- Work top to bottom, one milestone at a time. Do not start M(n+1) until M(n)'s Definition of
  Done is fully checked.
- Each milestone lists the concepts you will actually learn, the deliverables, and a Definition
  of Done (DoD) checklist. The DoD is the contract for "done", not "it runs on my machine".
- When a milestone forces a real architectural choice, capture it as an ADR in `docs/adr/`.
- Keep a running learning journal in `docs/notes/`. One note per milestone. Future-you and any
  reviewer of this portfolio should be able to reconstruct your reasoning.
- The Global Quality Gate at the bottom applies to every single milestone. It is non-negotiable.

## Product vision

The user spends about one minute a day chatting with Vitae. From that we build a private,
longitudinal health record and reason over it. The MVP proves five capabilities end to end:

1. Structured capture: free-text daily chat becomes validated, typed health data.
2. Longitudinal storage: a private, append-only-ish record that accumulates over time.
3. Similarity: find users with similar symptom profiles ("people like you").
4. Insight: surface correlations and evidence-based patterns, with citations to the user's own data.
5. Action: propose short, measurable intervention trials and track their effect.

This is not a medical device. Safety, disclaimers, and guardrails are a first-class module
(M11), not an afterthought.

## Engineering principles (first principles)

These are the axioms. Every design choice traces back to one of them.

1. Validate at every boundary, trust the core. Untrusted input (users, LLMs, external APIs)
   is parsed into typed models at the edge. Once inside, code trusts its types. The LLM boundary
   is just another untrusted boundary.
2. Types are the design. We use Python type hints everywhere, check them statically with `ty`,
   and enforce them at runtime with Pydantic. A type error caught by a tool is a bug that never
   reached production.
3. Explicit over implicit. Configuration, dependencies, and side effects are passed in, not
   reached for. This is why we use an app factory and dependency injection, not module globals.
4. Vertical slices, not horizontal layers. Code is organized by domain (checkins, insights,
   auth), each a self-contained feature, not by technical role (all routers here, all models there).
5. Fail fast and loud. Missing config crashes at startup, not at 3am on the first request.
   Silent fallbacks are forbidden. An error we can see beats a wrong answer we cannot.
6. Everything is testable and tested. If a thing cannot be tested in isolation, its design is
   wrong. AI features included: we test prompts and structured outputs with evals, not vibes.
7. Reproducible everywhere. `docker compose up` and `uv sync` give any machine, and CI, the
   exact same environment. No "works on my machine".
8. Observability is a feature. Structured logs, request IDs, and cost/latency tracking are built
   in, because you cannot operate what you cannot see.
9. Heavy work runs in pipelines, not the request path. Long or expensive operations (extraction,
   embedding, enrichment, external fetches) are queued and processed by workers. The API stays
   fast, and failed steps are retryable instead of lost.
10. External data is untrusted and cited. Information from outside sources is validated, kept
    separate from the user's private record, and every claim it supports is traceable to its source.

## Architecture at a glance

The shape is decided. The specific technology in the boxes marked TBD is not: we choose it in the
milestone that needs it, after weighing alternatives in an ADR.

```
                          Browser
                             |
                             v
             +-------------------------------+
             |  Next.js web app (apps/web)   |  typed API client, streaming chat UI
             +-------------------------------+
                             |   HTTP (JSON) + SSE
                             v
             +-------------------------------+
             |  FastAPI  (apps/api)          |  app factory, DI, auth
             +-------------------------------+
                             |
                    Domain modules (vertical slices)
        checkins / insights / similarity / knowledge / agent / auth / health
              |                    |                        |
              v                    v                        v
      Persistence (repos)      AI layer                Queue + worker
              |            prompts, extraction,      pipelines: extract,
              v            tools, RAG, streaming      embed, enrich, ingest
      Datastore (TBD, M2)  LLM provider (TBD, M5)            |
      Vectors (TBD, M7)                                      v
                                              External sources (TBD, M9)
                                              literature / references / wearables
```

What we commit to now is the structure: a monorepo with a Next.js web app and a FastAPI API app,
an app factory and dependency injection, domain modules as vertical slices, a persistence layer
behind a repository interface, an AI layer isolated behind its own module, and heavy work pushed
into a worker-driven pipeline. Because storage, provider, and external sources sit behind
interfaces, those choices can be made late and swapped without rewriting the domain code.

## Repository layout

A monorepo holds both apps so the full stack versions, reviews, and ships together (see ADR-0003).

```
vitae/
  apps/
    api/                 # FastAPI backend (Python, uv)
      src/vitae/         # domain-first modules: core, health, checkins, insights, ...
      tests/
      pyproject.toml
    web/                 # Next.js frontend (TypeScript, pnpm) - added in Phase D
  docs/                  # PROGRESS.md, adr/, notes/
  docker-compose.yml     # local infra, added when a milestone needs it
```

The API app is built in Phases A to C. The `web` app is added in Phase D. Until then, `apps/web`
does not exist and nothing references it.

## Tech stack

Two lists. The first is decided now, because these are either explicit project constraints or
foundational choices with an ADR already written. The second is deliberately open: each item is a
real decision we make in its milestone, from first principles, with alternatives, recorded as an
ADR at that point. We do not assume the answer here.

Decided now:

| Concern       | Choice            | Why (first principles)                                                       |
|---------------|-------------------|------------------------------------------------------------------------------|
| Tooling       | uv (ADR-0001)     | One fast tool for Python version, venv, deps, lockfile. Reproducible builds. |
| Structure     | Domain-first (ADR-0002) | Vertical slices keep features local and coupling visible.              |
| Repo layout   | Monorepo (ADR-0003) | One repo, `apps/api` + `apps/web`, so the full stack ships together.        |
| Web framework | FastAPI           | Project constraint. Async-native, type-driven, auto OpenAPI docs.            |
| Validation    | Pydantic v2       | Comes with FastAPI. Runtime validation from the same hints `ty` checks.      |
| Config        | pydantic-settings | Typed config from env. Missing or invalid config fails at startup.           |
| Type checker  | ty                | Project constraint. Static type checking, like tsc, from astral.             |
| Lint + format | ruff              | One fast tool replacing flake8, isort, black.                                |
| Tests (api)   | pytest            | Fixtures model dependency injection. Isolated test runs.                     |
| Frontend      | Next.js + React   | Project constraint. App Router, server components, streaming UI.             |
| Frontend pkg  | pnpm              | Workspace manager for the web app (per standing standard).                   |

To be decided in-milestone (each gets an ADR after weighing alternatives):

| Concern                    | Decide in | Alternatives we will actually compare                             |
|----------------------------|-----------|-------------------------------------------------------------------|
| Datastore                  | M2        | Relational vs document, managed vs self-hosted, and which engine. |
| Persistence style          | M3        | ORM vs query builder vs raw SQL, and which migration tool.        |
| LLM provider               | M5        | Which provider and SDK, and how we isolate it behind an interface.|
| Similarity / vectors       | M7        | In-database vectors vs a dedicated vector DB vs a library.        |
| External data sources      | M9        | Which sources, how fetched, and how they are cited and isolated.  |
| Background processing/queue| M12       | In-process tasks vs a broker vs a task framework.                 |
| Containerization           | M18       | Whether and how we containerize for dev and prod.                 |
| CI                         | M18       | Which CI runs the quality gate.                                   |
| Deployment target          | M18       | API and web deploy targets.                                       |

## Milestones

Legend: `[ ]` todo, `[~]` in progress, `[x]` done. Update as you go. Milestones are grouped into
five phases and numbered in build order. Do not start one until the previous Definition of Done is
fully met.

## Phase A - Backend skeleton

### M0 - Foundations and environment
Goal: understand the stack and prove the toolchain works before writing app code.

Concepts: uv vs node/pnpm, virtual environments, Python type hints and their dual role
(static via ty, runtime via Pydantic), the src layout, why a monorepo-free single package here.

Deliverables:
- uv installed and working. Other infrastructure (a datastore, containers) is installed later,
  in the milestone that decides it needs it, not up front.
- `docs/notes/00-python-for-typescript-devs.md` read and extended with your own words.

Definition of Done:
- [ ] `uv --version` works.
- [ ] You can explain, in the notes file, what a venv is and why type hints are not enforced by
      the Python runtime.

### M1 - Production skeleton
Goal: a running FastAPI app with the professional shape, living at `apps/api` in the monorepo. No
datastore yet, that decision is M2. The `apps/web` frontend arrives in Phase D.

Concepts: monorepo layout, app-factory pattern, domain-first module layout, typed settings, the
quality gate loop (ruff + ty), FastAPI routers, OpenAPI docs.

Deliverables:
- Monorepo root with `apps/api` holding a `uv` src-layout project (`apps/api/src/vitae/...`),
  pyproject with ruff + ty configured.
- `core/settings.py` (pydantic-settings), `core/app.py` (`create_app()`), `main.py`.
- `health/router.py` exposing `GET /health`.
- `.env` + committed `.env.example` for configuration (no secrets committed).

Definition of Done:
- [ ] `uv run fastapi dev apps/api/src/vitae/main.py` serves `GET /health -> {"status": "ok"}`.
- [ ] `/docs` renders the endpoint.
- [ ] `uv run ruff check` and `uv run ty check` pass clean.
- [ ] ADR-0001 (uv), ADR-0002 (domain-first), ADR-0003 (monorepo) reviewed and accurate.

### M2 - Choose and integrate the datastore
Goal: decide how Vitae persists data, then wire that store with correct lifecycle and DI.

Decision first: before any code, we compare the real options (relational vs document, managed vs
self-hosted, and the specific engine) against Vitae's needs (longitudinal records, later
similarity search, transactions). We write the ADR, then build. The concepts below assume we land
on an async relational store, but that is the output of the decision, not its premise.

Concepts: what a connection and a pool are, request-scoped sessions, dependency injection via
`Depends`, why the session lifecycle is per-request, a readiness check that verifies the real
dependency, keeping storage behind a repository interface so it can be swapped.

Deliverables:
- ADR for the datastore choice, with alternatives and consequences.
- `core/db.py`: connection/engine setup, session factory, a session dependency.
- `/health` split into `/health/live` (no dependencies) and `/health/ready` (checks the store).

Definition of Done:
- [ ] The datastore ADR is written and accepted before code lands.
- [ ] `/health/live` returns ok without touching the store (liveness).
- [ ] `/health/ready` returns ok only when the store responds, and 503 when it is down (test both).
- [ ] Connections/sessions are acquired and released per request, verified by a test.

### M3 - First domain model and schema migrations
Goal: the `CheckIn` entity, persisted, with versioned schema changes and a clean repository.

Decision first: how do we define the schema and evolve it over time (ORM vs query builder vs raw
SQL, and which migration tool). We compare the options for our store, write the ADR, then build.

Concepts: modeling an entity, the repository pattern (separating persistence from business logic),
UUIDs and timestamps, versioned and reversible migrations reviewed by eye, and the crucial
distinction between the storage model and the API request/response model (never leak internals).

Deliverables:
- ADR for the persistence and migration approach.
- `checkins/models.py` (storage model), `checkins/schemas.py` (Pydantic in/out),
  `checkins/repository.py`.
- The first migration that creates the `checkins` table, created and applied.
- `checkins/router.py`: create and list check-ins (CRUD subset).

Definition of Done:
- [ ] Applying migrations from empty creates the table on a fresh store.
- [ ] `POST /checkins` persists a row and returns the created resource (typed, no internal leak).
- [ ] `GET /checkins` returns the user's check-ins.
- [ ] The migration is reversible and was reviewed by eye, not accepted blindly.

### M4 - Testing foundation
Goal: fast, isolated, real-database tests so every later module is test-first.

Concepts: pytest fixtures as dependency injection, test database lifecycle, transaction rollback
per test, `httpx.AsyncClient` against the app, factory helpers, coverage as a signal not a target.

Deliverables:
- `tests/conftest.py`: throwaway test store, per-test isolation, app + client fixtures.
- Tests for health, checkins CRUD, and settings validation.

Definition of Done:
- [ ] `uv run pytest` runs green against a real, isolated test store.
- [ ] Tests are isolated: order does not matter, no shared state leaks between tests.
- [ ] CI (M18 will formalize) can run these headless.
- [ ] From here on, no feature is merged without tests. This is a standing rule.

## Phase B - The AI core

### M5 - First LLM call
Goal: call an LLM from the backend, treating the prompt as versioned code and the key as a secret.

Decision first: which provider and SDK, and how we hide it behind our own `ai/` interface so the
rest of the app never imports a vendor directly. We compare options for our needs (tool-use and
structured output quality, cost, latency), write the ADR, then build.

Concepts: the messages request shape, system vs user messages, prompt-as-code, secret handling via
settings, timeouts and retries, the LLM as an untrusted, non-deterministic boundary.

Deliverables:
- ADR for the LLM provider choice.
- `ai/client.py`: a thin, typed, vendor-isolating wrapper.
- A `reflect` endpoint that sends a check-in to the model and returns prose.

Definition of Done:
- [ ] API key loaded from env via settings, never hardcoded, never logged.
- [ ] Call has an explicit timeout and a retry policy.
- [ ] A test exercises the wrapper with the network call mocked (no real spend in CI).
- [ ] The provider ADR is written and the vendor is reachable only through `ai/`.

### M6 - In-depth structured extraction
Goal: turn free-text daily chat into a rich, validated `CheckIn`: symptoms, meals, medications,
wearable signals, and life events, normalized to canonical concepts, with per-field confidence.
This is the core magic of the product, so we go deep, not shallow.

Concepts: tool-use / JSON mode for structured output, Pydantic schema as the LLM contract, nested
and repeated structures, normalization to a controlled vocabulary (a raw phrase like "wiped out"
becomes a canonical concept, not a free string), per-field confidence scoring, validate-and-repair
loops, handling refusals and partial extractions, determinism knobs.

Deliverables:
- `ai/extract.py`: text in, validated `CheckInDraft` out (nested entities), with retry-on-invalid.
- A normalization step mapping extracted phrases to canonical concepts.
- `POST /checkins/from-text`: chat message in, persisted structured check-in out.

Definition of Done:
- [ ] Invalid or partial model output is caught and re-prompted, never silently accepted.
- [ ] Extracted entities are normalized to canonical concepts, not stored as raw strings.
- [ ] Eval set of at least 15 messages with expected fields and concepts; extraction passes them.
- [ ] The Pydantic schema is the single source of truth for the extraction shape.

### M7 - Embeddings and similarity search
Goal: "find people like you" via semantic similarity.

Decision first: where and how vectors live and get searched (in-database vectors, a dedicated
vector database, or a library), plus which embedding model. We compare against operational cost
and the datastore chosen in M2, write the ADR, then build.

Concepts: embeddings, cosine distance, keyword vs semantic search, approximate nearest neighbor
indexes and their tradeoffs, storing and querying vectors, keeping similarity behind a service
interface.

Deliverables:
- ADR for the vector approach and embedding model.
- Embedding generation for check-in text, stored where the ADR decided.
- `GET /checkins/{id}/similar`: nearest neighbors by embedding.

Definition of Done:
- [ ] The vector approach ADR is written with the tradeoff made explicit.
- [ ] Similarity query returns sensible neighbors on seeded data, ordered by distance.

### M8 - RAG over the user's own data
Goal: insight cards grounded in the user's private record, with citations, not hallucinations.

Concepts: retrieval-augmented generation, context assembly, citation and grounding, prompt
injection risk from stored user content, chunking and relevance.

Deliverables:
- `insights/service.py`: retrieve relevant check-ins, assemble context, ask the model for a pattern.
- `GET /insights`: returns insight cards each citing the check-ins that support them.

Definition of Done:
- [ ] Every insight references specific check-in ids as evidence.
- [ ] A test proves the model is not asked to invent data beyond the retrieved context.
- [ ] Stored user text is treated as untrusted (injection-aware prompt design).

### M9 - External information and knowledge integration
Goal: enrich insights with outside evidence (condition and treatment references, literature),
kept strictly separate from private data and always cited.

Decision first: which external sources, how they are fetched and cached, and how their content is
isolated from the user's private record. We compare options, write the ADR, then build.

Concepts: integrating external APIs, treating fetched content as untrusted, building a separate
knowledge corpus, retrieval over external vs private data, provenance and citation, prompt-injection
risk from third-party text, caching and rate limits, graceful degradation.

Deliverables:
- ADR for the external sources and isolation approach.
- `knowledge/` module: fetch, validate, store, and index external references.
- Insights can cite external evidence, visually and structurally separate from the user's own data.

Definition of Done:
- [ ] External content is stored and retrieved separately from private data.
- [ ] Every externally-supported claim carries a source citation.
- [ ] A fetch failure degrades gracefully: the insight still returns, without the external claim.

### M10 - Tool-calling and the agent loop
Goal: Vitae can act, logging data and querying its own store to answer, via tools.

Concepts: tool definitions as typed contracts, the think-act-observe loop, tool result handling,
loop termination and step limits, guardrails on tool arguments.

Deliverables:
- `ai/tools.py`: typed tools (log_checkin, query_history, propose_trial).
- `POST /agent/message`: a conversational turn that may call tools and returns a final answer.

Definition of Done:
- [ ] The loop has a hard step limit and cannot run unbounded.
- [ ] Tool arguments are validated with Pydantic before execution.
- [ ] A multi-step scenario (log then reason) passes an integration test.

### M11 - Streaming
Goal: the live one-minute chat feel via streamed responses.

Concepts: server-sent events / streaming responses, backpressure, streaming structured vs prose,
partial rendering, cancellation.

Deliverables:
- Streaming variant of the agent endpoint (SSE).

Definition of Done:
- [ ] Tokens stream to the client incrementally, verified end to end.
- [ ] Client cancellation stops server work (no orphaned generation).

## Phase C - Pipelines and processing

### M12 - Background processing and pipelines
Goal: move heavy work off the request path onto a worker, with a queue and retries.

Decision first: how we run background work (in-process background tasks vs a message broker vs a
task framework). We compare against reliability needs, write the ADR, then build.

Concepts: the request path vs background work, queues, workers, idempotency, retries and backoff,
dead-letter handling, at-least-once delivery, observing job state.

Deliverables:
- ADR for the background processing approach.
- A worker process and a queue.
- Extraction and embedding moved from inline endpoints to enqueued jobs.

Definition of Done:
- [ ] Submitting a check-in enqueues extraction and embedding; the endpoint returns immediately.
- [ ] A failing job retries with backoff and lands in a dead-letter path after N attempts.
- [ ] Job state is observable (queued, running, done, failed).

### M13 - Ingestion and enrichment pipeline
Goal: one coherent pipeline from raw input to indexed, enriched, queryable data, plus scheduled
external ingestion.

Concepts: pipeline stages and their contracts, idempotent stages, backfills and reprocessing,
scheduled jobs, batch vs streaming, data lineage, replayability.

Deliverables:
- A staged pipeline: raw text -> extract -> normalize -> embed -> index, each stage retryable.
- A scheduled job that refreshes the external knowledge corpus.
- A backfill command to reprocess historical check-ins through the current pipeline.

Definition of Done:
- [ ] A new check-in flows through all stages to a queryable, embedded, normalized record.
- [ ] The pipeline is replayable: reprocessing produces the same result (idempotent stages).
- [ ] The scheduled external refresh runs and updates the knowledge corpus.

## Phase D - The frontend (Next.js)

### M14 - Web app scaffold and typed API client
Goal: a Next.js app in `apps/web` that talks to the API with end-to-end types.

Concepts: App Router structure, server vs client components, generating a typed client from the
API's OpenAPI schema, environment config, the dev proxy to the API, data fetching patterns.

Deliverables:
- `apps/web` Next.js app (App Router, TypeScript strict).
- A typed API client generated from the API's OpenAPI schema (types shared, not hand-written).
- A first screen listing check-ins from the real API.

Definition of Done:
- [ ] The web app renders live data from the API.
- [ ] API types are generated, not duplicated by hand; a schema change surfaces as a type error.
- [ ] pnpm scripts run lint, types, and build clean.

### M15 - Core product screens
Goal: the real Atlas surfaces. Daily check-in, timeline, insight cards, similar journeys.

Concepts: component structure, client-side forms and validation, rendering structured insights,
loading and error states, accessibility basics, design consistency.

Deliverables:
- Daily check-in entry (free-text chat that posts to `/checkins/from-text`).
- A health timeline of check-ins.
- Insight cards with their citations.
- A "people like you" view backed by similarity search.

Definition of Done:
- [ ] Each screen handles loading, empty, and error states explicitly.
- [ ] Insights display citations; external evidence is visually distinct from private data.
- [ ] No `any`; the client validates input at its boundary.

### M16 - Streaming chat UI and interactions
Goal: the live one-minute chat feel, consuming the streaming agent endpoint.

Concepts: consuming SSE / streamed responses in the browser, incremental rendering, optimistic UI,
cancellation, rendering tool-call steps and structured results as they arrive.

Deliverables:
- A chat UI that streams the agent's response token by token.
- Optimistic display of the user's message and in-flight tool steps.
- A cancel control that stops both client rendering and server work.

Definition of Done:
- [ ] Responses stream visibly; the UI stays responsive during generation.
- [ ] Cancelling mid-stream stops server work, verified end to end.
- [ ] A check-in logged from chat appears in the timeline without a full reload.

## Phase E - Ship it

### M17 - Evals, guardrails, cost and latency
Goal: prove quality and safety, and control spend.

Concepts: offline evals as regression tests for prompts, LLM-as-judge, guardrails and refusals,
medical-safety disclaimers and red lines, token/cost accounting, latency budgets, caching.

Deliverables:
- `evals/`: a runnable suite scoring extraction and insight quality.
- A safety guardrail layer (disclaimers, refusal on out-of-scope medical advice).
- Cost and latency logged per LLM call.

Definition of Done:
- [ ] Eval suite runs in CI and fails the build if quality regresses past a threshold.
- [ ] Out-of-scope or unsafe requests are refused with a clear, tested message.
- [ ] Per-request cost and latency are visible in logs.
- [ ] The safety posture and disclaimers ADR is written.

### M18 - Auth, observability, CI/CD, deploy (full stack)
Goal: ship it. Real auth across API and web, real logs, real pipeline, real deployment of both apps.

Decision first: the authentication strategy, the containerization approach, the CI system, and the
deployment targets for both apps are each chosen here, with alternatives, recorded as ADRs. The
concepts below describe the shape; the specific technology is the output of those decisions.

Concepts: token verification and a request-scoped auth dependency, protecting web routes and
threading auth from web to API, structured logging with request ids, tracing basics, building
reproducible artifacts, a CI gate that runs the quality checks, deploying API and web.

Deliverables:
- ADRs for the auth strategy and the deployment targets.
- `auth/`: a token verifier, a `current_user` dependency, protected API routes.
- Web app auth integration: login and protected pages.
- Structured JSON logging with request-id middleware.
- Reproducible build artifacts, a CI pipeline running lint + types + tests + migration check for
  both apps, and a working deployment of API and web.

Definition of Done:
- [ ] Protected API endpoints reject missing/invalid tokens (tested).
- [ ] The web app gates protected screens and reflects auth state.
- [ ] Logs are structured JSON with a request id correlating a full request.
- [ ] CI is green and gates merges; a red gate blocks merge.
- [ ] Both apps deploy; the API serves `/health` and the web app loads against it.
- [ ] The auth and deployment ADRs are written.

## Global Quality Gate (applies to every milestone)

A milestone is not done until all of these hold. This is what makes it senior-level, not a demo.

- [ ] `uv run ruff check` and `uv run ruff format --check` pass.
- [ ] `uv run ty check` passes with no ignored errors (any `type: ignore` is justified inline).
- [ ] `uv run pytest` passes; new behavior has new tests.
- [ ] No secret is hardcoded or logged. Config comes from settings.
- [ ] No silent failure: errors surface, they are not swallowed by bare except or fallbacks.
- [ ] Public behavior is documented (endpoint appears correctly in `/docs`).
- [ ] Any real decision made is captured as an ADR.
- [ ] A learning note for the milestone exists in `docs/notes/`.

## Progress log

Append one line per working session. Newest at the bottom.

- 2026-08-21 - Plan authored. Milestones M0-M12 defined, ADR and notes scaffolding created.
- 2026-08-21 - Scope expanded: in-depth extraction, external knowledge (M9), pipelines phase
  (M12-M13), and a Next.js frontend phase (M14-M16). Repo is now a monorepo (ADR-0003). Milestones
  renumbered to M0-M18 across five phases.
