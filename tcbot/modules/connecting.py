# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group affiliation – bot join/leave events and manual /jointc command."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ChatMemberHandler, ContextTypes, MessageHandler

from tcbot.modules.helper.workflows.connected_flow import on_bot_added, on_join_decision
from tcbot.utils.prefixes import build_prefixed_filters
from tcbot import database as db
from tcbot.modules.helper.formatter import bold, esc

log = logging.getLogger(__name__)

__module_name__ = "Connect"
__help_text__ = (
    "<code>/jointc</code> – request affiliation with TCF (group admins only).\n"
    "When the bot is added to a group, a join request is automatically sent to the owner."
)


async def cmd_jointc(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await update.effective_message.reply_text("Use this command in a group.")
        return

    ## Check if user is admin in that group
    member = await ctx.bot.get_chat_member(chat.id, user.id)
    if member.status not in ("administrator", "creator"):
        await update.effective_message.reply_text("Only group admins can request affiliation.")
        return

    if await db.groups_db.is_affiliated(chat.id):
        await update.effective_message.reply_text("This group is already affiliated with TCF.")
        return

    pending = await db.groups_db.get_pending(chat.id)
    if pending:
        await update.effective_message.reply_text("A join request for this group is already pending.")
        return

    ## Trigger same flow as on_bot_added
    from tcbot.modules.helper import keyboards, parse_logmsg
    from tcbot.config import cfg

    text = parse_logmsg.join_request_log(chat.id, chat.title or "Unknown", user.id, user.full_name)
    try:
        msg = await ctx.bot.send_message(
            cfg.exec_group, text, parse_mode="HTML",
            reply_markup=keyboards.join_decision_kb(chat.id),
        )
        await db.groups_db.add_pending(chat.id, chat.title or "", user.id, msg.message_id)
        await update.effective_message.reply_text("✅ Affiliation request submitted. Waiting for owner approval.")
    except Exception as exc:
        log.error("jointc failed: %s", exc)
        await update.effective_message.reply_text("Failed to submit request.")


__handlers__ = [
    ChatMemberHandler(on_bot_added, ChatMemberHandler.MY_CHAT_MEMBER),
    MessageHandler(build_prefixed_filters("jointc"), cmd_jointc),
    CallbackQueryHandler(on_join_decision, pattern=r"^(join_accept|join_reject):"),
]
