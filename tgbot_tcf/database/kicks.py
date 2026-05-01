# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Repository for the ``kicks`` audit-log collection.

Kicks are intentionally non-stateful: there is no ``is_active`` flag because
a kick does not have an ongoing active/inactive lifecycle the way a ban does.
The collection is an immutable audit log only.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from .mongo import kicks


async def insert_kick(
    *,
    kick_id: str,
    kicked_user_id: int,
    chat_id: int,
    reason: str | None,
    admin_user_id: int,
    timestamp: datetime,
) -> None:
    """Append a new kick audit record."""
    await kicks.insert_one(
        {
            "kick_id": kick_id,
            "kicked_user_id": kicked_user_id,
            "chat_id": chat_id,
            "reason": reason or "",
            "admin_user_id": admin_user_id,
            "timestamp": timestamp,
        }
    )


async def find_kicks_for_user(
    user_id: int, *, limit: int = 10
) -> list[dict[str, Any]]:
    """Return the most-recent kick records for ``user_id``."""
    cursor = (
        kicks.find({"kicked_user_id": user_id})
        .sort("timestamp", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]


def iter_kicks_in_chat(chat_id: int) -> AsyncIterator[dict[str, Any]]:
    """Iterate all kick records for a specific chat, newest first."""
    return kicks.find({"chat_id": chat_id}).sort("timestamp", -1)
