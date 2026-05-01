# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Mute / unmute command handlers (PRD Features 34–35).

/mute and /unmute are group-scoped commands: they restrict or restore
messaging permissions for a single user in the current connected group.
They do not propagate across other groups.

Thin handler pattern: validation here, execution in
:mod:`tgbot_tcf.modules.muting`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from ..database import groups_repo, muted_repo
from ..modules import log_templates, muting
from ..modules.messages import M
from ..utils.format import safe_first_name, utcnow
from ..utils.logger import log_to_channel
from .helper import auth, targets

logger = logging.getLogger(__name__)


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mute, /tmute."""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    # Step 1 — authorisation.
    if not await auth.require_authorized(msg, user.id):
        return

    # Step 2 — resolve target.
    target = await targets.resolve_or_complain(update, context, msg)
    if target is None:
        return

    # Step 3 — target protection.
    if await auth.is_authorized(target.id):
        await msg.reply_text(M.MUTE_TC_ROLE_BLOCKED)
        return

    # Step 4 — self-mute guard.
    if target.id == user.id:
        await msg.reply_text(M.MUTE_SELF_BLOCKED)
        return

    # Step 5 — scope: connected groups only.
    if not await groups_repo.find_active(chat.id):
        await msg.reply_text(M.MUTE_CONNECTED_ONLY)
        return

    # Step 6 — parse [duration] [reason] from the remaining arguments.
    args = context.args or []
    remaining = args[1:] if target.from_args else args
    delta, reason = muting.split_duration_and_reason(remaining)

    # Step 7 — compute the absolute until_date for Telegram.
    until_naive = muting.compute_until_date(delta)
    until_aware: datetime | None = None
    if until_naive is not None:
        until_aware = until_naive.replace(tzinfo=timezone.utc)

    # Step 8 — execute mute via Telegram API.
    result = await muting.execute_mute(
        context, chat_id=chat.id, target_id=target.id, until_date=until_aware
    )
    if not result.success:
        await msg.reply_text(result.error_message or M.MUTE_FAILED)
        return

    # Step 9 — persist the mute record.
    ts = utcnow()
    await muting.record_mute(
        muted_user_id=target.id,
        chat_id=chat.id,
        reason=reason,
        admin_user_id=user.id,
        until_date=until_naive,
        timestamp=ts,
    )

    # Step 10 — dispatch log.
    duration_text = muting.format_duration(delta)
    admin_name = safe_first_name(user)
    group_title = chat.title or str(chat.id)
    group_username = getattr(chat, "username", None)
    log_text = log_templates.member_muted(
        admin_id=user.id,
        admin_name=admin_name,
        target_id=target.id,
        target_name=target.first_name,
        chat_id=chat.id,
        group_title=group_title,
        group_username=group_username,
        duration_text=duration_text,
        reason=reason,
        timestamp=ts,
    )
    await log_to_channel(context, log_text)

    # Step 11 — reply.
    if delta is not None:
        reply = M.MUTE_SUCCESS_TIMED.format(
            target_name=target.first_name,
            target_id=target.id,
            duration=duration_text,
        )
    else:
        reply = M.MUTE_SUCCESS.format(
            target_name=target.first_name,
            target_id=target.id,
        )
    await msg.reply_text(reply)


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unmute, /tunmute."""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    # Step 1 — authorisation.
    if not await auth.require_authorized(msg, user.id):
        return

    # Step 2 — resolve target.
    target = await targets.resolve_or_complain(update, context, msg)
    if target is None:
        return

    # Step 3 — scope: connected groups only.
    if not await groups_repo.find_active(chat.id):
        await msg.reply_text(M.MUTE_CONNECTED_ONLY)
        return

    # Step 4 — look up the active mute record.
    mute_record = await muted_repo.find_active_mute(target.id, chat.id)
    if mute_record is None:
        await msg.reply_text(M.UNMUTE_NOT_MUTED)
        return

    # Step 5 — restore permissions via Telegram API.
    result = await muting.execute_unmute(
        context, chat_id=chat.id, target_id=target.id
    )
    if not result.success:
        await msg.reply_text(result.error_message or M.UNMUTE_FAILED)
        return

    # Step 6 — deactivate the DB record.
    await muted_repo.deactivate_mute(mute_record["mute_id"])

    # Step 7 — dispatch log.
    ts = utcnow()
    admin_name = safe_first_name(user)
    group_title = chat.title or str(chat.id)
    group_username = getattr(chat, "username", None)
    log_text = log_templates.member_unmuted(
        admin_id=user.id,
        admin_name=admin_name,
        target_id=target.id,
        target_name=target.first_name,
        chat_id=chat.id,
        group_title=group_title,
        group_username=group_username,
        timestamp=ts,
    )
    await log_to_channel(context, log_text)

    # Step 8 — reply.
    await msg.reply_text(
        M.UNMUTE_SUCCESS.format(
            target_name=target.first_name,
            target_id=target.id,
        )
    )
