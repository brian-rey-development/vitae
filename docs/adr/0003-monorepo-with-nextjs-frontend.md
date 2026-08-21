# 0003 - Monorepo with a FastAPI API and a Next.js web app

- Status: Accepted
- Date: 2026-08-21

## Context

Vitae needs a visual interface, and we are building it with Next.js. That creates a second
deployable application (a TypeScript frontend) alongside the Python API. Two applications that
evolve together raise a structural question: do they live in one repository or two. The API
exposes a typed contract (OpenAPI) that the frontend consumes, so the two are tightly coupled at
the boundary and change in lockstep during feature work. We also want a single place for the
shared docs (PROGRESS.md, ADRs, notes) and one review surface per change that spans both.

## Decision

We will use a single monorepo with an `apps/` directory: `apps/api` for the FastAPI backend
(managed by uv) and `apps/web` for the Next.js frontend (managed by pnpm). Shared docs live at the
repo root under `docs/`. Each app keeps its own toolchain and lockfile; they are not forced into a
single package manager. The frontend consumes the API through a client generated from the API's
OpenAPI schema, so the contract is shared as generated types rather than copied by hand.

## Consequences

- One change that touches both apps is one branch, one review, one atomic commit. The API contract
  and its consumer cannot silently drift apart, because a schema change surfaces as a type error in
  the generated client.
- The full stack versions and ships together, which suits a portfolio and a small team.
- CI must run two toolchains (uv for Python, pnpm for the web app). We accept that added surface;
  the phases keep them independent so a failure is easy to localize.
- Deployment targets can still differ per app (the API and the web app may deploy to different
  places). The monorepo does not force a single deploy target; that is decided in M18.

## Alternatives considered

- Two separate repositories: cleaner isolation, independent histories. Rejected: cross-cutting
  changes need coordinated PRs across repos, and the shared API contract drifts more easily.
- One app serving both (Next.js API routes as the backend): simplest deploy. Rejected: the point of
  this project is to learn a production Python backend, so the API must be the FastAPI app, not
  Next.js route handlers.
- A JS/TS monorepo tool (Turborepo, Nx) owning both: strong for all-JS monorepos. Deferred: it adds
  machinery aimed at JS workspaces and does not manage the Python app. We keep per-app toolchains
  and can revisit if the web side grows into multiple packages.
