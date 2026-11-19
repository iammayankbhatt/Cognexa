import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.health_checks import DependencyStatus, check_neo4j, check_postgres

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Cheap liveness probe. Touches no dependencies."""
    return {"status": "ok"}


@router.get("/health/deep")
async def health_deep(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    """Pings Postgres and Neo4j. Always returns 200 with per-dependency status."""
    postgres, neo4j = await asyncio.gather(check_postgres(settings), check_neo4j(settings))
    deps: dict[str, DependencyStatus] = {"postgres": postgres, "neo4j": neo4j}
    overall = "degraded" if any(d["status"] == "error" for d in deps.values()) else "ok"
    return {"status": overall, "dependencies": deps}
