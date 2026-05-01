# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Repository for the ``muted`` collection.

A mute record is active until an explicit unmute deactivates it or until
``until_date`` passes (Telegram enforces expiry server-side; we mirror it
for audit purposes).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .mongo import muted as muted_col


async def insert_mute(
    *,
    mute_id: str,
    muted_user_id: int,
    chat_id: int,
    reason: str | None,
    admin_user_id: int,
    until_date: datetime | None,
    timestamp: datetime,
) -> None:
    """Insert a new active mute record."""
    await muted_col.insert_one(
        {
            "mute_id": mute_id,
            "muted_user_id": muted_user_id,
            "chat_id": chat_id,
            "reason": reason or "",
            "admin_user_id": admin_user_id,
            "until_date": until_date,
            "timestamp": timestamp,
            "is_active": True,
        }
    )


async def find_active_mute(
    user_id: int, chat_id: int
) -> dict[str, Any] | None:
    """Return the active mute for ``user_id`` in ``chat_id``, or ``None``."""
    return await muted_col.find_one(
        {"muted_user_id": user_id, "chat_id": chat_id, "is_active": True}
    )


async def deactivate_mute(mute_id: str) -> None:
    """Mark a mute record as no longer active."""
    await muted_col.update_one(
        {"mute_id": mute_id}, {"$set": {"is_active": False}}
    )
