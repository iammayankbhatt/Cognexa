"""Production settings audit (Phase 15)."""

import pytest

from app.core.config import Settings
from app.core.prod_check import production_problems
from app.main import create_app

GOOD: dict[str, object] = {
    "app_env": "production",
    "database_url": "postgresql+asyncpg://u:p@aws-0-eu.pooler.supabase.com:6543/postgres",
    "neo4j_uri": "neo4j+s://abcd1234.databases.neo4j.io",
    "neo4j_user": "neo4j",
    "neo4j_password": "pw",
    "supabase_url": "https://ref.supabase.co",
    "supabase_service_role_key": "srk",
    "llm_primary_provider": "groq",
    "llm_fallback_provider": "gemini",
    "llm_judge_provider": "gemini",
    "embedding_provider": "gemini",
    "groq_api_key": "g",
    "gemini_api_key": "k",
    "allowed_origins": ["https://cognexa.vercel.app"],
}


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**GOOD, **overrides})  # type: ignore[call-arg, arg-type]


def test_complete_production_config_has_no_problems() -> None:
    assert production_problems(make()) == []


def test_development_is_never_audited() -> None:
    assert production_problems(make(app_env="development", llm_primary_provider="fake")) == []


@pytest.mark.parametrize(
    ("overrides", "needle"),
    [
        ({"database_url": None}, "DATABASE_URL is not set"),
        ({"database_url": "postgresql+asyncpg://u:p@localhost:5432/x"}, "DATABASE_URL points"),
        ({"neo4j_password": None}, "NEO4J_URI"),
        ({"neo4j_uri": "bolt://127.0.0.1:7687"}, "NEO4J_URI points"),
        ({"supabase_url": "REPLACE_ME"}, "SUPABASE_URL"),
        ({"llm_primary_provider": "fake"}, "LLM_PRIMARY_PROVIDER"),
        ({"llm_fallback_provider": "fake"}, "LLM_FALLBACK_PROVIDER"),
        ({"llm_judge_provider": "fake"}, "LLM_JUDGE_PROVIDER"),
        ({"embedding_provider": "fake"}, "EMBEDDING_PROVIDER"),
        ({"groq_api_key": "REPLACE_ME"}, "GROQ_API_KEY"),
        ({"gemini_api_key": None}, "GEMINI_API_KEY"),
        ({"allowed_origins": ["*"]}, "'*'"),
        ({"allowed_origins": ["https://a.app", "http://localhost:3000"]}, "localhost"),
        ({"allowed_origins": ["http://cognexa.example.org"]}, "non-HTTPS"),
        ({"allowed_origins": []}, "empty"),
    ],
)
def test_each_problem_is_reported(overrides: dict[str, object], needle: str) -> None:
    problems = production_problems(make(**overrides))
    assert any(needle in p for p in problems), problems


def test_problems_never_contain_secret_values() -> None:
    secret = "sk-secret-value-123"
    s = make(
        groq_api_key=secret,
        gemini_api_key=None,
        database_url=f"postgresql://u:{secret}@localhost/x",
    )
    text = " ".join(production_problems(s))
    assert text  # there are problems to report ...
    assert secret not in text  # ... but never a value


def test_problems_are_logged_at_startup(capsys: pytest.CaptureFixture[str]) -> None:
    # configure_logging writes JSON lines to stdout (it does not propagate to caplog).
    create_app(make(llm_primary_provider="fake"))
    out = capsys.readouterr().out
    assert "production config: LLM_PRIMARY_PROVIDER" in out
    assert '"level": "WARNING"' in out
