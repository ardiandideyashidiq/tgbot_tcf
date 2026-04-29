# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Group affiliation, disaffiliation, and chat-member event handling.

Implements PROMPT Feature 1 (affiliation prompt + pending_joins fallback +
auto-completion when the bot is later promoted) and the affiliated-side
member-cache seeding hook for Feature 33.
"""
import logging

from telegram import (
    ChatMember,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ChatType
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .. import BRANDING, INITIAL_OWNER_ID
from ..database import federated_groups, pending_joins, tc_owners
from ..utils.auth import is_authorized
from ..utils.format import fmt_now, safe_first_name, user_link, utcnow
from ..utils.logger import log_to_channel
from .membercache import seed_member_cache

logger = logging.getLogger(__name__)

REQUIRED_PERMS = ("can_delete_messages", "can_restrict_members", "can_invite_users")
PERM_HINT = (
    "Please make the bot an admin with the necessary permissions "
    "(delete messages, ban users, invite users) and try again. "
    "Once you grant the permissions, affiliation will complete automatically."
)


async def _bot_has_required_perms(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> bool:
    """Check that the bot has the three required admin permissions."""
    try:
        me = await context.bot.get_chat_member(chat_id, context.bot.id)
    except TelegramError as exc:
        logger.warning("Permission check failed in %s: %s", chat_id, exc)
        return False
    if me.status not in ("administrator", "creator"):
        return False
    for perm in REQUIRED_PERMS:
        if not getattr(me, perm, False):
            return False
    return True


async def _ensure_first_owner() -> None:
    """Seed the initial owner if the tc_owners collection is empty."""
    if await tc_owners.find_one({}) is None:
        await tc_owners.insert_one({"user_id": INITIAL_OWNER_ID})


async def _record_pending(
    chat_id: int, title: str, requested_by: int, notice_message_id: int | None
) -> None:
    await pending_joins.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "chat_id": chat_id,
                "title": title,
                "requested_by": requested_by,
                "requested_at": utcnow(),
                "notice_message_id": notice_message_id,
            }
        },
        upsert=True,
    )


async def _finalize_affiliation(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    title: str,
    added_by: int,
    added_by_name: str,
) -> None:
    """Insert/refresh the federated group, seed the member cache, log it."""
    await federated_groups.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "chat_id": chat_id,
                "title": title,
                "added_by": added_by,
                "added_date": utcnow(),
                "is_active": True,
            }
        },
        upsert=True,
    )
    await pending_joins.delete_one({"chat_id": chat_id})
    await _ensure_first_owner()
    seeded = await seed_member_cache(context, chat_id)
    logger.info("Seeded %d members for newly affiliated chat %s", seeded, chat_id)

    await log_to_channel(
        context,
        "<b>New Affiliated Group</b>\n"
        f"{BRANDING}\n"
        f"Group: {title} (ID: {chat_id})\n"
        f"Added by Owner: {user_link(added_by, added_by_name)} (ID: {added_by})\n"
        f"Date: {fmt_now()}",
    )


async def on_new_chat_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send affiliation prompt when the bot is added to a group."""
    msg = update.effective_message
    if msg is None or msg.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    if not msg.new_chat_members:
        return
    if not any(m.id == context.bot.id for m in msg.new_chat_members):
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Join Transsion Core", callback_data="tc_join"
                ),
                InlineKeyboardButton("Cancel", callback_data="tc_cancel"),
            ]
        ]
    )
    try:
        await msg.reply_text(
            "Do you want this community to join the Transsion Core Federation?",
            reply_markup=keyboard,
        )
    except TelegramError as exc:
        logger.warning("Could not send affiliation prompt: %s", exc)


async def on_affiliation_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle tc_join / tc_cancel inline button presses."""
    cq = update.callback_query
    if cq is None or cq.message is None:
        return
    chat = cq.message.chat
    user = cq.from_user

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
    except TelegramError as exc:
        logger.warning("get_chat_member failed: %s", exc)
        await cq.answer("Cannot verify your role.", show_alert=True)
        return

    if member.status != ChatMember.OWNER:
        await cq.answer("Only the group owner can decide.", show_alert=True)
        return

    if cq.data == "tc_join":
        await cq.answer()
        existing = await federated_groups.find_one({"chat_id": chat.id})
        if existing and existing.get("is_active"):
            try:
                await cq.edit_message_text("Already affiliated.")
            except TelegramError:
                pass
            return

        if not await _bot_has_required_perms(context, chat.id):
            try:
                await cq.edit_message_text(PERM_HINT)
            except TelegramError:
                pass
            await _record_pending(
                chat.id,
                chat.title or str(chat.id),
                user.id,
                cq.message.message_id,
            )
            return

        await _finalize_affiliation(
            context,
            chat.id,
            chat.title or str(chat.id),
            user.id,
            safe_first_name(user),
        )
        try:
            await cq.edit_message_text(
                "This community is now affiliated with TCF. Federation commands "
                "can now be used here by authorized Transsion Core admins."
            )
        except TelegramError:
            pass
        return

    if cq.data == "tc_cancel":
        await cq.answer()
        try:
            await cq.edit_message_text("Affiliation cancelled. Leaving the group.")
        except TelegramError:
            pass
        await pending_joins.delete_one({"chat_id": chat.id})
        await log_to_channel(
            context,
            "<b>Affiliation Rejected &amp; Left</b>\n"
            f"{BRANDING}\n"
            f"Group: {chat.title or str(chat.id)} (ID: {chat.id})\n"
            f"Rejected by Owner: {user_link(user.id, safe_first_name(user))} (ID: {user.id})\n"
            f"Date: {fmt_now()}",
        )
        try:
            await context.bot.leave_chat(chat.id)
        except TelegramError:
            pass


async def cmd_joinfed(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Explicitly affiliate the current group with TCF."""
    msg = update.effective_message
    if msg is None:
        return
    if msg.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await msg.reply_text("This command must be used inside a group.")
        return
    user = update.effective_user
    if user is None:
        return

    if not await is_authorized(user.id):
        try:
            member = await context.bot.get_chat_member(msg.chat.id, user.id)
            is_group_owner = member.status == ChatMember.OWNER
        except TelegramError:
            is_group_owner = False
        if not is_group_owner:
            await msg.reply_text("Only the group owner can request affiliation.")
            return

    existing = await federated_groups.find_one({"chat_id": msg.chat.id})
    if existing and existing.get("is_active"):
        await msg.reply_text("Already affiliated.")
        return

    if not await _bot_has_required_perms(context, msg.chat.id):
        sent = await msg.reply_text(PERM_HINT)
        await _record_pending(
            msg.chat.id,
            msg.chat.title or str(msg.chat.id),
            user.id,
            sent.message_id,
        )
        return

    await _finalize_affiliation(
        context,
        msg.chat.id,
        msg.chat.title or str(msg.chat.id),
        user.id,
        safe_first_name(user),
    )
    await msg.reply_text("This community is now affiliated with TCF.")


