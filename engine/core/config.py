"""
Application configuration.
Production-ready settings management.
"""

from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Environment configuration.

    Pydantic:
    - Loads from .env
    - Validates types
    - Converts automatically
    """

    MISTRAL_API_KEY: str | None = None
    HUGGINGFACE_API_KEY: str | None = None

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Avoids reloading env variables repeatedly.
    """
    return Settings()
