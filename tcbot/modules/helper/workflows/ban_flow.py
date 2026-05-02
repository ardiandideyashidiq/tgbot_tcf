# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Ban conversation workflow – proof collection, confirmation, and execution."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import InputMediaPhoto, InputMediaVideo, Message, Update
from telegram.constants import ChatAction
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tcbot import database as db
from tcbot.config import cfg
from tcbot.modules.helper import extraction, keyboards, parse_logmsg
from tcbot.modules.helper.formatter import bold, code, esc, mention
from tcbot.modules.helper.parse_link import message_link

log = logging.getLogger(__name__)

WAITING_PROOF = 0
WAITING_CONFIRM = 1

## Pending ban drafts keyed by admin user_id
_drafts: dict[int, dict[str, Any]] = {}

## Album accumulator keyed by media_group_id
_albums: dict[str, list[Message]] = {}


async def _flush_album(media_group_id: str, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await asyncio.sleep(cfg.album_debounce)
    msgs = _albums.pop(media_group_id, [])
    if not msgs:
        return
    admin = msgs[0].from_user
    caption = msgs[0].caption or ""
    reason, *_ = caption.split("\n", 1)
    reason = reason.strip() or "No reason provided"

    _drafts[admin.id] = {
        "album": msgs,
        "reason": reason,
        "target_id": ctx.user_data.get("ban_target_id"),
        "target_name": ctx.user_data.get("ban_target_name", "Unknown"),
    }

    await msgs[0].reply_text(
        _confirm_text(_drafts[admin.id]),
        parse_mode="HTML",
        reply_markup=keyboards.confirm_ban_kb(f"draft:{admin.id}"),
    )


def _confirm_text(draft: dict) -> str:
    return "\n".join([
        f"⛔ {bold('Ban Confirmation')}",
        "",
        f"👤 Target: {mention(draft['target_id'], draft['target_name'])} "
        f"{code(str(draft['target_id']))}",
        f"📋 Reason: {esc(draft['reason'])}",
        "",
        "Confirm this ban?",
    ])


async def cmd_ban_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    uid = update.effective_user.id

    if not await db.admins_db.is_staff(uid):
        await msg.reply_text("You don't have permission to ban.")
        return ConversationHandler.END

    target_id, target_name = await extraction.extract_target(update, ctx.args or [])
    if not target_id:
        await msg.reply_text("Specify a target – reply to a message or provide a user ID.")
        return ConversationHandler.END

    ## Self-ban guard
    if target_id == uid:
        await msg.reply_text("You can't ban yourself.")
        return ConversationHandler.END

    ## Owner guard
    if await db.admins_db.is_owner(target_id):
        await msg.reply_text("The owner cannot be banned.")
        return ConversationHandler.END

    ctx.user_data["ban_target_id"] = target_id
    ctx.user_data["ban_target_name"] = target_name

    await msg.reply_text(
        f"Banning {mention(target_id, target_name)} {code(str(target_id))}.\n\n"
        "Send the proof (photo, video, or album) with the reason in the caption.",
        parse_mode="HTML",
    )
    return WAITING_PROOF


async def on_proof_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    uid = update.effective_user.id

    if not await db.admins_db.is_staff(uid):
        return WAITING_PROOF

    target_id = ctx.user_data.get("ban_target_id")
    target_name = ctx.user_data.get("ban_target_name", "Unknown")
    caption = msg.caption or msg.text or ""
    reason = caption.strip() or "No reason provided"

    ## Album handling
    if msg.media_group_id:
        gid = msg.media_group_id
        if gid not in _albums:
            _albums[gid] = []
            asyncio.create_task(_flush_album(gid, ctx))
        _albums[gid].append(msg)
        return WAITING_PROOF

    _drafts[uid] = {
        "album": [msg],
        "reason": reason,
        "target_id": target_id,
        "target_name": target_name,
    }

    await msg.reply_text(
        _confirm_text(_drafts[uid]),
        parse_mode="HTML",
        reply_markup=keyboards.confirm_ban_kb(f"draft:{uid}"),
    )
    return WAITING_CONFIRM


async def on_confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    action, key = q.data.split(":", 1)

    ## Extract admin id from key
    admin_id = int(key.split(":")[-1])
    draft = _drafts.get(admin_id)
    if not draft:
        await q.edit_message_text("Ban session expired.")
        return ConversationHandler.END

    if action == "ban_cancel":
        _drafts.pop(admin_id, None)
        await q.edit_message_text("Ban cancelled.")
        return ConversationHandler.END

    if action == "ban_edit":
        await q.edit_message_text("Send the updated proof and reason.")
        return WAITING_PROOF

    if action == "ban_confirm":
        return await _execute_ban(update, ctx, draft, admin_id)

    return WAITING_CONFIRM


async def _execute_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE, draft: dict, admin_id: int) -> int:
    q = update.callback_query
    admin = update.effective_user

    await q.edit_message_text("⏳ Processing ban...")

    target_id: int = draft["target_id"]
    target_name: str = draft["target_name"]
    reason: str = draft["reason"]
    msgs: list[Message] = draft["album"]

    ## Forward proof to PROOFS topic
    proof_chat, proof_thread = cfg.proofs
    proof_msg_id: int | None = None
    try:
        if len(msgs) > 1:
            media = []
            for m in msgs:
                if m.photo:
                    media.append(InputMediaPhoto(m.photo[-1].file_id))
                elif m.video:
                    media.append(InputMediaVideo(m.video.file_id))
            sent = await ctx.bot.send_media_group(proof_chat, media, message_thread_id=proof_thread)
            proof_msg_id = sent[0].message_id
        elif msgs[0].photo:
            sent = await ctx.bot.send_photo(
                proof_chat, msgs[0].photo[-1].file_id,
                caption=reason, message_thread_id=proof_thread,
            )
            proof_msg_id = sent.message_id
        elif msgs[0].video:
            sent = await ctx.bot.send_video(
                proof_chat, msgs[0].video.file_id,
                caption=reason, message_thread_id=proof_thread,
            )
            proof_msg_id = sent.message_id
    except Exception as exc:
        log.error("Failed to forward proof: %s", exc)

    ## Publish log to LOGS channel
    logs_chat, logs_thread = cfg.logs
    proof_link = message_link(proof_chat, proof_msg_id, proof_thread) if proof_msg_id else None

    ban_id = db.bans_db.make_ban_id(target_id)
    log_text = parse_logmsg.ban_log(target_id, target_name, admin_id, admin.full_name, reason, ban_id, proof_link)

    log_msg_id: int = 0
    try:
        log_msg = await ctx.bot.send_message(
            logs_chat, log_text, parse_mode="HTML", message_thread_id=logs_thread,
        )
        log_msg_id = log_msg.message_id
    except Exception as exc:
        log.error("Failed to send ban log: %s", exc)

    ## Save to DB
    await db.bans_db.create_ban(target_id, reason, admin_id, proof_msg_id or 0, log_msg_id)

    ## Ban in all affiliated groups
    groups = await db.groups_db.active_groups()
    failed = 0
    for grp in groups:
        try:
            await ctx.bot.ban_chat_member(grp["chat_id"], target_id)
        except Exception:
            failed += 1

    _drafts.pop(admin_id, None)
    summary = f"✅ {bold('Banned')} {mention(target_id, target_name)} {code(str(target_id))}.\nApplied to {len(groups) - failed}/{len(groups)} groups."
    await q.edit_message_text(summary, parse_mode="HTML")

    return ConversationHandler.END


async def on_timeout(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id if update.effective_user else None
    if uid:
        _drafts.pop(uid, None)
    if update.effective_message:
        await update.effective_message.reply_text("Ban session timed out.")
    return ConversationHandler.END


def build_handler() -> ConversationHandler:
    from tcbot.utils.prefixes import build_prefixed_filters

    return ConversationHandler(
        entry_points=[MessageHandler(build_prefixed_filters("tcban") | build_prefixed_filters("fban"), cmd_ban_start)],
        states={
            WAITING_PROOF: [
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.TEXT & ~filters.COMMAND, on_proof_received),
            ],
            WAITING_CONFIRM: [
                CallbackQueryHandler(on_confirm_callback, pattern=r"^(ban_confirm|ban_cancel|ban_edit):"),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, on_timeout)],
        conversation_timeout=cfg.proof_timeout,
        per_chat=True,
        per_user=True,
        per_message=False,
    )
