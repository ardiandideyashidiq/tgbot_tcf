# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Mute/unmute flow helpers."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

from tcbot import database as db
from tcbot.modules.helper.formatter import code, mention

log = logging.getLogger(__name__)


async def execute_mute(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
    reason: str,
    duration_minutes: int = 0,
) -> None:
    msg = update.effective_message
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id

    until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes) if duration_minutes else None

    try:
        await ctx.bot.restrict_chat_member(
            chat_id, target_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        dur_str = f" for {duration_minutes}m" if duration_minutes else ""
        await msg.reply_text(
            f"🔇 {mention(target_id, target_name)} has been muted{dur_str}: {reason}",
            parse_mode="HTML",
        )
        await db.mutes_db.log_mute(target_id, chat_id, reason, admin_id)
    except Exception as exc:
        log.error("Mute failed: %s", exc)
        await msg.reply_text("Failed to mute user.")
