# Deep dive 01b - Pydantic v2 as the validation boundary

Why this note exists: Pydantic is the library that turns Python's advisory type hints (deep dive 00)
into enforced runtime contracts. Anchor code: Vitae's `core/settings.py` and `health/router.py`, plus
the `CheckIn` model we build in M3/M6.

Interview framing: Pydantic is where "validate at the boundary, trust the core" (engineering principle
1) becomes real. If you can explain coercion vs strict mode, what a validator is and when it runs, and
how FastAPI uses models at the HTTP boundary, you own this topic.

Read in order. Each section builds on the last.

---

## 1. Why Pydantic exists (the boundary principle)

Recall from deep dive 00 that a Python type hint is metadata the interpreter ignores. Writing
`def f(x: int)` does nothing to stop `f("hi")` from running. Hints describe intent, but they never
execute, so on their own they cannot protect you from bad data arriving from outside the program.

The idea that fixes this starts with one observation: every program has a boundary, a line that
separates untrusted input from trusted internal code.

- On the untrusted side sit users, HTTP clients, LLM output, external APIs, environment variables, and
  files, none of which you control.
- On the trusted side sits your own logic.

The discipline that keeps a codebase sane is to parse untrusted input into typed objects right at that
boundary, and once inside, trust the types completely. The payoff is that you stop scattering defensive
`if isinstance(...)` checks through your business logic. The check already happened once, at the edge,
and everything downstream can assume it holds.

Pydantic is the tool that does that parsing. You declare a model using ordinary type hints, and at
runtime Pydantic reads those hints, validates and coerces incoming data into a typed, guaranteed-valid
object, or else raises a precise error explaining what was wrong. Put differently, it is the runtime
consumer of the exact same annotations that a static checker like `ty` reads at rest.

### If you come from TypeScript

The cleanest way to place Pydantic is to say Pydantic is your `zod`. These two lines are the same idea:

```python
z.object({ age: z.number() })     # TypeScript / zod
class User(BaseModel): age: int   # Python / Pydantic
```

Both turn a schema into a runtime validator plus a static type. The one real difference is where the
schema lives. In TypeScript you write the schema separately from the type and derive one from the
other. In Pydantic the type hints *are* the schema. One declaration does both jobs.

---

## 2. BaseModel, the unit of validation

```python
from pydantic import BaseModel

class CheckIn(BaseModel):
    mood: int                 # required (no default)
    note: str                 # required
    energy: int = 5           # optional, defaults to 5
    tags: list[str] = []      # optional, defaults to empty list
```

The rule for whether a field is required is simply whether it has a default:

- No default = required. Leaving it out is a validation error.
- Has a default = optional. Omitting it falls back to that default.

Validation happens inside `BaseModel.__init__`, so constructing a model is the moment the data is
checked. `CheckIn(mood=7, note="tired")` validates the inputs and builds the object, and bad data raises
before you ever hold a half-valid instance.

That last point is the whole guarantee worth internalizing: there is no such thing as an invalid
populated model instance. If you are holding one, its contents already passed.

At a boundary you usually receive a dict rather than keyword arguments, so the common construction path
is `model_validate`, with a JSON variant that parses and validates in a single step.

```python
CheckIn.model_validate({"mood": 7, "note": "tired"})   # validates a dict
CheckIn.model_validate_json('{"mood": 7, "note": "x"}') # parses + validates raw JSON in one step
```

---

## 3. Validation and coercion (lax by default)

This is the most misunderstood part of Pydantic and a frequent interview probe, so it is worth slowing
down.

By default Pydantic v2 runs in **lax mode**. When the incoming value is not already the declared type
but is compatible with it, Pydantic coerces it rather than rejecting it. The declared type is treated as
a target, and Pydantic tries to get there.

```python
class M(BaseModel):
    n: int

M(n="123")     # OK -> n == 123 (int)    string coerced to int
M(n=1.0)       # OK -> n == 1            float with no fractional part coerced
M(n=True)      # OK -> n == 1            bool is an int subclass
M(n="12.5")    # ERROR                   not a valid int
M(n="abc")     # ERROR                   not a valid int
```

Why is lax the default? Because data at a boundary very often arrives as strings. Query parameters, form
fields, environment variables, and some JSON all deliver text, and coercing `"123"` into `123` is almost
always what you actually want.

This is exactly why `settings.py` works without any manual parsing. When `DEBUG=false` comes in from the
environment it arrives as the string `"false"`, and Pydantic coerces it to the boolean `False`. Without
coercion every environment variable would stay a string and you would be writing conversion code by hand
everywhere.

### When you want the opposite: strict mode

Sometimes coercion is precisely what you do not want. **Strict mode** requires the exact declared type
and refuses to convert.

