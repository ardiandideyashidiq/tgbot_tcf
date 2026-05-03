# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Admin service layer – business logic for promotion, demotion and ownership transfer.

All database access is mediated through ``admins_repo`` and ``requests_repo``
so that unit tests can monkeypatch these objects without touching MongoDB.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from tcbot.database import admins_db, queues_db


class _AdminsRepo:
    """Adapter over the admins/owners collections."""

    async def add_admin(
        self,
        user_id: int,
        promoted_by: int,
        promoted_date: datetime,
    ) -> None:
        await admins_db.add_admin(user_id, promoted_by)

    async def remove_admin(self, user_id: int) -> bool:
        return await admins_db.remove_admin(user_id)

    async def is_admin(self, user_id: int) -> bool:
        return await admins_db.is_admin(user_id)

    async def replace_owner(self, new_owner_id: int) -> None:
        await admins_db.set_owner(new_owner_id)

    async def upsert_admin_if_missing(
        self,
        user_id: int,
        promoted_by: int,
    ) -> None:
        if not await admins_db.is_admin(user_id):
            await admins_db.add_admin(user_id, promoted_by)


class _RequestsRepo:
    """Adapter over the promotion-requests queue."""

    async def create(
        self,
        target_id: int,
        requested_by: int,
        request_id: str,
    ) -> None:
        await queues_db.enqueue(
            user_id=target_id,
            username=None,
            first_name=str(target_id),
            promoted_by=requested_by,
        )

    async def find_by_id(self, request_id: str) -> dict | None:
        return await queues_db.get_request_by_id(request_id)

    async def list_pending(self) -> list[dict]:
        return await queues_db.all_pending()

    async def resolve(
        self,
        request_id: str,
        status: str,
        resolved_by: int,
    ) -> None:
        await queues_db.resolve(request_id, status, resolved_by)


admins_repo: _AdminsRepo = _AdminsRepo()
requests_repo: _RequestsRepo = _RequestsRepo()


async def promote_immediately(target_id: int, by_owner_id: int) -> None:
    """Add target directly to the admins collection."""
    await admins_repo.add_admin(
        user_id=target_id,
        promoted_by=by_owner_id,
        promoted_date=datetime.now(timezone.utc),
    )


async def create_promotion_request(target_id: int, requested_by: int) -> str:
    """Persist a pending promotion request and return its UUID."""
    request_id = str(uuid.uuid4())
    await requests_repo.create(
        target_id=target_id,
        requested_by=requested_by,
        request_id=request_id,
    )
    return request_id


async def approve_request(
    request_id: str,
    by_owner_id: int,
) -> str | None:
    """Approve a promotion request.

    Returns the request_id on success, or None when the request is not
    found / no longer pending.
    """
    req = await requests_repo.find_by_id(request_id)
    if not req or req.get("status") != "pending":
        return None

    target_id: int = req["target_id"]
    if not await admins_repo.is_admin(target_id):
        await admins_repo.add_admin(
            user_id=target_id,
            promoted_by=by_owner_id,
            promoted_date=datetime.now(timezone.utc),
        )

    await requests_repo.resolve(
        request_id=request_id,
        status="approved",
        resolved_by=by_owner_id,
    )
    return request_id


async def reject_request(
    request_id: str,
    by_owner_id: int,
) -> str | None:
    """Reject a promotion request.

    Returns the request_id on success, or None when not found / not pending.
    """
    req = await requests_repo.find_by_id(request_id)
    if not req or req.get("status") != "pending":
        return None

    await requests_repo.resolve(
        request_id=request_id,
        status="rejected",
        resolved_by=by_owner_id,
    )
    return request_id


async def demote_user(user_id: int) -> bool:
    """Remove user from the admins collection. Returns True when removed."""
    return await admins_repo.remove_admin(user_id)


async def transfer_ownership(new_owner_id: int, old_owner_id: int) -> None:
    """Atomically transfer ownership: promote new owner, demote them from admin list,
    and ensure the previous owner is kept as a regular admin.
    """
    await admins_repo.replace_owner(new_owner_id)
    await admins_repo.remove_admin(new_owner_id)
    await admins_repo.upsert_admin_if_missing(
        user_id=old_owner_id,
        promoted_by=new_owner_id,
    )
