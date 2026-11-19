"""Application settings, loaded from environment variables / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Absolute so scripts work from any directory: apps/api/.env
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    # Comma-separated list in the environment, e.g. "http://localhost:3000,https://app.example.com"
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    database_url: str | None = None
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None

    health_check_timeout_s: float = 3.0

    default_subject_id: str = "dsa"

    # Embeddings: provider "fake" (deterministic, local) or a real provider wired in the LLM layer.
    # embedding_dim MUST equal the vector(N) column in supabase/migrations.
    embedding_provider: str = "fake"
    embedding_model: str = "fake-embedding"
    embedding_dim: int = 768

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