```python
from pydantic import BaseModel, ConfigDict, StrictInt

class S(BaseModel):
    model_config = ConfigDict(strict=True)
    n: int

S(n="123")     # ERROR in strict mode: expected int, got str
```

Strictness does not have to be all or nothing. You can make a single field strict with a type like
`StrictInt` or `StrictStr`, or with `Field(strict=True)`, and leave the rest lax.

The rule of thumb that follows:

- Stay **lax** at HTTP and environment boundaries, where strings are expected and coercion is a
  convenience.
- Reach for **strict** when the source should already be well-typed, such as an internal service
  payload, and where a silent coercion would quietly paper over a real bug.

---

## 4. The anatomy of a ValidationError

When validation fails, Pydantic does not stop at the first problem. It raises a single `ValidationError`
that aggregates every problem it found, and each entry carries a location, a message, and a type.

```python
from pydantic import ValidationError

class CheckIn(BaseModel):
    mood: int
    note: str

try:
    CheckIn.model_validate({"mood": "high", "extra": 1})
except ValidationError as e:
    print(e.errors())
# [
#   {'type': 'int_parsing', 'loc': ('mood',), 'msg': 'Input should be a valid integer...', ...},
#   {'type': 'missing',      'loc': ('note',), 'msg': 'Field required', ...},
# ]
```

The `loc` entry is a path to the offending field, expressed as a tuple. For nested models it grows into
something like `('items', 0, 'price')` to point exactly at the bad leaf.

This structure is the reason FastAPI can hand back a clean 422 response that lists every bad field at
once: it simply serializes `e.errors()`. Because the report is machine-readable and field-level, you get
precise error reporting for free rather than building it yourself.

---

## 5. Constraints with `Field` and `Annotated`

Types alone are often not enough, because a value can be the right type and still be nonsense. A mood
should fall between 1 and 10, and a note should not be empty.

You want to express those value rules declaratively, so they become part of the schema and the generated
docs rather than logic buried inside a function body.

```python
from typing import Annotated
from pydantic import BaseModel, Field

class CheckIn(BaseModel):
    mood: Annotated[int, Field(ge=1, le=10)]           # 1 <= mood <= 10
    note: Annotated[str, Field(min_length=1, max_length=500)]
    energy: Annotated[int, Field(ge=0, le=10)] = 5
```

The constraints you reach for most:

- numeric bounds: `gt`, `ge`, `lt`, `le`
- length bounds: `min_length`, `max_length` (strings and collections)
- `pattern` for a regex
- `multiple_of`

What makes them more than local guards is that they generate JSON Schema, so they flow straight into
FastAPI's `/docs` and constrain the OpenAPI contract that clients rely on.

The `Annotated[T, Field(...)]` form is the modern v2 style. It reads well because it keeps the type first
and the metadata second, and it composes cleanly when you stack several pieces of metadata on one field.

---

## 6. Custom validators (when declarative is not enough)

Declarative constraints cover value rules that can be stated as bounds or patterns. Some rules need real
logic, and for those you write validators.

There are two axes to keep straight, and holding both in mind is enough to place any validator you meet:

- **Scope**: a validator operates on a single field, or on the whole model.
- **Timing**: it runs before or after Pydantic's core type validation.

```python
from pydantic import BaseModel, field_validator, model_validator

class CheckIn(BaseModel):
    mood: int
    note: str
    tags: list[str] = []

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("note cannot be blank")
        return v.strip()                     # validators can transform, not just check

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        return [t.lower().strip() for t in v]

    @model_validator(mode="after")
    def check_consistency(self) -> "CheckIn":
        if self.mood <= 2 and "great" in self.tags:
            raise ValueError("mood<=2 inconsistent with tag 'great'")
        return self
```

Reading the two kinds:

- A `field_validator("x")` validates one field in isolation. By default it runs in `mode="after"`,
  meaning after that field's type coercion, so the value it receives is already the correct type.
  Switching to `mode="before"` lets you see the raw input first, useful when you need to reshape
  something before Pydantic tries to coerce it.
- A `model_validator(mode="after")` runs once the entire model has been built, which is what you want
  for cross-field rules where one field's validity depends on another. Its `mode="before"` variant
  receives the raw dict for the whole model before any field has been processed.

In every case a validator signals invalidity by raising `ValueError` or `AssertionError`, which Pydantic
catches and folds into the same aggregated `ValidationError`. And a validator can also return a
transformed value, which is exactly why normalization work like trimming whitespace or lowercasing tags
belongs here rather than being sprinkled through the rest of the code.

It helps to picture the order of events for a single field:

