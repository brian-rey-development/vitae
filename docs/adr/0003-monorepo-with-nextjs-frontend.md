# 0003 - Monorepo with a FastAPI API and a Next.js web app

- Status: Accepted
- Date: 2026-08-21

## Context

Vitae needs a UI, and we are building it in Next.js. That is a second deployable app (TypeScript) next to the Python API. The two can live in one repo or two.

The API publishes a typed OpenAPI contract that the frontend consumes, so they change together during feature work. We also want the shared docs (PROGRESS.md, ADRs, notes) in one place, and one review when a change spans both apps.

## Decision

We will keep both apps in one repo under `apps/`. `apps/api` is the FastAPI backend (uv). `apps/web` is the Next.js frontend (pnpm). Docs live at the repo root in `docs/`. Each app keeps its own toolchain and lockfile. The frontend talks to the API through a client generated from the OpenAPI schema, so the shared contract is generated types, not copied by hand.

## Consequences

A change that hits both apps is one branch and one review. If the API schema moves, the generated client fails typecheck instead of drifting silently.

CI runs two toolchains, uv for Python and pnpm for the web app. The jobs stay independent so a failure is easy to pin down.

Each app can still deploy somewhere different. The monorepo does not pick a deploy target. That stays an M18 decision.

## Alternatives considered

Two repos would isolate history cleanly. Cross-cutting work then needs paired PRs, and the OpenAPI contract drifts more easily.

Putting the backend in Next.js API routes would be the simplest deploy. This project is for learning a production Python backend, so the API has to be FastAPI, not route handlers.

Turborepo or Nx would help if both apps were JS. They do not manage the Python app, so we keep per-app toolchains. We can look again if the web side splits into multiple packages.
