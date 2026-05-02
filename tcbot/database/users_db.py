# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""User cache collection helpers."""
from __future__ import annotations

from datetime import datetime, timezone

from tcbot.database.mongos import col


def _users():
    return col("user_cache")


async def upsert_user(user_id: int, username: str | None, full_name: str) -> None:
    await _users().update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "last_seen": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


async def get_user(user_id: int) -> dict | None:
    return await _users().find_one({"user_id": user_id})


async def total_users() -> int:
    return await _users().count_documents({})
