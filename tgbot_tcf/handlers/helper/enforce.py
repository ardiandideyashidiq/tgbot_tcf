# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Automatic cross-group ban / unban enforcement (PROMPT Features 5, 6, 8).

Used after every Transsion Core ban, unban, and approved appeal — there is no
manual sync command in TCF. Each routine iterates over active federated groups
and only acts where the bot has ``can_restrict_members``.
"""
import logging

from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ...database import federated_groups

logger = logging.getLogger(__name__)


async def enforce_ban_across_groups(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> tuple[int, int]:
    """Ban ``user_id`` across every active federated group. Returns (success, failure)."""
    success = 0
    failure = 0
    cursor = federated_groups.find({"is_active": True})
    async for grp in cursor:
        chat_id = grp["chat_id"]
        try:
            me = await context.bot.get_chat_member(chat_id, context.bot.id)
            if not getattr(me, "can_restrict_members", False):
                failure += 1
                continue
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            success += 1
        except TelegramError as exc:
            failure += 1
            logger.warning("Cross-group ban in %s failed: %s", chat_id, exc)
    return success, failure


async def enforce_unban_across_groups(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> tuple[int, int]:
    """Unban ``user_id`` across every active federated group. Returns (success, failure)."""
    success = 0
    failure = 0
    cursor = federated_groups.find({"is_active": True})
    async for grp in cursor:
        chat_id = grp["chat_id"]
        try:
            me = await context.bot.get_chat_member(chat_id, context.bot.id)
            if not getattr(me, "can_restrict_members", False):
                failure += 1
                continue
            await context.bot.unban_chat_member(
                chat_id=chat_id, user_id=user_id, only_if_banned=True
            )
            success += 1
        except TelegramError as exc:
            failure += 1
            logger.warning("Cross-group unban in %s failed: %s", chat_id, exc)
    return success, failure
