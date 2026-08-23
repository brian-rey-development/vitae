from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _package_version() -> str:
    try:
        return version("vitae")
    except PackageNotFoundError:
        return "0.0.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VITAE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "Vitae"
    app_description: str = "Personal health agent API"
    app_version: str = Field(default_factory=_package_version)
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://vitae:vitae@localhost:5432/vitae"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def no_debug_in_prod(self) -> "Settings":
        if self.is_production and self.debug:
            raise ValueError("debug must be False in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
