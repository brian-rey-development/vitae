# 01 - Production skeleton

Milestone: M1. This note reconstructs why the FastAPI app is shaped the way it is. If I can defend
every choice here from first principles, I understand the skeleton.

## What we built

A running FastAPI app at `apps/api`, in a `src/vitae/` layout, organized as domain-first vertical
slices, booted through an app factory, configured by typed settings, exposing `GET /health`, and
passing ruff + ty clean. No datastore yet (that is M2, decided from first principles when needed).

```
apps/api/
  pyproject.toml          project manifest + ruff/ty config (the package.json equivalent)
  uv.lock                 exact dependency tree (the pnpm-lock.yaml equivalent)
  .python-version         pins the interpreter (3.13), managed by uv
  .env / .env.example     runtime config; .env is git-ignored, .env.example is committed
  src/vitae/
    main.py               entrypoint: app = create_app()
    core/
      settings.py         typed config (pydantic-settings)
      app.py              create_app() factory: builds and wires the app
    health/
      router.py           GET /health -> {"status": "ok"}
```

## The load-bearing ideas

### 1. The app factory (`create_app()`), not a module-level global

The naive FastAPI app is `app = FastAPI()` at module top level. That runs side effects at import
time and hardcodes one global instance. Instead we use a factory: a function that builds and
returns the app, optionally taking injected `settings`.

Why it matters:
- **Testability.** A test can call `create_app(settings=test_settings)` to build an app wired to a
  throwaway config or a test database, without patching globals. This is the seam M4 will use.
- **Explicit over implicit.** Dependencies flow in as arguments. Nothing is reached for from a
  module global. The app's construction is one readable function.
- **No import-time side effects.** Importing the module does not open connections or read the
  network. Construction happens only when you call the factory.

`main.py` then holds the single production instance: `app = create_app()`. The factory is the
recipe; `main.py` bakes exactly one cake for the server to serve.

### 2. Typed settings with pydantic-settings

`Settings(BaseSettings)` reads config from environment variables and an `.env` file, coerces each
value to its declared type, and fails loudly if a required value is missing or the wrong type. This
is the "validate at the boundary" principle applied to configuration: env vars are untrusted
strings from outside the process, so they are parsed into a typed object at the edge, and the rest
of the code trusts `settings.debug: bool` rather than re-reading and re-parsing `os.environ`.

`get_settings()` is wrapped in `@lru_cache` so the settings object is built once and reused. That
cached function is also the natural dependency-injection provider for FastAPI later
(`Depends(get_settings)`).

Fail-fast in practice: a field with no default and no env value crashes at **startup**, not at
2am on the first request that happens to need it. In M1 every field has a default, so nothing is
required yet; the pattern is in place for when secrets (a database URL, an API key) arrive.

### 3. Domain-first vertical slices (ADR-0002)

Code is grouped by feature, not by technical role. `health/` owns its own router. When `checkins/`
arrives it will own its router, models, schemas, and repository together. `core/` holds
cross-cutting concerns (settings, the app factory, later db and logging). A domain never imports
another domain's internals. Adding a feature is adding one folder, not editing five scattered ones.

### 4. Routers and response models -> free, correct OpenAPI

The endpoint returns a Pydantic model (`HealthStatus`) rather than a raw dict. Because the return
type is declared, FastAPI:
- validates the response against the schema on the way out,
- documents it in `/openapi.json` and renders it in `/docs` (Swagger UI),
- and gives the future generated TypeScript client (ADR-0003) a real type to consume.

The type annotation is doing triple duty: editor help, runtime validation, and API documentation.
Same "annotations have teeth" idea as note 00, now at the HTTP boundary.

## Tooling notes

- `uv add X` adds a runtime dependency; `uv add --dev X` adds a dev-only one. Same split as
  `dependencies` vs `devDependencies` in package.json. Both land in `pyproject.toml` and are pinned
  in `uv.lock`.
- `fastapi[standard]` is an extra that pulls in uvicorn (the ASGI server) and the `fastapi` CLI, so
  `uv run fastapi dev ...` works with hot reload.
- Config lives in `[tool.ruff]` / `[tool.ruff.lint]` and `[tool.ty.environment]` inside
  `pyproject.toml`. One manifest configures deps, lint, format, and type checking.
- The quality-gate loop for every change: `uv run ruff check` (lint), `uv run ruff format --check`
  (format), `uv run ty check` (types). All must be clean before a milestone is done.

## Interview self-check

- Why a factory instead of `app = FastAPI()` at module scope? (side effects, testability, DI)
- Where is the boundary in this skeleton, and what validates it? (env -> Settings; response ->
  HealthStatus)
- What does `@lru_cache` on `get_settings` buy, and how does it connect to FastAPI DI?
- Why return a Pydantic model from the route instead of a dict?
- What is the difference between `pyproject.toml`, `uv.lock`, and `.python-version`, and which one
  makes a deploy reproducible? (callback to note 00: lockfile reproduces, uv pins Python)
