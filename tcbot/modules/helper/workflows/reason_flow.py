# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Central reason collection infrastructure.

Every moderation action that requires a reason/proof conversation (kick, mute,
warn) uses this module exclusively.  The shared state constants, reason-step
keyboard builders, reason-step prompt helpers, and the generic
ConversationHandler factory all live here.  Individual flow files only define
their executor and call ``build_modaction_conv()``.

Proof-step concerns (keyboard, prompt, recording) live in proof_flow.py and
are imported from there by both this module and the individual entry points.

Exports
───────
Constants
    WAITING_REASON   = 0
    WAITING_PROOF    = 1

Keyboard builders  (callback_data: ``{action}_skip_reason`` etc.)
    reason_kb(action)        → InlineKeyboardMarkup  (Skip + Cancel)
    reason_only_kb(action)   → InlineKeyboardMarkup  (Cancel only — warn)

Prompt text helpers
    reason_prompt(target_mention, action_label, extra_info) → str
    reason_noted_prompt(action_label, inline_reason, target_mention) → str

Parsing
    parse_inline_reason(args, has_explicit_target) → str

ConversationHandler factory
    build_modaction_conv(action, entry_fn, executor, entry_filter, ...) → ConversationHandler
"""

from __future__ import annotations

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tcbot import cfg
from tcbot.modules.helper.workflows.proof_flow import (
    proof_kb,
    proof_step_prompt,
    record_proof,
)
from tcbot.utils.prefixes import ALL_PREFIXES_CMD_FILTER

log = logging.getLogger(__name__)

# * State constants used by all moderation ConversationHandlers
WAITING_REASON = 0
WAITING_PROOF  = 1


# ───────────────────────── Reason parsing ───────────────────────── #

def parse_inline_reason(
    args: list[str],
    has_explicit_target: bool,
) -> str:
    """Extract any inline reason text from command arguments."""
    tokens = args[1:] if has_explicit_target else args
    return " ".join(tokens).strip()


# ──────────────────────── Keyboard builders ─────────────────────── #

def reason_kb(action: str) -> InlineKeyboardMarkup:
    """Reason-step keyboard: Skip + Cancel."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip",   callback_data=f"{action}_skip_reason"),
        InlineKeyboardButton("Cancel", callback_data=f"{action}_cancel"),
    ]])


