"""Community ban (/cban) with proof collection, and unban (/cunban)."""
import asyncio
import logging
from datetime import datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..config import (
    ALBUM_DEBOUNCE_SECONDS,
    BRANDING,
    LOG_CHANNEL,
    MAIN_GROUP,
    PROOF_TOPIC,
    PROOF_WAIT_SECONDS,
)
from ..utils.format import chat_id_to_link_id
from ..db import bans
from ..utils.auth import is_authorized
from ..utils.format import (
    fmt_dt,
    fmt_now,
    safe_first_name,
    topic_link,
    user_link,
    utcnow,
)
from ..utils.logger import log_to_channel
from ..utils.targets import get_reason, resolve_target

logger = logging.getLogger(__name__)


def _session_key(chat_id: int, user_id: int) -> str:
    return f"cban:{chat_id}:{user_id}"


def _get_sessions(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.application.bot_data.setdefault("cban_sessions", {})


async def _timeout_session(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    key = job.data["key"]
    sessions = _get_sessions(context)
    sess = sessions.get(key)
    if sess is None:
        return
    sessions.pop(key, None)
    try:
        await context.bot.edit_message_text(
            chat_id=sess["chat_id"],
            message_id=sess["prompt_msg_id"],
            text="Proof submission timed out.",
        )
    except TelegramError:
        pass


async def cmd_cban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    if not await is_authorized(user.id):
        await msg.reply_text("You are not authorized.")
        return

    target = await resolve_target(update, context)
    if target is None:
        await msg.reply_text("Cannot resolve user.")
        return

    if target.id == user.id:
        await msg.reply_text("You cannot ban yourself.")
        return
    if target.id == context.bot.id:
        await msg.reply_text("I cannot ban myself.")
        return

    reason = get_reason(context, update)
    if not reason:
        await msg.reply_text("Usage: /cban <target> <reason>")
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Cancel", callback_data="cancel_proof")]]
    )
    prompt = await msg.reply_text(
        "Please provide proof for this ban. "
        "Send a photo or video (multiple media allowed). You have 60 seconds.",
        reply_markup=keyboard,
    )

    key = _session_key(msg.chat.id, user.id)
    sessions = _get_sessions(context)
    if key in sessions:
        old = sessions.pop(key)
        for j in (old.get("timeout_job"), old.get("album_job")):
            if j:
                try:
                    j.schedule_removal()
                except Exception:  # noqa: BLE001
                    pass

    timeout_job = context.application.job_queue.run_once(
        _timeout_session,
        when=PROOF_WAIT_SECONDS,
        data={"key": key},
        name=f"cban_timeout_{key}",
    )

    sessions[key] = {
        "chat_id": msg.chat.id,
        "user_id": user.id,
        "user_first_name": safe_first_name(user),
        "prompt_msg_id": prompt.message_id,
        "target_id": target.id,
        "target_first_name": target.first_name,
        "reason": reason,
        "media": [],  # list of dicts: {kind, file_id, media_group_id}
        "media_group_id": None,
        "timeout_job": timeout_job,
        "album_job": None,
        "lock": asyncio.Lock(),
        "finalizing": False,
    }


async def on_cancel_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cq = update.callback_query
    if cq is None or cq.message is None or cq.from_user is None:
        return
    chat_id = cq.message.chat.id
    sessions = _get_sessions(context)
    key = _session_key(chat_id, cq.from_user.id)
    sess = sessions.get(key)
    if sess is None:
        await cq.answer("No active proof session.", show_alert=False)
        return
    if cq.message.message_id != sess["prompt_msg_id"]:
        await cq.answer()
        return

    sessions.pop(key, None)
    for j in (sess.get("timeout_job"), sess.get("album_job")):
        if j:
            try:
                j.schedule_removal()
            except Exception:  # noqa: BLE001
                pass
    await cq.answer()
    try:
        await cq.edit_message_text("Operation cancelled.")
    except TelegramError:
        pass


async def on_proof_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    sessions = _get_sessions(context)
    key = _session_key(msg.chat.id, user.id)
    sess = sessions.get(key)
    if sess is None:
        return

    has_photo = bool(msg.photo)
    has_video = bool(msg.video)
    if not has_photo and not has_video:
        try:
            await msg.reply_text("Only photos and videos allowed.")
        except TelegramError:
            pass
        return

    if has_photo:
        kind = "photo"
        file_id = msg.photo[-1].file_id
    else:
        kind = "video"
        file_id = msg.video.file_id

    sess["media"].append(
        {
            "kind": kind,
            "file_id": file_id,
            "media_group_id": msg.media_group_id,
        }
    )

    if msg.media_group_id:
        sess["media_group_id"] = msg.media_group_id
        if sess.get("album_job"):
            try:
                sess["album_job"].schedule_removal()
            except Exception:  # noqa: BLE001
                pass
        sess["album_job"] = context.application.job_queue.run_once(
            _finalize_job,
            when=ALBUM_DEBOUNCE_SECONDS,
            data={"key": key},
            name=f"cban_album_{key}",
        )
    else:
        await _finalize(context, key)


async def _finalize_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    key = context.job.data["key"]
    await _finalize(context, key)


async def _finalize(context: ContextTypes.DEFAULT_TYPE, key: str) -> None:
    sessions = _get_sessions(context)
    sess = sessions.get(key)
    if sess is None:
        return
    async with sess["lock"]:
        if sess.get("finalizing"):
            return
        sess["finalizing"] = True
    try:
        await _do_finalize(context, sess)
    finally:
        sessions.pop(key, None)
        for j in (sess.get("timeout_job"), sess.get("album_job")):
            if j:
                try:
                    j.schedule_removal()
                except Exception:  # noqa: BLE001
                    pass


async def _do_finalize(context: ContextTypes.DEFAULT_TYPE, sess: dict) -> None:
    target_id = sess["target_id"]
    target_first_name = sess["target_first_name"]
    admin_id = sess["user_id"]
    admin_first_name = sess["user_first_name"]
    reason = sess["reason"]
    chat_id = sess["chat_id"]
    prompt_msg_id = sess["prompt_msg_id"]
    media = sess["media"]

    existing = await bans.find_one({"banned_user_id": target_id, "is_active": True})
    is_update = existing is not None

    now_dt = utcnow()
    ban_id = f"{target_id}_{int(now_dt.timestamp())}"

    if is_update:
        prev_proof_id = existing["proof_message_id"]
        prev_log_id = existing["log_message_id"]
        original_dt: datetime = existing["timestamp"]
        previous_proof_link = topic_link(MAIN_GROUP, prev_proof_id, PROOF_TOPIC)
        caption = (
            f"ID: {target_id}\n"
            f"Fed Admin: {user_link(admin_id, admin_first_name)}\n"
            f"Fed Admin ID: {admin_id}\n"
            f'Previous: <a href="{previous_proof_link}">Click Here</a>\n\n'
            f"Commit at: {fmt_dt(original_dt)}\n"
            f"Update at: {fmt_dt(now_dt)}"
        )
    else:
        prev_proof_id = None
        prev_log_id = None
        original_dt = now_dt
        caption = (
            f"ID: {target_id}\n"
            f"Fed Admin: {user_link(admin_id, admin_first_name)}\n"
            f"Fed Admin ID: {admin_id}\n\n"
            f"Commit at: {fmt_dt(now_dt)}"
        )

    proof_message_id = await _post_proof(context, media, caption)
    if proof_message_id is None:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=prompt_msg_id,
                text="Failed to upload proof. Please try again.",
            )
        except TelegramError:
            pass
        return

    proof_link = topic_link(MAIN_GROUP, proof_message_id, PROOF_TOPIC)

    if is_update:
        previous_log_link = (
            f"https://t.me/c/{chat_id_to_link_id(LOG_CHANNEL)}/{prev_log_id}"
            if prev_log_id
            else ""
        )
        old_admin_id = existing["admin_user_id"]
        log_text = (
            "<b>New Community Ban (Update)</b>\n"
            f"{BRANDING}\n"
            f"Admin: {user_link(admin_id, admin_first_name)}\n"
            f"Previous Admin: {user_link(old_admin_id, str(old_admin_id))}\n"
            f"User: {user_link(target_id, target_first_name)}\n"
            f"User ID: {target_id}\n"
            f"Reason: {reason}\n"
            f'Previous: <a href="{previous_log_link}">Click Here</a>\n\n'
            f"Commit at: {fmt_dt(original_dt)}\n"
            f"Update at: {fmt_dt(now_dt)}"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"Proof {target_id}", url=proof_link)],
                [
                    InlineKeyboardButton(
                        f"Previous Proof {target_id}", url=previous_proof_link
                    )
                ],
            ]
        )
    else:
        log_text = (
            "<b>New Community Ban</b>\n"
            f"{BRANDING}\n"
            f"Admin: {user_link(admin_id, admin_first_name)}\n"
            f"User: {user_link(target_id, target_first_name)}\n"
            f"User ID: {target_id}\n"
            f"Reason: {reason}\n\n"
            f"Commit at: {fmt_dt(now_dt)}"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"Proof {target_id}", url=proof_link)]]
        )

    log_message_id = await log_to_channel(context, log_text, reply_markup=keyboard)

    if is_update:
        await bans.update_one(
            {"ban_id": existing["ban_id"]},
            {
                "$set": {
                    "previous_proof_message_id": prev_proof_id,
                    "previous_log_message_id": prev_log_id,
                    "proof_message_id": proof_message_id,
                    "log_message_id": log_message_id,
                    "admin_user_id": admin_id,
                    "reason": reason,
                    "updated_timestamp": now_dt,
                },
                "$inc": {"update_count": 1},
            },
        )
    else:
        await bans.insert_one(
            {
                "ban_id": ban_id,
                "banned_user_id": target_id,
                "reason": reason,
                "admin_user_id": admin_id,
                "proof_message_id": proof_message_id,
                "log_message_id": log_message_id,
                "previous_proof_message_id": None,
                "previous_log_message_id": None,
                "timestamp": now_dt,
                "updated_timestamp": None,
                "is_active": True,
                "update_count": 0,
            }
        )

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=prompt_msg_id,
            text=f"User {target_id} has been banned from the federation. Reason: {reason}",
        )
    except TelegramError:
        pass


