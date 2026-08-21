from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Vitae"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

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
