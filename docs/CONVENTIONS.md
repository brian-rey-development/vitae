# Vitae API - Code Conventions

The goal is code that reads as if one person wrote it: predictable, simple, and boring in the best
way. A new endpoint should look like every existing endpoint. When in doubt, copy the exemplar (the
`conversations` slice) and change the names.

These are the judgment rules that tooling cannot enforce. The floor (formatting, lint, types) is
enforced automatically by `ruff` and `ty`; this document is the ceiling.

Enforcement ladder: prefer making a rule **impossible** (types, structure) over **automatic**
(lint, CI) over **reviewed** (PR) over **documented** (this file). If a documented rule keeps
getting broken, promote it up the ladder (add a lint rule) instead of restating it.

## Where code lives

- **`src/vitae/`** is the importable application package. It ships in the built wheel.
  - **`core/`** holds cross-cutting *application* code: `settings`, `db`, `auth`, `errors`, the app
    factory, `lifespan`. `core/` never imports a domain.
  - **`<domain>/`** is a vertical slice (`users`, `conversations`, `health`, `meta`, ...).
  - **`scripts/`** holds management and dev commands run with `python -m` (`seed`, `new_domain`).
    They use the app, so they live in the package (typed, importable, testable).
- **`apps/api/` root** holds *operational artifacts* that must NOT ship in the package:
  `alembic/` + `alembic.ini` (migrations), `docker-compose.yml`, `pyproject.toml`, `.env`, `tests/`.

The dividing rule: application code that ships goes in `src/vitae/`; operational tooling and
generated artifacts go at the app root. Migrations are operational, so they live in
`apps/api/alembic/`, never in `core/`.

## Anatomy of a domain slice

Every domain is a folder with these files, same names everywhere:

- `models.py` - SQLAlchemy storage models, plus the domain's enums and constants.
- `schemas.py` - Pydantic API models (the wire contract).
- `repository.py` - persistence, one class per aggregate.
- `router.py` - HTTP endpoints.
- `service.py` - business logic, added only when there is logic beyond CRUD.

A domain never imports another domain's internals. Cross-domain references are by foreign key (table
name) or id only. Anything shared by two domains lifts into `core/`.

## Naming

- Modules and packages: lowercase; domains are plural (`users`, `conversations`).
- Storage models: the singular noun (`User`, `Conversation`, `Message`).
- API schemas: `<Resource>Create` and `<Resource>Update` for requests, `<Resource>Read` for a
  resource response. Responses that are not a resource are named descriptively (`HealthStatus`,
  `MetaInfo`), never with an `Output`/`DTO` suffix.
- Functions and variables: `snake_case`, intent-revealing. Booleans read as predicates
  (`is_production`, `had_birthday`).
- Factories are `create_<thing>` (`create_db_engine`, `create_db_session_maker`); accessors are
  `get_<thing>`.
- Dependency-injection aliases are `PascalCase` (`SessionDep`, `CurrentUserId`, `OwnedConversation`),
  defined once in the module that owns the dependency and imported everywhere. Never re-inline
  `Annotated[T, Depends(...)]` at a call site.
- Constants are `UPPER_SNAKE`, co-located with what they constrain (length limits live in
  `models.py`).
- One concept, one spelling, forever. It is `session_maker`, never `sessionmaker`.

## Repositories

One class per aggregate, constructed with a session: `ConversationRepository(session)`. Standard
method vocabulary, where parameters express the scope:

- `create(...) -> Entity`
- `get(id, ...) -> Entity | None` - by primary key; an extra owner argument makes it
  ownership-scoped and returns `None` when not owned.
- `list(...) -> list[Entity]`
- `upsert(...) -> Entity` - atomic create-or-update (`ON CONFLICT`).

Repositories `flush`, never `commit`. The router owns the transaction boundary.

```python
class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation_id: uuid.UUID, role: MessageRole, content: str) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self._session.add(message)
        await self._session.flush()
        return message
```

## Routers

Routers are thin: parse, call a repository or service, return a schema. No business logic, no raw
queries. Inject through the shared aliases. Reads map storage to API with `model_validate`; a router
never returns an ORM object. Writes call the repository, then `await session.commit()`, then return
the schema. Missing or unowned resources raise `NotFoundError` (404, never 403 - do not reveal that
another user's resource exists). Every endpoint carries a one-line docstring; FastAPI publishes it as
the operation description in `/docs`, so the public API is documented by default.

```python
@router.get("/{conversation_id}/messages")
async def list_messages(conversation: OwnedConversation, session: SessionDep) -> list[MessageRead]:
    messages = await MessageRepository(session).list(conversation.id)
    return [MessageRead.model_validate(m) for m in messages]
```

## Storage model vs API schema

The SQLAlchemy model is storage-only; the Pydantic schema is the wire contract. They are separate
classes and the router maps between them. Never expose an internal column (`user_id`, soft-delete
flags) unless it is deliberately part of the response.

## Validation, errors, robustness

- Validate untrusted input at the edge with Pydantic (`Field` constraints, `field_validator`), then
  trust the typed core. The LLM is just another untrusted boundary.
- Fail fast and loud: no silent fallback, no bare `except` that swallows. Errors raise `AppError`
  subclasses and render through the single error envelope.
- Derived values are computed, never stored (`age` from `date_of_birth`).
- Writes that can be repeated are idempotent (profile `upsert`).

## Async and database

- One session per request (`SessionDep`), `expire_on_commit=False` so attributes survive commit.
- No blocking calls in an async path.
- Timezone-aware datetimes only (`DateTime(timezone=True)`).
- Parameterized SQL only; no secrets in code, config comes from settings.

## Migrations

- Autogenerate is a draft, always reviewed by eye and corrected (for example, Postgres enum types are
  not dropped by `drop_table`).
- Every migration has a working `downgrade`.
- Migrations are schema-only. They run in every environment, so they never seed data. Dev fixtures
  live in a production-guarded script (`vitae/scripts/seed.py`).

## Simplicity

- YAGNI: build the current milestone's need, nothing speculative.
- Rule of three: do not extract an abstraction until the third repetition.
- Delete dead code immediately; no commented-out code.
- Functions stay small (about 20 lines), do one job, use guard clauses over nesting, and take no
  flag arguments (a boolean that switches behavior is two functions).
- Default to zero comments; a comment explains a non-obvious *why*, never restates the code.

## The exemplar

The `conversations` slice is the reference implementation. Adding a domain means copying it and
changing the names. If your code does not look like it, it either has a reason worth writing down or
it is wrong.

## Scaffolding a new domain

Do not hand-write a new slice; generate it so it starts consistent by construction:

    uv run python -m vitae.scripts.new_domain <domain> [--entity <Entity>]

This creates `src/vitae/<domain>/` (models, schemas, repository, router) from the exemplar, with a
placeholder `name` field and documented endpoints. It then prints the wiring steps it leaves to you:
register the router in `api.py`, add the `OPENAPI_TAGS` entry, and replace the placeholder field
before generating the migration.

## Enforcement status

- Now: `ruff check`, `ruff format`, `ty` (no unjustified ignores). Run the full gate before every
  commit.
- Available: a domain scaffold generator (`python -m vitae.scripts.new_domain`) so a new slice starts
  consistent by construction.
- To add: `import-linter` (encode the layering rules above as CI contracts), `pre-commit` (run the
  gate locally on commit), and CI (the merge wall, formalized in M18).
