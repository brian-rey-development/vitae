# Deep dive 01d - Senior-level skeleton patterns

Four upgrades take the M1 skeleton from "runs" to "production-shaped," and one layering rule ties
them together.

Each section reasons from the problem outward: what breaks without the pattern, and why the pattern
is the right shape of answer. Anchor files live in `apps/api/src/vitae/`.

## Discipline note: what we deliberately left out

These four are the upgrades that genuinely belong to the *skeleton* itself. Several things you might
expect are missing on purpose, because each has its own milestone and gets an ADR when the moment
comes:

- structured logging with request IDs (M12)
- CORS for the frontend (Phase D)
- database readiness probes (M2)
- containerization with CI (M18)

Adding any of them now would be cargo-culting a feature ahead of the decision that justifies it, so
we hold off on purpose.

---

## 1. Application lifespan (startup and shutdown)

A server almost always needs to do some work exactly once when it boots, and some work exactly once
when it stops. At boot it might open a database pool, warm a cache, or verify a connection. At
shutdown it must close those resources cleanly so nothing leaks.

The real question is where that code can honestly live. Two obvious spots are both wrong:

- A **request handler** is wrong, because it would run on every request rather than once.
- **Import time** is wrong too: importing a module must never open sockets or reach out over the
  network (the reasoning is in deep dive 01b).

So we need a hook that fires once at the very start of the process and once at the very end, with the
request-serving phase in between.

FastAPI gives us exactly that with `lifespan`, an async context manager that wraps the whole
server's life. Everything before the `yield` runs once at startup, everything after it runs once at
shutdown, and the application serves requests during the `yield`.

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings
    logger.info("startup ...")          # setup: open pools, warm caches
    yield                               # <-- app serves requests here
    logger.info("shutdown ...")         # teardown: close pools
```

If the async-context-manager machinery here feels like magic, deep dive
`01e-generators-and-context-managers.md` in this same folder explains generators, `yield`, and
context managers from the ground up. `lifespan` is built directly on them, so that note is the piece
that makes this one click.

We wire the manager into the factory with `FastAPI(lifespan=lifespan)`. The shape is the same as a
`yield` dependency from deep dive 01c, only scoped to the entire application rather than a single
request, and this is precisely where M2 will open and close the database connection pool.

### Why `lifespan` replaced `on_event`

FastAPI once exposed `@app.on_event("startup")` and `@app.on_event("shutdown")` decorators. Those
are now deprecated, because they scatter the lifecycle across two separate functions that share no
scope. Whatever you open in the startup function you have to reach again, somehow, from the shutdown
function.

`lifespan` collapses both halves into one function. The resource you open before `yield` is the same
local variable you close after it, and the context-manager protocol guarantees the teardown actually
runs.

### Why `app.state`

The `app.state` reference in that snippet deserves a word of its own. It is a namespace for objects
that belong to the whole application.

We store `settings` on it so the lifespan (and later, middleware and dependencies) can read
app-scoped state without importing module-level globals. M2 will place the connection pool on
`app.state.db` in exactly the same way.

---

## 2. OpenAPI metadata and API versioning

An API's generated documentation is part of its contract, not a nicety bolted on afterward. A
default FastAPI app ships with no real title, version, or description, which means the OpenAPI
document it emits (and the client generated from that document, per ADR-0003) is effectively
anonymous.

We fix this by handing real metadata to the factory:

```python
FastAPI(title=..., description=..., version=settings.app_version, openapi_tags=OPENAPI_TAGS)
```

The `version` here is not a literal string. It is sourced from the installed package metadata via
`importlib.metadata.version("vitae")`, so the API version has a single source of truth in
`pyproject.toml` and cannot drift away from a hardcoded copy. `openapi_tags` attaches a description
to each tag, which is what groups the endpoints sensibly in `/docs`.

### Versioning is a promise, not a convenience

An API's URL shape is something clients build against. When that shape has to change in an
incompatible way, you cannot quietly break the callers who already depend on it.

The standard answer is to carry a version in the path, as in `/api/v1/...`. A `v2` can then be
introduced alongside `v1`, and clients migrate on their own schedule instead of yours. Retrofitting
versioning after clients already depend on unversioned URLs is painful, so the cheap move is to
establish it up front, while there are still zero clients to disrupt.

### The convention: which endpoints get a version

The convention draws a line between two kinds of endpoint:

- **Operational and infrastructure** endpoints such as `/health` stay **unversioned**, because load
  balancers and orchestrators probe them and they are not part of the product API contract. They
  should not move when product versions move.
- **Product** endpoints live under the **versioned** prefix, so `/api/v1/meta` today and
  `/api/v1/checkins` later.

The prefix is applied once to a `v1` router that aggregates the individual domain routers, which
means adding a new domain is a single `include_router` line rather than a change scattered across the
URL map.

---

## 3. Unified error handling

Without a deliberate policy, every failure in the system comes back shaped differently. FastAPI's
default validation error looks one way, an uncaught exception's 500 looks another, and a dict some
handler assembled by hand looks like a third thing entirely.

A client, and especially the generated frontend client, then has no uniform way to parse errors.
Worse, an uncaught exception can leak internal detail (stack traces, SQL fragments) straight into the
response body, which breaks the principle of failing loudly without leaking.

The answer is one typed error envelope backed by centralized exception handlers. It has a few moving
parts that fit together:

- **One shared response shape**, `{"error": {"code": ..., "message": ...}}`, expressed as a Pydantic
  model (`ErrorResponse`). `code` is a stable machine-readable string, `message` is meant for humans.
- **Expected failures** are modeled as subclasses of a base `AppError` exception, each carrying its
  own `status_code` and `code`. Domain code raises something like `NotFoundError` (404) or
  `ConflictError` (409), and a single handler turns any `AppError` into the envelope with the correct
  status.

```python
class AppError(Exception):
    status_code = 500
    code = "internal_error"

