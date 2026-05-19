# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Mute/unmute executor + conversation workflow

Sections
────────
parse_duration()      — parse '3d', '1mo', '2ye' tokens
fmt_duration()        — human-readable duration string
_execute_mute()       — federation-wide mute executor
execute_unmute()      — restore full permissions across all groups
WAITING_REASON/PROOF  — state constants
on_*                  — ConversationHandler state handlers
mute_conversation()   — ConversationHandler factory
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta

from telegram import ChatPermissions, Update
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
    record_proof,
)
from tcbot.utils.dispatch import fan_out
from tcbot.utils.prefixes import ALL_PREFIXES_CMD_FILTER, build_prefixed_filters
from tcbot.utils.timedate_format import utc_now

log = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"^(\d+)(ye|mo|[smhdw])$", re.IGNORECASE)

WAITING_REASON = 0
WAITING_PROOF  = 1


## ── Duration helpers ────────────────────────────────────────────────────────

def parse_duration(raw: str) -> timedelta | None:
    """Parse a single duration token like '3d', '1mo', '2ye'. Returns None if invalid."""
    m = _DURATION_RE.match(raw.strip())
    if not m:
        return None
    value = int(m.group(1))
    unit  = m.group(2).lower()
    mapping = {
        "s":  timedelta(seconds=value),
        "m":  timedelta(minutes=value),
        "h":  timedelta(hours=value),
        "d":  timedelta(days=value),
        "w":  timedelta(weeks=value),
        "mo": timedelta(days=value * 30),
        "ye": timedelta(days=value * 365),
    }
    return mapping.get(unit)


def fmt_duration(td: timedelta | None) -> str:
    """Human-readable duration string for use in replies."""
    if td is None:
        return "permanently"
    total = int(td.total_seconds())
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m"
    if total < 86400:
        return f"{total // 3600}h"
    days = total // 86400
    if days < 7:
        return f"{days}d"
    if days < 30:
        return f"{days // 7}w"
    if days < 365:
        return f"{days // 30}mo"
    return f"{days // 365}ye"


## ── Mute executor ───────────────────────────────────────────────────────────

async def _execute_mute(bot, update: Update, meta: dict) -> None:
    """Apply a federation-wide mute across all connected groups and edit the prompt to a summary."""
    target_id    = meta["mute_target_id"]
    target_fname = meta["mute_target_fname"]
    reason       = meta.get("mute_reason") or "No reason provided"
    admin_id     = meta["mute_admin_id"]
    duration     = meta.get("mute_duration")
    proof_desc   = meta.get("mute_proof_desc")
    prompt_chat  = meta.get("mute_prompt_chat")
    prompt_id    = meta.get("mute_prompt_id")
    dur_str      = fmt_duration(duration)

    until = utc_now() + duration if duration else None
    perms = ChatPermissions(can_send_messages=False)

    ## Apply across all connected groups - semaphore-bounded for rate safety
    groups  = await db.groups_db.active_groups()
    results = await fan_out(
        [bot.restrict_chat_member(
            grp["chat_id"], target_id,
            permissions=perms,
            until_date=until,
        ) for grp in groups]
    )
    failed = sum(1 for r in results if isinstance(r, BaseException))

    proof_line = f"\nProof: {proof_desc}" if proof_desc else ""
    summary = (
        f"{mention(target_id, target_fname)} {code(str(target_id))} "
        f"has been muted <b>{dur_str}</b>.\n"
        f"Reason: {reason}"
        f"{proof_line}\n"
        f"Applied to {len(groups) - failed}/{len(groups)} groups."
    )

    admin_fname = meta.get("mute_admin_fname", "Admin")
    lc, lt      = cfg.logs
    log_text    = parse_logmsg.mute_log(
        target_id, target_fname, admin_id, admin_fname, reason, dur_str,
    )

    ## Log to DB, post to log channel, and edit summary - all in parallel
    chat_id  = update.effective_chat.id
    results2 = await asyncio.gather(
        db.mutes_db.log_mute(target_id, chat_id, reason, admin_id),
        bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt),
        bot.edit_message_text(
            summary,
            chat_id=prompt_chat, message_id=prompt_id,
            parse_mode="HTML", reply_markup=None,
        ),
        return_exceptions=True,
    )
    if isinstance(results2[1], BaseException):
        log.error("Mute log send failed: %s", results2[1])
    if isinstance(results2[2], BaseException):
        msg = update.effective_message
        if msg:
            await msg.reply_text(summary, parse_mode="HTML")


## ── Unmute executor ─────────────────────────────────────────────────────────

