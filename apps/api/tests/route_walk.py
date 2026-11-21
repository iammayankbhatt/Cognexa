"""Test helpers for walking the app's routes (the walk itself lives in app.core.route_walk)."""

from __future__ import annotations

import re
import uuid

from app.core.route_walk import admin_routes, all_routes, depends_on, minimum_role, walk

__all__ = ["admin_routes", "all_routes", "concrete", "depends_on", "minimum_role", "walk"]


def concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
