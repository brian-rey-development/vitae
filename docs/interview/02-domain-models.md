# 02 - Domain models, persistence and transactions (M3)

Interview questions on the conversation-core domain. Models, repositories, transaction boundaries, and the storage-vs-API split. Each entry is the question, what I said, the feedback, and the correct answer.

---

## Q4 - flush vs commit, and why the repository flushes but the caller commits

### Question

In `conversations/repository.py`, `create` and `add_message` call `session.flush()` and return, never `commit()`. Only the router calls `session.commit()`.

1. Difference between `flush()` and `commit()`.
2. Why does the repo flush and the caller commit, and what is lost if the repo commits itself?
3. Why must `create` flush before returning the object, instead of just `add()` and return?

### What I said

1. `flush()` sends pending changes to the database's memory transaction buffer. `commit()` permanently saves them to disk and ends the transaction.
2. The router does the high-level coordination (would prefer the service layer). If we commit in the repository we lose coordination across multiple repositories or operations that touch multiple repos.
3. It would not generate primary keys and the object would not be uniquely identifiable. (Follow-up. Before flush `created_at` is None.)

### Feedback

All three essentially correct and senior-level. Tightened the flush/commit vocabulary (visibility, durability, reversibility), confirmed the service-layer instinct, and closed the gap in part 3. Beyond the PK, the server-default `created_at` is also None until flush.

### Correct answer

The precise axes are visibility, durability, reversibility.

`flush()` emits the actual SQL (`INSERT`/`UPDATE`) to the DB now, inside the open transaction. The DB assigns defaults and checks constraints, but the changes stay inside the transaction. Not visible to other connections, still fully reversible by rollback. Flush is also when integrity errors surface (unique/FK violations), so you can catch them at a precise point before commit.

`commit()` finalizes the transaction. Changes become durable and visible to everyone, and the transaction ends.

The transaction boundary belongs to whoever owns the use case (the unit of work), not to individual data-access methods. Today that is the router. It should move to the service layer once M5 adds one. If the repo committed, you would lose atomic composition. `create conversation` plus `add first message` are two repo calls that must succeed or fail as one. Separate commits are separate transactions. You cannot roll the pair back as a unit. The repo commits nothing so the caller can wrap N repo calls in one transaction.

Everything DB-generated lands on the object only at flush.

- `id` is `default=uuid.uuid4`, a client-side default, but SQLAlchemy only evaluates column defaults when building the INSERT, so it is None until flush. (If it were a Postgres autoincrement, you would definitely need the INSERT to run to learn it.)
- `created_at` is `server_default=func.now()`, computed by Postgres, so it is None until the INSERT runs. On SQLAlchemy 2.0 + Postgres the INSERT uses `RETURNING` to read server-generated columns straight back, populating the attribute.

Without flush, `ConversationRead.model_validate(conversation)` would serialize a row that does not exist yet and whose `id` and `created_at` are None. Flush turns a pending in-memory object into a fully-populated persistent one.

Connected detail. This is why `create_session_maker` sets `expire_on_commit=False`. It stops SQLAlchemy from expiring those attributes after commit, so the router can still read `conversation.id` / `created_at` when building the response after `session.commit()`.

### Common mistakes

Describing flush as "saves to memory, commit saves to disk" without visibility and reversibility.

Missing that the transaction boundary is the use-case owner's, so repo methods must not commit.

In part 3, naming only the PK and missing the server-default timestamp (and the `RETURNING` / `expire_on_commit=False` mechanics).

---

## Q5 - Storage model vs API schema, and why input/output split too

### Question

There are two parallel type hierarchies for a conversation. The ORM `Conversation` (storage) and the Pydantic `ConversationRead` (API), plus a separate `ConversationCreate` for input. FastAPI would let you return the ORM object directly. CLAUDE.md forbids it ("never leak internals").

1. `ConversationRead` omits `user_id`. Concrete reason that matters?
2. Two other distinct categories of problem from returning the ORM object directly.
3. Why split input from output too. Field-level example from this domain.

### What I said

Some fields are stored but shouldn't be returned (e.g. user_id, hashed password). Return as little as needed. Payload size, latency, maintainability. Input should validate/whitelist and sanitize supported fields (prevent injection) and reject disallowed fields. Output is different, shaped for easy consumption and controlled errors.

