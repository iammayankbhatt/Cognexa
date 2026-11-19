"""Supabase Auth admin API calls made with the service-role key (backend only, CLAUDE.md rule 5).

Endpoint checked against the local Supabase stack (CLI 3.2.0): DELETE
`<SUPABASE_URL>/auth/v1/admin/users/<id>` with headers `apikey` and `Authorization: Bearer`
set to the service-role key returns 200 and removes the user; profiles and every user row cascade.
"""

from __future__ import annotations

import uuid

import httpx

from app.core.config import Settings


class AuthAdminError(RuntimeError):
    pass


def admin_api_configured(settings: Settings) -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


async def delete_auth_user(settings: Settings, user_id: uuid.UUID) -> None:
    if not admin_api_configured(settings):
        raise AuthAdminError("Supabase admin API is not configured")
    key = settings.supabase_service_role_key or ""
    url = f"{(settings.supabase_url or '').rstrip('/')}/auth/v1/admin/users/{user_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    if resp.status_code not in (200, 204, 404):
        raise AuthAdminError(f"auth admin API returned {resp.status_code}")
