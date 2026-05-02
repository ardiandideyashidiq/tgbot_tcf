# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation statistics command."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.modules.helper.formatter import mention
from tcbot.utils.prefixes import build_prefixed_filters

__module_name__ = "Stats"
__help_text__ = (
    "<b>Help — Statistics</b>\n\n"

    "<b>Commands & Aliases</b>\n"
    "<code>/tcstats</code>\n\n"

    "<b>Who can use it</b>\n"
    "Anyone — no special permissions needed.\n\n"

    "<b>Where to use it</b>\n"
    "Anywhere — bot PM, exec group, or any connected group.\n\n"

    "<b>What it does</b>\n"
    "Shows a quick overview of the federation: who the current owner is, "
    "how many admins are active, how many groups are connected, "
    "and how many federation bans are currently active.\n\n"

    "<b>Example</b>\n"
    "<code>/tcstats</code>"
)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    owner_id = await db.admins_db.get_owner_id()
    owner_fname = await db.users_db.get_first_name(owner_id, "Owner") if owner_id else "Unknown"
    admins = await db.admins_db.admin_count()
    groups = await db.groups_db.active_group_count()
    bans = await db.bans_db.active_ban_count()
    owner_mention = mention(owner_id, owner_fname) if owner_id else "Unknown"

    lines = [
        "<b>TCF Statistics</b>",
        f"Owner: {owner_mention}",
        f"Admin Count: {admins}",
        f"Connected Groups: {groups}",
        f"Active Bans: {bans}",
    ]
    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


__handlers__ = [MessageHandler(build_prefixed_filters("tcstats"), cmd_stats)]
