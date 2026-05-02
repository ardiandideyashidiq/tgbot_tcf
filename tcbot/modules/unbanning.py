# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation unban command."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot.modules.helper import decorators, extraction
from tcbot.modules.helper.workflows.unban_flow import execute_unban
from tcbot.utils.prefixes import build_prefixed_filters

__module_name__ = "Unban"
__help_text__ = (
    "<code>/tcunban</code> <i>[reply or user_id]</i> – lift a federation ban.\n"
    "Alias: <code>/funban</code>"
)


@decorators.staff_only
async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    target_id, target_name = await extraction.extract_target(update, ctx.args or [])
    if not target_id:
        await update.effective_message.reply_text("Specify a target – reply or provide a user ID.")
        return
    await execute_unban(update, ctx, target_id, target_name)


__handlers__ = [
    MessageHandler(build_prefixed_filters("tcunban") | build_prefixed_filters("funban"), cmd_unban),
]
