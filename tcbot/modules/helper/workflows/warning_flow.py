# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Warning executor + conversation workflow

Sections
────────
execute_warn()        — per-group warn (auto-ban at WARN_LIMIT)
execute_unwarn()      — remove latest warning in group
execute_warnlist()    — show warning count + reasons
execute_resetwarns()  — clear all warnings for a user in a group
WAITING_REASON/PROOF  — state constants
on_warn_*             — ConversationHandler state handlers
warn_conversation()   — ConversationHandler factory
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
    reason_only_kb,
    reason_prompt,
    record_proof,
)
from tcbot.utils.prefixes import ALL_PREFIXES_CMD_FILTER, build_prefixed_filters

log = logging.getLogger(__name__)

WARN_LIMIT = 3

WAITING_REASON = 0
WAITING_PROOF  = 1


## ── Executors ───────────────────────────────────────────────────────────────

async def execute_warn(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
    reason: str,
    proof_desc: str | None = None,
) -> None:
    msg         = update.effective_message
    chat_id     = update.effective_chat.id
    admin_id    = update.effective_user.id
    proof_line  = f"\nProof: {proof_desc}" if proof_desc else ""
    chat_title  = update.effective_chat.title or str(chat_id)
    admin_fname = update.effective_user.first_name
    lc, lt      = cfg.logs

    count    = await db.warns_db.add_warn(target_id, reason, admin_id, chat_id)
    log_text = parse_logmsg.warn_log(
        target_id, target_name, admin_id, admin_fname,
        reason, count, WARN_LIMIT, chat_id, chat_title,
    )

    if count >= WARN_LIMIT:
        ## clear warns + ban + federation log - all in parallel
        results = await asyncio.gather(
            db.warns_db.clear_warns(target_id, chat_id),
            ctx.bot.ban_chat_member(chat_id, target_id),
            ctx.bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt),
            return_exceptions=True,
        )
        if isinstance(results[2], BaseException):
            log.error("Warn log send failed: %s", results[2])
        ban_result = results[1]
        if not isinstance(ban_result, BaseException):
            await msg.reply_text(
                f"{mention(target_id, target_name)} hit {WARN_LIMIT} warnings "
                f"and has been banned from this group.{proof_line}",
                parse_mode="HTML",
            )
        else:
            log.error("Auto-ban on warn limit failed: %s", ban_result)
            await msg.reply_text(
                f"{mention(target_id, target_name)} hit {WARN_LIMIT} warnings "
                f"but auto-ban failed - please ban them manually.{proof_line}",
                parse_mode="HTML",
            )
    else:
        ## federation log + reply in parallel
        results2 = await asyncio.gather(
            ctx.bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt),
            msg.reply_text(
                f"{mention(target_id, target_name)} has been warned "
                f"({count}/{WARN_LIMIT}) - {reason}{proof_line}",
                parse_mode="HTML",
            ),
            return_exceptions=True,
        )
        if isinstance(results2[0], BaseException):
            log.error("Warn log send failed: %s", results2[0])


async def execute_unwarn(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
) -> None:
    msg     = update.effective_message
    chat_id = update.effective_chat.id

    count = await db.warns_db.warn_count(target_id, chat_id)
    if count == 0:
        await msg.reply_text(
            f"{mention(target_id, target_name)} {code(str(target_id))} has no warnings in this group.",
            parse_mode="HTML",
        )
        return

    new_count   = max(count - 1, 0)
    chat_title  = update.effective_chat.title or str(chat_id)
    admin       = update.effective_user
    lc, lt      = cfg.logs
    log_text    = parse_logmsg.unwarn_log(
        target_id, target_name, admin.id, admin.first_name,
        new_count, WARN_LIMIT, chat_id, chat_title,
    )
    ## remove warn + send log + reply in parallel
    results = await asyncio.gather(
        db.warns_db.remove_last_warn(target_id, chat_id),
        ctx.bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt),
        msg.reply_text(
            f"One warning removed from {mention(target_id, target_name)}. "
            f"They're now at {new_count}/{WARN_LIMIT}.",
            parse_mode="HTML",
        ),
        return_exceptions=True,
    )
    if isinstance(results[1], BaseException):
        log.error("Unwarn log send failed: %s", results[1])


