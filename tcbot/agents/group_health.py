# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group health monitoring – detects stale affiliated groups and handles migrations.

A group is considered stale when:
  - The bot was removed (Forbidden)
  - The chat was deleted or otherwise unavailable (BadRequest)

Migrated groups (Telegram supergroup upgrades) are updated in-place rather than
deactivated, preserving federation membership.

Usage
-----
    agent = GroupHealthAgent(bot)
    report = await agent.run()
    # report = {"healthy": [...], "stale": [...], "migrated": [...]}
"""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.error import BadRequest, ChatMigrated, Forbidden

from tcbot import database as db

log = logging.getLogger(__name__)


class GroupHealthAgent:
    """Verifies the bot can still operate in each affiliated group.

    Stale groups are deactivated automatically when `auto_remove=True`.
    Migrated groups have their chat_id updated transparently.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def run(self, *, auto_remove: bool = True) -> dict[str, list[int]]:
        """Iterate all affiliated groups and check bot membership.

        Returns a dict with keys:
          - "healthy"  — bot is present and the group is reachable
          - "stale"    — bot was removed or group is gone (deactivated if auto_remove)
          - "migrated" — group migrated to a new chat_id (record updated)
        """
        result: dict[str, list[int]] = {"healthy": [], "stale": [], "migrated": []}
        groups = await db.groups_db.active_groups()

        for grp in groups:
            chat_id = grp["chat_id"]
            outcome, new_id = await self._check_single(chat_id)
            result[outcome].append(chat_id)

            if outcome == "stale" and auto_remove:
                await self._deactivate(chat_id, grp.get("title", str(chat_id)))
            elif outcome == "migrated" and new_id is not None:
                await self._handle_migration(grp, chat_id, new_id)

        log.info(
            "GroupHealthAgent: healthy=%d stale=%d migrated=%d",
            len(result["healthy"]),
            len(result["stale"]),
            len(result["migrated"]),
        )
        return result

    async def _check_single(self, chat_id: int) -> tuple[str, int | None]:
        """Return (outcome, new_chat_id_or_None)."""
        try:
            await self._bot.get_chat(chat_id)
            return "healthy", None
        except Forbidden:
            log.warning("GroupHealth: bot removed from %d", chat_id)
            return "stale", None
        except ChatMigrated as exc:
            log.info("GroupHealth: %d migrated to %d", chat_id, exc.new_chat_id)
            return "migrated", exc.new_chat_id
        except BadRequest as exc:
            log.warning("GroupHealth: %d unavailable — %s", chat_id, exc)
            return "stale", None
        except Exception as exc:
            # Unknown errors are treated as transient; do not deactivate.
            log.warning("GroupHealth: %d unknown error (skipped) — %s", chat_id, exc)
            return "healthy", None

    async def _deactivate(self, chat_id: int, title: str) -> None:
        try:
            await db.groups_db.deactivate_group(chat_id)
            log.info("GroupHealth: deactivated stale group %d (%s)", chat_id, title)
        except Exception as exc:
            log.error("GroupHealth: failed to deactivate %d: %s", chat_id, exc)

    async def _handle_migration(self, grp: dict, old_id: int, new_id: int) -> None:
        """Re-register the group under its new chat_id and deactivate the old record."""
        try:
            await db.groups_db.add_group(new_id, grp.get("title", ""), grp.get("added_by", 0))
            await db.groups_db.deactivate_group(old_id)
            log.info("GroupHealth: migrated group %d → %d", old_id, new_id)
        except Exception as exc:
            log.error("GroupHealth: failed to handle migration %d → %d: %s", old_id, new_id, exc)

    async def summary(self) -> str:
        """Run a health check and return a human-readable summary string."""
        report = await self.run(auto_remove=False)
        return (
            f"Group Health Report\n"
            f"Healthy:  {len(report['healthy'])}\n"
            f"Stale:    {len(report['stale'])}\n"
            f"Migrated: {len(report['migrated'])}"
        )
