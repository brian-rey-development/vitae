# Deep dive 01a - Async, ASGI, and the event loop

This is a from-scratch, senior-depth treatment of the async model FastAPI is built on. It assumes
no prior async knowledge and ends where a senior engineer should be able to reason. Anchor code is
Vitae's own `health/router.py`. Read in order; each section builds on the last.

Interview framing: if you can explain concurrency vs parallelism, the event loop, what `await`
actually does, the GIL, WSGI vs ASGI, and the sync-in-async footgun, you can answer almost any
async question by deriving it rather than reciting.

---

## 1. The root distinction: concurrency vs parallelism

These are different and interviewers probe the gap.

- **Parallelism**: multiple things executing at the same physical instant. Needs multiple CPU
cores. Four cores can run four computations literally simultaneously.
- **Concurrency**: multiple things making progress over a span of time by interleaving, possibly on
  a single worker. One cook cooking three dishes: start the pasta water, and *while it heats*, chop
  vegetables, then *while they saute*, plate the salad. The cook never does two actions in the same
  instant, but all three dishes progress because the cook fills waiting time with other work.

A web server is the cook. **Most of a request's lifetime is spent waiting on other systems (the
database, an LLM API, the network), not computing. Waiting is not CPU work. So to serve many slow
requests you do not need parallelism (more cores), you need concurrency: a way to start a wait,
set that request aside, and progress another until the wait completes.**

**Async is Python's mechanism for concurrency-during-waiting on a single thread.** Keep this exact
sentence: *async makes waiting cheap, it does not make computation fast.* **It does nothing for
CPU-bound work; it is everything for I/O-bound work.**

Node mapping: this is exactly Node's model. `await fetch(url)` does not freeze the Node process; it
yields so the loop can serve other work, then resumes when the response arrives. Python's asyncio is
the same idea, made explicit with `async`/`await`.

---

## 2. I/O-bound vs CPU-bound (why this is the whole game)

- **I/O-bound**: ++the task spends its time waiting on input/output from something external. A DB
  query, an HTTP call to an LLM, reading a file, a vector search over the network.++ The CPU is idle
  during the wait.
- **CPU-bound**: the ++task spends its time computing. Hashing, image resizing, a big sort, running a
  local model on CPU. The CPU is busy the whole time.++

> **Async wins only for I/O-bound concurrency, because the trick it exploits is "give the loop**  
> **control during the wait." A CPU-bound task has no wait to give back; it just hogs the thread.**

Vitae is overwhelmingly I/O-bound: every interesting operation (extract structure via an LLM,
embed text, query the datastore, fetch external literature) is a network wait. That is precisely
why FastAPI's async model is the right foundation, and it is the honest first-principles answer to
"why FastAPI" beyond "it's popular."

---

## 3. Why not just use threads? (and the GIL, explained properly)

Obvious objection: Python has threads. Give each waiting request a thread and let it block.

