# 0002 - Domain-first module structure

- Status: Accepted
- Date: 2026-08-21

## Context

Two layouts show up a lot. Layer-first puts all routers in one folder, all models in another, all services in a third. Domain-first puts a feature in one folder. `checkins` holds its router, model, schema, service, and repository. `insights` does the same.

The app will grow into capture, similarity, insights, an agent, and auth. Adding or changing a feature should stay a local edit.

## Decision

We will organize `src/vitae/` as domain-first vertical slices. Each domain module owns its router, ORM models, Pydantic schemas, repository, and service. Cross-cutting code lives in `core/` (settings, app factory, db, logging). A domain does not import another domain's internals. Shared behavior goes into `core/` or a small public interface.

## Consequences

Adding a feature is adding one folder, not touching five scattered ones. Reviews stay smaller and unrelated code is less likely to break.

A bad cross-domain dependency is obvious, because it is an import that crosses a folder boundary.

Each domain repeats the same file layout. That is extra structure, and we are fine with it. The sameness is what makes a new slice easy to add.

## Alternatives considered

Layer-first (`routers/`, `models/`, `services/`) is what most tutorials teach. Every feature then smears across folders, coupling grows without anyone noticing, and the big layer folders become dumps.

A single-file app is fine for a demo. It will not hold a multi-capability MVP.
