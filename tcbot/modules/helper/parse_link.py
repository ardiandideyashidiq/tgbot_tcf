# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Build t.me message links for private supergroups and deep links."""
from __future__ import annotations


def _strip_chat_id(chat_id: int) -> str:
    return str(chat_id).replace("-100", "")


def message_link(chat_id: int, message_id: int, thread_id: int | None = None) -> str:
    cid = _strip_chat_id(chat_id)
    if thread_id:
        return f"https://t.me/c/{cid}/{message_id}?thread={thread_id}"
    return f"https://t.me/c/{cid}/{message_id}"


def appeal_deep_link(bot_username: str, ban_id: str) -> str:
    return f"https://t.me/{bot_username}?start=appeal{ban_id}"
