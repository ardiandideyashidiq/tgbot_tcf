# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Proof collection helpers - keyboards, prompts, media recording, and channel upload.

All proof-related concerns live here so that reason_flow and individual
module entry points have a single, unambiguous import source for anything
that touches the proof step.

Exports
───────
Keyboard builder
    proof_kb(action)          → InlineKeyboardMarkup  (Skip + Cancel)

Prompt text helpers
    proof_step_prompt(target_mention, action_label, reason, extra_info) → str

Proof recording
    record_proof(msg) → str | None

Channel upload
    upload_proof(bot, msgs, caption, proof_chat, proof_thread) → int | None
"""

from __future__ import annotations

import logging

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

log = logging.getLogger(__name__)


# ─────────────────────────── Keyboard builder ───────────────────── #

def proof_kb(action: str) -> InlineKeyboardMarkup:
    """Proof-step keyboard: Skip + Cancel."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Skip",   callback_data=f"{action}_skip_proof"),
        InlineKeyboardButton("Cancel", callback_data=f"{action}_cancel"),
    ]])


# ──────────────────────────── Prompt text ───────────────────────── #

def proof_step_prompt(
    target_mention: str,
    action_label: str,
    reason: str,
    extra_info: str = "",
) -> str:
    """Proof-step prompt after reason was collected in-conversation."""
    suffix = f" {extra_info}" if extra_info else ""
    return (
        f"Reason noted — {action_label.lower()}ing {target_mention}{suffix}.\n"
        f"Reason: <b>{reason}</b>\n\n"
        "Got any proof? Send a photo or video, or tap <b>Skip</b> to proceed."
    )


# ─────────────────────────── Proof recording ────────────────────── #

def record_proof(msg: Message) -> str | None:
    """Return a short proof description from a photo/video message, or None."""
    if msg.photo:
        return f"Photo (msg {msg.message_id})"
    if msg.video:
        return f"Video (msg {msg.message_id})"
    return None


# ─────────────────────────── Channel upload ─────────────────────── #

async def upload_proof(
    bot: Bot,
    msgs: list[Message],
    caption: str,
    proof_chat: int,
    proof_thread: int | None,
) -> int | None:
    """Upload proof media to the proof channel. Returns proof_message_id or None on failure."""
    try:
        if len(msgs) > 1:
            media: list[InputMediaPhoto | InputMediaVideo] = []
            first_caption_set = False
            for m in msgs:
                if m.photo:
                    cap = caption if not first_caption_set else None
                    media.append(InputMediaPhoto(m.photo[-1].file_id, caption=cap, parse_mode="HTML"))
                    first_caption_set = True
                elif m.video:
                    cap = caption if not first_caption_set else None
                    media.append(InputMediaVideo(m.video.file_id, caption=cap, parse_mode="HTML"))
                    first_caption_set = True
            sent = await bot.send_media_group(proof_chat, media, message_thread_id=proof_thread)
            proof_msg_id = sent[0].message_id
            log.info("Proof album uploaded: %d items, message_id=%s", len(sent), proof_msg_id)
            return proof_msg_id
        elif msgs[0].photo:
            sent = await bot.send_photo(
                proof_chat, msgs[0].photo[-1].file_id,
                caption=caption, parse_mode="HTML",
                message_thread_id=proof_thread,
            )
            log.info("Proof photo uploaded: message_id=%s", sent.message_id)
            return sent.message_id
        elif msgs[0].video:
            sent = await bot.send_video(
                proof_chat, msgs[0].video.file_id,
                caption=caption, parse_mode="HTML",
                message_thread_id=proof_thread,
            )
            log.info("Proof video uploaded: message_id=%s", sent.message_id)
            return sent.message_id
    except Exception as exc:
        log.error("Proof upload failed: %s", exc)
    return None