def reason_only_kb(action: str) -> InlineKeyboardMarkup:
    """Reason-step keyboard when Skip is not offered (e.g. warn)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Cancel", callback_data=f"{action}_cancel"),
    ]])


# ──────────────────── Reason prompt text helpers ─────────────────── #

def reason_prompt(
    target_mention: str,
    action_label: str,
    extra_info: str = "",
) -> str:
    """Prompt asking the moderator to type a reason."""
    suffix = f" {extra_info}" if extra_info else ""
    return (
        f"About to {action_label} {target_mention}{suffix}.\n"
        "What's the reason? Type it below, or tap <b>Skip</b>."
    )


def reason_noted_prompt(
    action_label: str,
    inline_reason: str,
    target_mention: str,
    extra_info: str = "",
) -> str:
    """Proof-step prompt when an inline reason was already provided."""
    suffix = f" {extra_info}" if extra_info else ""
    return (
        f"{action_label.capitalize()}ing {target_mention}{suffix}.\n"
        f"Reason: <b>{inline_reason}</b>\n\n"
        "Got any proof? Send a photo or video, or tap <b>Skip</b> to proceed."
    )


# ────────────────── Generic ConversationHandler factory ─────────── #

def build_modaction_conv(
    action: str,
    entry_fn,
    executor,
    entry_filter,
    reason_required: bool = False,
    escape_filter=None,
) -> ConversationHandler:
    """Build a generic reason + proof ConversationHandler.

    All moderation actions (kick, mute, warn) use this single factory.
    Individual flow files only supply the ``executor`` coroutine and call
    this function — no state handler code lives outside this module.

    The executor is called as ``await executor(update, ctx)`` after all data
    has been collected into ``ctx.user_data``.  It is responsible for reading
    and cleaning up its own keys.

    ``ctx.user_data`` keys read by the generic handlers:

    - ``{action}_target_name``  or  ``{action}_target_fname``  — display name
    - ``{action}_extra_info``  — optional extra context for prompts (e.g. duration)
    - ``{action}_prompt_chat`` + ``{action}_prompt_id``  — if both are present the
      reason-step text handler edits that message instead of sending a new reply
      (used by mute to keep the conversation compact)

    Args:
        action:          Lowercase action slug: ``"kick"``, ``"mute"``, ``"warn"``.
        entry_fn:        Entry-point coroutine (the decorated command handler).
        executor:        Coroutine ``(update, ctx) → None`` that executes the action.
        entry_filter:    MessageHandler filter that triggers the ConversationHandler.
        reason_required: When ``True`` the Skip button is omitted on the reason step
                         (used for warn where a reason is mandatory).
        escape_filter:   Filter for commands that must NOT be consumed by the
                         fallback (e.g. unmute commands should reach their own
                         MessageHandler even if a mute conversation is open).
    """
    _reason_key      = f"{action}_reason"
    _proof_key       = f"{action}_proof_desc"
    _extra_info_key  = f"{action}_extra_info"
    _prompt_chat_key = f"{action}_prompt_chat"
    _prompt_id_key   = f"{action}_prompt_id"

    def _get_target(ctx: ContextTypes.DEFAULT_TYPE) -> str:
        return (
            ctx.user_data.get(f"{action}_target_name")
            or ctx.user_data.get(f"{action}_target_fname")
            or "target"
        )

    # ── WAITING_REASON handlers ──────────────────────────────────── #

    async def _on_reason_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        reason      = update.effective_message.text.strip()
        ctx.user_data[_reason_key] = reason
        extra_info  = ctx.user_data.get(_extra_info_key, "")
        prompt_txt  = proof_step_prompt(_get_target(ctx), action, reason, extra_info)
        prompt_chat = ctx.user_data.get(_prompt_chat_key)
        prompt_id   = ctx.user_data.get(_prompt_id_key)
        if prompt_id and prompt_chat:
            try:
                await ctx.bot.edit_message_text(
                    prompt_txt,
                    chat_id=prompt_chat,
                    message_id=prompt_id,
                    parse_mode="HTML",
                    reply_markup=proof_kb(action),
                )
            except Exception as exc:
                log.error("%s prompt edit failed (reason step): %s", action, exc)
        else:
            await update.effective_message.reply_text(
                prompt_txt, parse_mode="HTML", reply_markup=proof_kb(action),
            )
        return WAITING_PROOF

    async def _on_skip_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q = update.callback_query
        ctx.user_data[_reason_key] = "No reason provided"
        extra_info = ctx.user_data.get(_extra_info_key, "")
        prompt_txt = proof_step_prompt(_get_target(ctx), action, "No reason provided", extra_info)
        try:
            await asyncio.gather(
                q.answer(),
                q.edit_message_text(prompt_txt, parse_mode="HTML", reply_markup=proof_kb(action)),
            )
        except Exception as exc:
            log.error("%s prompt edit failed (skip-reason step): %s", action, exc)
        return WAITING_PROOF

    # ── WAITING_PROOF handlers ───────────────────────────────────── #

    async def _on_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        proof = record_proof(update.effective_message)
        if proof:
            ctx.user_data[_proof_key] = proof
        await executor(update, ctx)
        return ConversationHandler.END

    async def _on_skip_proof(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer()
        await executor(update, ctx)
        return ConversationHandler.END

    # ── Cancel / fallback ────────────────────────────────────────── #

    async def _on_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q = update.callback_query
        await asyncio.gather(
            q.answer(),
            q.edit_message_text(f"Got it, {action} cancelled. No action was taken."),
        )
        return ConversationHandler.END

    async def _end_conv(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        await update.effective_message.reply_text(f"{action.capitalize()} operation cancelled.")
        return ConversationHandler.END

    # ── Build states ─────────────────────────────────────────────── #

    reason_state = [
        MessageHandler(filters.TEXT & ~ALL_PREFIXES_CMD_FILTER, _on_reason_text),
        CallbackQueryHandler(_on_cancel, pattern=rf"^{action}_cancel$"),
    ]
    if not reason_required:
        reason_state.insert(1, CallbackQueryHandler(
            _on_skip_reason, pattern=rf"^{action}_skip_reason$",
        ))

    proof_state = [
        MessageHandler(filters.PHOTO | filters.VIDEO, _on_proof),
        CallbackQueryHandler(_on_skip_proof, pattern=rf"^{action}_skip_proof$"),
        CallbackQueryHandler(_on_cancel,     pattern=rf"^{action}_cancel$"),
    ]

    fallback_filter = ALL_PREFIXES_CMD_FILTER
    if escape_filter is not None:
        fallback_filter = fallback_filter & ~escape_filter

    return ConversationHandler(
        entry_points=[MessageHandler(entry_filter, entry_fn)],
        states={
            WAITING_REASON: reason_state,
            WAITING_PROOF:  proof_state,
        },
        fallbacks=[
            CallbackQueryHandler(_on_cancel, pattern=rf"^{action}_cancel$"),
            MessageHandler(fallback_filter, _end_conv),
        ],
        per_user=True,
        per_chat=True,
        conversation_timeout=cfg.proof_timeout,
        per_message=False,
    )
