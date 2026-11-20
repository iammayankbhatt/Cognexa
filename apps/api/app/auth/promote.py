"""Set a user's role by e-mail address: how the first admin is created (Phase 15).

There is no admin yet to use the Admin → Users page, so the deployer runs
`scripts/promote_admin.py` once against production. The change goes through
ProfileRepository.admin_update, so it is written to audit_log like any admin edit (actor = null,
meaning "a maintenance script").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.engine import session_factory
from app.db.profiles import ProfileRepository, auth_users

Role = Literal["student", "reviewer", "admin"]
ROLES: tuple[Role, ...] = ("student", "reviewer", "admin")


class UserNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class RoleChange:
    user_id: uuid.UUID
    old_role: str
    new_role: str

    @property
    def changed(self) -> bool:
        return self.old_role != self.new_role


async def set_role_by_email(engine: AsyncEngine, email: str, role: Role) -> RoleChange:
    """Give the account with this e-mail (case-insensitive) the role; idempotent."""
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    async with session_factory(engine)() as session, session.begin():
        found = await session.execute(
            select(auth_users.c.id).where(func.lower(auth_users.c.email) == email.strip().lower())
        )
        user_id = found.scalar_one_or_none()
        if user_id is None:
            raise UserNotFoundError(email)
        repo = ProfileRepository(session)
        before = await repo.get(user_id)
        if before is None:  # auth user without a profile row (trigger missing)
            raise UserNotFoundError(email)
        old = str(before["role"])
        if old != role:
            await repo.admin_update(None, user_id, {"role": role})
        return RoleChange(user_id=user_id, old_role=old, new_role=role)
