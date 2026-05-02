# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation ban enforcement – applied when members join affiliated groups.

Usage
-----
Instantiate once per application lifecycle and call `enforce_on_join` from any
join-event handler, or call `sweep_group` to retroactively remove banned members
from an existing group.

    enforcer = BanEnforcer(bot)
    banned = await enforcer.enforce_on_join(chat_id, user_id, user_fname)
"""
from __future__ import annotations

import logging

from telegram import Bot, ChatMember

from tcbot import database as db

log = logging.getLogger(__name__)


class BanEnforcer:
    """Checks and enforces the federation ban list.

    Designed to be called from join-event handlers across all affiliated groups,
    not just the main/exec group.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def enforce_on_join(self, chat_id: int, user_id: int, user_fname: str) -> bool:
        """Ban `user_id` from `chat_id` if they appear in the federation banlist.

        Returns True if the user was banned, False if they are clean.
        """
        record = await db.bans_db.get_active_ban(user_id)
        if not record:
            return False
        try:
            await self._bot.ban_chat_member(chat_id, user_id)
            log.info("Auto-banned %d in chat %d (fed ban: %s)", user_id, chat_id, record.get("ban_id"))
        except Exception as exc:
            log.warning("Auto-ban failed for %d in %d: %s", user_id, chat_id, exc)
        return True

    async def sweep_group(self, chat_id: int) -> tuple[int, int]:
        """Scan a group for members who are federation-banned and remove them.

        Returns (banned_count, error_count). This is a best-effort operation —
        errors on individual members do not abort the sweep.
        """
        banned = error = 0
        try:
            all_bans = await db.bans_db.active_bans()
        except Exception as exc:
            log.error("sweep_group: failed to fetch ban list: %s", exc)
            return 0, 1

        for record in all_bans:
            uid = record.get("banned_user_id")
            if not uid:
                continue
            try:
                member: ChatMember = await self._bot.get_chat_member(chat_id, uid)
                if member.status in ("member", "administrator", "creator", "restricted"):
                    await self._bot.ban_chat_member(chat_id, uid)
                    banned += 1
                    log.info("Sweep: banned %d from %d", uid, chat_id)
            except Exception as exc:
                log.debug("Sweep: skip %d in %d — %s", uid, chat_id, exc)
                error += 1

        log.info("sweep_group %d: banned=%d errors=%d", chat_id, banned, error)
        return banned, error

    async def sweep_all_groups(self) -> dict[int, tuple[int, int]]:
        """Run `sweep_group` across every currently affiliated group.

        Returns a mapping of chat_id → (banned_count, error_count).
        """
        results: dict[int, tuple[int, int]] = {}
        groups = await db.groups_db.active_groups()
        for grp in groups:
            chat_id = grp["chat_id"]
            results[chat_id] = await self.sweep_group(chat_id)
        return results
