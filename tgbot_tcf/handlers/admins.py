"""Federation owner / admin management."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..config import BRANDING
from ..db import fed_admins, fed_owners
from ..utils.auth import is_fed_owner
from ..utils.format import fmt_now, safe_first_name, user_link, utcnow
from ..utils.logger import log_to_channel
from ..utils.targets import resolve_target

logger = logging.getLogger(__name__)


async def cmd_promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    if not await is_fed_owner(user.id):
        await msg.reply_text("You are not authorized.")
        return

    target = await resolve_target(update, context)
    if target is None:
        if not (context.args or msg.reply_to_message):
            await msg.reply_text("Reply to a user, provide a user ID, or provide a username to promote.")
        else:
            await msg.reply_text("Cannot resolve user.")
        return

    if await fed_admins.find_one({"user_id": target.id}):
        await msg.reply_text("Already a Federation Admin.")
        return

    await fed_admins.insert_one(
        {"user_id": target.id, "promoted_by": user.id, "promoted_date": utcnow()}
    )
    await msg.reply_text(f"User {target.id} is now a Federation Admin.")
    await log_to_channel(
        context,
        "<b>New Federation Admin Promoted</b>\n"
        f"{BRANDING}\n"
        f"Admin: {user_link(target.id, target.first_name)} (ID: {target.id})\n"
        f"Promoted by Owner: {user_link(user.id, safe_first_name(user))} (ID: {user.id})\n"
        f"Date: {fmt_now()}",
    )


async def cmd_demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    if not await is_fed_owner(user.id):
        await msg.reply_text("You are not authorized.")
        return

    target = await resolve_target(update, context)
    if target is None:
        if not (context.args or msg.reply_to_message):
            await msg.reply_text("Reply to a user, provide a user ID, or provide a username to demote.")
        else:
            await msg.reply_text("Cannot resolve user.")
        return

    res = await fed_admins.delete_one({"user_id": target.id})
    if res.deleted_count == 0:
        await msg.reply_text("Not a Federation Admin.")
        return

    await msg.reply_text("User demoted from Federation Admin.")
    await log_to_channel(
        context,
        "<b>Federation Admin Demoted</b>\n"
        f"{BRANDING}\n"
        f"Admin: {user_link(target.id, target.first_name)} (ID: {target.id})\n"
        f"Demoted by Owner: {user_link(user.id, safe_first_name(user))} (ID: {user.id})\n"
        f"Date: {fmt_now()}",
    )


async def cmd_transfer_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    if not await is_fed_owner(user.id):
        await msg.reply_text("You are not authorized.")
        return

    target = await resolve_target(update, context)
    if target is None:
        if not (context.args or msg.reply_to_message):
            await msg.reply_text(
                "Reply to a user, provide a user ID, or provide a username to transfer ownership to."
            )
        else:
            await msg.reply_text("Cannot resolve user.")
        return

    if target.id == user.id:
        await msg.reply_text("You are already the Federation Owner.")
        return

    await fed_owners.delete_many({})
    await fed_owners.insert_one({"user_id": target.id})
    await fed_admins.delete_one({"user_id": target.id})
    await fed_admins.update_one(
        {"user_id": user.id},
        {"$setOnInsert": {"user_id": user.id, "promoted_by": user.id, "promoted_date": utcnow()}},
        upsert=True,
    )

    await msg.reply_text(f"Ownership transferred to {target.id}.")
    await log_to_channel(
        context,
        "<b>Federation Ownership Transferred</b>\n"
        f"{BRANDING}\n"
        f"New Owner: {user_link(target.id, target.first_name)} (ID: {target.id})\n"
        f"Previous Owner: {user_link(user.id, safe_first_name(user))} (ID: {user.id})\n"
        f"Date: {fmt_now()}",
    )
