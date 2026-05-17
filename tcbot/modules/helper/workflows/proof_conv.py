# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Proof collection conversation state handlers - album debounce, proof received, cancel, timeout
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import Bot, Message, Update
from telegram.ext import ContextTypes, ConversationHandler

from tcbot import cfg
from tcbot.database.roles_db import get_effective_role, role_rank
from tcbot.modules.helper.workflows.ban_flow import _execute_ban

log = logging.getLogger(__name__)

WAITING_PROOF = 0

## Module-level album accumulators
_albums:     dict[str, list[Message]]   = {}
_album_meta: dict[str, dict[str, Any]] = {}


## ── Proof received handler ──────────────────────────────────────────────────

async def on_proof_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    uid = update.effective_user.id

    if role_rank(await get_effective_role(uid)) < role_rank("developer"):
        return WAITING_PROOF

    if msg.media_group_id:
        mgid = msg.media_group_id
        if mgid not in _albums:
            _albums[mgid] = []
            _album_meta[mgid] = dict(ctx.user_data)
            asyncio.create_task(_flush_album(mgid, ctx.bot))
        _albums[mgid].append(msg)
        return WAITING_PROOF

    ## Single media - execute immediately
    await _execute_ban(ctx.bot, [msg], dict(ctx.user_data))
    return ConversationHandler.END


## ── Album debounce flush ────────────────────────────────────────────────────

async def _flush_album(mgid: str, bot: Bot) -> None:
    await asyncio.sleep(cfg.album_debounce)
    msgs = _albums.pop(mgid, [])
    meta = _album_meta.pop(mgid, {})
    if not msgs or not meta:
        return
    await _execute_ban(bot, msgs, meta)


## ── Cancel / timeout handlers ───────────────────────────────────────────────

async def on_cancel_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await asyncio.gather(
        q.answer(),
        q.edit_message_text("Cancelled. No ban was issued."),
    )
    return ConversationHandler.END


## ── Timeout handler ─────────────────────────────────────────────────────────

async def on_ban_timeout(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Timed out waiting for proof. No ban was issued."
        )
    return ConversationHandler.END
