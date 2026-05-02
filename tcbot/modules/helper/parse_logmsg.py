# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Log message composers – all messages sent to LOGS and PROOFS channels."""
from __future__ import annotations

from datetime import datetime, timezone

from tcbot.config import cfg
from tcbot.modules.helper.formatter import bold, code, esc, italic, link, mention
from tcbot.modules.helper.parse_link import message_link


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def ban_log(
    target_id: int,
    target_name: str,
    admin_id: int,
    admin_name: str,
    reason: str,
    ban_id: str,
    proof_link: str | None = None,
) -> str:
    lines = [
        f"⛔ {bold('TCF Federation Ban')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"👮 Admin: {mention(admin_id, admin_name)}",
        f"📋 Reason: {esc(reason)}",
        f"🔖 Ban ID: {code(ban_id)}",
    ]
    if proof_link:
        lines.append(f"📎 Proof: {link('View', proof_link)}")
    lines += ["", italic(_now())]
    return "\n".join(lines)


def ban_update_log(
    target_id: int,
    target_name: str,
    admin_id: int,
    admin_name: str,
    reason: str,
    ban_id: str,
    update_count: int,
    proof_link: str | None = None,
) -> str:
    lines = [
        f"✏️ {bold('TCF Ban Updated')} #{update_count}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"👮 Admin: {mention(admin_id, admin_name)}",
        f"📋 Reason: {esc(reason)}",
        f"🔖 Ban ID: {code(ban_id)}",
    ]
    if proof_link:
        lines.append(f"📎 New Proof: {link('View', proof_link)}")
    lines += ["", italic(_now())]
    return "\n".join(lines)


def unban_log(
    target_id: int,
    target_name: str,
    admin_id: int,
    admin_name: str,
    ban_id: str,
) -> str:
    return "\n".join([
        f"✅ {bold('TCF Federation Unban')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"👮 Admin: {mention(admin_id, admin_name)}",
        f"🔖 Ban ID: {code(ban_id)}",
        "",
        italic(_now()),
    ])


def appeal_submitted(
    target_id: int,
    target_name: str,
    ban_id: str,
    reason: str,
    log_link: str | None = None,
) -> str:
    lines = [
        f"📨 {bold('Appeal Submitted')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"🔖 Ban ID: {code(ban_id)}",
        f"📝 Reason: {esc(reason)}",
    ]
    if log_link:
        lines.append(f"📋 Ban Log: {link('View', log_link)}")
    lines += ["", italic(_now())]
    return "\n".join(lines)


def appeal_accepted(
    target_id: int,
    target_name: str,
    admin_id: int,
    admin_name: str,
    ban_id: str,
) -> str:
    return "\n".join([
        f"✅ {bold('Appeal Accepted')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"👮 Reviewed by: {mention(admin_id, admin_name)}",
        f"🔖 Ban ID: {code(ban_id)}",
        "",
        italic(_now()),
    ])


def appeal_rejected(
    target_id: int,
    target_name: str,
    admin_id: int,
    admin_name: str,
    ban_id: str,
    response: str | None = None,
) -> str:
    lines = [
        f"❌ {bold('Appeal Rejected')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"👮 Reviewed by: {mention(admin_id, admin_name)}",
        f"🔖 Ban ID: {code(ban_id)}",
    ]
    if response:
        lines.append(f"💬 Note: {esc(response)}")
    lines += ["", italic(_now())]
    return "\n".join(lines)


def join_request_log(chat_id: int, title: str, owner_id: int, owner_name: str) -> str:
    return "\n".join([
        f"📩 {bold('Group Join Request')}",
        "",
        f"🏠 Group: {bold(esc(title))} {code(str(chat_id))}",
        f"👤 Owner: {mention(owner_id, owner_name)}",
        "",
        italic(_now()),
    ])


def admin_promoted(
    target_id: int,
    target_name: str,
    admin_id: int,
    admin_name: str,
) -> str:
    return "\n".join([
        f"🛡️ {bold('Admin Promoted')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"👮 Promoted by: {mention(admin_id, admin_name)}",
        "",
        italic(_now()),
    ])


def admin_demoted(
    target_id: int,
    target_name: str,
    admin_id: int,
    admin_name: str,
) -> str:
    return "\n".join([
        f"🔻 {bold('Admin Demoted')}",
        "",
        f"👤 User: {mention(target_id, target_name)} {code(str(target_id))}",
        f"👮 Demoted by: {mention(admin_id, admin_name)}",
        "",
        italic(_now()),
    ])
