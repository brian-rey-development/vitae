# 00 - Python for a TypeScript developer

Milestone: M0. This note is the bridge between what I already know (TS/JS, Node, pnpm) and the
Python world Vitae is built in. Read it, then extend the last section with my own words.

## The mental model, mapped

| My TS/Node world      | Python / Vitae world | What it is                                                        |
|-----------------------|----------------------|-------------------------------------------------------------------|
| node + pnpm           | uv                   | Runtime version, package manager, venv, lockfile, in one tool     |
| package.json          | pyproject.toml       | Project manifest and dependency list                              |
| pnpm-lock.yaml        | uv.lock              | Exact, reproducible dependency tree                               |
| node_modules/         | .venv/               | Where installed dependencies live, per project                    |
| eslint + prettier     | ruff                 | Lint and format, one fast tool                                    |
| tsc                   | ty                   | Static type checker for type hints                                |
| zod                   | Pydantic             | Runtime validation built from type annotations                   |
| express / hono        | FastAPI              | The web framework                                                 |

## Two ideas that trip up TS developers

### 1. The virtual environment (.venv)

Node isolates dependencies per project automatically through `node_modules`. Python historically
installed packages globally, which caused version collisions between projects. A virtual
environment is a per-project sandbox of installed packages. uv creates and manages it, so I rarely
touch it directly, but I should know it exists: that folder is this project's `node_modules`
equivalent. Running tools via `uv run <cmd>` executes them inside that sandbox.

### 2. Type hints are annotations, not enforcement

In TypeScript, types are checked at compile time and then erased. The compiler blocks bad code.

In Python, a hint like `def f(x: int) -> str:` is just metadata. The Python runtime does not check
it and will happily run `f("not an int")`. Two separate tools give the hint teeth:

- ty reads the hints and checks them statically, the way tsc does. This catches bugs before run.
- Pydantic reads the same hints and validates actual data at runtime, the way zod does. This is
  how we enforce correctness at untrusted boundaries (user input, and later, LLM output).

Same annotations, two different consumers. This dual role is the single most important Python idea
for this project, because every boundary in an AI app is a place where real data must be validated
against a declared type.

## The src layout

Vitae uses a `src/vitae/` layout rather than putting packages at the repo root. The reason is
import hygiene: with a src layout, the code you test is the installed package, not loose files that
happen to be importable because of the current working directory. It prevents a class of "works
when I run it this way, breaks in CI" bugs. Think of it as making the package a real, installed
artifact rather than a pile of scripts.

## My own words (fill this in)

- A venv is ...
- Type hints are not enforced at runtime because ...
- The thing that surprised me most coming from TypeScript was ...
