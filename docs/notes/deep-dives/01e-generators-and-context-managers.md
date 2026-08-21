# Deep dive 01e - Generators and context managers

Why this note exists: FastAPI's `lifespan` and the M2 database-session dependency both use `yield`
and something called an "async context manager." That machinery rests on two plain Python ideas,
generators and context managers. Once they click, `lifespan` stops looking like magic.

Read top to bottom. Each idea sets up the next.

## The problem they solve: borrow, then give back

A lot of code borrows a resource and has to give it back. Open a file, close it. Take a lock,
release it. Grab a DB connection, return it to the pool.

The catch is the "give back" has to happen even if the code in the middle crashes. The basic tool
for that is `try/finally`:

```python
f = open("data.txt")
try:
    do_something(f)      # might crash
finally:
    f.close()            # runs no matter what
```

This works, but writing it by hand every time is noise and easy to forget. Python has two nicer
tools built on top of it. Let's build up to them.

## Context managers and `with`

You've already used this:

```python
with open("data.txt") as f:
    do_something(f)
# f is automatically closed here, even if do_something crashed
```

An object that works with `with` is called a **context manager**. It just promises two things: run
some code when you *enter* the block, and run some cleanup when you *leave* it (including when you
leave by crashing). The `try/finally` is now hidden inside the object.

You could build one as a class with `__enter__` and `__exit__` methods, but that's clunky. There's
a lighter way, and it needs generators. So let's detour there first.

## Generators and `yield`

A normal function runs start to finish and then it's done. A **generator** is a function that can
**pause in the middle**, hand back a value, and later **resume** right where it left off, with all
its variables intact.

What makes a function a generator is the `yield` keyword:

```python
def counter():
    print("start")
    yield 1
    print("middle")
    yield 2
    print("end")

g = counter()   # nothing prints yet! you just get a generator object
next(g)         # prints "start", pauses at 'yield 1', hands back 1
next(g)         # prints "middle", pauses at 'yield 2', hands back 2
```

Read that carefully:

- Calling `counter()` runs **none** of the body. You get back a paused generator.
- Each `next(g)` runs until the next `yield`, then **freezes** right there.
- The next `next(g)` **unfreezes** it and continues from that exact spot.

So `yield` is a pause button that also spits out a value. (This is the same suspend-and-resume idea
as `await` from the async note. `await` yields to the event loop; `yield` yields to whoever is
looping. Same shape, different audience.)

For streaming lots of values, generators save memory (one at a time, on demand). But for us, the
useful bit is the pause: a generator can pause **once** in the middle, and that single pause is the
perfect line between "setup" and "cleanup."

## Putting them together: `@contextmanager`

Python gives you a decorator that turns a single-`yield` generator into a context manager. The rule
is dead simple:

- code **before** `yield` = setup (runs on enter)
- the value you `yield` = what `as x` gives you
- code **after** `yield` = cleanup (runs on exit)

```python
from contextlib import contextmanager

@contextmanager
def open_file(path):
    f = open(path)          # setup
    try:
        yield f             # hand f to the block, pause here
    finally:
        f.close()           # cleanup, even on crash
```

Now `with open_file("x") as f:` runs the setup, pauses and gives you `f`, runs your block, then
resumes the generator into the `finally` to close the file. You wrote the borrow-and-return logic
once, as a readable function.

## The async version (and finally, `lifespan`)

Everything above was synchronous. But sometimes the cleanup itself needs to `await` (closing an
async DB pool, say). A normal context manager can't `await`. So Python has async twins:

- an **async generator** is an `async def` with `yield` in it
- an **async context manager** is used with `async with`
- **`@asynccontextmanager`** turns an async generator into one, same before/after-`yield` rule

And that is exactly what FastAPI's `lifespan` is:

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("startup")   # before yield = runs once at boot
    yield                    # app serves requests during this pause
    logger.info("shutdown")  # after yield = runs once at shutdown
```

Here's the mental picture: FastAPI enters this context manager when it boots. It runs the setup up
to `yield`, then **pauses there for the entire life of the server**. Every request is served during
that one pause. When the server stops, FastAPI resumes past the `yield` and runs the cleanup.

The whole running life of your app is literally the single pause of one async generator.

(The return type `AsyncIterator[None]` just means "an async generator that yields nothing useful."
If it yielded a value, it'd be `AsyncIterator[str]` or similar.)

## The one idea to keep

`yield` splits a function into **setup / pause / cleanup**. That one idea shows up three times in
this project, all the same underneath:

- a plain **generator** (pause to hand back values)
- a **context manager** via `@contextmanager` (pause between setup and cleanup)
- FastAPI's **`lifespan`** and its **`yield` dependencies** (M2's DB session): setup before `yield`,
  cleanup after, scoped to the app or to one request

See it once and all three read the same way.

## Quick self-check

1. What do you get back when you *call* a generator function? (a paused generator, body not run)
2. What does `yield` do to the function? (pauses it, hands back a value, resumes there next time)
3. In `@contextmanager`, what runs on enter vs exit? (before `yield` vs after `yield`)
4. Why does `lifespan` need the *async* version? (its cleanup may need to `await`)
5. In one sentence: what is `lifespan`? (an async context manager whose single pause is the app's
   whole serving life)
