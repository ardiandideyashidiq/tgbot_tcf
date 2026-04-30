# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Centralised log-channel writer used by every TCF event."""
import logging

from telegram import InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .. import LOG_CHANNEL

logger = logging.getLogger(__name__)


async def log_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> int | None:
    try:
        msg = await context.bot.send_message(
            chat_id=LOG_CHANNEL,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return msg.message_id
    except TelegramError as exc:
        logger.warning("Failed to log to channel: %s", exc)
        return None


async def edit_log_message(
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Edit an existing log-channel message in place. Returns True on success."""
    try:
        await context.bot.edit_message_text(
            chat_id=LOG_CHANNEL,
            message_id=message_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return True
    except TelegramError as exc:
        logger.warning("Failed to edit log message %s: %s", message_id, exc)
        return False
