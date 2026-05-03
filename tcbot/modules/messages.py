# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Central message-string namespace for the TCF bot.

All user-facing strings live here so they can be audited and tested in one
place. No emojis are used anywhere in this file.
"""
from __future__ import annotations


class _M:
    BRANDING_LINE = "𝘛𝘊𝘍 - 𝘛𝘳𝘢𝘯𝘴𝘴𝘪𝘰𝘯 𝘊𝘰𝘳𝘦 𝘍𝘦𝘥𝘦𝘳𝘢𝘵𝘪𝘰𝘯"

    NOT_AUTHORIZED = "You are not authorized."
    CANNOT_RESOLVE_USER = "Cannot resolve user."
    USER_NOT_BANNED = "User is not banned."
    ALREADY_TC_ADMIN = "Already a Transsion Core Admin."
    NOT_TC_ADMIN = "Not a Transsion Core Admin."
    INVALID_OR_EXPIRED_BAN = "Invalid or expired ban."

    BAN_SUCCESS = (
        "User {target_id} has been banned from the Transsion Core. Reason: {reason}"
    )
    UNBAN_SUCCESS = "User {target_id} has been unbanned from the Transsion Core."
    PROMOTE_OWNER_DONE = "User {target_id} is now a Transsion Core Admin."
    TRANSFER_DONE = "Ownership transferred to {target_id}."

    APPEAL_DECISION_APPROVED = (
        "User has been unbanned from the Transsion Core. Reviewed by {reviewer_link}."
    )
    APPEAL_DECISION_REJECTED = (
        "Your appeal has been reviewed and rejected. Reviewed by {reviewer_link}."
    )


M = _M()
