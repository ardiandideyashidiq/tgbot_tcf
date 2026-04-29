# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Resolve a command target from reply, @username, or numeric user id."""
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes


class ResolvedTarget:
    __slots__ = ("id", "first_name", "username", "raw")

    def __init__(self, user_id: int, first_name: str | None, username: str | None, raw=None):
        self.id = user_id
        self.first_name = first_name or str(user_id)
        self.username = username
        self.raw = raw


async def resolve_target(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> ResolvedTarget | None:
    msg = update.effective_message
    if msg is None:
        return None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        u = msg.reply_to_message.from_user
        return ResolvedTarget(u.id, u.first_name, u.username, raw=u)

    args = context.args or []
    if not args:
        return None

    raw = args[0].lstrip("@")
    if raw.lstrip("-").isdigit():
        try:
            chat = await context.bot.get_chat(int(raw))
        except TelegramError:
            return None
    else:
        try:
            chat = await context.bot.get_chat(raw)
        except TelegramError:
            return None

    first_name = getattr(chat, "first_name", None) or getattr(chat, "title", None)
    return ResolvedTarget(chat.id, first_name, getattr(chat, "username", None), raw=chat)


def get_reason(context: ContextTypes.DEFAULT_TYPE, update: Update) -> str:
    """For commands invoked as a reply, full args become the reason.
    Otherwise, args after the first (target) become the reason."""
    msg = update.effective_message
    args = context.args or []
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        return " ".join(args).strip()
    return " ".join(args[1:]).strip()
