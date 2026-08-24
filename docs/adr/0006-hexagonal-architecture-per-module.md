# 0006 - Hexagonal architecture (ports and adapters) per module

- Status: Accepted
- Date: 2026-08-23

## Context

ADR-0002 put each feature in its own folder. Those first slices were flat. `models`, `schemas`, `repository`, and `router` sat side by side, and the SQLAlchemy model was also the domain object. That works for thin CRUD.

Vitae's core is about to grow real domain logic that should not care about FastAPI or SQLAlchemy. Extraction, the agent loop, insight generation, similarity. We want to reason about that logic, and test it, without standing up infrastructure.

## Decision

We will split each module under `src/vitae/modules/<domain>/` into ports and adapters.

`domain/` stays free of frameworks. Stdlib and typing only. Frozen dataclass entities, enums, invariants, and repository interfaces as `typing.Protocol` ports.

`application/` holds the use cases. A service depends only on the domain ports and a `UnitOfWork` port. The service owns the transaction boundary with `uow.commit()`. It never imports a session.

`infra/` holds the adapters. `persistence/` has the SQLAlchemy `<Entity>Model`, the mappers, and the `Postgres<Entity>Repository` that implements the port. `http/` has the FastAPI router and Pydantic schemas. The router is the composition root. It wires the concrete adapters into the service.

Dependencies point only inward. `infra` depends on `application`, which depends on `domain`. Infra implements the domain's ports. The domain owns identity and time (the service generates `id` and `created_at`). Health and meta are not domains; they live as single-module routers under `platform/`.

## Consequences

Domain and application can be unit-tested with fake ports and a fake UnitOfWork. No database, no HTTP. The `unit` test tier is what keeps that honest.

Swapping an adapter (a different store, a second way in) only touches `infra`. Domain and application stay put.

`scripts/new_domain` generates the same layout, so new modules start out the same.

The cost is more files, a mapper per aggregate, and three representations of one concept (domain entity, ORM model, API schema) that have to stay in sync. That cost is worst on trivial CRUD and worth it once a module has real logic.

## Alternatives considered

Keep the flat slices. Then the domain object is a SQLAlchemy model, and business logic cannot exist without the framework. The AI-heavy modules coming next need that split.

Top-level technical layers (`models/`, `services/`) were already rejected in ADR-0002.

Skip the mappers and let the ORM model be the domain entity. Then the domain imports SQLAlchemy, so it is not actually framework-free.
