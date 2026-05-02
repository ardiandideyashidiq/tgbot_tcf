# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Maintenance commands – leaveall and cleanup."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.modules.helper import decorators
from tcbot.modules.helper.formatter import bold, code
from tcbot.utils.prefixes import build_prefixed_filters

log = logging.getLogger(__name__)

__module_name__ = "Maintenance"
__help_text__ = (
    "<code>/leaveall</code> – leave all affiliated groups and deactivate them (owner only).\n"
    "<code>/cleanup</code> – remove disbanded groups that the bot was kicked from (owner only)."
)


@decorators.owner_only
async def cmd_leaveall(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    groups = await db.groups_db.active_groups()
    if not groups:
        await update.effective_message.reply_text("No affiliated groups.")
        return

    status = await update.effective_message.reply_text(f"⏳ Leaving {len(groups)} groups...")
    left, failed = 0, 0

    for grp in groups:
        try:
            await ctx.bot.leave_chat(grp["chat_id"])
            await db.groups_db.deactivate_group(grp["chat_id"])
            left += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ Left {code(str(left))} groups. Failed: {code(str(failed))}.",
        parse_mode="HTML",
    )


@decorators.owner_only
async def cmd_cleanup(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    groups = await db.groups_db.active_groups()
    removed = 0

    for grp in groups:
        try:
            await ctx.bot.get_chat(grp["chat_id"])
        except Exception:
            await db.groups_db.deactivate_group(grp["chat_id"])
            removed += 1

    await update.effective_message.reply_text(
        f"🧹 Cleanup done. Removed {code(str(removed))} defunct group(s).",
        parse_mode="HTML",
    )


__handlers__ = [
    MessageHandler(build_prefixed_filters("leaveall"), cmd_leaveall),
    MessageHandler(build_prefixed_filters("cleanup"), cmd_cleanup),
]
