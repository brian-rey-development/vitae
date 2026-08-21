# Deep dive 01c - Dependency Injection in FastAPI

Why this note exists: FastAPI's `Depends` is the mechanism behind almost every shared resource in this project. M2's DB session, M12's `current_user`, config from `get_settings`, they are all wired the same way. Once `Depends` clicks, all of them read the same.

Anchor code: `core/settings.py` (`get_settings`) and the request-scoped DB session we build in M2.

If you can explain what a dependency is, how `Depends` resolves it, request-scoped caching, `yield` dependencies for setup and teardown, and dependency overrides in tests, you own the topic.

Read top to bottom. Each section sets up the next.

---

## 1. What DI is, from first principles

A function needs things to do its job: config, a database session, the current user. There are only two ways it can get them, and the gap between those two ways is the whole subject of this note.

**The first way is to reach for them.** The function imports a global or builds what it needs itself:

```python
def handler():
    db = Database(GLOBAL_DSN)
    ...
```

This looks convenient, but it welds the handler to a concrete database, a specific global config, and a fixed construction order. You cannot test it without standing up a real database. You cannot swap the dependency for anything else, because the handler owns the decision of where its `db` comes from.

**The second way is to declare them.** The function states, in its own signature, what it needs, and something else becomes responsible for providing it:

```python
def handler(db = Depends(get_db)):
    ...
```

The handler no longer knows or cares where `db` comes from. It simply receives one. The act of providing has been lifted out of the function and handed to the framework.

That lifting has a name: **Inversion of Control**. The function does not control the acquisition of its dependencies; the framework does. DI is the specific technique of passing dependencies in rather than reaching for them, and it is engineering principle 3, explicit over implicit, made mechanical.

Why does this ceremony pay for itself? A handful of properties all fall out of that single inversion:

- **Testable.** The handler receives its dependencies instead of building them, so a test can hand it a fake `db` with no real database in sight (section 8 shows exactly this).
- **Explicit.** The needs are written into the signature, so a reader sees at a glance what the handler touches, instead of hunting the body for hidden imports.
- **Single responsibility.** Acquiring and releasing resources lives in the provider, not the handler, so the handler is left to do only its own job.
- **Lifecycle management.** The provider is free to set up and tear down a resource around the request (section 5).

These are not four separate features. They are four consequences of the same design choice.

TS mapping: if you know NestJS, this is its `@Injectable` / constructor injection, but function-based. If you know Express, a dependency is a bit like middleware that computes a value and hands it to the handler, except FastAPI resolves it by type among parameters and injects the return value directly.

---

## 2. `Depends`, where a dependency is just a callable

A FastAPI dependency is any callable, usually a plain function. You attach it to a parameter with `Depends`, and before your endpoint runs, FastAPI calls that callable and injects its return value into the parameter.

```python
from fastapi import Depends
from vitae.core.settings import Settings, get_settings

@router.get("/info")
def info(settings: Settings = Depends(get_settings)):
    return {"app": settings.app_name, "env": settings.environment}
```

Follow one request to `/info` through the machinery, step by step:

1. FastAPI sees the `settings` parameter is `Depends(get_settings)`.
2. It calls `get_settings()`.
3. It passes the returned `Settings` object as `settings`.
4. Your function body runs with a ready-to-use `settings`.

The endpoint never calls `get_settings()` itself and never imports a global. It declares "I need settings" and receives them. That is the entire core idea. Everything else in this note is refinement.

The modern syntax, preferred in the v2 era, uses `Annotated`. It lets you reuse the dependency as a type alias and avoids putting a call in the parameter default.

```python
from typing import Annotated

SettingsDep = Annotated[Settings, Depends(get_settings)]

@router.get("/info")
def info(settings: SettingsDep):
    ...
```

`SettingsDep` can now be reused across many endpoints, so the dependency wiring is declared once and referenced everywhere.

---

