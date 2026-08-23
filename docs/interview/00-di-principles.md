# 00 - Dependency injection principles (cross-cutting)

Not tied to one milestone. This is the model for where to inject, and how much.

## Two kinds of DI, used at different layers

Framework DI (`Depends`) lives at one layer only, the HTTP boundary. The router. That is the composition root, the layer that knows about the request. `Depends` is a request-scoped assembler.

Plain constructor injection lives everywhere below. Services, repositories. No framework, no magic. Pass what you need as an argument.

The repo already does this. The router receives `session` via `Depends`, then constructs the repository with it.

```python
# router = composition root, Depends assembles here
async def create_conversation(payload, user_id: CurrentUserId, session: SessionDep):
    conversation = await ConversationRepository(session).create(user_id, payload.title)
    #                                        ^ constructor injection: session passed in
```

When services arrive (M5+), the same shape extends down one more step.

```python
async def reflect(payload, session: SessionDep):
    repo = ConversationRepository(session)
    service = ReflectionService(repo, llm_client)   # inject repo + client into the service
    return await service.run(payload)
```

`Depends` at the edge, constructors underneath. Never put `Depends` inside a service. That couples the domain to FastAPI. A service has to be testable with no web framework in the room.

## Inject at seams, not at everything

DI costs indirection and ceremony. Pay it only where it buys something.

Inject when the implementation actually varies across environments, or between prod and test. Those are the seams.

- session/engine (prod DB vs test DB)
- external clients (LLM, HTTP, email), so tests mock them and nothing real gets spent
- config/settings
- non-deterministic sources (clock, uuid generator), if tests need to control them

Do not inject pure, deterministic logic. A model-to-schema mapper, a validator, a price calculator. Just call it. Wrapping a function that has one implementation behind an interface is all cost and no flexibility.

The test. Would I ever want a different implementation here, in prod or in a test? If yes, inject. If no, just write the code.

## The layering

```
router (Depends: session, current_user)     <- framework DI, composition root
  └─ service (constructor: repo, clients)    <- plain DI, pure domain logic
       └─ repository (constructor: session)  <- plain DI, hides the ORM
            └─ session                        <- the injected seam from M2
```

Each layer receives its dependencies. None reaches for a global. `Depends` only appears in the top box.

The repository is a seam of its own. It hides SQLAlchemy so the service depends on a narrow interface, not on `AsyncSession` internals. That is the swap point. Postgres to Mongo, or to an in-memory fake for tests.

## TypeScript bridge

`Depends` at the router is like a NestJS controller with injected providers, or a tRPC/Express handler that pulls from a request-scoped context. Constructor injection below is the same as TS. `new Service(repo, client)`. What you avoid in both languages is the module-global singleton (`export const db = connect(env.URL)`), which binds at import time and fights tests.