async def execute_unmute(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    target_id: int,
    target_name: str,
) -> None:
    """Restore full send permissions across all connected groups."""
    msg        = update.effective_message
    full_perms = ChatPermissions(
        can_send_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
    )

    ## Unrestrict across all connected groups - semaphore-bounded for rate safety
    groups  = await db.groups_db.active_groups()
    results = await fan_out(
        [ctx.bot.restrict_chat_member(
            grp["chat_id"], target_id,
            permissions=full_perms,
        ) for grp in groups]
    )
    failed = sum(1 for r in results if isinstance(r, BaseException))

    admin    = update.effective_user
    lc, lt   = cfg.logs
    log_text = parse_logmsg.unmute_log(
        target_id, target_name, admin.id, admin.first_name,
    )

    reply = (
        f"{mention(target_id, target_name)} {code(str(target_id))} has been unmuted - "
        f"restored in {len(groups) - failed}/{len(groups)} groups."
    )

    ## Send log to channel and reply in parallel
    if lc:
        results2 = await asyncio.gather(
            ctx.bot.send_message(lc, log_text, parse_mode="HTML", message_thread_id=lt),
            msg.reply_text(reply, parse_mode="HTML"),
            return_exceptions=True,
        )
        if isinstance(results2[0], BaseException):
            log.error("Unmute log send failed: %s", results2[0])
    else:
        await msg.reply_text(reply, parse_mode="HTML")


## ── WAITING_REASON handlers ─────────────────────────────────────────────────

async def on_reason_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["mute_reason"] = update.effective_message.text.strip()
    target_id    = ctx.user_data["mute_target_id"]
    target_fname = ctx.user_data["mute_target_fname"]
    duration     = ctx.user_data["mute_duration"]
    prompt_chat  = ctx.user_data["mute_prompt_chat"]
    prompt_id    = ctx.user_data.get("mute_prompt_id")
    dur_str        = fmt_duration(duration)
    target_mention = mention(target_id, target_fname)
    extra_info     = f"{code(str(target_id))} — {dur_str}"
    try:
        await ctx.bot.edit_message_text(
            proof_step_prompt(target_mention, "mute", ctx.user_data["mute_reason"], extra_info),
            chat_id=prompt_chat,
            message_id=prompt_id,
            parse_mode="HTML",
            reply_markup=proof_kb("mute"),
        )
    except Exception as exc:
        log.error("Mute prompt edit failed (reason step): %s", exc)
    return WAITING_PROOF


async def on_skip_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    ctx.user_data["mute_reason"] = "No reason provided"
    target_id    = ctx.user_data["mute_target_id"]
    target_fname = ctx.user_data["mute_target_fname"]
    duration     = ctx.user_data["mute_duration"]
    dur_str        = fmt_duration(duration)
    target_mention = mention(target_id, target_fname)
    extra_info     = f"{code(str(target_id))} — {dur_str}"
    try:
        await asyncio.gather(
            q.answer(),
            q.edit_message_text(
                proof_step_prompt(target_mention, "mute", "No reason provided", extra_info),
                parse_mode="HTML",
                reply_markup=proof_kb("mute"),
            ),
        )
    except Exception as exc:
        log.error("Mute prompt edit failed (skip-reason step): %s", exc)
    return WAITING_PROOF


## ── WAITING_PROOF handlers ──────────────────────────────────────────────────

async def on_proof_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    proof = record_proof(update.effective_message)
    if proof:
        ctx.user_data["mute_proof_desc"] = proof
    await _execute_mute(ctx.bot, update, ctx.user_data)
    return ConversationHandler.END


async def on_skip_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await asyncio.gather(
        q.answer(),
        _execute_mute(ctx.bot, update, ctx.user_data),
    )
    return ConversationHandler.END


## ── Cancel ──────────────────────────────────────────────────────────────────

async def on_mute_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await asyncio.gather(
        q.answer(),
        q.edit_message_text("Got it, mute cancelled. No action was taken."),
    )
    return ConversationHandler.END


async def _end_conversation(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Mute operation cancelled.")
    return ConversationHandler.END


## ── ConversationHandler factory ─────────────────────────────────────────────

## Unmute commands must NOT be caught by the fallback — excluding them here
## lets PTB fall through to the MessageHandler registered for cmd_unmute.
_UNMUTE_ESCAPE = (
    build_prefixed_filters("tcunmute")
    | build_prefixed_filters("tcunm")
    | build_prefixed_filters("tcum")
)


def mute_conversation(entry_fn) -> ConversationHandler:
    """Return the mute ConversationHandler with the given entry-point function."""
    _entry = build_prefixed_filters("tcmute") | build_prefixed_filters("tcm")
    return ConversationHandler(
        entry_points=[MessageHandler(_entry, entry_fn)],
        states={
            WAITING_REASON: [
                CallbackQueryHandler(on_skip_reason, pattern=r"^mute_skip_reason$"),
                CallbackQueryHandler(on_mute_cancel, pattern=r"^mute_cancel$"),
                MessageHandler(filters.TEXT & ~ALL_PREFIXES_CMD_FILTER, on_reason_text),
            ],
            WAITING_PROOF: [
                CallbackQueryHandler(on_skip_proof,  pattern=r"^mute_skip_proof$"),
                CallbackQueryHandler(on_mute_cancel, pattern=r"^mute_cancel$"),
                MessageHandler(filters.PHOTO | filters.VIDEO, on_proof_received),
            ],
        },
        fallbacks=[MessageHandler(ALL_PREFIXES_CMD_FILTER & ~_UNMUTE_ESCAPE, _end_conversation)],
        conversation_timeout=cfg.proof_timeout,
        per_chat=True,
        per_user=True,
        per_message=False,
    )