## 3. Dependencies can depend on dependencies (the graph)

A dependency is itself a normal function, so it can take `Depends` parameters of its own. FastAPI resolves the whole graph, deepest first.

```python
def get_settings() -> Settings: ...

def get_db_engine(settings: Annotated[Settings, Depends(get_settings)]):
    return create_engine(settings.database_url)          # M2 shape

def get_session(engine = Depends(get_db_engine)):
    ...

@router.get("/checkins")
async def list_checkins(session = Depends(get_session)):
    ...                                                  # session -> engine -> settings, all injected
```

FastAPI builds this dependency tree per request. To make `session` it first makes `engine`, and to make `engine` it first makes `settings`.

You compose small, focused providers instead of writing one large setup function that does everything. This is exactly how M2 wires the database: `get_session` depends on the engine, which in turn depends on settings.

---

## 4. Request scope and caching

Within a single request, the same dependency is often required in several places at once. The endpoint needs `settings`, and so do two of the other dependencies it pulls in.

Rather than run the provider three times, FastAPI calls it once and reuses that result for the rest of the request. This is per-request caching, controlled by `use_cache=True`, which is the default. The same dependency in the same request is computed once and shared; a different request computes it fresh.

Why does this matter? It becomes concrete with a database session, which has two demands that seem to pull in opposite directions:

- It must be the **same** session everywhere within one request, so every query runs inside one shared transaction.
- It must be a **new** session for each request, so concurrent requests stay isolated from one another.

Per-request caching gives you both at once: shared within, fresh between. On the rare occasion you genuinely need a new instance each time even inside a single request, you opt out with `Depends(dep, use_cache=False)`.

Note that `get_settings` is also wrapped in `@lru_cache` (deep dive 01b), which makes settings effectively a process-wide singleton. That is a second, coarser cache sitting on top of request scope, and for configuration a singleton is precisely what you want.

---

## 5. `yield` dependencies, for setup and teardown around the request

This is the most important pattern for resources. A dependency can `yield` its value instead of `return`ing it. The code before the `yield` is setup, and the code after it runs as teardown, after the response has been sent.

```python
async def get_session():
    session = SessionFactory()          # setup: acquire
    try:
        yield session                   # this is injected into the endpoint
    finally:
        await session.close()           # teardown: always released, even on error
```

FastAPI runs the setup, injects the yielded value, runs your endpoint, and then resumes the dependency after the `yield` to clean up. The `try/finally` is what guarantees the resource is released even if the endpoint raises partway through.

This is the standard shape for anything that must be opened and then reliably closed once per request: database sessions (M2), files, network clients. It is the DI answer to the question "where does connection lifecycle live?" The answer is not in the handler, but in a `yield` dependency wrapped around it.

The generator mechanism underneath all of this, how `yield` suspends and resumes a function and how it relates to context managers, is covered in its own note, `01e-generators-and-context-managers.md`, if you want to go deeper on why a single function can pause in the middle and pick up again later.

Ordering follows the same rule as nested `with` blocks. For a given request the setups run outermost-in, and the teardowns run in reverse, innermost-out.

---

## 6. Dependencies that take parameters, and class dependencies

A dependency can declare its own request parameters, and FastAPI will parse them straight from the request. This is common for shared query parameters like pagination, where several endpoints want the same parsing and clamping logic.

```python
def pagination(limit: int = 20, offset: int = 0) -> dict:
    return {"limit": min(limit, 100), "offset": offset}

@router.get("/checkins")
async def list_checkins(page: Annotated[dict, Depends(pagination)]):
    ...                                    # ?limit=50&offset=0 parsed and injected
```

A class works as a dependency too, because a class is callable through its constructor, and FastAPI injects the resulting instance. This is the better fit when the dependency carries several related parameters or exposes methods, since the instance gives you a natural place to hold that state.

