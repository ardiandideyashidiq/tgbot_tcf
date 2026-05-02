# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Build deep-link URLs pointing to specific messages/topics."""
from __future__ import annotations


def message_link(chat_id: int, message_id: int, thread_id: int | None = None) -> str:
    """Produces a t.me/c/... link for a message inside a private supergroup."""
    cid = str(chat_id).replace("-100", "")
    if thread_id:
        return f"https://t.me/c/{cid}/{thread_id}/{message_id}"
    return f"https://t.me/c/{cid}/{message_id}"
