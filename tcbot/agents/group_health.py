# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group health agent — detects stale or migrated groups and keeps the DB clean."""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.error import BadRequest, Forbidden

from tcbot import database as db

log = logging.getLogger(__name__)


class GroupHealthAgent:
    """Probes every affiliated group and deactivates stale records.

    A group is considered stale when the bot has been removed, the group
    has been deleted, or the chat ID is no longer reachable. Migrated
    supergroups are detected via the `migrate_to_chat_id` attribute and
    their records are updated in place.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def run(self, *, auto_remove: bool = True) -> dict[str, list[int]]:
        """Probe all affiliated groups and classify them.

        Returns:
            {
                "healthy":  [...],   # reachable and bot is present
                "stale":    [...],   # unreachable or bot removed
                "migrated": [...],   # chat_id updated due to supergroup migration
            }
        """
        groups = await db.groups_db.active_groups()
        report: dict[str, list[int]] = {
            "healthy":  [],
            "stale":    [],
            "migrated": [],
        }

        for grp in groups:
            chat_id = grp["chat_id"]
            result  = await self._probe(chat_id)

            if result == "healthy":
                report["healthy"].append(chat_id)

            elif result == "stale":
                report["stale"].append(chat_id)
                if auto_remove:
                    await db.groups_db.deactivate_group(chat_id)
                    log.info("GroupHealthAgent: deactivated stale group %d", chat_id)

            elif isinstance(result, int):
                # result is the new chat_id after migration
                new_id = result
                report["migrated"].append(chat_id)
                if auto_remove:
                    await db.groups_db.deactivate_group(chat_id)
                    await db.groups_db.add_group(new_id, grp.get("title", ""), grp.get("owner_id", 0))
                    log.info(
                        "GroupHealthAgent: migrated %d → %d", chat_id, new_id,
                    )

        log.info(
            "GroupHealthAgent: healthy=%d stale=%d migrated=%d",
            len(report["healthy"]),
            len(report["stale"]),
            len(report["migrated"]),
        )
        return report

    async def summary(self) -> str:
        """Run a dry-run health check and return a human-readable summary."""
        report = await self.run(auto_remove=False)
        return (
            f"Group health check:\n"
            f"Healthy:  {len(report['healthy'])}\n"
            f"Stale:    {len(report['stale'])}\n"
            f"Migrated: {len(report['migrated'])}"
        )

    async def _probe(self, chat_id: int) -> str | int:
        """Return 'healthy', 'stale', or new_chat_id (int) on migration."""
        try:
            chat = await self._bot.get_chat(chat_id)
            if getattr(chat, "migrate_to_chat_id", None):
                return chat.migrate_to_chat_id
            return "healthy"
        except Forbidden:
            return "stale"
        except BadRequest as exc:
            log.debug("GroupHealthAgent: BadRequest for %d — %s", chat_id, exc)
            return "stale"
        except Exception as exc:
            log.warning("GroupHealthAgent: unexpected error for %d — %s", chat_id, exc)
            return "stale"
