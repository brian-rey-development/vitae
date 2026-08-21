# 0001 - Use uv as the single Python toolchain

- Status: Accepted
- Date: 2026-08-21

## Context

Python's tooling has historically been fragmented: one tool to manage interpreter versions
(pyenv), another for virtual environments (venv/virtualenv), another for installing packages
(pip), another for locking (pip-tools/poetry), and separate tools for linting and formatting.
This fragmentation causes "works on my machine" drift and slows onboarding. Coming from the
JS/TS world, the mental model we want is closer to a single fast tool (like pnpm plus a runtime
manager) that owns the whole dependency and environment story reproducibly.

## Decision

We will use uv as the single tool for Python version management, virtual environment creation,
dependency installation, and lockfile generation. The project uses a src layout and is defined
entirely by `pyproject.toml` plus `uv.lock`.

## Consequences

- One command surface for setup: `uv sync` reproduces the exact environment from the lockfile,
  locally and in CI. This directly serves the reproducibility principle.
- Fast installs and resolution reduce the cost of adding and testing dependencies.
- uv is younger than pip/poetry, so some edge-case ecosystem docs still assume pip. We accept a
  small amount of translation friction in exchange for speed and a single tool.
- ruff and ty (same vendor, astral) compose cleanly, giving a coherent lint, format, and type
  toolchain.

## Alternatives considered

- pip + venv + pip-tools: the traditional stack. Rejected: multiple tools, slower, more moving
  parts to keep in sync.
- Poetry: popular all-in-one. Rejected: slower resolver and heavier than uv, and uv's lockfile
  and speed better match the reproducibility goal.
- Conda: strong for scientific stacks. Rejected: heavier than needed for a web service, and
  environment management diverges from standard pyproject workflows.
