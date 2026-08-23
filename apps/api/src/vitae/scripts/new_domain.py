"""Scaffold a new domain slice that follows docs/CONVENTIONS.md.

Usage:
    uv run python -m vitae.scripts.new_domain <domain> [--entity <Entity>]

Creates src/vitae/<domain>/ (models, schemas, repository, router) from the
exemplar, then prints the wiring steps it deliberately leaves to you.
"""

import argparse
import subprocess
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

_MODELS = """from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from vitae.core.db import Base, TimestampMixin, UUIDPrimaryKey

{name_const} = 120


class {model}(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "{domain}"

    name: Mapped[str] = mapped_column(String({name_const}))
"""

_SCHEMAS = """import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vitae.{domain}.models import {name_const}


class {model}Create(BaseModel):
    name: str = Field(min_length=1, max_length={name_const})


class {model}Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
"""

_REPOSITORY = """import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.{domain}.models import {model}


class {model}Repository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str) -> {model}:
        {var} = {model}(name=name)
        self._session.add({var})
        await self._session.flush()
        return {var}

    async def get(self, {var}_id: uuid.UUID) -> {model} | None:
        return await self._session.get({model}, {var}_id)

    async def list(self) -> list[{model}]:
        result = await self._session.execute(select({model}).order_by({model}.created_at.desc()))
        return list(result.scalars().all())
"""

_ROUTER = '''import uuid

from fastapi import APIRouter

from vitae.core.db import SessionDep
from vitae.core.errors import NotFoundError
from vitae.{domain}.repository import {model}Repository
from vitae.{domain}.schemas import {model}Create, {model}Read

router = APIRouter(prefix="/{domain}", tags=["{domain}"])


@router.post("")
async def create_{var}(payload: {model}Create, session: SessionDep) -> {model}Read:
    """Create a {var}."""
    {var} = await {model}Repository(session).create(payload.name)
    await session.commit()
    return {model}Read.model_validate({var})


@router.get("")
async def list_{domain}(session: SessionDep) -> list[{model}Read]:
    """List all {domain}."""
    items = await {model}Repository(session).list()
    return [{model}Read.model_validate(item) for item in items]


@router.get("/{{{var}_id}}")
async def get_{var}({var}_id: uuid.UUID, session: SessionDep) -> {model}Read:
    """Get a {var} by id."""
    {var} = await {model}Repository(session).get({var}_id)
    if {var} is None:
        raise NotFoundError("{var} not found")
    return {model}Read.model_validate({var})
'''

_FILES = {
    "__init__.py": "",
    "models.py": _MODELS,
    "schemas.py": _SCHEMAS,
    "repository.py": _REPOSITORY,
    "router.py": _ROUTER,
}


def _default_model(domain: str) -> str:
    singular = domain[:-1] if domain.endswith("s") else domain
    return singular[:1].upper() + singular[1:]


def _next_steps(domain: str, model: str) -> str:
    return (
        f"Created src/vitae/{domain}/ ({model}).\n\n"
        "Wire it up (this generator does not edit other files):\n"
        f"  1. src/vitae/api.py:\n"
        f"       from vitae.{domain}.router import router as {domain}_router\n"
        f"       v1.include_router({domain}_router)\n"
        f"  2. src/vitae/core/app.py OPENAPI_TAGS:\n"
        f'       {{"name": "{domain}", "description": "..."}},\n'
        f"  3. Replace the placeholder `name` column with the real fields, then:\n"
        f'       uv run alembic revision --autogenerate -m "create {domain}"\n'
        f"       # review the migration by eye, then\n"
        f"       uv run alembic upgrade head\n"
    )


def _format(target: Path) -> None:
    for command in (["ruff", "format", str(target)], ["ruff", "check", "--fix", str(target)]):
        try:
            subprocess.run(command, capture_output=True)
        except OSError:
            return


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="new_domain",
        description="Scaffold a new domain slice following docs/CONVENTIONS.md.",
    )
    parser.add_argument("domain", help="slice name, lowercase and plural (e.g. insights)")
    parser.add_argument(
        "--entity",
        help="model class name in PascalCase; defaults to the singularized, capitalized domain",
    )
    args = parser.parse_args()

    domain: str = args.domain
    if not domain.isidentifier() or not domain.islower():
        parser.error("domain must be a lowercase identifier, e.g. insights")

    model: str = args.entity or _default_model(domain)
    if not model.isidentifier() or not model[:1].isupper():
        parser.error("--entity must be a PascalCase identifier, e.g. Insight")

    var = model.lower()
    name_const = f"{var.upper()}_NAME_MAX_LENGTH"

    target = _PACKAGE_ROOT / domain
    if target.exists():
        parser.error(f"{target} already exists; refusing to overwrite")

    target.mkdir()
    for filename, template in _FILES.items():
        rendered = template.format(domain=domain, model=model, var=var, name_const=name_const)
        (target / filename).write_text(rendered)

    _format(target)
    print(_next_steps(domain, model))


if __name__ == "__main__":
    main()
