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
    # Tests only: when set, the test suite uses this database instead of database_url.
    test_database_url: str | None = None
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

    # Auth (Supabase). Tokens are verified against the project's JWKS (ES256/RS256). The legacy
    # HS256 secret is accepted only when configured. Values equal to "REPLACE_ME" count as unset.
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwks_url: str | None = None
    supabase_jwt_secret: str | None = None
    jwt_audience: str = "authenticated"
    jwks_cache_ttl_s: int = 600
    profile_cache_ttl_s: float = 30.0

    @field_validator(
        "supabase_url",
        "supabase_service_role_key",
        "supabase_jwks_url",
        "supabase_jwt_secret",
        "database_url",
        "test_database_url",
        mode="after",
    )
    @classmethod
    def _placeholder_is_unset(cls, v: str | None) -> str | None:
        if v is None or not v.strip() or v.strip() == "REPLACE_ME":
            return None
        return v.strip()

    @property
    def jwt_issuer(self) -> str | None:
        return f"{self.supabase_url.rstrip('/')}/auth/v1" if self.supabase_url else None

    @property
    def effective_jwks_url(self) -> str | None:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        return f"{self.jwt_issuer}/.well-known/jwks.json" if self.jwt_issuer else None

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
