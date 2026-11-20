"""Startup audit of production settings.

Production may legitimately start before every key is in place (the free-tier deploy goes live
first, keys follow), so problems are logged loudly instead of refusing to boot. Only setting
NAMES and provider ids are reported, never values.
"""

from urllib.parse import urlparse

from app.core.config import Settings

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _host(url: str | None) -> str:
    return (urlparse(url).hostname or "") if url else ""


def production_problems(settings: Settings) -> list[str]:
    """Human-readable problems with a production configuration (empty when it looks right)."""
    if settings.app_env != "production":
        return []
    problems: list[str] = []
    if not settings.database_url:
        problems.append("DATABASE_URL is not set")
    elif _host(settings.database_url) in _LOCAL_HOSTS:
        problems.append("DATABASE_URL points at a local host")
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        problems.append("NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD are not all set")
    elif _host(settings.neo4j_uri) in _LOCAL_HOSTS:
        problems.append("NEO4J_URI points at a local host")
    if not settings.supabase_url:
        problems.append("SUPABASE_URL is not set: no request can be authenticated")
    if not settings.supabase_service_role_key:
        problems.append("SUPABASE_SERVICE_ROLE_KEY is not set: account deletion falls back to SQL")
    if settings.llm_primary_provider == "fake":
        problems.append("LLM_PRIMARY_PROVIDER is 'fake': tutor answers are canned")
    if settings.llm_fallback_provider in (None, "fake"):
        problems.append("LLM_FALLBACK_PROVIDER is not a real provider: no fallback")
    if settings.llm_judge_provider == "fake":
        problems.append("LLM_JUDGE_PROVIDER is 'fake': short answers are graded by keywords")
    if settings.embedding_provider == "fake":
        problems.append("EMBEDDING_PROVIDER is 'fake': hybrid fallback and plain RAG are weak")
    uses_groq = "groq" in (settings.llm_primary_provider, settings.llm_fallback_provider)
    if uses_groq and not settings.groq_api_key:
        problems.append("GROQ_API_KEY is not set but Groq is configured")
    uses_gemini = "gemini" in (
        settings.llm_primary_provider,
        settings.llm_fallback_provider,
        settings.llm_judge_provider,
        settings.embedding_provider,
    )
    if uses_gemini and not settings.gemini_api_key:
        problems.append("GEMINI_API_KEY is not set but Gemini is configured")
    origins = settings.allowed_origins
    if not origins:
        problems.append("ALLOWED_ORIGINS is empty: the web app cannot call the API")
    if "*" in origins:
        problems.append("ALLOWED_ORIGINS contains '*'")
    if any(_host(o) in _LOCAL_HOSTS for o in origins):
        problems.append("ALLOWED_ORIGINS includes localhost (remove it in production)")
    if any(o.startswith("http://") and _host(o) not in _LOCAL_HOSTS for o in origins):
        problems.append("ALLOWED_ORIGINS has a non-HTTPS origin")
    return problems
