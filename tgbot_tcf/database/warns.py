# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Repository for the ``warns`` collection.

A warning is scoped to a specific chat. ``is_active`` is ``False`` after
/unwarn clears the latest warning.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .mongo import warns as warns_col


async def insert_warn(
    *,
    warn_id: str,
    warned_user_id: int,
    chat_id: int,
    reason: str,
    admin_user_id: int,
    timestamp: datetime,
) -> None:
    """Insert a new active warning record."""
    await warns_col.insert_one(
        {
            "warn_id": warn_id,
            "warned_user_id": warned_user_id,
            "chat_id": chat_id,
            "reason": reason,
            "admin_user_id": admin_user_id,
            "timestamp": timestamp,
            "is_active": True,
        }
    )


async def count_active_warns(user_id: int, chat_id: int) -> int:
    """Number of active warnings for ``user_id`` in ``chat_id``."""
    return await warns_col.count_documents(
        {"warned_user_id": user_id, "chat_id": chat_id, "is_active": True}
    )


async def list_active_warns(
    user_id: int, chat_id: int
) -> list[dict[str, Any]]:
    """All active warnings for ``user_id`` in ``chat_id``, oldest first."""
    cursor = warns_col.find(
        {"warned_user_id": user_id, "chat_id": chat_id, "is_active": True}
    ).sort("timestamp", 1)
    return [doc async for doc in cursor]


async def find_latest_active_warn(
    user_id: int, chat_id: int
) -> dict[str, Any] | None:
    """Most-recent active warning for ``user_id`` in ``chat_id``."""
    cursor = (
        warns_col.find(
            {"warned_user_id": user_id, "chat_id": chat_id, "is_active": True}
        )
        .sort("timestamp", -1)
        .limit(1)
    )
    async for doc in cursor:
        return doc
    return None


async def deactivate_warn(warn_id: str) -> None:
    """Mark a warning record as cleared."""
    await warns_col.update_one(
        {"warn_id": warn_id}, {"$set": {"is_active": False}}
    )
