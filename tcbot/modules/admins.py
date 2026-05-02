# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Admin management – promote, demote, transfer ownership, and promo requests."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.config import cfg
from tcbot.modules.helper import decorators, extraction, keyboards, parse_logmsg
from tcbot.modules.helper.formatter import bold, code, esc, mention
from tcbot.utils.prefixes import build_prefixed_filters

log = logging.getLogger(__name__)

__module_name__ = "Admins"
__help_text__ = (
    "<code>/tcpromote</code> <i>[reply or user_id]</i> – promote a user to admin (owner only).\n"
    "<code>/tcdemote</code> <i>[reply or user_id]</i> – remove admin status (owner only).\n"
    "<code>/tctransfer</code> <i>[reply or user_id]</i> – transfer ownership (owner only).\n"
    "<code>/tcpromoterequests</code> – request promotion to admin.\n"
    "<code>/tcpromotelist</code> – list pending promotion requests (staff only)."
)


@decorators.owner_only
async def cmd_promote(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    admin = update.effective_user
    target_id, target_name = await extraction.extract_target(update, ctx.args or [])
    if not target_id:
        await update.effective_message.reply_text("Specify a target.")
        return

    if await db.admins_db.is_admin(target_id):
        await update.effective_message.reply_text(f"{mention(target_id, target_name)} is already an admin.", parse_mode="HTML")
        return

    await db.admins_db.add_admin(target_id, admin.id)

    ## Send log
    lc, lt = cfg.logs
    await ctx.bot.send_message(
        lc, parse_logmsg.admin_promoted(target_id, target_name, admin.id, admin.full_name),
        parse_mode="HTML", message_thread_id=lt,
    )
    await update.effective_message.reply_text(
        f"✅ {mention(target_id, target_name)} promoted to admin.", parse_mode="HTML",
    )


@decorators.owner_only
async def cmd_demote(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    admin = update.effective_user
    target_id, target_name = await extraction.extract_target(update, ctx.args or [])
    if not target_id:
        await update.effective_message.reply_text("Specify a target.")
        return

    removed = await db.admins_db.remove_admin(target_id)
    if not removed:
        await update.effective_message.reply_text("That user isn't an admin.")
        return

    lc, lt = cfg.logs
    await ctx.bot.send_message(
        lc, parse_logmsg.admin_demoted(target_id, target_name, admin.id, admin.full_name),
        parse_mode="HTML", message_thread_id=lt,
    )
    await update.effective_message.reply_text(
        f"✅ {mention(target_id, target_name)} has been demoted.", parse_mode="HTML",
    )


@decorators.owner_only
async def cmd_transfer(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    current_owner = update.effective_user
    target_id, target_name = await extraction.extract_target(update, ctx.args or [])
    if not target_id:
        await update.effective_message.reply_text("Specify a target.")
        return

    await db.admins_db.set_owner(target_id)
    await update.effective_message.reply_text(
        f"✅ Ownership transferred to {mention(target_id, target_name)} {code(str(target_id))}.",
        parse_mode="HTML",
    )


async def cmd_promote_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    existing = await db.queues_db.get_request(user.id)
    if existing:
        await update.effective_message.reply_text("You already have a pending promotion request.")
        return

    ## Post to exec group with decision buttons
    text = (
        f"📋 {bold('Promotion Request')}\n\n"
        f"👤 {mention(user.id, user.full_name)} {code(str(user.id))}\n"
        f"🔗 @{user.username or 'no username'}"
    )
    msg = await ctx.bot.send_message(
        cfg.exec_group, text, parse_mode="HTML",
        reply_markup=keyboards.promo_decision_kb(user.id),
    )
    await db.queues_db.enqueue(user.id, user.username, user.full_name, msg.message_id)
    await update.effective_message.reply_text("✅ Your promotion request has been submitted.")


@decorators.staff_only
async def cmd_promote_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    pending = await db.queues_db.all_pending()
    if not pending:
        await update.effective_message.reply_text("No pending promotion requests.")
        return

    lines = [f"📋 {bold('Pending Requests')} ({len(pending)})\n"]
    for req in pending:
        uname = f"@{req['username']}" if req.get("username") else "no username"
        lines.append(f"• {mention(req['user_id'], req['full_name'])} {code(str(req['user_id']))} – {uname}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


async def on_promo_decision(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    admin = update.effective_user

    if not await db.admins_db.is_owner(admin.id):
        await q.answer("Owner only.", show_alert=True)
        return

    action, uid_str = q.data.split(":", 1)
    target_id = int(uid_str)
    req = await db.queues_db.get_request(target_id)
    target_name = req["full_name"] if req else str(target_id)

    if action == "promo_accept":
        await db.admins_db.add_admin(target_id, admin.id)
        await db.queues_db.resolve(target_id, "approved")
        try:
            await ctx.bot.send_message(target_id, "✅ Your promotion request has been approved. You are now an admin.")
        except Exception:
            pass
        await q.edit_message_text(q.message.text + f"\n\n✅ Approved by {admin.full_name}")

    elif action == "promo_reject":
        await db.queues_db.resolve(target_id, "rejected")
        try:
            await ctx.bot.send_message(target_id, "❌ Your promotion request has been rejected.")
        except Exception:
            pass
        await q.edit_message_text(q.message.text + f"\n\n❌ Rejected by {admin.full_name}")


__handlers__ = [
    MessageHandler(build_prefixed_filters("tcpromote"), cmd_promote),
    MessageHandler(build_prefixed_filters("tcdemote"), cmd_demote),
    MessageHandler(build_prefixed_filters("tctransfer"), cmd_transfer),
    MessageHandler(build_prefixed_filters("tcpromoterequests"), cmd_promote_request),
    MessageHandler(build_prefixed_filters("tcpromotelist"), cmd_promote_list),
    CallbackQueryHandler(on_promo_decision, pattern=r"^(promo_accept|promo_reject):"),
]