async def cmd_defed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disaffiliate the current group from TCF."""
    msg = update.effective_message
    if msg is None:
        return
    if msg.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await msg.reply_text("This command must be used inside a federated group.")
        return
    user = update.effective_user
    if user is None:
        return

    record = await federated_groups.find_one(
        {"chat_id": msg.chat.id, "is_active": True}
    )
    if not record:
        await msg.reply_text("This group is not affiliated with TCF.")
        return

    try:
        member = await context.bot.get_chat_member(msg.chat.id, user.id)
        is_group_owner = member.status == ChatMember.OWNER
    except TelegramError:
        is_group_owner = False

    if not is_group_owner and not await is_authorized(user.id):
        await msg.reply_text(
            "Only the group owner or Transsion Core admins can disaffiliate this group."
        )
        return

    await federated_groups.update_one(
        {"chat_id": msg.chat.id}, {"$set": {"is_active": False}}
    )
    await msg.reply_text(
        "This group has been removed from the Transsion Core Federation."
    )
    await log_to_channel(
        context,
        "<b>Group Disaffiliated</b>\n"
        f"{BRANDING}\n"
        f"Group: {msg.chat.title or str(msg.chat.id)} (ID: {msg.chat.id})\n"
        f"Removed by: {user_link(user.id, safe_first_name(user))} (ID: {user.id})\n"
        f"Date: {fmt_now()}",
    )
    try:
        await context.bot.leave_chat(msg.chat.id)
    except TelegramError:
        pass


async def cmd_rmfed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a federated group by ID. TC owner/admins only."""
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    if not await is_authorized(user.id):
        await msg.reply_text("You are not authorized.")
        return

    args = context.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await msg.reply_text("Usage: /rmtc <group_id>")
        return

    target_id = int(args[0])
    record = await federated_groups.find_one(
        {"chat_id": target_id, "is_active": True}
    )
    if not record:
        await msg.reply_text("Group not found or already removed.")
        return

    await federated_groups.update_one(
        {"chat_id": target_id}, {"$set": {"is_active": False}}
    )
    title = record.get("title") or str(target_id)
    try:
        await context.bot.leave_chat(target_id)
    except TelegramError:
        pass
    await msg.reply_text(
        f"Group {target_id} has been removed from the federation."
    )
    await log_to_channel(
        context,
        "<b>Group Disaffiliated</b>\n"
        f"{BRANDING}\n"
        f"Group: {title} (ID: {target_id})\n"
        f"Removed by: {user_link(user.id, safe_first_name(user))} (ID: {user.id})\n"
        f"Date: {fmt_now()}",
    )


async def on_my_chat_member(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Track bot status changes: removal **and** promotion-to-admin."""
    upd = update.my_chat_member
    if upd is None:
        return
    chat = upd.chat
    new = upd.new_chat_member
    new_status = new.status

    # 1) Bot removed from a federated group → mark inactive.
    if new_status in ("kicked", "left"):
        record = await federated_groups.find_one(
            {"chat_id": chat.id, "is_active": True}
        )
        if record:
            await federated_groups.update_one(
                {"chat_id": chat.id}, {"$set": {"is_active": False}}
            )
            await log_to_channel(
                context,
                "<b>Group Removed Bot</b>\n"
                f"{BRANDING}\n"
                f"Group: {chat.title or str(chat.id)} (ID: {chat.id})\n"
                f"Date: {fmt_now()}",
            )
        await pending_joins.delete_one({"chat_id": chat.id})
        return

    # 2) Bot promoted to admin with the required perms → auto-complete a pending join.
    if new_status not in ("administrator", "creator"):
        return
    if not all(getattr(new, p, False) for p in REQUIRED_PERMS):
        return

    pending = await pending_joins.find_one({"chat_id": chat.id})
    if not pending:
        return

    requested_by = pending.get("requested_by", 0)
    requested_by_name = str(requested_by)
    try:
        u = await context.bot.get_chat(requested_by)
        requested_by_name = u.first_name or requested_by_name
    except TelegramError:
        pass

    title = chat.title or pending.get("title") or str(chat.id)
    await _finalize_affiliation(
        context, chat.id, title, requested_by, requested_by_name
    )

    notice_id = pending.get("notice_message_id")
    if notice_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat.id,
                message_id=notice_id,
                text=(
                    "Permissions granted. This community is now affiliated with TCF. "
                    "Federation commands can now be used here."
                ),
            )
        except TelegramError:
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=(
                        "Permissions granted. This community is now affiliated with TCF."
                    ),
                )
            except TelegramError:
                pass
