"""Scaffold a new hexagonal domain module that follows docs/CONVENTIONS.md.

Usage:
    uv run python -m vitae.scripts.new_domain <domain> [--entity <Entity>]

Creates src/vitae/modules/<domain>/ with domain, application, and infra layers
(ports, service, ORM model, mappers, repository, schemas, router), then prints
the wiring steps it deliberately leaves to you.
"""

import argparse
import subprocess
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_API_ROOT = _PACKAGE_ROOT.parent.parent

_ENTITIES = """import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class {model}:
    id: uuid.UUID
    name: str
    created_at: datetime
"""

_CONSTANTS = """{name_const} = 120
"""

_PORTS = """import uuid
from typing import Protocol

from vitae.modules.{domain}.domain.entities import {model}


class {model}Repository(Protocol):
    async def add(self, {var}: {model}) -> None: ...

    async def get(self, {var}_id: uuid.UUID) -> {model} | None: ...

    async def list_all(self) -> list[{model}]: ...
"""

_SERVICES = """import uuid
from datetime import UTC, datetime

from vitae.core.unit_of_work import UnitOfWork
from vitae.modules.{domain}.domain.entities import {model}
from vitae.modules.{domain}.domain.ports import {model}Repository


class {model}Service:
    def __init__(self, {domain}: {model}Repository, uow: UnitOfWork) -> None:
        self._{domain} = {domain}
        self._uow = uow

    async def create(self, name: str) -> {model}:
        {var} = {model}(id=uuid.uuid4(), name=name, created_at=datetime.now(UTC))
        await self._{domain}.add({var})
        await self._uow.commit()
        return {var}

    async def get(self, {var}_id: uuid.UUID) -> {model} | None:
        return await self._{domain}.get({var}_id)

    async def list_{domain}(self) -> list[{model}]:
        return await self._{domain}.list_all()
"""

_MODELS = """from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from vitae.core.db import Base, TimestampMixin, UUIDPrimaryKey
from vitae.modules.{domain}.domain.constants import {name_const}


class {model}Model(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "{domain}"

    name: Mapped[str] = mapped_column(String({name_const}))
"""

_MAPPERS = """from vitae.modules.{domain}.domain.entities import {model}
from vitae.modules.{domain}.infra.repository.models import {model}Model


def to_{var}(model: {model}Model) -> {model}:
    return {model}(id=model.id, name=model.name, created_at=model.created_at)


def to_{var}_model(entity: {model}) -> {model}Model:
    return {model}Model(id=entity.id, name=entity.name, created_at=entity.created_at)
"""

_REPOSITORY = """import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.modules.{domain}.domain.entities import {model}
from vitae.modules.{domain}.infra.repository.mappers import to_{var}, to_{var}_model
from vitae.modules.{domain}.infra.repository.models import {model}Model


class Sql{model}Repository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, {var}: {model}) -> None:
        self._session.add(to_{var}_model({var}))
        await self._session.flush()

    async def get(self, {var}_id: uuid.UUID) -> {model} | None:
        model = await self._session.get({model}Model, {var}_id)
        if model is None:
            return None
        return to_{var}(model)

    async def list_all(self) -> list[{model}]:
        result = await self._session.execute(
            select({model}Model).order_by({model}Model.created_at.desc())
        )
        return [to_{var}(model) for model in result.scalars().all()]
"""

_SCHEMAS = """import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vitae.modules.{domain}.domain.constants import {name_const}


class {model}Create(BaseModel):
    name: str = Field(min_length=1, max_length={name_const})


class {model}Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
"""

_ROUTER = '''import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.db import SessionDep, SqlUnitOfWork
from vitae.core.errors import NotFoundError
from vitae.modules.{domain}.application.services import {model}Service
from vitae.modules.{domain}.infra.http.schemas import {model}Create, {model}Read
from vitae.modules.{domain}.infra.repository.repository import Sql{model}Repository

router = APIRouter(prefix="/{domain}", tags=["{domain}"])


def get_{var}_service(session: SessionDep) -> {model}Service:
    return {model}Service(Sql{model}Repository(session), SqlUnitOfWork(session))


ServiceDep = Annotated[{model}Service, Depends(get_{var}_service)]


@router.post("")
async def create_{var}(payload: {model}Create, service: ServiceDep) -> {model}Read:
    """Create a {var}."""
    {var} = await service.create(payload.name)
    return {model}Read.model_validate({var})


@router.get("")
async def list_{domain}(service: ServiceDep) -> list[{model}Read]:
    """List all {domain}."""
    items = await service.list_{domain}()
    return [{model}Read.model_validate(item) for item in items]


@router.get("/{{{var}_id}}")
async def get_{var}({var}_id: uuid.UUID, service: ServiceDep) -> {model}Read:
    """Get a {var} by id."""
    {var} = await service.get({var}_id)
    if {var} is None:
        raise NotFoundError("{var} not found")
    return {model}Read.model_validate({var})
'''

