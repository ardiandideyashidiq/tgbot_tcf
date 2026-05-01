# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Warn / unwarn lifecycle business logic.

Warnings are scoped to a single connected group. Each /warn call inserts an
active record. /unwarn deactivates the most recent active record. /warns
returns all active records for a user in the current chat.

There is no cross-group propagation. Warnings are purely an in-group
moderation tool.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from ..database import warns_repo
from ..utils.format import fmt_dt


async def record_warn(
    *,
    warned_user_id: int,
    chat_id: int,
    reason: str,
    admin_user_id: int,
    timestamp: datetime,
) -> tuple[str, int]:
    """Persist a warning and return ``(warn_id, new_total_active_count)``."""
    warn_id = f"{warned_user_id}_{chat_id}_{int(timestamp.timestamp())}"
    await warns_repo.insert_warn(
        warn_id=warn_id,
        warned_user_id=warned_user_id,
        chat_id=chat_id,
        reason=reason,
        admin_user_id=admin_user_id,
        timestamp=timestamp,
    )
    count = await warns_repo.count_active_warns(warned_user_id, chat_id)
    return warn_id, count


async def remove_latest_warn(
    user_id: int, chat_id: int
) -> dict[str, Any] | None:
    """Deactivate the most recent active warning.

    Returns the deactivated document, or ``None`` when no active warnings exist.
    """
    doc = await warns_repo.find_latest_active_warn(user_id, chat_id)
    if doc is None:
        return None
    await warns_repo.deactivate_warn(doc["warn_id"])
    return doc


async def build_warns_list(
    user_id: int, chat_id: int, target_name: str
) -> str:
    """Build an HTML summary of all active warnings for the target in this chat."""
    docs = await warns_repo.list_active_warns(user_id, chat_id)
    if not docs:
        return ""
    lines = []
    for idx, doc in enumerate(docs, start=1):
        reason = escape(doc.get("reason", "No reason provided"))
        date = fmt_dt(doc["timestamp"])
        lines.append(f"  {idx}. {reason} — {date}")
    body = "\n".join(lines)
    safe_name = escape(target_name)
    return (
        f"<b>Warnings for {safe_name} (ID: {user_id}) in this group:</b>\n"
        f"{body}"
    )
