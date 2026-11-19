"""FastAPI dependencies for the LLM router and the usage guard (one instance per app)."""

from __future__ import annotations

from fastapi import Request

from app.llm.router import LLMRouter
from app.usage.guard import UsageGuard


def get_llm(request: Request) -> LLMRouter:
    router: LLMRouter = request.app.state.llm
    return router


def get_judge_llm(request: Request) -> LLMRouter:
    router: LLMRouter = request.app.state.judge_llm
    return router


def get_usage_guard(request: Request) -> UsageGuard:
    guard: UsageGuard = request.app.state.usage_guard
    return guard
