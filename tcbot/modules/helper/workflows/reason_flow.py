# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Shared reason + proof collection utilities.

This module provides stateless helpers reused across every conversation that
requires a reason/proof step (kick, mute, warn).  The actual conversation
state machines live in their own ``*_conv.py`` files; only the pure parsing,
keyboard-building, and formatting logic lives here.

Exports
───────
Parsing
    parse_inline_reason(args, has_explicit_target) → str

Keyboard builders  (callback_data follows ``{action}_skip_reason`` etc.)
    reason_kb(action)        → InlineKeyboardMarkup  (Skip + Cancel)
    reason_only_kb(action)   → InlineKeyboardMarkup  (Cancel only — warn)
    proof_kb(action)         → InlineKeyboardMarkup  (Skip + Cancel)

Prompt text helpers
    reason_prompt(target_mention, action_label, extra_info) → str
    reason_noted_prompt(action_label, inline_reason, target_mention) → str
    proof_step_prompt(target_mention, action_label, reason) → str

Proof recording
    record_proof(msg) → str | None
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message


## ── Reason parsing ─────────────────────────────────────────────────────────

def parse_inline_reason(
    args: list[str],
    has_explicit_target: bool,
) -> str:
    """Extract any inline reason text from command arguments.

    Args:
        args:                 Raw token list from :func:`parse_cmd_args`.
        has_explicit_target:  ``True`` when the first token was identified as a
            user reference (ID or @username) so it should be skipped.

    Returns:
        The joined reason string, or an empty string when no reason was given.

    Example::

        args = ["@user", "spamming", "in", "groups"]
        reason = parse_inline_reason(args, has_explicit_target=True)
        # → "spamming in groups"

        args = ["spamming", "in", "groups"]
        reason = parse_inline_reason(args, has_explicit_target=False)
        # → "spamming in groups"
    """
    tokens = args[1:] if has_explicit_target else args
    return " ".join(tokens).strip()


## ── Keyboard builders ──────────────────────────────────────────────────────

def reason_kb(action: str) -> InlineKeyboardMarkup:
    """Keyboard for the reason step with Skip and Cancel buttons.

    Callback data uses the pattern ``<action>_skip_reason`` / ``<action>_cancel``.

    Args:
        action: Lowercase action slug — ``"kick"``, ``"mute"``, ``"warn"`` etc.
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip",   callback_data=f"{action}_skip_reason"),
        InlineKeyboardButton("Cancel", callback_data=f"{action}_cancel"),
    ]])


def reason_only_kb(action: str) -> InlineKeyboardMarkup:
    """Keyboard for the reason step when Skip is NOT offered (e.g. warn).

    Callback data: ``<action>_cancel``.

    Args:
        action: Lowercase action slug.
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Cancel", callback_data=f"{action}_cancel"),
    ]])


def proof_kb(action: str) -> InlineKeyboardMarkup:
    """Keyboard for the proof step with Skip and Cancel buttons.

    Callback data: ``<action>_skip_proof`` / ``<action>_cancel``.

    Args:
        action: Lowercase action slug.
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip",   callback_data=f"{action}_skip_proof"),
        InlineKeyboardButton("Cancel", callback_data=f"{action}_cancel"),
    ]])


## ── Reason prompt helpers ──────────────────────────────────────────────────

def reason_prompt(
    target_mention: str,
    action_label: str,
    extra_info: str = "",
) -> str:
    """Return the prompt message asking the moderator for a reason.

    Args:
        target_mention: HTML mention or plain name of the target user.
        action_label:   Human-readable action name, e.g. ``"kick"``, ``"mute"``.
        extra_info:     Optional context appended after the target mention in
            parentheses - e.g. a duration string for mutes.

    Returns:
        An HTML-formatted prompt string ready to send as a bot reply.

    Example::

        reason_prompt("<a href='...'>Alice</a>", "mute", extra_info="(7d)")
        # → "About to mute <a href='...'>Alice</a> (7d).\\nWhat's the reason?..."
    """
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
    """Return the proof-step prompt when an inline reason was already provided.

    Args:
        action_label:   Human-readable action name, e.g. ``"kick"``.
        inline_reason:  The reason text already captured from the command.
        target_mention: HTML mention or plain name of the target user.
        extra_info:     Optional context shown after the target mention.

    Returns:
        An HTML-formatted prompt string for the proof step.
    """
    suffix = f" {extra_info}" if extra_info else ""
    return (
        f"{action_label.capitalize()}ing {target_mention}{suffix}.\n"
        f"Reason: <b>{inline_reason}</b>\n\n"
        "Got any proof? Send a photo or video, or tap <b>Skip</b> to proceed."
    )


def proof_step_prompt(
    target_mention: str,
    action_label: str,
    reason: str,
    extra_info: str = "",
) -> str:
    """Return the proof-step prompt after the reason has been collected in-conversation.

    Used in the WAITING_PROOF step when the reason was typed by the moderator
    (not given inline with the command).

    Args:
        target_mention: HTML mention or plain name of the target user.
        action_label:   Human-readable action name, e.g. ``"kick"``.
        reason:         The reason collected from the previous conversation step.
        extra_info:     Optional context shown after the target mention.

    Returns:
        An HTML-formatted prompt string for the proof step.
    """
    suffix = f" {extra_info}" if extra_info else ""
    return (
        f"Reason noted — {action_label.lower()}ing {target_mention}{suffix}.\n"
        f"Reason: <b>{reason}</b>\n\n"
        "Got any proof? Send a photo or video, or tap <b>Skip</b> to proceed."
    )


## ── Proof recording ─────────────────────────────────────────────────────────

def record_proof(msg: Message) -> str | None:
    """Extract a proof description string from a photo or video message.

    Returns a short description (``"Photo (msg <id>)"`` / ``"Video (msg <id>)"``),
    or ``None`` if the message contains neither a photo nor a video.

    Args:
        msg: The :class:`telegram.Message` sent by the moderator as proof.
    """
    if msg.photo:
        return f"Photo (msg {msg.message_id})"
    if msg.video:
        return f"Video (msg {msg.message_id})"
    return None