1. The raw input arrives.
2. Any `before` validators see it first.
3. Type coercion happens.
4. Any `after` validators run.
5. The result is the value stored on the model.

Once every field has gone through that sequence, the model-level `after` validators run against the
finished object.

---

## 7. Pydantic v2 internals (why it is fast, and v1 vs v2)

Pydantic v2's validation core, `pydantic-core`, is written in Rust. When you define a model class,
Pydantic compiles it down to a validation schema that the Rust core executes.

That is why v2 runs roughly 5 to 50x faster than v1, fast enough to validate every single request
without becoming the bottleneck. You write Python, but the hot path runs in Rust.

If you run into v1 code, which is still common in the wild, the renamed API is worth recognizing. This is
a genuine reference matrix, so it stays a table.

| Pydantic v1                 | Pydantic v2                        |
|-----------------------------|------------------------------------|
| `.dict()`                   | `.model_dump()`                    |
| `.json()`                   | `.model_dump_json()`              |
| `parse_obj()`               | `model_validate()`                |
| `parse_raw()`               | `model_validate_json()`           |
| `@validator`                | `@field_validator`                |
| `@root_validator`           | `@model_validator`                |
| `class Config:`             | `model_config = ConfigDict(...)`  |
| `Config.orm_mode = True`    | `model_config: from_attributes=True` |

Vitae is v2 throughout, since it ships with FastAPI, so you only need the v1 names to read older code,
not to write anything new.

---

## 8. Parsing in, serializing out

A model is a two-way boundary tool, and it helps to see both directions together.

- **Coming in, you parse and validate.** `model_validate(obj)` takes a dict or object.
  `model_validate_json(raw)` takes a JSON string and parses and validates it in one pass, which is
  faster than calling `json.loads` and then validating separately.
- **Going out, you serialize.** `model_dump()` produces a dict and `model_dump_json()` produces a JSON
  string. Both accept options that shape the output:
  - `exclude_none=True` to drop null fields
  - `exclude={"field"}` to omit specific keys
  - `by_alias=True` to use field aliases
  - `mode="json"` to render everything as JSON-compatible primitives, so datetimes come out as strings

```python
c = CheckIn.model_validate_json(raw_request_body)   # untrusted JSON -> validated object
payload = c.model_dump(mode="json")                 # object -> JSON-safe dict for a response
```

This in-and-out pair is the whole shape of an API handler. You parse the incoming request into a model,
do your work against the trusted object, and serialize a response model back out.

---

## 9. BaseModel vs BaseSettings (our settings.py, revisited)

`BaseSettings`, from `pydantic-settings`, is a `BaseModel` whose default data source is the environment
and `.env` files, rather than arguments you pass in by hand. Everything covered so far (the types, the
coercion, the constraints, the validators, and the required-versus-optional rule) applies identically.
The only thing that changes is where the values come from.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Vitae"
    environment: str = "development"
    debug: bool = False
```

Several behaviors fall out of this that are worth naming:

- Because `debug: bool = False` is a boolean field, setting `DEBUG=true` in the environment coerces the
  string `"true"` into the boolean `True`, exactly the mechanism from section 3. That coercion is the
  entire reason typed settings feel effortless instead of like a wall of manual conversions.
- A field with no default and no value in the environment raises at startup, which is "fail fast and
  loud" (principle 5) applied to configuration. When we add `database_url: str` with no default in M2, a
  missing `DATABASE_URL` will crash the app at boot rather than at the first query, which is precisely
  where you want the failure.
- `extra="ignore"` tells the model not to error on unrelated keys. `extra="forbid"` would turn a typo'd
  environment key into a startup error, a stricter form of fail-fast that trades some friction for
  safety. We chose ignore for now.

The takeaway is that `Settings` is not a special mechanism at all. It is a `BaseModel` pointed at the
environment, the same validation engine reading from a different source.

---

## 10. How FastAPI uses Pydantic (the HTTP boundary)

FastAPI is essentially Pydantic wired into HTTP, and this is where the boundary principle stops being a
guideline and becomes the framework's entire design.

Consider request bodies first. When you declare a model as a parameter, FastAPI parses and validates the
request body into it and returns a 422 with `e.errors()` if the data is invalid. Your handler only ever
runs against data that already passed.

```python
class CheckInCreate(BaseModel):
    mood: Annotated[int, Field(ge=1, le=10)]
    note: Annotated[str, Field(min_length=1)]

@router.post("/checkins")
async def create_checkin(payload: CheckInCreate):   # body validated before this runs
    ...                                             # payload is guaranteed valid here
```

Responses work symmetrically. The return annotation, or an explicit `response_model=`, validates and
serializes whatever you send back and documents it at the same time, which is what our health endpoint
already relies on.

```python
class HealthStatus(BaseModel):
    status: str

