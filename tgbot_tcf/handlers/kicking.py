# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Kick command handler (PRD Feature 39).

This file is intentionally thin: it parses the Telegram update, enforces
every validation gate mandated by the PRD, then delegates execution,
recording, and log dispatch to :mod:`tgbot_tcf.modules.kicking`.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..database import groups_repo
from ..modules import kicking, log_templates
from ..modules.messages import M
from ..utils.format import safe_first_name
from ..utils.logger import log_to_channel
from .helper import auth, targets

logger = logging.getLogger(__name__)


async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /kick, /tckkick, /kickout."""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    # Step 1 — authorisation: TC Owner or Admin only.
    if not await auth.require_authorized(msg, user.id):
        return

    # Step 2 — resolve target.
    target = await targets.resolve_or_complain(update, context, msg)
    if target is None:
        return

    # Step 3 — target protection: cannot kick a TC admin or owner.
    if await auth.is_authorized(target.id):
        await msg.reply_text(M.KICK_TC_ROLE_BLOCKED)
        return

    # Step 4 — self-kick guard.
    if target.id == user.id:
        await msg.reply_text(M.KICK_SELF_BLOCKED)
        return

    # Step 5 — scope: command is only valid inside a connected group.
    if not await groups_repo.find_active(chat.id):
        await msg.reply_text(M.KICK_CONNECTED_ONLY)
        return

    # Step 6 — extract optional reason.
    reason = targets.reason_from_args(context, update, target) or None

    # Step 7 — execute the ban-then-unban sequence.
    result = await kicking.execute_kick(
        context, chat_id=chat.id, target_id=target.id, admin_id=user.id
    )
    if not result.success:
        await msg.reply_text(result.error_message or M.KICK_FAILED)
        return

    # Step 8 — persist audit record.
    kick_id, ts = kicking.make_kick_id(target.id)
    await kicking.record_kick(
        kicked_user_id=target.id,
        chat_id=chat.id,
        reason=reason,
        admin_user_id=user.id,
        timestamp=ts,
    )

    # Step 9 — dispatch log to channel.
    admin_name = safe_first_name(user)
    group_title = chat.title or str(chat.id)
    group_username = getattr(chat, "username", None)
    log_text = log_templates.member_kicked(
        admin_id=user.id,
        admin_name=admin_name,
        target_id=target.id,
        target_name=target.first_name,
        chat_id=chat.id,
        group_title=group_title,
        group_username=group_username,
        reason=reason,
        timestamp=ts,
    )
    await log_to_channel(context, log_text)

    # Step 10 — reply confirmation.
    await msg.reply_text(
        M.KICK_SUCCESS.format(
            target_name=target.first_name,
            target_id=target.id,
        )
    )
