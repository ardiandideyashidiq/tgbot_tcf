# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Broadcast a message to all affiliated groups."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.modules.helper import decorators
from tcbot.modules.helper.formatter import bold, code
from tcbot.utils.prefixes import build_prefixed_filters

log = logging.getLogger(__name__)

__module_name__ = "Broadcast"
__help_text__ = (
    "<code>/tcbroadcast</code> – broadcast the replied-to message to all affiliated groups (staff only).\n"
    "Must be used as a reply."
)


@decorators.staff_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message

    if not msg.reply_to_message:
        await msg.reply_text("Reply to the message you want to broadcast.")
        return

    target = msg.reply_to_message
    groups = await db.groups_db.active_groups()

    if not groups:
        await msg.reply_text("No affiliated groups.")
        return

    status = await msg.reply_text(f"⏳ Broadcasting to {len(groups)} group(s)...")
    success, failed = 0, 0

    for grp in groups:
        try:
            await target.forward(grp["chat_id"])
            success += 1
        except Exception as exc:
            log.warning("Broadcast failed for %d: %s", grp["chat_id"], exc)
            failed += 1
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ Broadcast complete.\n"
        f"Success: {code(str(success))} | Failed: {code(str(failed))}",
        parse_mode="HTML",
    )


__handlers__ = [
    MessageHandler(build_prefixed_filters("tcbroadcast"), cmd_broadcast),
]
