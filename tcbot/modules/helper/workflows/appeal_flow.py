# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Appeal conversation workflow – DM-only, reason collection and submission."""
from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tcbot import database as db
from tcbot.config import cfg
from tcbot.modules.helper import keyboards, parse_logmsg
from tcbot.modules.helper.formatter import bold, code, esc, mention
from tcbot.modules.helper.parse_link import message_link

log = logging.getLogger(__name__)

WAITING_REASON = 0
WAITING_CONFIRM = 1

_drafts: dict[int, dict[str, Any]] = {}


async def cmd_appeal(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    uid = update.effective_user.id

    ## DM only
    if update.effective_chat.type != "private":
        await msg.reply_text("Please use /appeal in my DMs.")
        return ConversationHandler.END

    ban = await db.bans_db.get_active_ban(uid)
    if not ban:
        await msg.reply_text("You don't have an active federation ban.")
        return ConversationHandler.END

    ctx.user_data["appeal_ban_id"] = ban["ban_id"]
    await msg.reply_text(
        f"Your ban reason was: {esc(ban['reason'])}\n\n"
        "Please explain why this ban should be lifted. Send your appeal reason:",
        parse_mode="HTML",
    )
    return WAITING_REASON


async def on_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    uid = update.effective_user.id
    reason = (msg.text or "").strip()

    if not reason:
        await msg.reply_text("Please provide a reason.")
        return WAITING_REASON

    ban_id = ctx.user_data.get("appeal_ban_id")
    _drafts[uid] = {"reason": reason, "ban_id": ban_id}

    await msg.reply_text(
        f"📋 {bold('Appeal Preview')}\n\n{esc(reason)}\n\nSubmit this appeal?",
        parse_mode="HTML",
        reply_markup=keyboards.appeal_confirm_kb(ban_id),
    )
    return WAITING_CONFIRM


async def on_confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    action, ban_id = q.data.split(":", 1)
    draft = _drafts.get(uid)

    if action == "appeal_cancel":
        _drafts.pop(uid, None)
        await q.edit_message_text("Appeal cancelled.")
        return ConversationHandler.END

    if action == "appeal_edit":
        await q.edit_message_text("Send your updated appeal reason.")
        return WAITING_REASON

    if action == "appeal_submit":
        if not draft:
            await q.edit_message_text("Session expired.")
            return ConversationHandler.END
        return await _submit_appeal(update, ctx, draft, uid, ban_id)

    return WAITING_CONFIRM


async def _submit_appeal(update: Update, ctx: ContextTypes.DEFAULT_TYPE, draft: dict, uid: int, ban_id: str) -> int:
    q = update.callback_query
    user = update.effective_user
    reason = draft["reason"]

    ban = await db.bans_db.get_ban(ban_id)
    log_link = None
    if ban and ban.get("log_message_id"):
        lc, lt = cfg.logs
        log_link = message_link(lc, ban["log_message_id"], lt)

    appeal_chat, appeal_thread = cfg.appeals
    appeal_text = parse_logmsg.appeal_submitted(uid, user.full_name, ban_id, reason, log_link)

    try:
        rv_msg = await ctx.bot.send_message(
            appeal_chat, appeal_text, parse_mode="HTML",
            message_thread_id=appeal_thread,
            reply_markup=keyboards.appeal_review_kb(ban_id),
        )
        if ban:
            await db.bans_db.set_review(ban_id, rv_msg.message_id)
    except Exception as exc:
        log.error("Failed to post appeal: %s", exc)
        await q.edit_message_text("Failed to submit appeal, please try again later.")
        return ConversationHandler.END

    _drafts.pop(uid, None)
    await q.edit_message_text(
        "✅ Your appeal has been submitted. The staff will review it shortly.",
    )
    return ConversationHandler.END


async def on_appeal_decision(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    admin = update.effective_user

    if not await db.admins_db.is_staff(admin.id):
        await q.answer("You don't have permission.", show_alert=True)
        return

    action, ban_id = q.data.split(":", 1)
    ban = await db.bans_db.get_ban(ban_id)
    if not ban:
        await q.edit_message_text("Ban not found.")
        return

    target_id = ban["banned_user_id"]
    target = await db.users_db.get_user(target_id)
    target_name = target["full_name"] if target else str(target_id)

    if action == "appeal_accept":
        await db.bans_db.deactivate_ban(ban_id)
        ## Unban in all groups
        for grp in await db.groups_db.active_groups():
            try:
                await ctx.bot.unban_chat_member(grp["chat_id"], target_id, only_if_banned=True)
            except Exception:
                pass
        ## Notify user in DM
        try:
            await ctx.bot.send_message(
                target_id,
                f"✅ Your appeal for ban {code(ban_id)} has been accepted. You have been unbanned.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        ## Log
        lc, lt = cfg.logs
        log_text = parse_logmsg.appeal_accepted(target_id, target_name, admin.id, admin.full_name, ban_id)
        await ctx.bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt)
        await q.edit_message_text(q.message.text + f"\n\n✅ Accepted by {admin.full_name}")

    elif action == "appeal_reject":
        try:
            await ctx.bot.send_message(
                target_id,
                f"❌ Your appeal for ban {code(ban_id)} has been rejected.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        lc, lt = cfg.logs
        log_text = parse_logmsg.appeal_rejected(target_id, target_name, admin.id, admin.full_name, ban_id)
        await ctx.bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt)
        await q.edit_message_text(q.message.text + f"\n\n❌ Rejected by {admin.full_name}")


def build_handler() -> ConversationHandler:
    from tcbot.utils.prefixes import build_prefixed_filters

    return ConversationHandler(
        entry_points=[MessageHandler(build_prefixed_filters("appeal"), cmd_appeal)],
        states={
            WAITING_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_reason)],
            WAITING_CONFIRM: [CallbackQueryHandler(on_confirm_callback, pattern=r"^(appeal_submit|appeal_edit|appeal_cancel):")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, lambda u, c: ConversationHandler.END)],
        conversation_timeout=cfg.appeal_timeout,
        per_chat=False,
        per_user=True,
        per_message=False,
    )
