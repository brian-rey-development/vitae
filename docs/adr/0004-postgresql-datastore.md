# 0004 - PostgreSQL as the datastore, run locally via Docker

- Status: Accepted
- Date: 2026-08-21

## Context

M2 requires choosing how Vitae persists data before any persistence code lands. The workload has a
clear shape. The data is longitudinal and relational: a user has many check-ins, and check-ins
produce insights, with real relationships between them. Writes should be transactional, so a
check-in and its derived data commit all-or-nothing. Some fields are semi-structured, because
LLM-extracted data varies in shape. And a later milestone (M7, "find people like you") needs
similarity search over embedding vectors.

Three decisions are on the table: the data model (relational vs document), the specific engine, and
where the database runs during development. The persistence style (ORM vs query builder vs raw SQL)
and the migration tool are deliberately deferred to M3; this ADR only fixes the store and its
lifecycle location.

## Decision

We will use PostgreSQL as the datastore.

Relational is the right model, because the core data is relational and we want transactions and
referential integrity. Postgres specifically is chosen over other relational engines because of one
decisive advantage for Vitae: the pgvector extension lets Postgres store and search embedding
vectors inside the same database, so M7's similarity search needs no separate vector database. On
top of that, Postgres offers JSONB for the semi-structured fields and has mature async drivers,
which the async request path (see deep dive 01a) needs so database calls do not block the event
loop.

In development, PostgreSQL runs locally via Docker Compose, so `docker compose up` gives every
machine and CI an identical database. The production database target (likely a managed Postgres) is
an M18 decision and is not made here.

## Consequences

- One store covers the relational core, the flexible JSON fields, and M7 vector search. We avoid
  standing up and syncing a second system for vectors until scale genuinely demands it.
- Docker enters the project now, but only to run the development database. This is a different thing
  from containerizing the application itself, which remains an M18 decision. Using Docker for a dev
  dependency does not commit us to a container deployment.
- We gain transactions and foreign-key integrity, which serve the correctness principle.
- The request path must use an async Postgres driver, so every query is awaited or offloaded (deep
  dive 01a). The specific driver and whether we use an ORM is an M3 decision.
- Local development now depends on a running Postgres. Docker Compose mitigates this: the dependency
  is declared once and started with one command, and CI uses the same image.

## Alternatives considered

- SQLite: zero-setup and excellent for fast tests, but weak on concurrent writes and it has no
  native production-grade vector search, so M7 would force a separate vector store. We may still
  choose it specifically for isolated unit tests; that is an M4 decision, not the primary datastore.
- MySQL or MariaDB: solid relational engines, but their vector support is less mature than pgvector,
  which would weaken the M7 story. Rejected for that reason.
- MongoDB (document): flexible schema, but weaker relational integrity and transactions, and less
  mature vector search. It fights the relational shape of the data rather than fitting it. Rejected.
- Managed Postgres (Supabase, Neon) for development: faster to start, but it adds a cloud account and
  network dependency to local dev and reduces reproducibility. We keep dev self-hosted via Docker and
  defer the managed/production choice to M18.
- A dedicated vector database (Pinecone, Qdrant) now: premature. pgvector keeps vectors in the one
  store we already run. We can revisit a dedicated vector store in M7 if scale requires it, and that
  is exactly where the vector ADR lives.
