# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Kick executor + conversation workflow

Sections
────────
execute_kick()        — group-level user removal (ban + immediate unban)
WAITING_REASON/PROOF  — state constants
on_kick_*             — ConversationHandler state handlers
kick_conversation()   — ConversationHandler factory
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tcbot import cfg, database as db
from tcbot.modules.helper import parse_logmsg
from tcbot.modules.helper.formatter import code, mention
from tcbot.modules.helper.workflows.reason_flow import (
    proof_kb,
    proof_step_prompt,
    reason_kb,
    reason_noted_prompt,
    record_proof,
)
from tcbot.utils.prefixes import ALL_PREFIXES_CMD_FILTER, build_prefixed_filters

log = logging.getLogger(__name__)

WAITING_REASON = 0
WAITING_PROOF  = 1


## ── Kick executor ───────────────────────────────────────────────────────────

async def execute_kick(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
    reason: str,
    proof_desc: str | None = None,
) -> None:
    """Kick (ban then immediately unban) a user from the current group."""
    msg      = update.effective_message
    chat_id  = update.effective_chat.id
    admin_id = update.effective_user.id

    try:
        await ctx.bot.ban_chat_member(chat_id, target_id)
        proof_line  = f"\nProof: {proof_desc}" if proof_desc else ""
        chat_title  = update.effective_chat.title or str(chat_id)
        admin_fname = update.effective_user.first_name
        lc, lt      = cfg.logs
        log_text    = parse_logmsg.kick_log(
            target_id, target_name, admin_id, admin_fname, reason, chat_id, chat_title,
        )
        ## unban + log_kick + federation log + reply all run in parallel
        results = await asyncio.gather(
            ctx.bot.unban_chat_member(chat_id, target_id, only_if_banned=True),
            db.kicks_db.log_kick(target_id, chat_id, reason, admin_id),
            ctx.bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt),
            msg.reply_text(
                f"{mention(target_id, target_name)} {code(str(target_id))} has been kicked.\n"
                f"Reason: {reason}{proof_line}\n"
                "They can rejoin via invite link.",
                parse_mode="HTML",
            ),
            return_exceptions=True,
        )
        if isinstance(results[2], BaseException):
            log.error("Kick log send failed: %s", results[2])
    except Exception as exc:
        log.error("Kick failed for %s in %s: %s", target_id, chat_id, exc)
        await msg.reply_text(
            f"Couldn't kick {mention(target_id, target_name)}: {exc}",
            parse_mode="HTML",
        )


## ── Helpers ─────────────────────────────────────────────────────────────────

def _clear(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    for k in ("kick_target_id", "kick_target_name", "kick_reason", "kick_proof_desc"):
        ctx.user_data.pop(k, None)


async def _end_conversation(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    _clear(ctx)
    await update.effective_message.reply_text("Kick operation cancelled.")
    return ConversationHandler.END


async def _do_kick(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    target_id   = ctx.user_data["kick_target_id"]
    target_name = ctx.user_data["kick_target_name"]
    reason      = ctx.user_data.get("kick_reason", "No reason provided")
    proof_desc  = ctx.user_data.get("kick_proof_desc")
    _clear(ctx)
    await execute_kick(update, ctx, target_id, target_name, reason, proof_desc=proof_desc)
    return ConversationHandler.END


## ── WAITING_REASON handlers ─────────────────────────────────────────────────

async def on_kick_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    reason = update.effective_message.text.strip()
    ctx.user_data["kick_reason"] = reason
    target_mention = ctx.user_data.get("kick_target_name", "target")
    await update.effective_message.reply_text(
        proof_step_prompt(target_mention, "kick", reason),
        parse_mode="HTML",
        reply_markup=proof_kb("kick"),
    )
    return WAITING_PROOF


async def on_kick_skip_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    ctx.user_data["kick_reason"] = "No reason provided"
    target_mention = ctx.user_data.get("kick_target_name", "target")
    await asyncio.gather(
        q.answer(),
        q.edit_message_text(
            proof_step_prompt(target_mention, "kick", "No reason provided"),
            parse_mode="HTML",
            reply_markup=proof_kb("kick"),
        ),
    )
    return WAITING_PROOF


## ── WAITING_PROOF handlers ──────────────────────────────────────────────────

async def on_kick_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    proof = record_proof(update.effective_message)
    if proof:
        ctx.user_data["kick_proof_desc"] = proof
    return await _do_kick(update, ctx)


async def on_kick_skip_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    return await _do_kick(update, ctx)


async def on_kick_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    _clear(ctx)
    await asyncio.gather(
        q.answer(),
        q.edit_message_text("Got it, kick cancelled. No action was taken."),
    )
    return ConversationHandler.END


## ── ConversationHandler factory ─────────────────────────────────────────────

_KICK_FILTER = build_prefixed_filters("tckick") | build_prefixed_filters("tck")


def kick_conversation(entry_fn) -> ConversationHandler:
    """Return the kick ConversationHandler with the given entry-point function."""
    return ConversationHandler(
        entry_points=[MessageHandler(_KICK_FILTER, entry_fn)],
        states={
            WAITING_REASON: [
                MessageHandler(filters.TEXT & ~ALL_PREFIXES_CMD_FILTER, on_kick_reason),
                CallbackQueryHandler(on_kick_skip_reason, pattern=r"^kick_skip_reason$"),
                CallbackQueryHandler(on_kick_cancel,      pattern=r"^kick_cancel$"),
            ],
            WAITING_PROOF: [
                MessageHandler(filters.PHOTO | filters.VIDEO, on_kick_proof),
                CallbackQueryHandler(on_kick_skip_proof, pattern=r"^kick_skip_proof$"),
                CallbackQueryHandler(on_kick_cancel,     pattern=r"^kick_cancel$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(on_kick_cancel, pattern=r"^kick_cancel$"),
            MessageHandler(ALL_PREFIXES_CMD_FILTER, _end_conversation),
        ],
        per_user=True,
        per_chat=True,
        conversation_timeout=cfg.proof_timeout,
    )
