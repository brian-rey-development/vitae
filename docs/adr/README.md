# Architecture Decision Records

An ADR captures one significant, hard-to-reverse decision: the context that forced it, the
choice we made, and the consequences we accept. It is a decision's paper trail. If a future
reader (including future-you, or anyone reviewing this portfolio) asks "why is it built this
way", the answer lives here, not in tribal memory.

## When to write one

Write an ADR when a decision meets any of these:

- It is expensive or painful to reverse (database, framework, auth model, provider).
- It rules out an obvious alternative someone would otherwise try.
- It affects the shape of the code across many modules.

Do not write one for reversible, local choices (a variable name, a helper's location).

## Format

We use a lightweight MADR-style format. Copy `0000-template.md`, number it sequentially, and
keep it short. A good ADR is one page. Status moves through: Proposed, Accepted, Superseded.

## Decisions are earned, not assumed

We only record a decision once we have hit the problem it solves and weighed the alternatives.
We deliberately do not pre-commit to a datastore, a vector search approach, an ORM, or an LLM
provider up front. Those ADRs get written in the milestone where the need is real, so the
reasoning reflects understanding rather than habit.

## Index

Accepted:

- 0001 - Use uv as the single Python toolchain
- 0002 - Domain-first module structure
- 0003 - Monorepo with a FastAPI API and a Next.js web app

Open questions, each to be decided in its milestone after considering alternatives:

- Data persistence and datastore choice (M2)
- Schema change and migration approach (M3)
- LLM provider (M5)
- Similarity and vector search approach (M7)
- External data sources and isolation (M9)
- Background processing and queue approach (M12)
- Safety posture and medical disclaimers (M17)
- Authentication strategy (M18)
- Deployment targets for API and web (M18)

These are named as questions, not answers. The technology is chosen when we get there.
