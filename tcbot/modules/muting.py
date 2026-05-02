# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group mute / unmute commands."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot.modules.helper import decorators, extraction
from tcbot.modules.helper.workflows.mute_flow import build_handler, execute_unmute
from tcbot.utils.prefixes import build_prefixed_filters, parse_cmd_args

__module_name__ = "Mute"
__help_text__ = (
    "<code>/tcmute</code> <i>&lt;target&gt; [duration] [reason]</i> – restrict a user from "
    "sending messages in this group.\n"
    "Aliases: <code>/tcm</code>\n\n"
    "<b>Duration tokens</b> (optional, place before the reason):\n"
    "<code>3s</code> · <code>5m</code> · <code>2h</code> · <code>7d</code> · "
    "<code>1w</code> · <code>3mo</code> · <code>2ye</code>\n"
    "Omit to mute permanently.\n\n"
    "The bot will ask for a reason and optional proof, or you can provide them inline:\n"
    "<code>/tcm @user 3d spamming</code>\n\n"
    "<code>/tcunmute</code> <i>&lt;target&gt;</i> – restore a user's chat permissions.\n"
    "Aliases: <code>/tcunm</code>"
)


@decorators.staff_only
async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_cmd_args(update.effective_message.text)
    target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
    if not target_id:
        await update.effective_message.reply_text(
            "Specify a target – reply to a message or provide a user ID."
        )
        return
    await execute_unmute(update, ctx, target_id, target_name or str(target_id))


_UNMUTE_FILTER = (
    build_prefixed_filters("tcunmute")
    | build_prefixed_filters("tcunm")
)

__handlers__ = [
    build_handler(),
    MessageHandler(_UNMUTE_FILTER, cmd_unmute),
]
