# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Feature 33: per-affiliated-group member tracking.

Three update paths populate ``member_cache``:

1. ``seed_member_cache`` — on first affiliation, snapshot every reachable
   administrator (Bot API does not allow listing arbitrary members).
2. ``on_message_in_group`` — every message in an active federated group
   upserts its author.
3. ``on_chat_member_update`` — Telegram chat-member events update status
   transitions (joined / left / promoted / restricted / banned).
"""
import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..database import federated_groups, member_cache
from ..utils.format import safe_first_name, utcnow

logger = logging.getLogger(__name__)


def _key(chat_id: int, user_id: int) -> dict:
    return {"chat_id": chat_id, "user_id": user_id}


async def _upsert_member(
    chat_id: int,
    user_id: int,
    *,
    first_name: str | None = None,
    username: str | None = None,
    status: str | None = None,
) -> None:
    payload: dict = {"last_seen": utcnow()}
    if first_name is not None:
        payload["first_name"] = first_name
    if username is not None:
        payload["username"] = username
    if status is not None:
        payload["status"] = status
    await member_cache.update_one(
        _key(chat_id, user_id),
        {
            "$set": payload,
            "$setOnInsert": {"chat_id": chat_id, "user_id": user_id, "first_seen": utcnow()},
        },
        upsert=True,
    )


async def seed_member_cache(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> int:
    """Seed the member cache for a freshly-affiliated group. Returns count seeded."""
    seeded = 0
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
    except TelegramError as exc:
        logger.warning("Could not seed member cache for %s: %s", chat_id, exc)
        return 0
    for cm in admins:
        u = cm.user
        await _upsert_member(
            chat_id,
            u.id,
            first_name=safe_first_name(u),
            username=u.username,
            status=cm.status,
        )
        seeded += 1
    return seeded


async def on_message_in_group(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Upsert the message author into ``member_cache`` for affiliated groups."""
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None or user.is_bot:
        return
    chat_id = msg.chat.id
    grp = await federated_groups.find_one({"chat_id": chat_id, "is_active": True})
    if not grp:
        return
    await _upsert_member(
        chat_id,
        user.id,
        first_name=safe_first_name(user),
        username=user.username,
    )


async def on_chat_member_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Apply per-user chat_member status updates."""
    cm = update.chat_member
    if cm is None:
        return
    chat_id = cm.chat.id
    grp = await federated_groups.find_one({"chat_id": chat_id, "is_active": True})
    if not grp:
        return
    new = cm.new_chat_member
    user = new.user
    await _upsert_member(
        chat_id,
        user.id,
        first_name=safe_first_name(user),
        username=user.username,
        status=new.status,
    )
