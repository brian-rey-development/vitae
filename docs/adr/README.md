# Architecture Decision Records

An ADR is a short record of a hard-to-reverse choice. It says what forced the decision, what we picked, and what we gave up. If someone later asks why the system is built this way, the answer should be here.

## When to write one

Write one when any of these is true.

- The decision is expensive or painful to reverse (database, framework, auth, provider).
- It rules out an alternative someone would otherwise try.
- It changes the shape of the code across many modules.

Skip it for local, reversible choices. A variable name or where a helper lives does not need an ADR.

## Format

Copy `0000-template.md`, number it sequentially, and keep it to about a page. Status moves from Proposed to Accepted, and to Superseded if a later ADR replaces it.

## Write it when the problem is real

Do not pre-commit to a datastore, vector search, an ORM, or an LLM provider. Write those ADRs in the milestone where you actually need the choice.

## Index

Accepted

- 0001 - Use uv as the single Python toolchain
- 0002 - Domain-first module structure
- 0003 - Monorepo with a FastAPI API and a Next.js web app
- 0004 - PostgreSQL as the datastore, run locally via Docker
- 0005 - SQLAlchemy 2.0 async ORM and Alembic for persistence and migrations
- 0006 - Hexagonal architecture (ports and adapters) per module

Still open. Each one gets decided in its milestone.

- LLM provider (M5)
- Similarity and vector search approach (M7)
- External data sources and isolation (M9)
- Background processing and queue approach (M12)
- Safety posture and medical disclaimers (M17)
- Authentication strategy (M18)
- Deployment targets for API and web (M18)
