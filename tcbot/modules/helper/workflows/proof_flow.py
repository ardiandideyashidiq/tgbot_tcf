# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Proof upload helper - sends ban proof media to the configured proof channel
"""

from __future__ import annotations

import logging

from telegram import Bot, InputMediaPhoto, InputMediaVideo, Message

log = logging.getLogger(__name__)


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
            return sent[0].message_id
        elif msgs[0].photo:
            sent = await bot.send_photo(
                proof_chat, msgs[0].photo[-1].file_id,
                caption=caption, parse_mode="HTML",
                message_thread_id=proof_thread,
            )
            return sent.message_id
        elif msgs[0].video:
            sent = await bot.send_video(
                proof_chat, msgs[0].video.file_id,
                caption=caption, parse_mode="HTML",
                message_thread_id=proof_thread,
            )
            return sent.message_id
    except Exception as exc:
        log.error("Proof upload failed: %s", exc)
    return None
