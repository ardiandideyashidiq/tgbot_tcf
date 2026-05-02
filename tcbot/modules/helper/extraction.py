# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Resolve a ban target (user_id, display_name) from command context."""
from __future__ import annotations

from telegram import Message, Update, User


async def extract_target(update: Update, args: list[str]) -> tuple[int, str] | tuple[None, None]:
    """
    Returns (user_id, name) from reply, mention, or raw numeric ID.
    Returns (None, None) if no valid target found.
    """
    msg: Message = update.effective_message

    ## Priority 1: reply
    if msg.reply_to_message and msg.reply_to_message.from_user:
        u: User = msg.reply_to_message.from_user
        return u.id, u.full_name

    ## Priority 2: first arg is @username or numeric ID
    if args:
        arg = args[0].lstrip("@")
        if arg.isdigit():
            return int(arg), f"User {arg}"
        ## Try to resolve @username via message entities
        for ent in msg.entities or []:
            if ent.type == "mention":
                text = msg.text or ""
                uname = text[ent.offset + 1 : ent.offset + ent.length]
                if uname.lower() == arg.lower() and ent.user:
                    return ent.user.id, ent.user.full_name
        return None, None

    ## Priority 3: text_mention entity anywhere in message
    for ent in msg.entities or []:
        if ent.type == "text_mention" and ent.user:
            return ent.user.id, ent.user.full_name

    return None, None
