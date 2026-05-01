# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Warn / unwarn / warns command handlers (PRD Features 36–38).

Warnings are scoped to the group where the command is issued. They do not
propagate to other groups and are not related to the federation ban system.

Thin handler pattern: validation here, business logic in
:mod:`tgbot_tcf.modules.warnings`.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..database import groups_repo
from ..modules import log_templates, warnings
from ..modules.messages import M
from ..utils.format import safe_first_name, utcnow
from ..utils.logger import log_to_channel
from .helper import auth, targets

logger = logging.getLogger(__name__)


async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /warn, /twarn."""
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

    # Step 3 — target protection: cannot warn TC admins or the owner.
    if await auth.is_authorized(target.id):
        await msg.reply_text(M.WARN_TC_ROLE_BLOCKED)
        return

    # Step 4 — self-warn guard.
    if target.id == user.id:
        await msg.reply_text(M.WARN_SELF_BLOCKED)
        return

    # Step 5 — scope: connected groups only.
    if not await groups_repo.find_active(chat.id):
        await msg.reply_text(M.WARN_CONNECTED_ONLY)
        return

    # Step 6 — reason is required.
    reason = targets.reason_from_args(context, update, target).strip()
    if not reason:
        await msg.reply_text(M.WARN_NEEDS_REASON)
        return

    # Step 7 — persist the warning.
    ts = utcnow()
    _warn_id, count = await warnings.record_warn(
        warned_user_id=target.id,
        chat_id=chat.id,
        reason=reason,
        admin_user_id=user.id,
        timestamp=ts,
    )

    # Step 8 — dispatch log.
    admin_name = safe_first_name(user)
    group_title = chat.title or str(chat.id)
    group_username = getattr(chat, "username", None)
    log_text = log_templates.member_warned(
        admin_id=user.id,
        admin_name=admin_name,
        target_id=target.id,
        target_name=target.first_name,
        chat_id=chat.id,
        group_title=group_title,
        group_username=group_username,
        reason=reason,
        warn_count=count,
        timestamp=ts,
    )
    await log_to_channel(context, log_text)

    # Step 9 — reply with confirmation including the new warn count.
    await msg.reply_text(
        M.WARN_SUCCESS.format(
            target_name=target.first_name,
            target_id=target.id,
            count=count,
        )
    )


async def cmd_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unwarn, /tunwarn."""
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
        await msg.reply_text(M.WARN_CONNECTED_ONLY)
        return

    # Step 4 — find and deactivate the most recent active warning.
    removed = await warnings.remove_latest_warn(target.id, chat.id)
    if removed is None:
        await msg.reply_text(M.UNWARN_NONE_FOUND)
        return

    # Step 5 — dispatch log.
    ts = utcnow()
    admin_name = safe_first_name(user)
    group_title = chat.title or str(chat.id)
    group_username = getattr(chat, "username", None)
    log_text = log_templates.warning_removed(
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

    # Step 6 — reply.
    await msg.reply_text(
        M.UNWARN_SUCCESS.format(
            target_name=target.first_name,
            target_id=target.id,
        )
    )


async def cmd_warns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /warns, /twarnlist — list active warnings for a user in this group."""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None or user is None or chat is None:
        return

    # Viewing the warn list requires at least TC Admin level.
    if not await auth.require_authorized(msg, user.id):
        return

    # Resolve target.
    target = await targets.resolve_or_complain(update, context, msg)
    if target is None:
        return

    # Scope: connected groups only.
    if not await groups_repo.find_active(chat.id):
        await msg.reply_text(M.WARN_CONNECTED_ONLY)
        return

    # Build and send the list.
    summary = await warnings.build_warns_list(
        target.id, chat.id, target.first_name
    )
    if not summary:
        await msg.reply_text(M.WARNS_EMPTY)
        return

    await msg.reply_text(summary, parse_mode="HTML")
