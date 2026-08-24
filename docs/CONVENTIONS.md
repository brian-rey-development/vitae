# Vitae API - Code Conventions

The goal is code that reads as if one person wrote it: predictable, simple, and boring in the best
way. A new module should look like every existing module. When in doubt, copy the exemplar (the
`conversations` module) and change the names.

These are the judgment rules that tooling cannot enforce. The floor (formatting, lint, types) is
enforced automatically by `ruff` and `ty`; this document is the ceiling.

Enforcement ladder: prefer making a rule **impossible** (types, structure) over **automatic**
(lint, CI) over **reviewed** (PR) over **documented** (this file). If a documented rule keeps
getting broken, promote it up the ladder instead of restating it.

## Architecture: hexagonal, per module

Each domain is a vertical slice built as a hexagon (ports and adapters). Dependencies point only
inward: `infra -> application -> domain`, and `infra` also implements the ports the domain declares.
The domain knows nothing about FastAPI, SQLAlchemy, or Pydantic, so it is testable with zero infra.

```
infra/http  ->  application  ->  domain  <-  infra/persistence
 (router,        (service,        (entities,    (ORM models,
  schemas)        use cases)       ports)        adapters, mappers)
```

## Where code lives

- **`src/vitae/`** is the importable application package (ships in the wheel).
  - **`core/`** is cross-cutting framework glue: `config` (all env vars), `database/` (the
    persistence package: `orm` = `Base` + column mixins, `engine`, `session` + `SessionDep`,
    `unit_of_work` = the `UnitOfWork` port and its `SqlUnitOfWork` adapter), `errors`, `auth`, the app
    factory (`app`), `lifespan`. `core/` never imports a module. Import persistence from the package
    surface (`from vitae.core.database import Base, SessionDep`), never a submodule path, so the
    internal file layout stays free to change.
  - **`modules/<domain>/`** is a hexagonal slice (see anatomy below).
  - **`health/`, `meta/`** are operational endpoints, not domains; they stay flat (a `router.py`).
  - **`scripts/`** holds management commands run with `python -m` (`seed`, `new_domain`).
- **`apps/api/` root** holds operational artifacts that must NOT ship: `alembic/` + `alembic.ini`,
  `docker-compose.yml`, `pyproject.toml`, `.env`, `tests/`. Migrations are operational, so they live
  here, never in `core/`.

## Anatomy of a module

```
modules/<domain>/
  domain/            # framework-free: stdlib + typing only
    entities.py      #   frozen dataclasses (the domain model)
    enums.py         #   domain enums
    constants.py     #   domain invariants (length limits, ...)
    ports.py         #   repository interfaces (typing.Protocol)
  application/
    services.py      #   the use cases; depends on ports + the UnitOfWork port only
  infra/
    http/
      router.py      #   endpoints + composition root (wires adapters into the service)
      schemas.py     #   Pydantic request/response
    persistence/
      models.py      #   SQLAlchemy ORM models (<Entity>Model)
      repository.py  #   Sql<Entity>Repository, implements the port
      mappers.py     #   ORM row <-> domain entity
```

A module never imports another module's internals. Cross-module references are by foreign key (table
name) only. Anything shared by two modules lifts into `core/`.

## The three representations

The same concept appears in three shapes, and they stay separate:

- **Domain entity** (`Conversation`) - a frozen dataclass, the currency of the domain and
  application layers. It owns identity and time: the service generates the `id` (`uuid4`) and
  `created_at` (`datetime.now(UTC)`), so the database is storage, not the source of truth for those.
- **ORM model** (`ConversationModel`) - SQLAlchemy, storage only, in `infra/persistence`.
- **API schema** (`ConversationCreate` / `ConversationRead`) - Pydantic, the wire contract, in
  `infra/http`. A response never exposes an internal field (`user_id`) unless intended.

Mappers translate ORM <-> entity; the router maps entity -> schema with `model_validate`.

## Unit of Work: the service commits, never the router

The transaction boundary is an application concern. The service depends on the `UnitOfWork` port and
calls `await uow.commit()` after a mutation; it never imports `AsyncSession`. The SQLAlchemy
`SqlUnitOfWork` (in `core/database/unit_of_work.py`) is the adapter. The router's composition root wires the
session-bound repositories and the UoW into the service; endpoints just call the service.

## Naming

- A filename names the **responsibility** it holds, never a framework mechanic or a catch-all.
  Banned: `base.py`, `utils.py`, `helpers.py`, `common.py`, `misc.py`, and `types.py` as a junk
  drawer. The ORM foundation is `orm.py` (not `base.py`), even though the class inside stays `Base`
  (the SQLAlchemy idiom). If a file would need one of the banned names, its contents don't yet cohere
  into a concept - split them into files that do.
- Modules and packages are lowercase; domains are plural (`users`, `conversations`).
- Domain entity = the singular noun (`Conversation`). ORM model = `<Entity>Model`. Repository
  implementation = `Sql<Entity>Repository`. Application service = `<Entity>Service`.
