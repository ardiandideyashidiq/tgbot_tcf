# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Welcome and goodbye messages for affiliated groups."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from tcbot import database as db
from tcbot.config import cfg
from tcbot.modules.helper.formatter import bold, esc, mention

log = logging.getLogger(__name__)

## No __module_name__ – greeting is implicit, no help entry needed


async def on_new_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat

    if not await db.groups_db.is_affiliated(chat.id):
        return

    for member in msg.new_chat_members:
        if member.is_bot:
            continue

        ## Cache the user
        await db.users_db.upsert_user(member.id, member.username, member.full_name)

        ## Auto-ban if federation-banned
        ban = await db.bans_db.get_active_ban(member.id)
        if ban:
            try:
                await ctx.bot.ban_chat_member(chat.id, member.id)
                await msg.reply_text(
                    f"⛔ {mention(member.id, member.full_name)} is federation-banned and was automatically removed.",
                    parse_mode="HTML",
                )
            except Exception as exc:
                log.error("Auto-ban on join failed: %s", exc)
            continue

        await msg.reply_text(
            f"👋 Welcome to {bold(esc(chat.title or cfg.community_name))}, "
            f"{mention(member.id, member.full_name)}!",
            parse_mode="HTML",
        )


async def on_left_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat

    if not await db.groups_db.is_affiliated(chat.id):
        return

    member = msg.left_chat_member
    if member and not member.is_bot:
        await msg.reply_text(
            f"👋 {mention(member.id, member.full_name)} has left {bold(esc(chat.title or ''))}.",
            parse_mode="HTML",
        )


__handlers__ = [
    MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member),
    MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_left_member),
]
