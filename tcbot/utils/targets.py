# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Target resolution helpers – dataclass and reason extraction."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResolvedTarget:
    """A resolved Telegram user target with a guaranteed display name."""

    id: int
    first_name: str | None
    username: str | None = None
    raw: object = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not self.first_name:
            self.first_name = str(self.id)


def get_reason(context: object, update: object) -> str:
    """Extract the ban/action reason from command arguments.

    When the command was used as a reply, *all* args are the reason.
    When the command used an explicit target (@user or user_id as first arg),
    the first arg is skipped and the rest form the reason.
    """
    msg = getattr(update, "effective_message", None)
    reply = getattr(msg, "reply_to_message", None) if msg else None
    is_reply = bool(reply and getattr(reply, "from_user", None))

    args: list[str] = list(getattr(context, "args", None) or [])
    if is_reply:
        return " ".join(args)
    return " ".join(args[1:])
