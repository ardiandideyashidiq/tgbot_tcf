# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group affiliation flow – bot added/removed events and join request handlers."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from tcbot import database as db
from tcbot.config import cfg
from tcbot.modules.helper import keyboards, parse_logmsg
from tcbot.modules.helper.formatter import bold, code, esc, mention

log = logging.getLogger(__name__)


async def on_bot_added(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered when bot is added to a group via my_chat_member."""
    cmc = update.my_chat_member
    if not cmc:
        return

    chat = cmc.chat
    new_status = cmc.new_chat_member.status

    if new_status in ("member", "administrator"):
        ## If group is already affiliated, just log it
        if await db.groups_db.is_affiliated(chat.id):
            log.info("Bot re-added to affiliated group %d", chat.id)
            return

        ## Post join request to exec group for owner decision
        added_by = cmc.from_user
        lc, lt = cfg.logs
        text = parse_logmsg.join_request_log(chat.id, chat.title or "Unknown", added_by.id, added_by.full_name)
        try:
            await ctx.bot.send_message(
                cfg.exec_group, text, parse_mode="HTML",
                reply_markup=keyboards.join_decision_kb(chat.id),
            )
            await db.groups_db.add_pending(chat.id, chat.title or "", added_by.id, 0)
        except Exception as exc:
            log.error("Join request dispatch failed: %s", exc)

    elif new_status in ("left", "kicked"):
        await db.groups_db.deactivate_group(chat.id)
        log.info("Bot removed from %d – group deactivated", chat.id)


async def on_join_decision(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    admin = update.effective_user

    if not await db.admins_db.is_owner(admin.id):
        await q.answer("Owner only.", show_alert=True)
        return

    action, chat_id_str = q.data.split(":", 1)
    chat_id = int(chat_id_str)
    pending = await db.groups_db.get_pending(chat_id)

    if action == "join_accept":
        await db.groups_db.add_group(chat_id, pending["title"] if pending else "", admin.id)
        await db.groups_db.remove_pending(chat_id)
        ## Apply all active bans to new group
        bans = await db.bans_db.active_bans()
        applied = 0
        for ban in bans:
            try:
                await ctx.bot.ban_chat_member(chat_id, ban["banned_user_id"])
                applied += 1
            except Exception:
                pass
        await q.edit_message_text(
            q.message.text + f"\n\n✅ Accepted by {admin.full_name}. {applied} bans applied.",
        )
        ## Notify the group owner
        if pending:
            try:
                await ctx.bot.send_message(
                    pending["owner_id"],
                    f"✅ Your group {bold(esc(pending['title']))} has been accepted into the federation.",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    elif action == "join_reject":
        await db.groups_db.remove_pending(chat_id)
        try:
            await ctx.bot.leave_chat(chat_id)
        except Exception:
            pass
        if pending:
            try:
                await ctx.bot.send_message(
                    pending["owner_id"],
                    "❌ Your group's join request has been rejected.",
                )
            except Exception:
                pass
        await q.edit_message_text(q.message.text + f"\n\n❌ Rejected by {admin.full_name}.")
