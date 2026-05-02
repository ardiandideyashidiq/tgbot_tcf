# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Warn flow helpers – per-group warning tracking."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from tcbot import database as db
from tcbot.modules.helper.formatter import code, mention

log = logging.getLogger(__name__)

WARN_LIMIT = 3


async def execute_warn(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
    reason: str,
) -> None:
    msg = update.effective_message
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id

    count = await db.warns_db.add_warn(target_id, reason, admin_id, chat_id)

    if count >= WARN_LIMIT:
        await db.warns_db.clear_warns(target_id, chat_id)
        try:
            await ctx.bot.ban_chat_member(chat_id, target_id)
            await msg.reply_text(
                f"⛔ {mention(target_id, target_name)} reached {WARN_LIMIT} warnings and has been banned.",
                parse_mode="HTML",
            )
        except Exception as exc:
            log.error("Auto-ban on warn limit failed: %s", exc)
    else:
        await msg.reply_text(
            f"⚠️ {mention(target_id, target_name)} warned ({count}/{WARN_LIMIT}): {reason}",
            parse_mode="HTML",
        )
