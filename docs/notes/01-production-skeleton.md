# 01 - Production skeleton

Milestone: M1. This note is me reconstructing why the FastAPI app is shaped the way it is.

My test for whether I actually understand the skeleton is simple: if I can defend every choice here from first principles, without hand-waving, then I get it. So instead of listing what exists, I reason through each decision.

## What we built

What runs today is a FastAPI app living at `apps/api`, laid out under `src/vitae/`. In one breath:

- domain-first vertical slices for the layout
- an app factory to boot it
- typed settings for configuration
- a single endpoint, `GET /health`

The whole thing passes ruff and ty clean. There is no datastore yet. That is deliberately deferred to M2, to be decided from first principles at the point where I can feel the need for it rather than guessing up front.

The layout on disk looks like this:

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

The tree is worth reading as a claim about where things belong. Cross-cutting machinery (settings, the factory that assembles the app) sits in `core/`, while each feature gets its own folder next to it.

The root files are the toolchain's, and I unpack them at the end of this note. Everything below is me arguing for why the interesting pieces are where they are.

## The load-bearing ideas

### 1. The app factory instead of a module-level global

The obvious way to start a FastAPI app is to write `app = FastAPI()` at the top level of a module. It works, but it has two properties I don't want.

First, it runs at import time. The moment anything imports that module, the app is constructed, and any side effects baked into construction fire whether I wanted them or not. Second, it hardcodes exactly one global instance, so every consumer is implicitly coupled to that single object.

The alternative is an app factory: just a function that builds and returns the app, optionally taking an injected `settings` argument. That small shift buys three things that compound as the project grows.

**Testability.** Because construction is a function call, a test can build its own app wired to whatever configuration it needs:

```python
create_app(settings=test_settings)
```

That points at a throwaway config or a test database, with no monkey-patching of module globals. This is precisely the seam M4 will lean on when it needs to stand up an app against a test datastore.

**Explicit dependencies.** Everything the app needs flows in as an argument, so nothing is silently reached for from a module-level global. The whole construction of the app is one function you can read top to bottom.

**No import-time side effects.** Importing the module no longer opens connections or touches the network, because none of that work happens until you actually call the factory. Import becomes cheap and safe again.

Given all that, `main.py` stays tiny. It holds the single production instance:

```python
app = create_app()
```

The mental model I keep: the factory is the recipe, and `main.py` bakes exactly one cake for the server to serve.

### 2. Typed settings with pydantic-settings

Before I can explain the settings object, I should name the principle it serves: validate at the boundary.

Configuration enters the process as environment variables, which are untrusted strings coming from outside. Rather than let those raw strings leak into the codebase and get re-read and re-parsed everywhere, the idea is to parse and validate them once, at the edge, into a typed object the rest of the code can trust.

That is exactly what `Settings(BaseSettings)` does:

- reads configuration from environment variables and an `.env` file
- coerces each value into its declared type
- fails loudly if a required value is missing or has the wrong type

Downstream code then trusts `settings.debug: bool` directly, instead of reaching back into `os.environ` and re-parsing a string every time it needs the value.

Building that object is not free, and there's no reason to do it more than once, so `get_settings()` is wrapped in `@lru_cache`. The cache means the settings object is constructed a single time and reused on every subsequent call.

That same cached function doubles as the natural dependency-injection provider for FastAPI later on, via `Depends(get_settings)`. So the caching decision and the DI decision turn out to be the same decision.

The fail-fast behavior is the real payoff. A field with no default and no environment value crashes at startup, when the process is coming up and someone is watching, rather than at 2am on the first request that happens to need it.

In M1 every field has a default, so nothing is strictly required yet. But the pattern is already in place for when real secrets arrive: a database URL, an API key, anything whose absence should stop the server from booting at all.

### 3. Domain-first vertical slices (ADR-0002)

The organizing question for any codebase is what you group code by. The common default is to group by technical role: all routers together, all models together, all repositories together.

We do the opposite and group by feature, which is what "vertical slice" means. Each slice cuts top to bottom through the technical layers for one piece of the domain.

Concretely, `health/` owns its own router today. When `checkins/` arrives, it will own its router, its models, its schemas, and its repository together in one folder. The `core/` folder is reserved for genuinely cross-cutting concerns: settings, the app factory, and later things like the database and logging.

The discipline that makes this hold together is one rule: a domain never imports another domain's internals. The concrete payoff is that adding a feature means adding one folder, rather than threading an edit through five scattered files organized by layer.

### 4. Routers and response models give free, correct OpenAPI

The health endpoint returns a Pydantic model, `HealthStatus`, rather than a raw dict. That choice looks cosmetic but it's load-bearing, because declaring the return type lets FastAPI do three things it otherwise couldn't:

- validates the outgoing response against the schema on the way out, so the app can't accidentally return a shape that violates its own contract
- documents that shape in `/openapi.json` and renders it in `/docs` through Swagger UI
- hands the future generated TypeScript client (ADR-0003) a real type to consume, so the frontend inherits the backend's contract for free

One annotation is doing triple duty: editor help while writing, runtime validation while serving, and API documentation for consumers. It's the same "annotations have teeth" idea from note 00, except now it's operating at the HTTP boundary instead of inside the code.

## Tooling notes

A few pieces of the toolchain are worth understanding rather than just copying, because they map cleanly onto the JavaScript ecosystem I already know.

**Dependencies split like pnpm.** `uv add X` adds a runtime dependency and `uv add --dev X` adds a dev-only one, which is exactly the `dependencies` versus `devDependencies` distinction from `package.json`. Either way the dependency lands in `pyproject.toml` and gets pinned in `uv.lock`.

**The FastAPI install uses an extra:** `fastapi[standard]`. That extra pulls in uvicorn, the ASGI server that actually runs the app, along with the `fastapi` CLI. It's what makes `uv run fastapi dev ...` work with hot reload during development.

**One manifest configures everything.** Configuration for the quality tools lives inside `pyproject.toml` too, under `[tool.ruff]` and `[tool.ruff.lint]` for linting and formatting, and `[tool.ty.environment]` for type checking. Dependencies, lint, format, and types all in a single file to look at.

The loop I run on every change is three commands:

```bash
uv run ruff check          # linting
uv run ruff format --check # formatting
uv run ty check            # types
```

All three have to be clean before I'll call a milestone done.

## Interview self-check

- Why a factory instead of `app = FastAPI()` at module scope? (side effects, testability, DI)
- Where is the boundary in this skeleton, and what validates it? (env -> Settings; response ->
  HealthStatus)
- What does `@lru_cache` on `get_settings` buy, and how does it connect to FastAPI DI?
- Why return a Pydantic model from the route instead of a dict?
- What is the difference between `pyproject.toml`, `uv.lock`, and `.python-version`, and which one
  makes a deploy reproducible? (callback to note 00: lockfile reproduces, uv pins Python)
