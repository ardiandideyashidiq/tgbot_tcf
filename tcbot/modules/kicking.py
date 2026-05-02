# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group kick command."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot.modules.helper import decorators, extraction
from tcbot.modules.helper.workflows.kick_flow import execute_kick
from tcbot.utils.prefixes import build_prefixed_filters, parse_cmd_args

__module_name__ = "Kick"
__help_text__ = (
    "<code>/kick</code> <i>&lt;target&gt; &lt;reason&gt;</i> – remove a user from this group.\n"
    "The user can rejoin via invite link. Reply to a message or provide a user ID / @username.\n"
    "Aliases: <code>/tckick</code>"
)


@decorators.staff_only
async def cmd_kick(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    args = parse_cmd_args(msg.text)

    if msg.reply_to_message:
        target_id, target_name = await extraction.extract_target(update, [], ctx.bot)
        reason = " ".join(args).strip() or "No reason provided"
    else:
        target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
        reason = " ".join(args[1:]).strip() or "No reason provided"

    if not target_id:
        await msg.reply_text("Specify a target – reply to a message or provide a user ID.")
        return

    await execute_kick(update, ctx, target_id, target_name or str(target_id), reason)


_KICK_FILTER = build_prefixed_filters("kick") | build_prefixed_filters("tckick")

__handlers__ = [MessageHandler(_KICK_FILTER, cmd_kick)]
