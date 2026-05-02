# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Ban status check commands."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.modules.helper import extraction
from tcbot.modules.helper.formatter import bold, code, esc, italic, mention
from tcbot.modules.helper.parse_link import message_link
from tcbot.config import cfg
from tcbot.utils.prefixes import build_prefixed_filters

__module_name__ = "Check"
__help_text__ = (
    "<code>/checkme</code> – check your own federation ban status.\n"
    "<code>/baninfo</code> <i>[reply or user_id]</i> – check ban details for any user (staff only)."
)


async def cmd_checkme(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    name = update.effective_user.full_name
    ban = await db.bans_db.get_active_ban(uid)

    if not ban:
        await update.effective_message.reply_text(
            f"✅ {mention(uid, name)}, you don't have an active federation ban.",
            parse_mode="HTML",
        )
        return

    lc, lt = cfg.logs
    proof_link = message_link(lc, ban["log_message_id"], lt) if ban.get("log_message_id") else None
    lines = [
        f"⛔ {bold('You are federation-banned.')}",
        "",
        f"📋 Reason: {esc(ban['reason'])}",
        f"🔖 Ban ID: {code(ban['ban_id'])}",
        f"📅 Date: {italic(ban['timestamp'].strftime('%Y-%m-%d %H:%M UTC'))}",
    ]
    if proof_link:
        from tcbot.modules.helper.formatter import link
        lines.append(f"📎 Log: {link('View', proof_link)}")
    lines.append("\nUse /appeal in my DMs to submit an appeal.")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_baninfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not await db.admins_db.is_staff(uid):
        await update.effective_message.reply_text("Staff only.")
        return

    target_id, target_name = await extraction.extract_target(update, ctx.args or [])
    if not target_id:
        await update.effective_message.reply_text("Specify a target.")
        return

    ban = await db.bans_db.get_active_ban(target_id)
    if not ban:
        await update.effective_message.reply_text(
            f"No active ban for {mention(target_id, target_name)} {code(str(target_id))}.",
            parse_mode="HTML",
        )
        return

    lines = [
        f"⛔ {bold('Active Federation Ban')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"📋 Reason: {esc(ban['reason'])}",
        f"🔖 Ban ID: {code(ban['ban_id'])}",
        f"📅 Date: {italic(ban['timestamp'].strftime('%Y-%m-%d %H:%M UTC'))}",
        f"✏️ Updated: {ban.get('update_count', 0)} time(s)",
    ]
    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


__handlers__ = [
    MessageHandler(build_prefixed_filters("checkme"), cmd_checkme),
    MessageHandler(build_prefixed_filters("baninfo"), cmd_baninfo),
]