@router.get("/health")
def health() -> HealthStatus:          # response validated + documented as HealthStatus
    return HealthStatus(status="ok")
```

The documentation is not a separate effort either. Because models generate JSON Schema, every request
and response shape shows up in `/openapi.json` and in Swagger at `/docs`, and per ADR-0003 that same
schema becomes the typed client the Next.js frontend consumes. The Pydantic model ends up being the
single source of truth for the shape across validation, docs, and the frontend type all at once.

One separation is worth respecting as we get to M3. The API request and response models in `schemas.py`
are deliberately not the same as the database and storage models in `models.py`. Keeping them distinct
stops internal storage details from leaking out through the HTTP boundary. It is the same Pydantic tool
playing a different role on each side.

---

## 11. The LLM boundary (M6 preview), the core magic

This is where Pydantic earns its place in an AI app rather than a generic web service.

An LLM returns untrusted, non-deterministic text, and there is no guarantee about its shape. To turn a
sentence like "I slept badly and felt anxious" into structured data, we ask the model to emit JSON that
matches a Pydantic schema, and then we validate that JSON at the boundary just like any other untrusted
input.

```python
class CheckInDraft(BaseModel):
    mood: Annotated[int, Field(ge=1, le=10)]
    symptoms: list[str]
    sleep_hours: Annotated[float, Field(ge=0, le=24)] | None = None

raw = call_llm(prompt, schema=CheckInDraft.model_json_schema())  # model returns JSON text
draft = CheckInDraft.model_validate_json(raw)                     # validate at the boundary
```

The LLM is just another untrusted boundary in the sense of principle 1, and it deserves the same
suspicion as an HTTP client. If it hallucinates `mood: 15` or drops a required field,
`model_validate_json` raises, and we re-prompt or repair rather than silently storing garbage, which is
exactly M6's validate-and-retry loop.

What makes this so clean is that the single Pydantic schema is doing three jobs at once:

- It is the **instruction** to the model, delivered through `model_json_schema()`.
- It is the **validator** of whatever the model returns.
- It is the **type** the rest of the app trusts from then on.

One declaration, three jobs, at the riskiest boundary in the whole system.

---

## 12. Gotchas and interview questions

A handful of Pydantic behaviors surprise people. It is worth understanding why each one is the way it is.

- **Mutable defaults are safe here**, a genuine departure from plain Python. Writing
  `tags: list[str] = []` does not share one list across every instance the way a mutable default
  argument to a function would, because Pydantic deep-copies defaults per instance.
- **Boolean coercion in lax mode is broad**, so `"true"`, `"1"`, `"yes"`, and `1` all become `True`.
  Convenient for config, but it calls for deliberate care at any boundary where a stray truthy string
  could flip a flag you did not mean to flip.
- **An `int` field will accept `True`**, because `bool` is a subclass of `int`, unless you make the
  field strict. That is rarely what you want for something like an id.
- **Validation runs on construction and on `model_validate`, but not on plain attribute assignment.**
  After an object is built, `obj.mood = 999` is not re-checked unless you opt in with
  `model_config = ConfigDict(validate_assignment=True)`.
- **Extra fields are ignored by default** under `extra="ignore"`. You can tighten to `extra="forbid"`
  to reject unknown keys outright, or loosen to `extra="allow"` to keep them around.

Interview questions:

1. How does Pydantic give runtime teeth to Python's advisory type hints?
2. Lax vs strict mode: what does `M(n="123")` do in each, and why is lax the default at boundaries?
3. Walk through what happens when validation fails: what is raised, and what does it contain?
4. `field_validator` vs `model_validator`, and `before` vs `after` mode. When do you need each?
5. How does `BaseSettings` relate to `BaseModel`? Where does `DEBUG=true` become `True`?
6. How does FastAPI use a Pydantic model on a request body vs a response, and what does it generate?
7. Why is validating LLM output with a Pydantic schema the right design for structured extraction?
8. Why is `.model_validate_json(raw)` preferable to `json.loads(raw)` then constructing the model?

## 13. The one-paragraph summary to memorize

Pydantic turns Python's advisory type hints into enforced runtime contracts: you declare a `BaseModel`
with typed fields, and at the boundary it validates and (in lax mode) coerces untrusted input into a
guaranteed-valid typed object, or raises a structured `ValidationError` listing every problem. It is
Python's `zod`, but the type hints are the schema. Its v2 core is Rust-fast, so FastAPI uses it to
validate every request body, serialize and document every response, drive typed settings from the
environment, and, most importantly for an AI app, validate untrusted LLM JSON into trusted structured
data, one declaration serving as instruction, validator, and type at once.
