# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Promotion request queue helpers."""
from __future__ import annotations

from datetime import datetime, timezone

from tcbot.database.mongos import col


def _queue():
    return col("promo_queue")


async def enqueue(user_id: int, username: str | None, full_name: str, msg_id: int) -> None:
    await _queue().update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "request_message_id": msg_id,
            "status": "pending",
            "timestamp": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


async def get_request(user_id: int) -> dict | None:
    return await _queue().find_one({"user_id": user_id, "status": "pending"})


async def all_pending() -> list[dict]:
    return await _queue().find({"status": "pending"}).to_list(None)


async def resolve(user_id: int, status: str) -> None:
    await _queue().update_one(
        {"user_id": user_id},
        {"$set": {"status": status, "resolved_date": datetime.now(timezone.utc)}},
    )


async def pending_count() -> int:
    return await _queue().count_documents({"status": "pending"})
