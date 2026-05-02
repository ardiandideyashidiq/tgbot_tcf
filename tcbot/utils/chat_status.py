# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Chat member status helpers."""
from __future__ import annotations

from telegram import ChatMember


def is_admin_status(status: str) -> bool:
    return status in (ChatMember.ADMINISTRATOR, ChatMember.OWNER)


def is_member_status(status: str) -> bool:
    return status in (ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER, ChatMember.RESTRICTED)
