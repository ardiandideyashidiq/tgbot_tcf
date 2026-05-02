# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Broadcast agent — send messages to all affiliated groups with rate limiting and retry."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from telegram import Bot, Message

from tcbot import database as db

log = logging.getLogger(__name__)

_DEFAULT_DELAY   = 0.05  # 50 ms between groups — well under flood limits
_DEFAULT_RETRIES = 2


@dataclass
class BroadcastResult:
    total:      int       = 0
    success:    int       = 0
    failed:     int       = 0
    failed_ids: list[int] = field(default_factory=list)


class BroadcastAgent:
    """Sends messages to all affiliated groups with configurable pacing and retry logic.

    A reusable alternative to the inline broadcast loop in broadcasting.py,
    providing progress tracking and per-group retry on transient errors.
    """

    def __init__(
        self,
        bot: Bot,
        *,
        delay:   float = _DEFAULT_DELAY,
        retries: int   = _DEFAULT_RETRIES,
    ) -> None:
        self._bot     = bot
        self._delay   = delay
        self._retries = retries

    async def send_text(self, text: str, **kwargs) -> BroadcastResult:
        """Send a plain text message to every affiliated group.

        Supports all keyword arguments accepted by `bot.send_message()`
        (e.g. `parse_mode`, `reply_markup`).
        """
        groups = await db.groups_db.active_groups()
        result = BroadcastResult(total=len(groups))

        for grp in groups:
            ok = await self._send_with_retry(grp["chat_id"], text, **kwargs)
            if ok:
                result.success += 1
            else:
                result.failed += 1
                result.failed_ids.append(grp["chat_id"])
            await asyncio.sleep(self._delay)

        log.info("BroadcastAgent: %d/%d sent", result.success, result.total)
        return result

    async def forward_message(self, message: Message) -> BroadcastResult:
        """Forward an existing Telegram message to every affiliated group."""
        groups = await db.groups_db.active_groups()
        result = BroadcastResult(total=len(groups))

        for grp in groups:
            try:
                await message.forward(grp["chat_id"])
                result.success += 1
            except Exception as exc:
                log.warning(
                    "BroadcastAgent: forward failed to %d: %s",
                    grp["chat_id"], exc,
                )
                result.failed += 1
                result.failed_ids.append(grp["chat_id"])
            await asyncio.sleep(self._delay)

        log.info("BroadcastAgent: forwarded %d/%d", result.success, result.total)
        return result

    def format_summary(self, result: BroadcastResult) -> str:
        return (
            f"Broadcast complete.\n"
            f"Sent: {result.success}/{result.total}\n"
            f"Failed: {result.failed}"
        )

    async def _send_with_retry(self, chat_id: int, text: str, **kwargs) -> bool:
        for attempt in range(self._retries + 1):
            try:
                await self._bot.send_message(chat_id, text, **kwargs)
                return True
            except Exception as exc:
                if attempt < self._retries:
                    await asyncio.sleep(self._delay * (attempt + 1))
                else:
                    log.warning(
                        "BroadcastAgent: gave up on %d after %d attempts: %s",
                        chat_id, self._retries + 1, exc,
                    )
        return False
