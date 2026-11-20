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

    # LLM providers (app/llm). Provider ids: fake | groq | gemini. Model ids come only from env.
    llm_primary_provider: str = "fake"
    llm_primary_model: str = "fake-model"
    llm_fallback_provider: str | None = "fake"
    llm_fallback_model: str | None = "fake-model"
    llm_judge_provider: str = "fake"
    llm_judge_model: str = "fake-model"
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # Empty = the google-genai SDK default; set "v1beta" if a model/feature needs the beta API.
    gemini_api_version: str | None = None
    llm_timeout_s: float = 30.0
    llm_max_attempts: int = 3  # per provider, including the first try
    llm_backoff_base_s: float = 0.5
    llm_backoff_max_s: float = 8.0
    llm_breaker_threshold: int = 3  # consecutive failed calls before a provider is skipped
    llm_breaker_cooldown_s: float = 60.0

    # Tutor pipeline (Phase 6).
    classify_threshold: float = 0.55  # below this the hybrid fallback also runs
    context_token_budget: int = 3000
    plain_rag_top_k: int = 6
    tutor_history_turns: int = 4

    # Mastery model (Phase 8, docs/ARCHITECTURE.md "Mastery model").
    mastery_learning_rate: float = 0.3
    mastery_weight_easy: float = 0.8  # difficulty 1
    mastery_weight_medium: float = 1.0  # difficulty 2
    mastery_weight_hard: float = 1.2  # difficulty 3
    mastery_prereq_penalty: float = 0.05  # wrong answer that diagnoses a weak prerequisite
    mastery_decay_base: float = 0.98  # effective = score * base ** (days / period)
    mastery_decay_period_days: float = 7.0
    mastery_weak_below: float = 0.4
    mastery_strong_above: float = 0.75

    # Quizzes (Phase 8).
    quiz_default_count: int = 8
    quiz_seconds_per_question: int = 60  # timed mode
    quiz_no_repeat_days: int = 7
    quiz_time_grace_s: int = 5

    # Feature flags (defaults; admins can override them in app_settings at runtime).
    agentic_mode: bool = True
    study_mode: bool = False

    @field_validator(
        "supabase_url",
        "supabase_service_role_key",
        "supabase_jwks_url",
        "supabase_jwt_secret",
        "database_url",
        "test_database_url",
        "groq_api_key",
        "gemini_api_key",
        "gemini_api_version",
        "llm_fallback_provider",
        "llm_fallback_model",
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