class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
```

Two more handlers finish the policy:

- One catches `RequestValidationError` so that invalid input comes back in the same envelope with a
  422, instead of FastAPI's default shape.
- The other is a catch-all `Exception` handler, and its behavior is the heart of the "fail loud, do
  not leak" rule. It logs the full traceback with `logger.exception` so nothing is ever swallowed
  silently (principle 5), then returns a generic 500 envelope carrying no internal detail at all. The
  failure is loud in the logs and safe in the response.

That split is really the whole point:

- **Expected failures** are the ones the code raises on purpose, where a missing check-in is simply a
  `NotFoundError`. They map cleanly onto their intended status codes.
- **Unexpected failures** are the ones nobody planned for. They fall through to the catch-all, get
  logged loudly, and return a safe generic message.

All of these handlers are registered in the factory through `register_error_handlers(app)`, so the
entire error policy is applied in one place.

---

## 4. Settings hardening

Three changes to `core/settings.py` push it from workable to production-shaped, building on the
settings work from deep dive 01b.

### `env_prefix="VITAE_"`

This namespaces every environment variable we read, so `VITAE_ENVIRONMENT`, `VITAE_DEBUG`, and
`VITAE_APP_NAME`.

The reason is collision avoidance. A bare `ENVIRONMENT` or `DEBUG` can clash with an unrelated
variable already set in a shell, a CI runner, or a container base image, and a prefix guarantees our
config only ever reads *our* variables. The cost is that the `.env` keys have to carry the prefix
too.

### `frozen=True`

This makes the settings object immutable once it has been constructed.

Configuration is read-only at runtime by nature, and freezing the object turns an accidental
`settings.debug = True` buried deep in the code into an immediate error rather than a silent,
hard-to-trace change in state. Combined with the `@lru_cache` singleton from before, this gives the
process a single immutable, shared, validated settings object.

### `app_version` from package metadata

Using `Field(default_factory=_package_version)` reads the version from the installed package
(ultimately `pyproject.toml`) instead of hardcoding it, so the API version, the package version, and
the OpenAPI version are all one value coming from one source.

---

## 5. The layering rule (why `core/` vs `api.py` vs the factory)

This is the structural principle that decides where files live, and it is worth being able to defend
out loud.

### `core/` is the foundation, and never imports a domain

`core/` holds domain-agnostic infrastructure: settings, errors, lifespan, and later the database and
logging.

The hard rule that makes the whole arrangement work is that `core/` must never import a domain.
Domains are allowed to depend on `core`, so a domain freely imports `core.settings`. But if `core`
were to import a domain back, that would be an import cycle. Keeping `core` strictly domain-free is
exactly what lets everything else depend on it safely.

### `api.py` is the composition layer

Above that sits `api.py` at the package root. It is the single place that imports every domain router
and wires them into the URL map, putting operational endpoints at the root and product endpoints
under `/api/v1`.

Because it imports domains, it cannot live inside `core/`. Instead it sits beside `main.py` as the
API's table of contents, where adding a domain is one line.

### `core/app.py` is the factory that delegates

Then there is `core/app.py`, the factory, which is infrastructure whose job is to assemble the
application. It applies the infrastructure pieces (lifespan, error handlers, metadata) and delegates
all route composition to `api.py` through `register_routers(app, ...)`.

So the factory itself imports no individual domain. It reaches the composition layer through a single
function and lets that layer do the domain wiring.

### Proving the invariant

You can verify the rule mechanically with a grep:

```bash
grep -r "from vitae.(health|meta|checkins)" src/vitae/core/
```

This should return nothing. If `core/` ever imports a domain, the layering has been violated and an
import cycle is probably close behind.

Reading the dependency direction from top to bottom, it runs `main.py` -> `core/app.py` (factory) ->
`api.py` (composition) -> domain routers -> `core/*` (infra). Infrastructure sits at the bottom and
points at nothing above it.

---

## 6. Interview questions

1. What is `lifespan` for, and why is it better than `on_event("startup")`?
2. Why must startup work not go at import time or in a request handler?
3. Why version an API in the path, and why keep `/health` unversioned?
4. How do you return a consistent error shape, and how do you avoid leaking internals on a 500
   while still not failing silently?
5. Difference between an expected failure (`AppError`) and an unexpected one, in handling terms?
6. Why `env_prefix` and `frozen=True` on settings? What does each prevent?
7. Why does `api.py` live at the package root while `app.py` lives in `core/`? (dependency direction)
8. How would you prove `core/` does not import a domain?

## 7. Summary paragraph

The senior skeleton adds four things the bare app lacked: a `lifespan` context manager for
once-per-process startup/shutdown (where M2's DB pool will live), real OpenAPI metadata plus path
versioning (`/api/v1`, health left unversioned) so the API contract is named and evolvable, a unified
typed error envelope with handlers that model expected failures as `AppError` and log-then-mask
unexpected ones, and hardened settings (`env_prefix`, `frozen`, version-from-package). They are held
together by one layering rule: `core/` is domain-agnostic infrastructure that never imports a domain,
`api.py` at the root is the single composition point that does, and the factory delegates route
wiring to it, so dependencies always point downward and no import cycle is possible.