async def _post_proof(
    context: ContextTypes.DEFAULT_TYPE,
    media: list[dict],
    caption: str,
) -> int | None:
    try:
        if len(media) == 1:
            item = media[0]
            if item["kind"] == "photo":
                m = await context.bot.send_photo(
                    chat_id=MAIN_GROUP,
                    message_thread_id=PROOF_TOPIC,
                    photo=item["file_id"],
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
            else:
                m = await context.bot.send_video(
                    chat_id=MAIN_GROUP,
                    message_thread_id=PROOF_TOPIC,
                    video=item["file_id"],
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
            return m.message_id

        items = []
        for idx, it in enumerate(media):
            cap = caption if idx == 0 else None
            if it["kind"] == "photo":
                items.append(
                    InputMediaPhoto(
                        media=it["file_id"], caption=cap, parse_mode=ParseMode.HTML
                    )
                )
            else:
                items.append(
                    InputMediaVideo(
                        media=it["file_id"], caption=cap, parse_mode=ParseMode.HTML
                    )
                )
        msgs = await context.bot.send_media_group(
            chat_id=MAIN_GROUP,
            message_thread_id=PROOF_TOPIC,
            media=items,
        )
        return msgs[0].message_id if msgs else None
    except TelegramError as exc:
        logger.exception("Failed to post proof: %s", exc)
        return None


async def cmd_cunban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    if not await is_authorized(user.id):
        await msg.reply_text("You are not authorized.")
        return

    target = await resolve_target(update, context)
    if target is None:
        await msg.reply_text("Cannot resolve user.")
        return

    record = await bans.find_one({"banned_user_id": target.id, "is_active": True})
    if not record:
        await msg.reply_text("User is not banned.")
        return

    await bans.update_one({"ban_id": record["ban_id"]}, {"$set": {"is_active": False}})
    await msg.reply_text(f"User {target.id} has been unbanned from the federation.")
    await log_to_channel(
        context,
        "<b>Community Unban</b>\n"
        f"{BRANDING}\n"
        f"Admin: {user_link(user.id, safe_first_name(user))}\n"
        f"User: {user_link(target.id, target.first_name)}\n"
        f"User ID: {target.id}\n"
        f"Date: {fmt_now()}",
    )