async def execute_warnlist(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
) -> None:
    msg     = update.effective_message
    chat_id = update.effective_chat.id

    warns = await db.warns_db.get_warns(target_id, chat_id)
    count = len(warns)

    if count == 0:
        await msg.reply_text(
            f"{mention(target_id, target_name)} {code(str(target_id))} has no warnings in this group.",
            parse_mode="HTML",
        )
        return

    lines = [f"{mention(target_id, target_name)} has {count}/{WARN_LIMIT} warnings:\n"]
    for i, w in enumerate(warns, 1):
        lines.append(f"  {i}. {w.get('reason', 'No reason')}")

    await msg.reply_text("\n".join(lines), parse_mode="HTML")


async def execute_resetwarns(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
) -> None:
    msg     = update.effective_message
    chat_id = update.effective_chat.id

    removed = await db.warns_db.clear_warns(target_id, chat_id)
    if removed == 0:
        await msg.reply_text(
            f"{mention(target_id, target_name)} {code(str(target_id))} has no warnings to clear.",
            parse_mode="HTML",
        )
        return

    await msg.reply_text(
        f"All {removed} warning(s) cleared for {mention(target_id, target_name)}. Clean slate.",
        parse_mode="HTML",
    )


## ── Conversation helpers ─────────────────────────────────────────────────────

def _clear(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    for k in ("warn_target_id", "warn_target_name", "warn_reason", "warn_proof_desc"):
        ctx.user_data.pop(k, None)


async def _end_conversation(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Warn operation cancelled.")
    return ConversationHandler.END


async def _do_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    target_id   = ctx.user_data["warn_target_id"]
    target_name = ctx.user_data["warn_target_name"]
    reason      = ctx.user_data["warn_reason"]
    proof_desc  = ctx.user_data.get("warn_proof_desc")
    _clear(ctx)
    await execute_warn(update, ctx, target_id, target_name, reason, proof_desc=proof_desc)
    return ConversationHandler.END


## ── WAITING_REASON handlers ─────────────────────────────────────────────────

async def on_warn_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    reason = update.effective_message.text.strip()
    ctx.user_data["warn_reason"] = reason
    target_mention = mention(
        ctx.user_data["warn_target_id"],
        ctx.user_data["warn_target_name"],
    )
    await update.effective_message.reply_text(
        proof_step_prompt(target_mention, "warn", reason),
        parse_mode="HTML",
        reply_markup=proof_kb("warn"),
    )
    return WAITING_PROOF


## ── WAITING_PROOF handlers ──────────────────────────────────────────────────

async def on_warn_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    proof = record_proof(update.effective_message)
    if proof:
        ctx.user_data["warn_proof_desc"] = proof
    return await _do_warn(update, ctx)


async def on_warn_skip_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    return await _do_warn(update, ctx)


async def on_warn_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    _clear(ctx)
    await asyncio.gather(
        q.answer(),
        q.edit_message_text("Got it, warning cancelled. No action was taken."),
    )
    return ConversationHandler.END


## ── ConversationHandler factory ─────────────────────────────────────────────

_WARN_FILTER = build_prefixed_filters("tcwarn") | build_prefixed_filters("tcw")

## Commands that must NOT be swallowed by the fallback so they reach their own
## MessageHandlers registered after warn_conversation() in __handlers__.
_WARN_CONV_ESCAPE = (
    build_prefixed_filters("tcunwarn")
    | build_prefixed_filters("tcunw")
    | build_prefixed_filters("warns")
    | build_prefixed_filters("warnlist")
    | build_prefixed_filters("resetwarns")
    | build_prefixed_filters("clearwarns")
)


def warn_conversation(entry_fn) -> ConversationHandler:
    """Return the warn ConversationHandler with the given entry-point function."""
    return ConversationHandler(
        entry_points=[MessageHandler(_WARN_FILTER, entry_fn)],
        states={
            WAITING_REASON: [
                MessageHandler(filters.TEXT & ~ALL_PREFIXES_CMD_FILTER, on_warn_reason),
                CallbackQueryHandler(on_warn_cancel, pattern=r"^warn_cancel$"),
            ],
            WAITING_PROOF: [
                MessageHandler(filters.PHOTO | filters.VIDEO, on_warn_proof),
                CallbackQueryHandler(on_warn_skip_proof, pattern=r"^warn_skip_proof$"),
                CallbackQueryHandler(on_warn_cancel,     pattern=r"^warn_cancel$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(on_warn_cancel, pattern=r"^warn_cancel$"),
            MessageHandler(ALL_PREFIXES_CMD_FILTER & ~_WARN_CONV_ESCAPE, _end_conversation),
        ],
        per_user=True,
        per_chat=True,
        conversation_timeout=cfg.proof_timeout,
    )
