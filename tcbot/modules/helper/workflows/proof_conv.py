# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Generic proof collection conversation state handlers.

This module provides the WAITING_PROOF state handlers shared across ALL
proof-required conversations (ban, and any future flow).  The actual executor
is stored by each entry-point in ``ctx.user_data["_proof_executor"]`` so this
module remains completely decoupled from any specific action.

Flow
────
• on_proof_received  — single or album media → dispatch to stored executor
• on_cancel_proof    — cancel button → end conversation, no action taken
• on_proof_timeout   — conversation timed out → end conversation, no action

Usage (entry-point side)
────────────────────────
Before entering WAITING_PROOF, the entry-point stores the executor::

    from tcbot.modules.helper.workflows.ban_flow import _execute_ban
    ctx.user_data["_proof_executor"] = _execute_ban

The executor signature must be::

    async def executor(bot: Bot, msgs: list[Message], meta: dict) -> None: ...
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Bot, Message, Update
from telegram.ext import ContextTypes, ConversationHandler

from tcbot import cfg

log = logging.getLogger(__name__)

WAITING_PROOF = 0

## Module-level album accumulators (keyed by media_group_id)
_albums:     dict[str, list[Message]]  = {}
_album_meta: dict[str, dict[str, Any]] = {}

_Executor = Callable[[Bot, list[Message], dict[str, Any]], Awaitable[None]]


## ── Proof received handler ──────────────────────────────────────────────────

async def on_proof_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    msg:      Message         = update.effective_message
    executor: _Executor | None = ctx.user_data.get("_proof_executor")

    if not executor:
        log.error("proof_conv.on_proof_received: no _proof_executor in user_data")
        return ConversationHandler.END

    if msg.media_group_id:
        mgid = msg.media_group_id
        if mgid not in _albums:
            _albums[mgid]     = []
            _album_meta[mgid] = dict(ctx.user_data)
            asyncio.create_task(_flush_album(mgid, ctx.bot))
        _albums[mgid].append(msg)
        return WAITING_PROOF

    ## Single media file - execute immediately
    await executor(ctx.bot, [msg], dict(ctx.user_data))
    return ConversationHandler.END


## ── Album debounce flush ────────────────────────────────────────────────────

async def _flush_album(mgid: str, bot: Bot) -> None:
    await asyncio.sleep(cfg.album_debounce)
    msgs = _albums.pop(mgid, [])
    meta = _album_meta.pop(mgid, {})
    if not msgs or not meta:
        return
    executor: _Executor | None = meta.get("_proof_executor")
    if not executor:
        log.error("proof_conv._flush_album: no _proof_executor in album meta for %s", mgid)
        return
    await executor(bot, msgs, meta)


## ── Cancel / timeout handlers ───────────────────────────────────────────────

async def on_cancel_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await asyncio.gather(
        q.answer(),
        q.edit_message_text("Cancelled. No action was taken."),
    )
    return ConversationHandler.END


async def on_proof_timeout(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Timed out waiting for proof. No action was taken."
        )
    return ConversationHandler.END


## ── Backwards-compat alias ──────────────────────────────────────────────────

## ban_conv.py previously referenced on_ban_timeout; keep the alias so no
## imports break while callers are updated.
on_ban_timeout = on_proof_timeout
