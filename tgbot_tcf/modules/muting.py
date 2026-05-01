# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Mute / unmute lifecycle business logic.

A mute restricts all sending permissions in a single connected group.
It is not a federation-wide action. The bot uses
``restrict_chat_member`` with an all-False ``ChatPermissions`` object to
silence a user and restores default permissions via an all-True object on
unmute.

Duration tokens follow the format ``<int><unit>`` where unit is one of:
``m`` (minutes), ``h`` (hours), ``d`` (days). No token means permanent.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from telegram import ChatPermissions
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..database import muted_repo
from ..utils.format import utcnow

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"^(\d+)(m|h|d)$")

_MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
)

_DEFAULT_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=False,
)


@dataclass(frozen=True, slots=True)
class MuteResult:
    success: bool
    error_message: str | None = None


def parse_duration(token: str) -> timedelta | None:
    """Return a :class:`timedelta` for a token like ``30m``, ``2h``, ``1d``.

    Returns ``None`` when the token does not match the duration pattern,
    allowing the caller to treat it as the beginning of a reason string.
    """
    match = _DURATION_RE.match(token.strip().lower())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)


def format_duration(delta: timedelta | None) -> str:
    """Human-readable duration label for use in replies and log entries."""
    if delta is None:
        return "Permanent"
    total = int(delta.total_seconds())
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "< 1m"


def split_duration_and_reason(
    remaining_args: list[str],
) -> tuple[timedelta | None, str | None]:
    """Separate an optional duration token from the reason string.

    The first token is consumed as a duration only when it matches the
    duration pattern; otherwise the full ``remaining_args`` list forms the
    reason.
    """
    if not remaining_args:
        return None, None
    delta = parse_duration(remaining_args[0])
    if delta is not None:
        reason_parts = remaining_args[1:]
        return delta, " ".join(reason_parts) if reason_parts else None
    return None, " ".join(remaining_args)


async def execute_mute(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_id: int,
    target_id: int,
    until_date: datetime | None,
) -> MuteResult:
    """Apply ``restrict_chat_member`` with all permissions revoked."""
    try:
        await context.bot.restrict_chat_member(
            chat_id,
            target_id,
            permissions=_MUTE_PERMISSIONS,
            until_date=until_date,
        )
    except TelegramError as exc:
        msg = str(exc).lower()
        if "not enough rights" in msg or "restricted" in msg:
            return MuteResult(
                success=False,
                error_message=(
                    "I do not have permission to restrict members in this group."
                ),
            )
        logger.warning(
            "Mute failed for user %s in chat %s: %s", target_id, chat_id, exc
        )
        return MuteResult(
            success=False,
            error_message="Failed to mute the user. Please try again.",
        )
    return MuteResult(success=True)


async def execute_unmute(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_id: int,
    target_id: int,
) -> MuteResult:
    """Restore default group permissions for the target user."""
    try:
        await context.bot.restrict_chat_member(
            chat_id,
            target_id,
            permissions=_DEFAULT_PERMISSIONS,
        )
    except TelegramError as exc:
        msg = str(exc).lower()
        if "not enough rights" in msg or "restricted" in msg:
            return MuteResult(
                success=False,
                error_message=(
                    "I do not have permission to unrestrict members in this group."
                ),
            )
        logger.warning(
            "Unmute failed for user %s in chat %s: %s", target_id, chat_id, exc
        )
        return MuteResult(
            success=False,
            error_message="Failed to unmute the user. Please try again.",
        )
    return MuteResult(success=True)


async def record_mute(
    *,
    muted_user_id: int,
    chat_id: int,
    reason: str | None,
    admin_user_id: int,
    until_date: datetime | None,
    timestamp: datetime,
) -> str:
    """Persist the mute record and return the generated mute_id."""
    mute_id = f"{muted_user_id}_{chat_id}_{int(timestamp.timestamp())}"
    await muted_repo.insert_mute(
        mute_id=mute_id,
        muted_user_id=muted_user_id,
        chat_id=chat_id,
        reason=reason,
        admin_user_id=admin_user_id,
        until_date=until_date,
        timestamp=timestamp,
    )
    return mute_id


def compute_until_date(delta: timedelta | None) -> datetime | None:
    """Convert a timedelta into an absolute UTC datetime, or ``None`` for permanent."""
    if delta is None:
        return None
    return utcnow() + delta


def aware_utcnow() -> datetime:
    """UTC-aware datetime used as ``until_date`` when Telegram needs one."""
    return datetime.now(timezone.utc)