Correct principles but generic. Folded part 2 into part 1, missed the two heaviest categories and the concrete domain examples. Then guessed the `role` attack was about stolen cookies. Wrong axis.

### Feedback

The `role` question is not about auth or stolen cookies (a different axis). It is about what a legitimately authenticated user may claim. Also needed the concrete this-domain examples, not general best practice.

### Correct answer

Part 1. Why omit `user_id`.

It is an internal foreign key. Exposing it leaks the data model shape and internal ID space, raw material for IDOR-style probing across responses.

It is also redundant, which is the tell. The resource is already scoped to the authenticated user (`get_owned_conversation`), so the client does not need it. A field the client does not need that also exposes an internal reference is exactly what the API shape drops.

Part 2. Two heavy categories.

Relationship leakage (`Conversation.messages`), two failure modes. Payload. A list endpoint would dump every message of every conversation. Async throw. Touching an unloaded relationship during serialization triggers a lazy load outside the awaited path and SQLAlchemy raises `MissingGreenlet`. Declaring exactly `id` / `title` / `created_at` sidesteps both.

Contract-storage coupling. If the API type is the ORM model, renaming a column or adding an internal `is_flagged` field changes the public API by accident, or leaks internals. The Pydantic schema is a firewall. Storage evolves behind it. The contract changes only on purpose. Without the split you lose independent evolution of storage and API.

Part 3. Input vs output, concrete example.

`role` is output-only and server-forced (`add_message(..., MessageRole.user, ...)`). If it were an input field, a normal user could POST `{"content": "...", "role": "assistant"}` and inject a fake assistant message. Since from M5 the history is fed back to the LLM as context, this is context poisoning / prompt injection via stored history. The user puts words in the model's mouth. Forcing role server-side guarantees message provenance. This is a security property, not tidiness.

Server-assigned, output-only pair. `id` and `created_at` appear in `*Read`, never accepted in `*Create` (else a client could collide/overwrite rows or backdate records).

`*Read` / `*Create` are the boundary contract. The ORM model is an internal detail. Input schemas whitelist what a client may assert (never `id`, `role`, `user_id`). Output schemas whitelist what a client may see (never internal FKs or unintended relationships).

### Common mistakes

Answering only "expose less" without the FK-leak and redundancy reasons for `user_id`.

Missing the async `MissingGreenlet` relationship failure and the contract-coupling category.

Treating the `role` split as tidiness, or confusing it with auth/session security.

---

## Q6 - Ownership check. IDOR/BOLA, 404 vs 403, and SQL vs Python authorization

### Question

Every conversation route goes through `get_owned_conversation`, which calls `get_for_user`, which does `session.get(Conversation, id)` then `if conversation.user_id != user_id: return None`.

1. Vulnerability class this prevents. The exact attacker request. What leaks without it.
2. Why return 404 (not 403) when the row exists but belongs to another user?
3. Python-side ownership check vs pushing it into the query (`WHERE id AND user_id`). When is Python-side actively worse?

### What I said

Ensures the conversation belongs to the requesting user rather than letting them get another's. 404 so attackers cannot learn whether something exists that they cannot access. You hide the existence condition. Python gives a structured way. Raw SQL might allow injection if done wrong. Also Postgres row-level security could enforce it and be easier.

Parts 1-2 right in spirit. Part 3 had misconceptions.

### Feedback

Injection is not the differentiator. Both use bound parameters. RLS is valid defense-in-depth but not the answer to which pattern to write. Needed the vuln name (BOLA/IDOR), the concrete request, and the collection/forgotten-check argument.

### Correct answer

Part 1. The class is IDOR / Broken Object Level Authorization (BOLA), OWASP API Top 10 #1. The attacker swaps the UUID in the URL for another user's. `GET /conversations/{victim-uuid}/messages`. Without the scope-by-user check the server loads by primary key and returns another user's conversation and history.

Part 2. A 403 confirms the resource exists (you are just not allowed), so an attacker enumerates real IDs by watching 403 vs 404. A 404 collapses "does not exist" and "exists but not yours" into one response, leaking nothing about the ID space. Legitimate clients cannot tell a missing conversation from one they do not own. That is the trade.

Part 3. Prefer filtering in SQL (or a repository method that always scopes by `user_id`).

