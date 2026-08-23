# 0004 - PostgreSQL as the datastore, run locally via Docker

- Status: Accepted
- Date: 2026-08-21

## Context

M2 needs a datastore before any persistence code lands.

The data is longitudinal and relational. A user has many check-ins. Check-ins produce insights. Writes should be transactional, so a check-in and anything derived from it commit together or not at all. Some fields are semi-structured because LLM-extracted data does not have a fixed shape. M7 ("find people like you") needs similarity search over embedding vectors.

We also have to pick where the database runs in development. How we talk to it (ORM, query builder, or raw SQL) and how we migrate are M3. This ADR only picks the store and where it runs locally.

## Decision

We will use PostgreSQL as the datastore, running locally via Docker Compose in development.

We want transactions and foreign keys. Postgres also has pgvector, so M7 embeddings can live in the same database instead of a separate vector store. JSONB covers the odd-shaped LLM fields. Async drivers exist for the request path.

Where production Postgres lives is an M18 decision.

## Consequences

One database covers relational rows, JSON fields, and vector search. We do not stand up a second system for embeddings unless scale later forces it.

Docker is in the project only to run the dev database. That is not a decision to containerize the app.

Local dev now needs Postgres running. Compose makes that one command, and CI uses the same image.

The request path has to use an async Postgres driver. The driver and whether we use an ORM are M3.

## Alternatives considered

SQLite needs no setup and is great for fast tests. Concurrent writes are weak, and there is no production-grade vector search, so M7 would need a second store. We might still use it for isolated unit tests. That is an M4 call, not the primary datastore.

MySQL and MariaDB are solid relational engines. Their vector support is behind pgvector, which would make M7 harder.

MongoDB is flexible, but weaker on relational integrity and transactions, and its vector search is less mature. The data is relational. A document store fights that.

A managed Postgres (Supabase, Neon) for development would start faster. It also adds a cloud account and a network dependency to local work, and it is less reproducible. Dev stays self-hosted. Production hosting waits for M18.

Standing up Pinecone or Qdrant now would be early. pgvector keeps vectors in the store we already run. M7 is the time to reopen that if scale requires it.