_FILES = {
    "__init__.py": "",
    "domain/__init__.py": "",
    "domain/entities.py": _ENTITIES,
    "domain/constants.py": _CONSTANTS,
    "domain/ports.py": _PORTS,
    "application/__init__.py": "",
    "application/services.py": _SERVICES,
    "infra/__init__.py": "",
    "infra/http/__init__.py": "",
    "infra/http/schemas.py": _SCHEMAS,
    "infra/http/router.py": _ROUTER,
    "infra/repository/__init__.py": "",
    "infra/repository/models.py": _MODELS,
    "infra/repository/mappers.py": _MAPPERS,
    "infra/repository/repository.py": _REPOSITORY,
}


_UNIT_TEST = """import uuid

import pytest

from vitae.modules.{domain}.application.services import {model}Service
from vitae.modules.{domain}.domain.entities import {model}

pytestmark = pytest.mark.unit


class Fake{model}Repository:
    def __init__(self) -> None:
        self._items: dict[uuid.UUID, {model}] = {{}}

    async def add(self, {var}: {model}) -> None:
        self._items[{var}.id] = {var}

    async def get(self, {var}_id: uuid.UUID) -> {model} | None:
        return self._items.get({var}_id)

    async def list_all(self) -> list[{model}]:
        return list(self._items.values())


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


async def test_create_persists_and_commits() -> None:
    uow = FakeUnitOfWork()
    service = {model}Service(Fake{model}Repository(), uow)

    {var} = await service.create("example")

    assert {var}.name == "example"
    assert uow.commits == 1
    assert await service.get({var}.id) == {var}
"""

_INTEGRATION_TEST = """import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BASE = "/api/v1/{domain}"


async def test_create_and_list(client: AsyncClient) -> None:
    created = await client.post(BASE, json={{"name": "example"}})
    assert created.status_code == 200

    listed = await client.get(BASE)
    assert [item["id"] for item in listed.json()] == [created.json()["id"]]
"""


def _default_model(domain: str) -> str:
    singular = domain[:-1] if domain.endswith("s") else domain
    return singular[:1].upper() + singular[1:]


def _next_steps(domain: str, model: str) -> str:
    return (
        f"Created src/vitae/modules/{domain}/ ({model}).\n\n"
        "Wire it up (this generator does not edit other files):\n"
        f"  1. src/vitae/api.py:\n"
        f"       from vitae.modules.{domain}.infra.http.router import router as {domain}_router\n"
        f"       v1.include_router({domain}_router)\n"
        f"  2. src/vitae/core/app.py OPENAPI_TAGS:\n"
        f'       {{"name": "{domain}", "description": "..."}},\n'
        f"  3. alembic/env.py:\n"
        f"       from vitae.modules.{domain}.infra.repository import models  # noqa: F401\n"
        f"  4. Replace the placeholder `name` field with the real fields, then:\n"
        f'       uv run alembic revision --autogenerate -m "create {domain}"\n'
        f"       # review the migration by eye, then\n"
        f"       uv run alembic upgrade head\n"
        "\n"
        f"Tests: tests/unit/{domain}/ passes now; tests/integration/{domain}/ passes once wired.\n"
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
        description="Scaffold a new hexagonal domain module following docs/CONVENTIONS.md.",
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

    target = _PACKAGE_ROOT / "modules" / domain
    if target.exists():
        parser.error(f"{target} already exists; refusing to overwrite")

    fields = {"domain": domain, "model": model, "var": var, "name_const": name_const}
    for relative_path, template in _FILES.items():
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(template.format(**fields))

    unit_dir = _API_ROOT / "tests" / "unit" / domain
    integration_dir = _API_ROOT / "tests" / "integration" / domain
    for directory, template, filename in (
        (unit_dir, _UNIT_TEST, "test_service.py"),
        (integration_dir, _INTEGRATION_TEST, "test_api.py"),
    ):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_text(template.format(**fields))

    _format(target)
    _format(unit_dir)
    _format(integration_dir)
    print(_next_steps(domain, model))


if __name__ == "__main__":
    main()
