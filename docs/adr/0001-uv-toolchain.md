# 0001 - Use uv as the single Python toolchain

- Status: Accepted
- Date: 2026-08-21

## Context

Python tooling is split across several programs. pyenv picks the interpreter, venv or virtualenv makes the environment, pip installs packages, pip-tools or Poetry lock them, and linting and formatting sit in yet more tools. That split is how "works on my machine" happens, and it slows down anyone joining the repo.

Coming from JS/TS, we want one fast tool. pnpm plus a runtime manager does that on the frontend. On the Python side we want the same coverage for versions, the virtualenv, installs, and the lockfile.

## Decision

We will use uv for Python version management, virtualenvs, package installs, and lockfile generation. The project uses a src layout and is defined by `pyproject.toml` and `uv.lock`.

## Consequences

`uv sync` rebuilds the environment from the lockfile, locally and in CI.

Installs and resolution are fast, so trying a new dependency is cheap.

uv is newer than pip and Poetry. A lot of ecosystem docs still assume pip, so we will have to translate those instructions. That is a small tax for speed and one tool.

ruff and ty come from the same vendor (astral). We use them for lint, format, and typecheck.

## Alternatives considered

pip + venv + pip-tools is the old stack. Too many tools to keep in step, and it is slower.

Poetry handles the whole workflow in one tool and is widely used. The resolver is slower and the tool is heavier than uv. uv's lockfile and speed match what we want.

Conda is strong for scientific stacks. Too heavy for a web service, and it does not follow standard pyproject workflows.
