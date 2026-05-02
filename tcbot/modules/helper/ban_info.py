# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Shared ban detail builder — used by checking.py and stats_flow.py."""
from __future__ import annotations

from tcbot import cfg, database as db
from tcbot.modules.helper.formatter import code, esc, mention
from tcbot.modules.helper.parse_link import message_link


async def build_ban_detail(ban: dict, target_fname: str | None = None) -> tuple[str, str | None]:
    """Return (formatted text, proof_link or None) for a ban document."""
    uid = ban["banned_user_id"]
    aid = ban.get("admin_user_id", 0)

    if target_fname is None:
        target_fname = await db.users_db.get_first_name(uid, str(uid))
    admin_fname = await db.users_db.get_first_name(aid, str(aid))

    proof_chat, proof_thread = cfg.proofs
    proof_link = (
        message_link(proof_chat, ban["proof_message_id"], proof_thread)
        if ban.get("proof_message_id") else None
    )

    text = (
        "<b>Users Ban Informations</b>\n\n"
        "<b>User Information:</b>\n"
        f"- User: {mention(uid, target_fname)}\n"
        f"- User ID: {code(str(uid))}\n\n"
        "<b>Banned by:</b>\n"
        f"- ID: {code(str(aid))}\n"
        f"- Admin/Staff: {mention(aid, admin_fname)}\n\n"
        f"- Ban ID: {code(ban['ban_id'])}\n\n"
        f"<i>You can check ban using ban ID or target</i>"
    )
    return text, proof_link