- Ports are the plain interface name (`ConversationRepository`), a `typing.Protocol`.
- API schemas: `<Resource>Create` / `<Resource>Update` (requests), `<Resource>Read` (responses).
  Non-resource responses are named descriptively (`HealthStatus`, `MetaInfo`).
- Repository methods: `add`, `get`, `list_all`, `upsert`. Never name a method `list` - it shadows the
  builtin and `ty` then rejects `-> list[...]` return annotations.
- Factories are `create_<thing>`; accessors are `get_<thing>`. DI aliases are `PascalCase`
  (`SessionDep`, `CurrentUserId`, `ServiceDep`), defined once and imported, never re-inlined.
- Constants are `UPPER_SNAKE`, co-located in the domain that owns the invariant.
- One concept, one spelling, forever. It is `session_maker`, never `sessionmaker`.

## Routers

Thin: parse, call the service, return a schema. No business logic, no queries, no commits. Inject the
service through `ServiceDep`; reads map entity -> schema with `model_validate` (never return an ORM
object or an entity directly). Missing or unowned resources raise `NotFoundError` (404, never 403 -
do not reveal another user's resource exists). Every endpoint carries a one-line docstring; FastAPI
publishes it as the operation description in `/docs`, so the public API is documented by default.

## Validation, errors, robustness

- Validate untrusted input at the edge with Pydantic (`Field` constraints, `field_validator`), then
  trust the typed core. The LLM is just another untrusted boundary.
- Fail fast and loud: no silent fallback, no bare `except`. Errors raise `AppError` subclasses and
  render through the single error envelope.
- Derived values are computed, never stored (`age` from `date_of_birth`).
- Writes that can repeat are idempotent (profile `upsert` via `ON CONFLICT`).

## Async and database

- One session per request (`SessionDep`), `expire_on_commit=False`.
- No blocking calls in an async path. Timezone-aware datetimes only.
- Parameterized SQL only; no secrets in code, config comes from `core/config`.

## Migrations

- Autogenerate is a draft: reviewed by eye and corrected (Postgres enum types are not dropped by
  `drop_table`). Every migration has a working `downgrade`.
- Migrations are schema-only and run in every environment, so they never seed data. Dev fixtures live
  in a production-guarded script (`vitae/scripts/seed.py`).

## Testing

Tests mirror the architecture and the test pyramid. A test file is named after the source unit it
exercises and declares its tier with `pytestmark`.

```
tests/
  conftest.py                    # shared fixtures: rolled-back session, ASGI client
  unit/<module>/test_service.py         # fast, no I/O: service with fake ports
  integration/<module>/test_api.py      # real Postgres + ASGI app, per-test rollback
```

- **unit** (`pytestmark = pytest.mark.unit`) tests the application/domain with fake repositories and
  a fake UoW. No database, no HTTP. This is the payoff of hexagonal - run with `uv run pytest -m
  unit`.
- **integration** (`pytestmark = pytest.mark.integration`) drives the endpoints through the ASGI app
  against a throwaway `vitae_test` database. Each test runs in a transaction rolled back afterward
  (`join_transaction_mode="create_savepoint"`), so the app's real commits stay isolated.
- Add a `test_repository.py` under `integration/<module>/` only when a repository needs coverage the
  API path does not give (for example the atomic upsert).
- `health` and `meta` are modules like any other: `tests/integration/health/`, `.../meta/`.

From M4 on, no feature merges without tests.

## Simplicity

- YAGNI: build the current milestone's need, nothing speculative.
- Rule of three before extracting an abstraction. Delete dead code; no commented-out code.
- Functions stay small, do one job, use guard clauses over nesting, take no flag arguments.
- Default to zero comments; a comment explains a non-obvious *why*, never restates the code (endpoint
  docstrings are the one documented exception, since they are the public API contract).

## The exemplar and the generator

The `conversations` module is the reference implementation. Do not hand-write a new module; generate
it so it starts consistent by construction, tests included:

    uv run python -m vitae.scripts.new_domain <domain> [--entity <Entity>]

It creates `src/vitae/modules/<domain>/` (all layers) plus `tests/unit/<domain>/test_service.py` and
`tests/integration/<domain>/test_api.py`, runs `ruff` over the output, and prints the wiring steps it
leaves to you (register the router, add the `OPENAPI_TAGS` entry, register the model in
`alembic/env.py`, replace the placeholder field, generate the migration).

## Enforcement status

- Now: `ruff check`, `ruff format`, `ty` (no unjustified ignores), `pytest` (unit + integration). Run
  the full gate before every commit.
- Available: the domain scaffold generator, so a new module starts consistent and tested.
- To add: `import-linter` (encode the dependency rule above as CI contracts), `pre-commit` (run the
  gate locally on commit), and CI (the merge wall, formalized in M18).
