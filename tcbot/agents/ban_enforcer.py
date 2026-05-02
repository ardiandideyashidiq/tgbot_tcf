# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Ban enforcer — checks and applies federation bans at the point of member join."""
from __future__ import annotations

import logging

from telegram import Bot

from tcbot import database as db

log = logging.getLogger(__name__)


class BanEnforcer:
    """Enforces the federation ban list when members join affiliated groups.

    Wire `enforce_on_join()` into your join-event handlers to catch banned
    users the moment they enter any affiliated group. Use `sweep_group()` or
    `sweep_all_groups()` for retroactive enforcement after new bans are issued.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def enforce_on_join(
        self,
        chat_id: int,
        user_id: int,
        user_fname: str,
    ) -> bool:
        """Check and enforce federation ban for a user joining `chat_id`.

        Returns True if the user was banned and removed, False if they are clean.
        """
        ban = await db.bans_db.get_active_ban(user_id)
        if not ban:
            return False

        try:
            await self._bot.ban_chat_member(chat_id, user_id)
            log.info(
                "BanEnforcer: removed %d ('%s') from %d (ban_id: %s)",
                user_id, user_fname, chat_id, ban.get("ban_id"),
            )
            return True
        except Exception as exc:
            log.warning(
                "BanEnforcer: could not ban %d in %d: %s",
                user_id, chat_id, exc,
            )
            return False

    async def sweep_group(self, chat_id: int) -> tuple[int, int]:
        """Ban all currently-present federation-banned members in `chat_id`.

        Returns (banned_count, error_count). Individual errors do not abort
        the sweep.
        """
        bans    = await db.bans_db.active_bans()
        banned  = 0
        errors  = 0

        for ban in bans:
            uid = ban.get("banned_user_id")
            if not uid:
                continue
            try:
                member = await self._bot.get_chat_member(chat_id, uid)
                if member.status in ("member", "administrator", "creator", "restricted"):
                    await self._bot.ban_chat_member(chat_id, uid)
                    banned += 1
                    log.debug("BanEnforcer sweep: banned %d in %d", uid, chat_id)
            except Exception as exc:
                log.debug("BanEnforcer sweep: skip %d in %d — %s", uid, chat_id, exc)
                errors += 1

        return banned, errors

    async def sweep_all_groups(self) -> dict[int, tuple[int, int]]:
        """Run `sweep_group()` across every affiliated group.

        Returns a mapping of `chat_id → (banned, errors)`.
        """
        groups  = await db.groups_db.active_groups()
        results: dict[int, tuple[int, int]] = {}

        for grp in groups:
            cid = grp["chat_id"]
            results[cid] = await self.sweep_group(cid)

        total_banned = sum(v[0] for v in results.values())
        total_errors = sum(v[1] for v in results.values())
        log.info(
            "BanEnforcer: swept %d groups — %d banned, %d errors",
            len(results), total_banned, total_errors,
        )
        return results
