# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation groups listing."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.modules.helper import decorators
from tcbot.modules.helper.formatter import bold, code, esc
from tcbot.utils.prefixes import build_prefixed_filters

__module_name__ = "Groups"
__help_text__ = (
    "<code>/tcfgroups</code> – list all affiliated federation groups (staff only)."
)


@decorators.staff_only
async def cmd_tcfgroups(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    groups = await db.groups_db.active_groups()
    if not groups:
        await update.effective_message.reply_text("No affiliated groups yet.")
        return

    lines = [f"🏘 {bold('Affiliated Groups')} ({len(groups)})\n"]
    for grp in groups:
        lines.append(f"• {esc(grp['title'])} {code(str(grp['chat_id']))}")

    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


__handlers__ = [
    MessageHandler(build_prefixed_filters("tcfgroups"), cmd_tcfgroups),
]
