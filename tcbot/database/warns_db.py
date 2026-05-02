# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Warnings collection helpers."""
from __future__ import annotations

from datetime import datetime, timezone

from tcbot.database.mongos import col


def _warns():
    return col("warns")


async def add_warn(user_id: int, reason: str, admin_id: int, chat_id: int) -> int:
    await _warns().insert_one({
        "user_id": user_id,
        "reason": reason,
        "admin_id": admin_id,
        "chat_id": chat_id,
        "timestamp": datetime.now(timezone.utc),
    })
    return await _warns().count_documents({"user_id": user_id, "chat_id": chat_id})


async def warn_count(user_id: int, chat_id: int) -> int:
    return await _warns().count_documents({"user_id": user_id, "chat_id": chat_id})


async def clear_warns(user_id: int, chat_id: int) -> int:
    r = await _warns().delete_many({"user_id": user_id, "chat_id": chat_id})
    return r.deleted_count
