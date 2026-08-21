# 00 - Python for a TypeScript developer

Milestone: M0. This note is the bridge between what I already know (TS/JS, Node, pnpm) and the
Python world Vitae is built in. Read it, then extend the last section with my own words.

## The mental model, mapped

The fastest way for me to get oriented is to notice which Python thing plays the role of each Node
thing I already reach for, and where the two worlds stop lining up.

### One tool instead of five

In the Node world I juggle a small pile of tools without really thinking about it: `node` pins the
runtime version, `pnpm` manages packages and writes the lockfile, and each project quietly gets its
own isolated dependency tree.

Python has historically spread those same jobs across a handful of separate tools:

- `pyenv` for Python versions
- `pip` for installs
- `venv` for isolation
- something else again for locking

Vitae collapses all of that into one tool, `uv`. It pins the Python version, resolves and installs
packages, creates the per-project environment, and writes the lockfile.

That consolidation matters because it removes the "which tool owns this problem?" confusion that
makes Python setup miserable for a newcomer. There is one command surface to learn, not five.

### Manifest and lockfile

The project manifest is the next familiar landmark. Where Node describes a project in
`package.json`, Python uses `pyproject.toml`. Same idea: a single file that names the project and
lists its dependencies.

Alongside it sits the lockfile. My `pnpm-lock.yaml` becomes `uv.lock`, and it does the same job,
recording the exact, fully resolved dependency tree so an install is reproducible on another machine
or in CI rather than "whatever versions happened to resolve today."

### Where installed code lives

Installed dependencies have to live somewhere, and here the mental picture carries over cleanly.

- Node drops them in `node_modules/` at the project root.
- Python puts them in a `.venv/` folder.

Both are the per-project home for third-party code, and I mostly leave both alone and let the package
manager fill them.

### The rest of the toolbelt

For code quality, Node has me running ESLint for linting and Prettier for formatting as two separate
passes. Python folds both into `ruff`, a single fast tool that lints and formats, so one command
covers ground that took two in the JS world.

Type checking stays a distinct concern in both ecosystems. `tsc` reads TypeScript's types and checks
them statically; Vitae uses `ty` to do the equivalent for Python's type hints.

Two more mappings matter because they are where the AI parts of this project live:

- **Runtime validation** (the job I would give `zod` in TS) belongs to `Pydantic`: build a schema
  from type annotations and validate real data against it at runtime.
- **The web framework** (the slot filled by Express or Hono) is `FastAPI` here.

Here is the whole map in one place:

| Node / TS | Python / Vitae | Job |
|---|---|---|
| `node` | `uv` | Pin the runtime version |
| `pnpm` | `uv` | Install packages, write the lockfile |
| `package.json` | `pyproject.toml` | Project manifest |
| `pnpm-lock.yaml` | `uv.lock` | Locked, reproducible dependency tree |
| `node_modules/` | `.venv/` | Per-project home for installed code |
| ESLint + Prettier | `ruff` | Lint and format |
| `tsc` | `ty` | Static type checking |
| `zod` | `Pydantic` | Runtime validation |
| Express / Hono | `FastAPI` | Web framework |

The next two sections dig into the ideas underneath these mappings, because two of them behave in
ways that surprised me.

## Two ideas that trip up TS developers

### 1. The virtual environment (.venv)

Node isolates dependencies per project automatically. When I `import` something, its resolver walks
up the directory tree looking in `node_modules`, so two projects on the same machine can depend on
different versions of the same library without ever colliding. I get isolation for free, as a
structural property of how imports resolve.

Python's import system works differently. It looks for packages on a shared search path
(`sys.path`), which historically meant packages were installed globally. Two projects that needed
different versions of the same library would fight over one shared install.

A virtual environment is the fix: a per-project sandbox of installed packages with its own private
copy of that search path. `uv` creates and manages it for me, so I rarely touch it directly, but I
should know it exists, because that `.venv/` folder is exactly this project's `node_modules`
equivalent.

When I run a tool with `uv run <cmd>`, it executes inside that sandbox, seeing this project's
dependencies and no others.

### 2. Type hints are annotations, not enforcement

This is the one that genuinely inverts my TypeScript intuition, so it is worth slowing down on.

In TypeScript, types are checked at compile time and then erased. The compiler is a gate: bad code
does not make it through to run. The types are enforcement.

In Python, a hint like `def f(x: int) -> str:` is not enforcement at all. It is just metadata
attached to the function. The interpreter does not check it and will happily execute
`f("not an int")` and return whatever that produces. On its own, the hint does nothing.

What gives it teeth is that two separate tools can read those same hints and act on them, at two
different moments:

- `ty` reads the hints and checks them statically, before the code runs, the way `tsc` does. This
  is what catches type bugs ahead of time.
- Pydantic reads the same hints and validates actual data against them at runtime, the way `zod`
  does. This is how we enforce correctness at untrusted boundaries: user input now, and LLM output
  later.

Same annotations, two different consumers, two different moments. This dual role is the single most
important Python idea for this project, because every boundary in an AI app is a place where real
data has to be validated against a declared type. In Python that validation is something I choose to
run rather than something the language does for me.

## The src layout

Vitae keeps its code under `src/vitae/` rather than putting packages at the repo root, and the
reason is import hygiene.

With a flat layout, a package at the root is importable simply because the current working directory
happens to be on the path. That means the code I test locally might not be the code that actually
gets installed and shipped.

A `src` layout forces the package to be installed before it can be imported, so what I test is the
installed package, not loose files that were importable by accident. That closes a whole class of
"works when I run it this way, breaks in CI" bugs.

The mental shift is to treat the package as a real, installed artifact rather than a pile of scripts
sitting next to my terminal.

## My own words

- **A venv is** a per-project sandbox with its own `site-packages/`, so each project's dependencies
  stay isolated and never collide. That is the one job a venv does: isolation. Python needed a
  dedicated mechanism for it because its import system is global (a shared `site-packages` on
  `sys.path`), whereas Node gets isolation structurally, resolving imports locally by walking up to
  `node_modules`. The other things I care about are separate mechanisms layered on top: the lockfile
  (`uv.lock`) is what makes installs identical across machines and deploys, and uv is what pins the
  Python version itself. Together they give reproducibility; the venv alone only gives isolation.

- **Type hints are not enforced at runtime because** Python is dynamically typed by deliberate
  design: the interpreter runs on duck typing, caring what an object can do at the moment of use,
  not what type it was declared. Enforcing declarations would break that model and tax a language
  whose point is flexibility, so hints were added as optional, ignorable metadata (gradual typing),
  stored on the function in `__annotations__`. Enforcement is opt-in through external tools that
  read those same annotations: `ty` statically before running (like `tsc`, but analysis only, no
  compiled artifact), and Pydantic at runtime to validate real data at untrusted boundaries (like
  `zod`). Same annotations, two consumers, two moments in time.

- **The thing that surprised me most coming from TypeScript was** that Python types are advisory,
  not the law. In TS the compiler blocks bad code before it runs; in Python you bolt on the
  enforcement yourself with ty and Pydantic. That inversion is the whole thesis of this project:
  every boundary in an AI app is a place where advisory hints must be turned into real validation.