**Cost problem.** An OS thread carries a stack (often ~1 MB) and the OS must context-switch between
threads (save/restore registers, cross into the kernel, thrash CPU caches). Hundreds of threads is
heavy; hundreds of thousands is impossible. A coroutine (async's unit of work) costs a few KB and
switches in userspace without involving the OS scheduler. Async scales to tens of thousands of
concurrent waits on one thread; threads do not.

**The GIL (Global Interpreter Lock).** CPython has a single global lock that allows **only one
thread to execute Python bytecode at a time**. It exists because CPython's memory management
(reference counting) is not thread-safe without it, and the GIL is the simple, fast way to protect
that.

Consequences you must be able to state:

- Python threads give you **no parallelism for pure-Python CPU work**. Two threads both crunching
  numbers take turns holding the GIL; you do not get 2x on 2 cores, you get ~1x plus overhead.
- Python threads **do** help for I/O, because the GIL is **released during blocking I/O syscalls**
  (and inside many C extensions). While a thread waits on the network, it holds no GIL, so another
  thread can run. So threads are a *valid* concurrency tool for I/O, just an expensive one.
- Async sidesteps the GIL fight entirely for I/O: one thread, one loop, no lock contention, no
  thread-switch overhead. That is why it scales better for the "many concurrent waits" workload.
- For real CPU **parallelism** in Python you use **multiple processes** (each has its own
  interpreter and its own GIL), not threads. This returns in section 11 (uvicorn workers).

Note: recent CPython has an experimental "free-threaded" no-GIL build, but assume the GIL exists in
an interview unless told otherwise, and reason from it.

---

## 4. The event loop (the engine)

![](https://cdn.hackersandslackers.com/2021/04/async_eventloop.jpg)

The event loop is a single thread running, in effect, this loop forever:

1. Look at the set of tasks that are **ready to run** (not waiting on anything).
2. Run one until it either finishes or hits an `await` on something not yet ready.
3. When a task `await`s I/O, register that I/O with the OS and **park** the task (remove it from
   ready).
4. Ask the OS "which of my registered I/O operations are now ready?" using an efficient syscall
   (`epoll` on Linux, `kqueue` on macOS, IOCP on Windows). This is how one thread watches thousands
   of sockets without polling each.
5. For each ready I/O, move its parked task back to the ready set.
6. Repeat.

The key insight: ++the loop never *waits* on any single I/O. It hands all waiting to the OS and only
runs tasks that can make progress right now. One thread, thousands of in-flight waits, near-zero
idle. This is what "async server" means mechanically.++

---

## 5. Coroutines and `await` (what the keywords actually do)

`async def` does not define a normal function. **Calling it do es not run the body; it constructs
and returns a coroutine object, a resumable, pausable computation. Nothing happens until
something *drives* it (the event loop, or** `await`**).**

```python
async def f():
    print("running")

c = f()          # prints NOTHING. c is a coroutine object, body not executed.
await c          # NOW the body runs. (or asyncio.run(f()) at top level)
```

Node mapping: an `async` function in JS returns a Promise and the body runs eagerly; Python is
*lazier*, the coroutine does not start until awaited/scheduled. Do not carry the JS intuition that
calling starts it.

**What `await x` does**, step by step:
1. It requires `x` to be awaitable (a coroutine, Task, or Future).
2. It runs `x` until `x` itself needs to wait on I/O.
3. ++At that point the current function **suspends** at the++ `await` ++line, and **yields control back
   to the event loop**, along with a note: "resume me when this I/O is ready."++
4. The loop is now free to run other ready tasks.
5. When the I/O completes, the loop resumes this function right after the `await`, with the result.

So `await` is a **suspension point**: the one place a coroutine can be paused and the loop can jump
elsewhere.

**Cooperative scheduling (the crucial property).** Between two `await` points, your code runs to
completion **without interruption**. The loop can only switch tasks *at* an `await`. This is
"cooperative" multitasking: each task must voluntarily yield (by awaiting) to let others run. It is
the opposite of OS threads, which are **preemptive** (the OS can pause a thread mid-instruction at
any time).

This single property is the source of both async's efficiency (no locking needed between awaits,
because nothing else runs in that gap) and its biggest footgun (section 9).

---

## 6. WSGI vs ASGI (the server protocols)

A Python web app talks to its server through a standard interface.

**WSGI** (Web Server Gateway Interface): the classic sync standard. The app is a callable
`app(environ, start_response)`. It is fundamentally **one request, one thread, blocking, then
return a response**. It has no concept of an async handler, and no clean way to hold a long-lived
connection open. Flask (classic), Django (classic), served by gunicorn/uWSGI.

**ASGI** (Asynchronous Server Gateway Interface): the async successor. The app is an async callable
`app(scope, receive, send)`:
- `scope`: a dict describing the connection (type: http / websocket / lifespan, path, headers...).
- `receive`: an async callable to pull incoming events (request body chunks, websocket messages).
- `send`: an async callable to push outgoing events (response start, body chunks).

Why ASGI matters for Vitae specifically:
- It is **async-native**, so path operations can `await` I/O and the loop stays free.
- `receive`/`send` are **streaming** primitives: the response can be sent in chunks over time. This
  is what makes Server-Sent Events and token streaming (milestone M10, the live chat feel) possible
  and natural. WSGI cannot do this cleanly.
- It supports **websockets** and a **lifespan** protocol (startup/shutdown events), which the app
  factory hooks into (deep dive 01d).

Served by **uvicorn** (or hypercorn/daphne).

---

## 7. The layers: uvicorn -> Starlette -> FastAPI

FastAPI is not a monolith. Know the stack, interviewers ask "what is FastAPI actually":

- **uvicorn**: the ASGI **server**. It owns the event loop, speaks HTTP on the socket, and calls
  your ASGI app with `scope/receive/send`. (It often uses `uvloop`, a faster event-loop
  implementation written in Cython, as a drop-in for asyncio's default loop.)
- **Starlette**: the ASGI **toolkit/framework** FastAPI is built on. It provides routing, requests
  and responses, middleware, websockets, background tasks, and the lifespan handling. FastAPI's
  `APIRouter`, middleware, and streaming come from Starlette.
- **FastAPI**: adds, on top of Starlette, the developer-facing magic: **Pydantic** integration
  (request/response validation from type hints), the **dependency injection** system (`Depends`),
  and automatic **OpenAPI/Swagger** generation. FastAPI = Starlette (transport/routing) + Pydantic
  (validation) + DI + docs.

So our `GET /health` request path is: socket -> uvicorn (event loop, HTTP parse) -> FastAPI/Starlette
(route match, run the path operation, validate the `HealthStatus` response) -> back out through
uvicorn to the socket.

---

## 8. sync `def` vs async `def` in a FastAPI path operation

This is where the theory meets our code. FastAPI lets a path operation (and a dependency) be either
`def` or `async def`, and it runs them **differently**:

- **`async def`**: ++FastAPI awaits it **directly on the event loop**. Fast, zero thread overhead. The
  contract: you must not block, everything inside must be non-blocking / awaitable.++
- **plain `def`**: ++FastAPI assumes it may block (it cannot know), so it runs it in an **external
  threadpool** (via anyio's++ `run_in_threadpool`++), keeping the event loop free. There is a bounded
  pool of worker threads (anyio default is 40). This is safe for blocking code but has thread
  overhead and a concurrency ceiling equal to the pool size.++

Our endpoint:

```python
@router.get("/health")
def health() -> HealthStatus:      # plain def
    return HealthStatus(status="ok")
```

It is a plain `def`, so FastAPI offloads it to the threadpool. That is correct and safe (though the
work is trivial). We wrote `def` and not `async def` deliberately: `health()` does no awaiting, and a
plain function is simpler. If later it needs to `await` the datastore, it becomes `async def` and we
`await` an async DB call.

Decision rule you can state in an interview:
- Endpoint does `await`-able async I/O (async DB driver, httpx async client, the LLM SDK's async
  methods) -> write `async def` and `await` it.
- Endpoint calls **blocking** libraries with no async version (a sync DB driver, a CPU task, a
  blocking SDK) -> write plain `def` and let FastAPI's threadpool absorb it.
- Never mix: never call a blocking function from inside `async def` without offloading it.

---

## 9. The footgun: blocking inside `async def` (the #1 FastAPI mistake)

From section 5: the loop can only switch tasks at an `await`. If an `async def` runs a **blocking**
call (something that does not yield to the loop), the single loop thread is stuck inside that call,
and **every other request stalls**, because there is no `await` at which to switch away.

```python
import time

@router.get("/slow")
async def slow():
    time.sleep(5)          # BLOCKING: freezes the event loop for 5 seconds
    return {"done": True}
```

While `time.sleep(5)` runs, no other request progresses, not even `/health`. You have converted a
concurrent server into a one-at-a-time server for those 5 seconds. Under load, throughput collapses.

The same happens with any blocking call inside `async def`: a synchronous DB query, `requests.get()`
(the blocking HTTP lib), reading a large file synchronously, or a heavy CPU loop.

**Fixes, in order of preference:**
1. Use the async version and await it: `await asyncio.sleep(5)`, `await async_db.execute(...)`,
   `httpx.AsyncClient` instead of `requests`.
2. If no async version exists, make the endpoint a plain `def` so FastAPI runs the whole thing in
   the threadpool.
3. Offload just the blocking part from async code: `await asyncio.to_thread(blocking_fn, args)` (or
   Starlette's `run_in_threadpool`). This hands the blocking work to a thread and awaits it, keeping
   the loop free.

Interview soundbite: *"Inside `async def`, everything you call must be non-blocking. A blocking call
freezes the single event-loop thread and stalls all concurrent requests. Fix it with an async
library, a plain `def` endpoint, or `asyncio.to_thread`."*

---

## 10. CPU-bound work blocks the loop too

Subtlety many miss: the problem is not "sync calls," it is **not yielding**. A pure-Python CPU loop
inside `async def` (no I/O at all) also freezes the loop, because it never hits an `await`:

```python
@router.get("/hash")
async def hash_it():
    total = 0
    for i in range(10_000_000):   # CPU-bound, no await -> loop frozen the whole time
        total += i
    return {"total": total}
```

And because of the GIL, moving it to a thread does **not** give you parallelism for the CPU part.
Correct handling of CPU-bound work: offload to a **process** pool (`ProcessPoolExecutor` via
`loop.run_in_executor`, or a task queue with worker processes, which is exactly milestone M12). Each
process has its own GIL and can use a real core.

Full mental table:

| Work type          | Inside `async def` directly | Correct handling                              |
|--------------------|-----------------------------|-----------------------------------------------|
| async I/O          | Fine: `await` it            | `await` the async call                        |
| blocking I/O       | BAD: freezes loop           | plain `def` endpoint, or `asyncio.to_thread`  |
| CPU-bound          | BAD: freezes loop           | process pool / task queue (M12)               |

---

## 11. Scaling out: uvicorn workers and real parallelism

++One event loop uses one CPU core. To use a multi-core machine you run **multiple worker processes**,
each with its own event loop and its own GIL:++ `uvicorn --workers 4` ++(or gunicorn managing uvicorn
workers). Now four cores serve requests in true parallel, and within each worker the event loop
gives high I/O concurrency. This is the standard production shape: N workers (parallelism across
cores) x async concurrency (many waits per worker).++

Implication for state: ++because workers are separate processes, in-memory state is **not shared**
between them. Anything that must be shared (cache, sessions, rate-limit counters) lives in an
external store (Redis, the database), not a module-level dict. This is a common production bug and a
good interview point.++

`fastapi dev` (what our DoD uses) runs a single worker with hot reload, for development only.
Production uses multiple workers and no reload.

---

## 12. Vitae-specific consequences (where this bites us later)

- **M2 datastore**: we must pick an **async** driver (e.g. an async database library), or every
  query becomes a blocking call we have to offload. The async model pushes the whole stack to be
  async end to end.
- **M5 LLM calls**: these are long I/O waits (hundreds of ms to seconds). They must be `await`ed
  async calls so one slow generation does not stall other users. This is the strongest case for
  async in the whole app.
- **M10 streaming**: SSE/token streaming is only clean because ASGI's `send` is a streaming
  primitive. WSGI could not do the live one-minute-chat feel.
- **M12 pipeline/workers**: heavy or CPU-bound work (embedding batches, enrichment) is pushed to
  worker **processes**, off the request path and off the event loop, for both responsiveness and
  real parallelism.

---

## 13. The live experiment (measured, not asserted)

We proved section 9 instead of trusting it. Two endpoints with an identical body, differing by one
keyword, plus a fast `/health`. `time.sleep(1)` is the stand-in for any blocking call (a sync DB
driver, `requests.get`, a large synchronous file read).

```python
import time
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/slow-async")
async def slow_async():
    time.sleep(1)   # BLOCKING inside async def -> runs ON the loop thread, no yield
    return {"done": "async"}

@app.get("/slow-sync")
def slow_sync():
    time.sleep(1)   # same call, but plain def -> FastAPI offloads it to the threadpool
    return {"done": "sync"}
```

A client fired 5 concurrent slow requests, waited 0.3s, then timed a single `/health` while the
server was buried. Measured results:

| Scenario                        | `/health` latency | 5-request batch total |
|---------------------------------|-------------------|-----------------------|
| idle baseline                   | 3.2 ms            | -                     |
| 5x blocking inside `async def`  | **4724 ms**       | **5.03 s** (serial)   |
| 5x blocking inside plain `def`  | **7.1 ms**        | **1.03 s** (parallel) |

How to read it:

- **`async def` (4724 ms, 5.03 s).** FastAPI trusted the `async` promise and put all 5 on the single
  loop thread. `time.sleep` never yields, so they ran one-at-a-time to completion: 5 x 1s = 5.03s.
  That serial total is the proof the loop was frozen (concurrent would be ~1s). `/health` queued
  behind the frozen loop and took 4.7s, a ~1500x blowup from its 3ms idle. FastAPI did not rescue
  us: there is no safety net inside `async def`.
- **plain `def` (7.1 ms, 1.03 s).** FastAPI offloaded each request to the threadpool, so all 5
  `time.sleep(1)` ran in parallel on separate threads (batch = 1.03s, not 5s). The event loop stayed
  free, so `/health` answered in 7ms, essentially idle speed. (Threads run concurrently here because
  `time.sleep`, like real blocking I/O, releases the GIL, section 3.)

One keyword flipped the server between 4724ms/serialized and 7ms/parallel. That is the whole lesson,
measured.

---

## 14. Real-world versions of the footgun and its fixes

`time.sleep` is a teaching stand-in. In a real service the blocking call is usually a database
driver or an HTTP client. Same trap, same fixes.

### The bug, with a synchronous DB driver

```python
import psycopg2  # a BLOCKING (synchronous) Postgres driver

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    conn = psycopg2.connect(DSN)          # blocking
    cur = conn.cursor()
    cur.execute("SELECT ... WHERE id=%s", (user_id,))  # blocking, no await -> freezes loop
    return cur.fetchone()
```

### The bug, with the blocking `requests` library

```python
import requests

@router.get("/enrich")
async def enrich(term: str):
    resp = requests.get(f"https://api.example.com/lookup?q={term}")  # blocking -> freezes loop
    return resp.json()
```

Both look harmless and pass every unit test (a single request is fine). They only fail under
**concurrency**, which is why they reach production. Under load the loop is pinned inside the
blocking call and every other request, including health checks, stalls.

### Fix 1 (best): use an async library and `await` it

The right answer for I/O is an async driver, so the wait actually yields to the loop.

```python
import httpx  # async-capable HTTP client

@router.get("/enrich")
async def enrich(term: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.example.com/lookup?q={term}")  # yields at await
    return resp.json()
```

```python
# DB: use an async driver / async SQLAlchemy session (the shape Vitae targets in M2)
@router.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.id == user_id))  # yields at await
    return result.scalar_one_or_none()
```

This is why M2's datastore choice must include an **async** driver: it keeps the whole request path
non-blocking end to end. A sync driver forces you into fix 2 or 3 on every query.

### Fix 2: if the library is only synchronous, make the endpoint plain `def`

Let FastAPI put the whole thing in the threadpool. Note the endpoint is no longer `async`.

```python
@router.get("/users/{user_id}")
def get_user(user_id: int):          # plain def -> threadpool, blocking is safe here
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT ... WHERE id=%s", (user_id,))
    return cur.fetchone()
```

### Fix 3: keep `async def` but offload just the blocking call

When the endpoint is mostly async but must call one blocking function, push that call to a thread and
`await` the result, keeping the loop free.

```python
import asyncio

@router.get("/report")
async def report(user_id: int):
    fresh = await fetch_prefs_async(user_id)                 # real async work stays on the loop
    rows = await asyncio.to_thread(legacy_sync_query, user_id)  # blocking call offloaded to a thread
    return {"prefs": fresh, "rows": rows}
```

`asyncio.to_thread(fn, *args)` (or Starlette's `run_in_threadpool`) runs `fn` on a worker thread and
gives you an awaitable, so the one blocking call no longer freezes the loop.

### Choosing between them

| Situation                                        | Fix                                   |
|--------------------------------------------------|---------------------------------------|
| An async version of the library exists           | Fix 1: `await` the async call         |
| Only a sync library exists, whole endpoint sync  | Fix 2: make the endpoint plain `def`  |
| Mostly-async endpoint with one blocking call     | Fix 3: `asyncio.to_thread` that call  |
| The blocking work is CPU-bound, not I/O          | Process pool / task queue (section 10)|

---

## 15. Interview questions you should be able to answer cold

1. Difference between concurrency and parallelism, with an example of each.
2. What is the event loop and how does it serve thousands of connections on one thread?
3. What does `await` actually do to the calling function?
4. Why does calling an `async def` "not run it"? What do you get back?
5. What is the GIL, and what does it mean for threads doing CPU work vs I/O work?
6. Why is async pointless for CPU-bound work, and what do you use instead?
7. WSGI vs ASGI, and one concrete thing ASGI enables that WSGI cannot.
8. In FastAPI, what is the difference between a `def` and an `async def` path operation?
9. Show a bug where a blocking call in `async def` tanks the server, and three ways to fix it.
10. How do you use all cores of an 8-core box with FastAPI, and what breaks about in-memory state
    when you do?

## 16. The one-paragraph summary to memorize

FastAPI runs on an ASGI server (uvicorn) whose single-threaded event loop serves many concurrent
requests by switching between them at `await` points, filling each request's I/O waiting time with
other work. `async def` endpoints run on that loop and must never block; plain `def` endpoints are
offloaded to a threadpool so blocking is safe. Async makes *waiting* cheap, not computation fast, so
it is ideal for an I/O-bound AI backend, while CPU-bound work and multi-core scaling need separate
*processes* because of the GIL.
