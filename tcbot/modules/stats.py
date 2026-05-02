# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation statistics command."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.config import cfg
from tcbot.modules.helper import decorators
from tcbot.modules.helper.formatter import bold, code
from tcbot.utils.prefixes import build_prefixed_filters

__module_name__ = "Stats"
__help_text__ = (
    "<code>/tcstats</code> – show federation stats (staff only)."
)


@decorators.staff_only
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    bans = await db.bans_db.active_ban_count()
    groups = await db.groups_db.active_group_count()
    admins = await db.admins_db.admin_count()
    users = await db.users_db.total_users()
    pending = await db.queues_db.pending_count()

    lines = [
        f"📊 {bold(cfg.community_name)} Stats\n",
        f"⛔ Active bans: {code(str(bans))}",
        f"🏘 Affiliated groups: {code(str(groups))}",
        f"🛡️ Admins: {code(str(admins))}",
        f"👥 Cached users: {code(str(users))}",
        f"📋 Pending requests: {code(str(pending))}",
    ]
    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


__handlers__ = [
    MessageHandler(build_prefixed_filters("tcstats"), cmd_stats),
]
