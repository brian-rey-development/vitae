# 0005 - SQLAlchemy 2.0 async ORM and Alembic for persistence and migrations

- Status: Accepted
- Date: 2026-08-21

## Context

ADR-0004 chose PostgreSQL. We now need two related decisions before the first table lands:

1. How the schema is expressed in code (persistence style).
2. How the schema evolves over time (migrations).

The project's principles pull in a clear direction: types are the design, we validate at
boundaries and trust the typed core, and storage stays behind a repository interface so it can be
swapped. Whatever we pick has to keep the storage model separate from the API request/response
model and must produce reversible, reviewable schema changes, not implicit auto-creation.

## Decision

Use SQLAlchemy 2.0 in its modern typed style (`DeclarativeBase`, `Mapped`, `mapped_column`) as the
persistence layer, async throughout (the async engine and `AsyncSession` from ADR-0004). ORM models
live in each domain's `models.py` and are reached only through a per-domain repository class, never
imported by routers or services directly.

Use Alembic for migrations. Schema changes are generated with `alembic revision --autogenerate`,
reviewed by eye, and applied with `alembic upgrade`. Autogenerate is a draft the human edits, not a
command we trust blindly. Every migration has a working `downgrade`.

The ORM model is the storage shape only. The API shape is a separate Pydantic model in each domain's
`schemas.py`; the repository maps between them.

## Consequences

- The typed model is a single source of truth that both `ty` checks statically and Alembic diffs to
  generate migrations, so the schema in code and the schema in the database stay in step.
- Repositories keep SQLAlchemy out of the domain surface: a router depends on a repository, not on a
  `Session` full of ORM internals, which preserves the vertical-slice boundary.
- Async Alembic needs its `env.py` wired to run migrations through the async engine. This is a
  one-time setup cost we pay now.
- Autogenerate does not catch everything (server defaults, some type changes, data migrations), so
  every generated migration is read and corrected before it is committed.

## Alternatives considered

- Raw SQL over asyncpg (hand-written queries, hand-maintained DDL). Rejected: throws away static
  typing on the data layer and makes us the migration tool. It buys control we do not need yet and
  costs the type-driven safety the project is built on.
- SQLModel (one class for table and API). Rejected: it deliberately merges the storage model and the
  API model, which is the exact split this project requires (never leak internals). It is also
  thinner and less mature than SQLAlchemy underneath, which it wraps anyway.
- SQLAlchemy Core without the ORM. Rejected: more boilerplate to map rows to objects by hand, for no
  gain over the typed ORM at this scale.
- Migration tools other than Alembic (yoyo, sqitch, hand-run SQL files). Rejected: none integrate
  with SQLAlchemy model metadata, so we would lose autogenerate and maintain schema drift by hand.
  Alembic is the native, reversible choice for a SQLAlchemy project.
