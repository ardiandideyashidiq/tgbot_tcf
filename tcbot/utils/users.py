# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Cross-source identity resolver – Telegram API with member-cache fallback."""
from __future__ import annotations

from dataclasses import dataclass

from telegram.error import TelegramError

from tcbot.database import users_db


@dataclass(frozen=True)
class UserIdentity:
    """Resolved identity for a Telegram user."""

    user_id: int
    display_name: str
    username: str | None

    @property
    def name_with_username(self) -> str:
        if self.username:
            return f"{self.display_name} (@{self.username})"
        return self.display_name


class _MembersRepo:
    """Thin adapter over the member-cache collection."""

    async def find_latest_for_user(self, user_id: int) -> dict | None:
        return await users_db.get_user(user_id)


members_repo = _MembersRepo()


async def resolve_identity(ctx: object, user_id: int) -> UserIdentity:
    """Resolve a user's display identity.

    Resolution order:
    1. ``ctx.bot.get_chat`` – live data from Telegram.
    2. ``members_repo.find_latest_for_user`` – member-cache fallback.
    3. Bare user_id string – ultimate fallback.
    """
    try:
        chat = await ctx.bot.get_chat(user_id)  # type: ignore[attr-defined]
        first = getattr(chat, "first_name", None)
        title = getattr(chat, "title", None)
        uname = getattr(chat, "username", None)
        if first or title:
            return UserIdentity(
                user_id=user_id,
                display_name=str(first or title),
                username=uname,
            )
    except TelegramError:
        pass

    cached = await members_repo.find_latest_for_user(user_id)
    if cached:
        first = cached.get("first_name")
        uname = cached.get("username")
        if first:
            display = first
        elif uname:
            display = f"@{uname}"
        else:
            display = str(user_id)
        return UserIdentity(user_id=user_id, display_name=display, username=uname)

    return UserIdentity(user_id=user_id, display_name=str(user_id), username=None)
