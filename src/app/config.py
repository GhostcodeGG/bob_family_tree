"""Application configuration management."""

from functools import lru_cache
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration for the API."""

    app_name: str = Field(default="Bob Family Tree API")
    database_url: str = Field(
        default="sqlite:///./family_tree.db",
        description="Database connection URL compatible with SQLAlchemy",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()  # type: ignore[arg-type]
