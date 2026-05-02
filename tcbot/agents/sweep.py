# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation sweep — retroactively applies all active bans across every affiliated group."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from telegram import Bot

from tcbot import database as db

log = logging.getLogger(__name__)


@dataclass
class SweepResult:
    chat_id: int
    banned:  int = 0
    errors:  int = 0


class SweepAgent:
    """Applies all active federation bans across all affiliated groups.

    Useful after a new ban is issued (to catch members who are already inside
    a group) or as a scheduled maintenance sweep.
    """

    def __init__(self, bot: Bot, *, concurrency: int = 4, delay: float = 0.05) -> None:
        self._bot         = bot
        self._concurrency = concurrency
        self._delay       = delay

    async def sweep_group(self, chat_id: int) -> SweepResult:
        """Ban all federation-banned members currently present in `chat_id`."""
        result = SweepResult(chat_id=chat_id)
        bans   = await db.bans_db.active_bans()

        for ban in bans:
            uid = ban.get("banned_user_id")
            if not uid:
                continue
            try:
                member = await self._bot.get_chat_member(chat_id, uid)
                if member.status in ("member", "administrator", "creator", "restricted"):
                    await self._bot.ban_chat_member(chat_id, uid)
                    result.banned += 1
                    log.debug("Sweep: banned %d in %d", uid, chat_id)
            except Exception as exc:
                log.debug("Sweep: skip %d in %d — %s", uid, chat_id, exc)
                result.errors += 1
            await asyncio.sleep(self._delay)

        return result

    async def sweep_all(self) -> list[SweepResult]:
        """Run `sweep_group()` across every affiliated group with bounded concurrency."""
        groups  = await db.groups_db.active_groups()
        results: list[SweepResult] = []
        sem     = asyncio.Semaphore(self._concurrency)

        async def _bounded(grp: dict) -> SweepResult:
            async with sem:
                return await self.sweep_group(grp["chat_id"])

        tasks = [asyncio.create_task(_bounded(g)) for g in groups]
        for done in asyncio.as_completed(tasks):
            results.append(await done)

        log.info(
            "SweepAgent: %d groups swept — %d banned, %d errors",
            len(results),
            sum(r.banned for r in results),
            sum(r.errors for r in results),
        )
        return results

    def format_summary(self, results: list[SweepResult]) -> str:
        banned = sum(r.banned for r in results)
        errors = sum(r.errors for r in results)
        return (
            f"Sweep complete — {len(results)} groups scanned.\n"
            f"Users banned: {banned}\n"
            f"Errors: {errors}"
        )
