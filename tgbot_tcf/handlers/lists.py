"""Read-only listing commands: fedgroups, fedstats, fedchannels."""
import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..config import (
    APPEAL_TOPIC,
    EXEC_GROUP,
    LOG_CHANNEL,
    MAIN_CHANNEL,
    MAIN_GROUP,
    PROOF_TOPIC,
)
from ..db import bans, fed_admins, federated_groups, fed_owners
from ..utils.format import user_link

logger = logging.getLogger(__name__)


async def cmd_fedgroups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    cursor = federated_groups.find({"is_active": True})
    groups = [g async for g in cursor]
    if not groups:
        await msg.reply_text("No groups are currently affiliated with TCF.")
        return
    lines = ["<b>Affiliated TCF Groups</b>"]
    for g in groups[:50]:
        title = g.get("title") or str(g["chat_id"])
        lines.append(f"{title} (ID: {g['chat_id']})")
    if len(groups) > 50:
        lines.append(f"... and {len(groups) - 50} more groups.")
    await msg.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_fedstats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    owner = await fed_owners.find_one({})
    admins_count = await fed_admins.count_documents({})
    groups_count = await federated_groups.count_documents({"is_active": True})
    bans_count = await bans.count_documents({"is_active": True})
    owner_line = "Not set"
    if owner:
        owner_id = owner["user_id"]
        try:
            chat = await context.bot.get_chat(owner_id)
            owner_name = chat.first_name or str(owner_id)
        except TelegramError:
            owner_name = str(owner_id)
        owner_line = f"{user_link(owner_id, owner_name)}"
    text = (
        "<b>TCF Federation Statistics</b>\n"
        f"Owner: {owner_line}\n"
        f"Federation Admins: {admins_count}\n"
        f"Affiliated Groups: {groups_count}\n"
        f"Active Bans: {bans_count}"
    )
    await msg.reply_text(text, parse_mode="HTML")


async def cmd_fedchannels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    text = (
        f"Log Channel: {LOG_CHANNEL}\n"
        f"Main Group: {MAIN_GROUP}\n"
        f"Proof Topic: {PROOF_TOPIC}\n"
        f"Appeal Topic: {APPEAL_TOPIC}\n"
        f"Main Channel: {MAIN_CHANNEL}\n"
        f"Exec Group: {EXEC_GROUP}"
    )
    await msg.reply_text(text)
