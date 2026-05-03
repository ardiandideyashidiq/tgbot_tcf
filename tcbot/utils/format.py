# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Unified formatting helpers – datetime, HTML user links, chat ID utilities."""
from __future__ import annotations

import html
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime (tzinfo=None)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fmt_dt(dt: datetime) -> str:
    """Format a datetime as DD-MM-YYYY | HH:MM."""
    return dt.strftime("%d-%m-%Y | %H:%M")


def fmt_now() -> str:
    """Format the current UTC time as DD-MM-YYYY | HH:MM."""
    return fmt_dt(utcnow())


def user_link(user_id: int, name: str) -> str:
    """HTML mention link. Falls back to str(user_id) when name is blank."""
    display = html.escape(str(name)) if name else str(user_id)
    return f'<a href="tg://user?id={user_id}">{display}</a>'


def chat_id_to_link_id(chat_id: int) -> str:
    """Strip the -100 supergroup prefix for use in t.me/c/ URLs."""
    s = str(chat_id)
    if s.startswith("-100"):
        return s[4:]
    return s.lstrip("-")


def topic_link(chat_id: int, message_id: int, thread_id: int) -> str:
    """Build a t.me/c/ deep-link to a specific message inside a topic thread."""
    link_id = chat_id_to_link_id(chat_id)
    return f"https://t.me/c/{link_id}/{message_id}?thread={thread_id}"


def safe_first_name(obj: object) -> str:
    """Extract a display name from a Telegram User/Chat-like object.

    Priority: first_name → title → str(id) → "Unknown".
    """
    first = getattr(obj, "first_name", None)
    if first:
        return str(first)
    title = getattr(obj, "title", None)
    if title:
        return str(title)
    uid = getattr(obj, "id", None)
    if uid is not None:
        return str(uid)
    return "Unknown"
