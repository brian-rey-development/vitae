# 0002 - Domain-first module structure

- Status: Accepted
- Date: 2026-08-21

## Context

A backend can be organized two ways. Layer-first groups code by technical role: all routers in
one folder, all models in another, all services in a third. Domain-first groups code by feature:
a `checkins` folder containing its own router, model, schema, service, and repository, and an
`insights` folder doing the same. As the app grows to cover capture, similarity, insights, an
agent, and auth, we need a structure where adding or changing a feature is a local operation.

## Decision

We will organize `src/vitae/` as domain-first vertical slices. Each domain module owns its
router, ORM models, Pydantic schemas, repository, and service. Cross-cutting concerns live in a
`core/` module (settings, app factory, db, logging). A domain never imports another domain's
internals; shared behavior is lifted into `core/` or exposed through a narrow public interface.

## Consequences

- Adding a feature means adding one folder, not editing five scattered ones. Changes stay local,
  which lowers the risk of unrelated breakage and makes review easier.
- Boundaries between domains are explicit, which keeps coupling visible and controllable.
- There is mild duplication of structure (each domain repeats the same file shape). We accept
  this as the cost of independence; consistency across slices makes it a feature, not noise.
- A poorly placed cross-domain dependency is easy to spot because it crosses a folder boundary.

## Alternatives considered

- Layer-first (routers/, models/, services/): familiar from many tutorials. Rejected: every
  feature smears across folders, coupling grows silently, and large layers become dumping grounds.
- Single-file app: fine for a demo. Rejected: does not scale to the multi-capability MVP and
  teaches none of the structure this portfolio is meant to demonstrate.
