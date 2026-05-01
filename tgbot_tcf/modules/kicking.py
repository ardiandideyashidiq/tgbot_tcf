# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Kick lifecycle business logic.

A kick removes a user from a single federated group only. Unlike a federation
ban, it:

* Has no proof-collection step.
* Does not propagate across other groups.
* Cannot be appealed (the user may rejoin at any time).
* Is logged to the federation log channel for audit purposes only.

Implementation detail: Telegram's Bot API has no dedicated "kick" endpoint.
Instead we call ``ban_chat_member`` (which removes and blocks the user from
the group) immediately followed by ``unban_chat_member`` (which lifts the
block). This achieves the desired one-group-ejection effect without leaving
the user on the permanent ban list of that group.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..database import kicks_repo
from ..utils.format import utcnow

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KickResult:
    success: bool
    error_message: str | None = None


async def execute_kick(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_id: int,
    target_id: int,
    admin_id: int,
) -> KickResult:
    """Perform the ban-then-unban sequence that implements a group kick.

    Returns a :class:`KickResult`. On Telegram API failure the result carries
    the caller-friendly error message so the handler can reply directly.
    """
    try:
        await context.bot.ban_chat_member(chat_id, target_id)
        await context.bot.unban_chat_member(chat_id, target_id)
    except TelegramError as exc:
        msg = str(exc).lower()
        if "not enough rights" in msg or "restricted" in msg:
            return KickResult(
                success=False,
                error_message=(
                    "I do not have permission to kick members in this group."
                ),
            )
        logger.warning(
            "Kick failed for user %s in chat %s: %s", target_id, chat_id, exc
        )
        return KickResult(
            success=False,
            error_message="Failed to kick the user. Please try again.",
        )
    return KickResult(success=True)


async def record_kick(
    *,
    kicked_user_id: int,
    chat_id: int,
    reason: str | None,
    admin_user_id: int,
    timestamp: datetime,
) -> str:
    """Persist the kick audit record and return the generated kick_id."""
    kick_id = f"{kicked_user_id}_{int(timestamp.timestamp())}"
    await kicks_repo.insert_kick(
        kick_id=kick_id,
        kicked_user_id=kicked_user_id,
        chat_id=chat_id,
        reason=reason,
        admin_user_id=admin_user_id,
        timestamp=timestamp,
    )
    return kick_id


def make_kick_id(user_id: int) -> tuple[str, datetime]:
    """Generate a deterministic kick_id and return it together with the timestamp."""
    now = utcnow()
    return f"{user_id}_{int(now.timestamp())}", now
