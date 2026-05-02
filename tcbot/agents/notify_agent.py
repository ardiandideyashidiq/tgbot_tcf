# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Notification agent — route system alerts to the owner, all staff, or the log channel."""
from __future__ import annotations

import logging

from telegram import Bot

from tcbot import cfg, database as db

log = logging.getLogger(__name__)


class NotifyAgent:
    """Routes notifications to the TCF owner, all staff, or the configured log channel.

    Used internally to surface events that cannot be replied to inline —
    e.g. failed group operations, scheduled task results, audit alerts.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def notify_owner(self, text: str, **kwargs) -> bool:
        """Send `text` to the current federation owner.

        Returns True on success. Logs a warning and returns False if no
        owner is set or the message cannot be delivered.
        """
        owner_id = await db.admins_db.get_owner_id()
        if not owner_id:
            log.warning("NotifyAgent: no owner set — notification dropped")
            return False
        try:
            await self._bot.send_message(owner_id, text, **kwargs)
            return True
        except Exception as exc:
            log.warning("NotifyAgent: failed to notify owner %d: %s", owner_id, exc)
            return False

    async def notify_all_staff(self, text: str, **kwargs) -> tuple[int, int]:
        """Broadcast `text` to every admin and the owner.

        Returns (success_count, fail_count).
        """
        owner_id = await db.admins_db.get_owner_id()
        admins   = await db.admins_db.all_admins()

        targets: set[int] = {a["user_id"] for a in admins}
        if owner_id:
            targets.add(owner_id)

        success = fail = 0
        for uid in targets:
            try:
                await self._bot.send_message(uid, text, **kwargs)
                success += 1
            except Exception as exc:
                log.debug("NotifyAgent: failed to notify %d: %s", uid, exc)
                fail += 1

        log.info("NotifyAgent: notified %d/%d staff", success, success + fail)
        return success, fail

    async def log_channel(self, text: str, **kwargs) -> bool:
        """Post `text` to the configured log channel/topic.

        Returns True on success.
        """
        lc, lt = cfg.logs
        if not lc:
            return False
        try:
            await self._bot.send_message(lc, text, message_thread_id=lt, **kwargs)
            return True
        except Exception as exc:
            log.warning("NotifyAgent: log channel post failed: %s", exc)
            return False
