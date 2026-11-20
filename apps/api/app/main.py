import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin_ai,
    admin_eval,
    admin_users,
    concepts,
    dashboard,
    graph,
    health,
    learn,
    me,
    notes,
    quiz,
    recommendations,
    revision_sheets,
    study,
    tutor,
)
from app.auth.deps import ProfileCache
from app.auth.jwks import JwksCache
from app.cache.service import CachedQueryEmbedder, LLMCache
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.db.session import Database
from app.graph.provider import GraphProvider
from app.llm.embeddings import EmbeddingProviderUnavailableError, get_embedding_provider
from app.llm.registry import build_judge_router, build_router
from app.tutor.catalogue import CatalogueCache
from app.tutor.service import TutorDeps
from app.usage.guard import UsageGuard

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    db = Database(settings)
    graph_provider = GraphProvider(settings)
    llm = build_router(settings)
    judge = build_judge_router(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await db.dispose()
        await graph_provider.close()
        for provider in [*llm.providers, *judge.providers]:
            await provider.aclose()

    app = FastAPI(title="Cognexa API", version="0.1.0", lifespan=lifespan)
    app.dependency_overrides[get_settings] = lambda: settings
    app.state.db = db
    app.state.graph = graph_provider
    app.state.graph_cache = {}
    jwks_url = settings.effective_jwks_url
    app.state.jwks = JwksCache(jwks_url, ttl_s=settings.jwks_cache_ttl_s) if jwks_url else None
    app.state.profile_cache = ProfileCache(settings.profile_cache_ttl_s)
    app.state.llm = llm
    app.state.judge_llm = judge
    app.state.usage_guard = UsageGuard(db)
    try:
        embedder = CachedQueryEmbedder(get_embedding_provider(settings), LLMCache(db))
    except EmbeddingProviderUnavailableError:
        logger.warning("embedding provider unavailable: hybrid fallback and plain_rag degraded")
        embedder = None
    app.state.tutor = TutorDeps(
        llm=llm, embedder=embedder, catalogues=CatalogueCache(), cache=LLMCache(db)
    )
    register_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # Added last => outermost, so the request ID is set for CORS preflights and errors too.
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(concepts.router)
    app.include_router(graph.router)
    app.include_router(admin_users.router)
    app.include_router(admin_ai.router)
    app.include_router(admin_eval.router)
    app.include_router(tutor.router)
    app.include_router(quiz.router)
    app.include_router(learn.router)
    app.include_router(notes.router)
    app.include_router(recommendations.router)
    app.include_router(dashboard.router)
    app.include_router(revision_sheets.router)
    app.include_router(study.router)
    return app


app = create_app()