```python
class Pagination:
    def __init__(self, limit: int = 20, offset: int = 0):
        self.limit = min(limit, 100)
        self.offset = offset

@router.get("/checkins")
async def list_checkins(page: Annotated[Pagination, Depends(Pagination)]):
    ...
```

---

## 7. Dependencies for cross-cutting concerns (auth, guards)

A dependency does not have to return a value you go on to use. It can exist purely for its side effect or its check.

This is how authentication works in M12. A `current_user` dependency reads the token, verifies it, and then either returns the user or raises `HTTPException(401)`, which short-circuits the request before the endpoint body ever runs.

```python
async def current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    user = decode_and_verify(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@router.get("/me")
async def me(user: Annotated[User, Depends(current_user)]):
    return user                              # only reached if auth passed
```

You can also attach dependencies whose return value you ignore entirely, purely to gate a route, through the route decorator's `dependencies=[Depends(verify_api_key)]`.

DI thus centralizes auth into one dependency, reused across every protected endpoint, instead of a check copied and pasted into each handler where it can drift out of sync.

---

## 8. The testability payoff, through dependency overrides

This is where DI earns its keep, and it is the M4 foundation. FastAPI lets a test replace any dependency with a fake, application-wide, through `app.dependency_overrides`.

```python
def fake_settings() -> Settings:
    return Settings(environment="development", debug=True)

app.dependency_overrides[get_settings] = fake_settings
# now every endpoint that Depends(get_settings) receives the fake, no env needed
```

For the DB session, the override swaps the real session for one bound to a throwaway test database or a rolled-back transaction (M4). Because handlers receive their session by injection, the test can substitute it without touching a line of handler code.

Had the handler reached for a global instead, this would be impossible without monkeypatching. DI is what makes the application testable by construction rather than testable only after a fight.

---

## 9. Gotchas and interview questions

A few sharp edges are worth internalizing before they bite you.

- **Pass the callable, not its result.** You write `Depends(get_x)`, not `Depends(get_x())`. You pass the callable and let FastAPI call it; passing the result of calling it is one of the most common DI bugs.
- **DI only runs where FastAPI is in charge.** It resolves values for endpoint parameters and other dependencies, nothing more. Call your endpoint function directly in a unit test and you bypass the graph entirely, so nothing gets injected. Test through the app or a test client so the graph actually resolves.
- **Teardown runs after the reply is gone.** In a `yield` dependency, the teardown code runs after the response has already been sent, so raising there cannot change what the client received. Handle and log errors in teardown deliberately.
- **The cache keys on the callable object.** Following from section 4, two different wrapper functions that do the same work are cached separately. If you want two call sites to share the cached value, they must reference the same dependency callable.
- **Match the flavor to the work.** Tying back to deep dive 01a, a sync `def` dependency runs in the threadpool while an async one runs on the event loop, the same rule that governs endpoints. A blocking call inside an `async def` provider blocks the loop for everyone.

Interview questions:
1. What problem does DI solve, and what is "inversion of control"?
2. Mechanically, what does `Depends(get_db)` do before your endpoint runs?
3. What is request-scoped caching and why is it exactly right for a DB session?
4. What is a `yield` dependency and why is `try/finally` around the `yield` important?
5. How do you swap a real dependency for a fake in a test, and why is that impossible with globals?
6. How does DI centralize authentication across many endpoints?
7. Why `Depends(get_x)` and not `Depends(get_x())`?

## 10. The one-paragraph summary to memorize

FastAPI dependency injection lets an endpoint declare what it needs (settings, a DB session, the current user) as parameters wrapped in `Depends(provider)`; before the endpoint runs, FastAPI calls each provider, resolving a whole dependency graph deepest-first, caches each provider once per request, and injects the results. Providers can `yield` to set up and reliably tear down resources around the request (the standard shape for DB sessions), can gate requests by raising (auth), and can be overridden wholesale in tests, which is what makes the app testable by construction instead of welded to globals.
