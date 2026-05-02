# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Member tracker — caches user info and enforces bans on join events."""
from __future__ import annotations

import logging

from telegram import Bot, User

from tcbot import database as db

log = logging.getLogger(__name__)


class MemberTracker:
    """Handles member join and leave events for affiliated groups.

    Extend the behaviour currently in greeting.py (which covers only
    MAIN_GROUP and EXEC_GROUP) to any affiliated group by wiring this
    tracker into your join-event handlers.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def on_join(self, chat_id: int, user: User) -> bool:
        """Process a new member join event.

        - Caches the user's info in the users collection.
        - Checks and enforces the federation ban list.

        Returns True if the user was federation-banned and removed.
        """
        if user.is_bot:
            return False

        await db.users_db.upsert_user(
            user.id, user.username, user.first_name, user.last_name,
        )

        ban = await db.bans_db.get_active_ban(user.id)
        if not ban:
            return False

        try:
            await self._bot.ban_chat_member(chat_id, user.id)
            log.info(
                "MemberTracker: auto-banned %d in %d (ban_id: %s)",
                user.id, chat_id, ban.get("ban_id"),
            )
        except Exception as exc:
            log.warning(
                "MemberTracker: auto-ban failed for %d in %d: %s",
                user.id, chat_id, exc,
            )

        return True

    async def on_leave(self, chat_id: int, user: User) -> None:
        """Process a member leave event — currently only logs debug info."""
        if user.is_bot:
            return
        log.debug("MemberTracker: %d left chat %d", user.id, chat_id)