The safe path becomes the default. Load-then-check-in-Python is a manual guard a developer can forget on the next endpoint. It still compiles and still returns data, silently leaking. Scoping in the query makes "unauthorized" and "no rows" the same path. No separate check to forget.

For anything that is not a single row, Python-side is actively worse. Filtering ownership in Python means fetching rows you have no right to into memory first. `WHERE user_id = ...` means the DB never returns them.

Misconceptions to avoid. Injection risk is equal (both parameterize). RLS is defense-in-depth on top, not a substitute for scoping the query.

Live example in the repo. `list_messages` filters only by `conversation_id`, no `user_id`. It is safe only because the router verified ownership via `OwnedConversation` first. Defensible (authorize the parent once, scope children by parent id) but fragile. `list_messages` leaks if ever called with an arbitrary `conversation_id` without going through `get_owned_conversation`.

Make authorization a property of the query, not a step you remember to run. Repository methods take `user_id` and scope every query by it, so the unsafe query cannot be written by accident.

### Common mistakes

Not naming BOLA/IDOR or the concrete URL-tampering request.

Thinking the SQL-vs-Python choice is about injection.

Missing that Python-side checks over-fetch for collections and are forgettable manual guards.

---

## Q7 - Migrations. Why not trust autogenerate, seed vs migration, and reversibility

### Question

1. Why can't you trust `alembic revision --autogenerate` blindly? Two concrete things it gets wrong.
2. First-principles argument for seeding the dev user in a separate guarded script, not a migration. What breaks if `INSERT INTO users (dev user)` goes in a migration?
3. Why does every migration need a working `downgrade` when prod rarely runs it? When does reversibility actually pay off?

### What I said

1. It might drop something on the surface due to an unexpected schema change. Also data retrofitting/backfill.
2. Seed creates data for dev/testing with realistic data. Migration sets up tables, indexes, relationships, not data.
3. A downgrade gives a clean automated rollback if something fails, without restoring by hand.

Right instincts, but fuzzy on the concrete failures and the "what breaks in prod" argument.

### Feedback

Part 1 needed named failures (renames as drop+add = data loss; enum/type/server-default gaps; data migrations never generated). Part 2 needed the concrete break. The migration also runs in prod and injects a fake account. Part 3 needed the real payoff. The dev inner loop.

### Correct answer

Part 1. Autogenerate diffs model metadata vs the DB with no memory of history.

Renames read as drop + add. Data-loss trap. Rename `title` to `name` becomes `DROP COLUMN title` plus `ADD COLUMN name`, destroying the column's data. Must be rewritten to `alter_column(... new_column_name=...)`. That is why you read the generated file.

Type, enum, and server-default changes it cannot see. Postgres enums especially (adding a value needs `ALTER TYPE ... ADD VALUE`, not generated). `server_default` changes and some type conversions are not detected.

Data migrations are never generated. Autogenerate writes DDL only. Backfilling or transforming existing rows is hand-written.

Part 2. Migrations run in every environment (dev, CI, staging, prod) as the shared, ordered, deterministic history of the schema. They must be environment-agnostic. Putting `INSERT INTO users (dev user, id=000...001)` in a migration means it runs in production too, injecting a fake account with a predictable, guessable ID. A data-integrity and security hole. Guarding a migration by environment makes it branch, so it stops being a pure schema transform and the history no longer matches the schema. So the dev user lives in a production-guarded, idempotent, re-runnable script instead.

Schema is structure that must be identical everywhere. Seed is content that is environment-specific. Structure goes in migrations. Content does not.

Part 3. When reversibility pays off.

The dev inner loop is the primary payoff. While writing a migration you upgrade, see the model was wrong, downgrade, fix, upgrade again. No working downgrade means rebuild the DB from scratch each iteration.

Release rollback. A bad migration in a reverted release can roll schema back with code.

In prod you often roll forward with a corrective migration instead, because downgrades can lose data (rename-in-reverse). So the everyday payoff of `downgrade` is the dev loop, and the discipline it forces. If you cannot write the reverse, you do not fully understand the change. Literal prod rollbacks are the rarer case.

### Common mistakes

Not naming the rename as drop+add data-loss failure.

Part 2. Describing schema-vs-data without the "runs in prod, injects a fake user" consequence.

Part 3. Citing only prod rollback and missing the dev-loop payoff.
