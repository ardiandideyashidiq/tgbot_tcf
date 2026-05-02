# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group de-affiliation commands."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.config import cfg
from tcbot.modules.helper import decorators
from tcbot.modules.helper.formatter import bold, code, esc
from tcbot.utils.prefixes import build_prefixed_filters

log = logging.getLogger(__name__)

__module_name__ = "Disconnect"
__help_text__ = (
    "<code>/detc</code> – remove the current group from TCF (group admin only).\n"
    "<code>/rmtc</code> <i>[chat_id]</i> – force-remove a group by ID (staff only)."
)


async def cmd_detc(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await update.effective_message.reply_text("Use this command in a group.")
        return

    member = await ctx.bot.get_chat_member(chat.id, user.id)
    if member.status not in ("administrator", "creator"):
        await update.effective_message.reply_text("Only group admins can use this command.")
        return

    removed = await db.groups_db.deactivate_group(chat.id)
    if removed:
        await update.effective_message.reply_text("✅ This group has been removed from the TCF federation.")
        try:
            await ctx.bot.leave_chat(chat.id)
        except Exception:
            pass
    else:
        await update.effective_message.reply_text("This group wasn't affiliated.")


@decorators.staff_only
async def cmd_rmtc(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = ctx.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text("Usage: /rmtc <chat_id>")
        return

    chat_id = int(args[0])
    removed = await db.groups_db.deactivate_group(chat_id)
    if removed:
        try:
            await ctx.bot.leave_chat(chat_id)
        except Exception:
            pass
        await update.effective_message.reply_text(f"✅ Group {code(str(chat_id))} removed.", parse_mode="HTML")
    else:
        await update.effective_message.reply_text("Group not found in federation.")


__handlers__ = [
    MessageHandler(build_prefixed_filters("detc"), cmd_detc),
    MessageHandler(build_prefixed_filters("rmtc"), cmd_rmtc),
]
