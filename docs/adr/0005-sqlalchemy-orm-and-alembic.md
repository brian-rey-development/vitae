# 0005 - SQLAlchemy 2.0 async ORM and Alembic for persistence and migrations

- Status: Accepted
- Date: 2026-08-21

## Context

ADR-0004 picked PostgreSQL. Before the first table lands we still have to choose how the schema shows up in code, and how it changes over time.

Storage stays behind a repository so it can be swapped. The storage model and the API request/response model stay separate. Schema changes should be reversible and reviewable, not created implicitly at startup.

## Decision

We will use SQLAlchemy 2.0 in its typed style (`DeclarativeBase`, `Mapped`, `mapped_column`) as the persistence layer, async all the way (async engine and `AsyncSession`). ORM models live in each domain's `models.py` and are reached only through that domain's repository. Routers and services do not import them.

We will use Alembic for migrations. `alembic revision --autogenerate` drafts a revision. A human reads it, edits it, then `alembic upgrade` applies it. Autogenerate is a draft. Every migration has a working `downgrade`.

The ORM model is the storage shape. The API shape is a Pydantic model in `schemas.py`. The repository maps between them.

## Consequences

`ty` type-checks the same models Alembic diffs for migrations, so the code schema and the database schema stay aligned.

Routers depend on a repository, not on a `Session`. SQLAlchemy stays out of the HTTP layer.

Alembic's `env.py` has to run through the async engine. That is a one-time wiring job.

Autogenerate misses things (server defaults, some type changes, data migrations). Every generated file gets read and fixed before it is committed.

## Alternatives considered

Raw SQL over asyncpg means hand-written queries and hand-maintained DDL. We lose static typing on the data layer and become the migration tool. Extra control we do not need yet.

SQLModel uses one class for the table and the API. That merges the two models we want kept apart, and it is a thinner wrap around SQLAlchemy anyway.

SQLAlchemy Core without the ORM means mapping rows to objects by hand. More boilerplate, no win at this scale.

yoyo, sqitch, or hand-run SQL files do not hook into SQLAlchemy model metadata. We would lose autogenerate and keep schema in two places. Alembic is the tool that ships with this stack.
