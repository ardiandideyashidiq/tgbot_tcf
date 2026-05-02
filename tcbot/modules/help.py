# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Help command and all help topic callbacks."""
from __future__ import annotations

import logging

from telegram import CallbackQuery, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler

from tcbot.modules.helper import keyboards
from tcbot.utils.prefixes import build_prefixed_filters

log = logging.getLogger(__name__)

__module_name__ = None

## ---------------------------------------------------------------------------
## Help content per module topic
## ---------------------------------------------------------------------------

HELP_CONTENT: dict[str, tuple[str, str]] = {
    "help_ban": (
        "Ban",
        "<code>/tcban &lt;target&gt; &lt;reason&gt;</code> – ban a user federation-wide.\n"
        "Reply to a message or provide a user ID / @username as the target.\n"
        "Aliases: <code>/ban</code>, <code>/tcfban</code>",
    ),
    "help_unban": (
        "Unban",
        "<code>/tcunban &lt;target&gt;</code> – lift a federation ban.\n"
        "Aliases: <code>/unban</code>, <code>/tcfunban</code>",
    ),
    "help_check": (
        "Check Ban",
        "<code>/checkme</code> – check your own federation ban status.\n"
        "Aliases: <code>/myban</code>, <code>/amibanned</code>",
    ),
    "help_baninfo": (
        "Ban Info",
        "<code>/baninfo &lt;target&gt;</code> – check ban details for any user.\n"
        "Aliases: <code>/checkban</code>, <code>/banstatus</code>",
    ),
    "help_admins": (
        "Promote/Demote",
        "<code>/tcpromote &lt;target&gt;</code> – promote a user to admin.\n"
        "Aliases: <code>/promote</code>, <code>/tcfpromote</code>\n\n"
        "<code>/tcdemote &lt;target&gt;</code> – remove admin status (owner only).\n"
        "Aliases: <code>/demote</code>, <code>/tcfdemote</code>\n\n"
        "<code>/tcpromoterequests</code> – submit a promotion request.\n"
        "Aliases: <code>/promoreqs</code>, <code>/tcreqs</code>\n\n"
        "<code>/tcpromotelist</code> – list pending requests (staff only).",
    ),
    "help_transfer": (
        "Transfer Owner",
        "<code>/tctransfer &lt;target&gt;</code> – transfer ownership (owner only).\n"
        "Aliases: <code>/transfer</code>, <code>/tcowner</code>",
    ),
    "help_broadcast": (
        "Broadcast",
        "<code>/tcbroadcast &lt;message&gt;</code> – send to all affiliated groups.\n"
        "Provide text or reply to a message. Staff only.\n"
        "Aliases: <code>/broadcast</code>, <code>/tcannounce</code>",
    ),
    "help_appeal": (
        "Appeal",
        "Submit a ban appeal via the <b>Submit Appeal</b> button on your ban log,\n"
        "or by using <code>/start appeal_&lt;ban_id&gt;</code> in my private chat.\n\n"
        "Reply with a message starting with <code>#appeal</code> containing:\n"
        "- <b>Log link:</b> (from @TranssionCoreFederationLogs)\n"
        "- <b>Clarification:</b> (your honest explanation)\n"
        "- <b>Agreement:</b> (your commitment not to repeat the violation)\n\n"
        "<b>Example:</b>\n"
        "<pre>#appeal\n"
        "Log link: https://t.me/TranssionCoreFederationLogs/1\n"
        "Clarification: I spammed unintentionally.\n"
        "Agreement: I will not use automation tools again.</pre>\n\n"
        "Your appeal will be reviewed by Transsion Core admins. "
        "The banning admin has 12 hours to decide; after that, any admin can approve or reject it.\n"
        "If approved, the ban is lifted; if rejected, the ban remains. You will be notified of the decision.",
    ),
    "help_connect": (
        "Group Affiliation",
        "<code>/jointc</code> – request affiliation with TCF (group admin only).\n"
        "Aliases: <code>/requestjoin</code>, <code>/applytc</code>\n\n"
        "When the bot is added to a group, it automatically prompts the group owner to join.",
    ),
    "help_disconnect": (
        "Disaffiliate",
        "<code>/detc</code> – remove the current group from TCF (group owner or TC admin).\n"
        "Aliases: <code>/leavetc</code>, <code>/untc</code>\n\n"
        "<code>/rmtc &lt;chat_id&gt;</code> – force-remove by ID (staff only).\n"
        "Aliases: <code>/removetc</code>, <code>/deletetc</code>",
    ),
    "help_cleanup": (
        "Cleanup",
        "<code>/cleanup</code> – remove defunct groups (TC staff only).\n"
        "Aliases: <code>/purge</code>, <code>/tcclean</code>",
    ),
    "help_joinleave": (
        "Join/Leave",
        "<code>/leaveall</code> – leave all affiliated groups (owner only).\n"
        "Aliases: <code>/exitall</code>, <code>/tcleave</code>",
    ),
    "help_stats": (
        "Statistics",
        "<code>/tcstats</code> – show federation statistics.\n"
        "Aliases: <code>/stats</code>, <code>/tcinfo</code>",
    ),
}

_HELP_TOPIC_PATTERN = (
    r"^help_(ban|unban|check|baninfo|admins|transfer|broadcast|appeal"
    r"|connect|disconnect|cleanup|joinleave|stats)$"
)


## ---------------------------------------------------------------------------
## Handlers
## ---------------------------------------------------------------------------

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "<b>TCF Bot Help</b>\n"
        "I manage Transsion Core groups, bans, appeals, and more. Select a topic below:",
        parse_mode="HTML",
        reply_markup=keyboards.help_topics_kb(),
    )


async def on_menu_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "<b>TCF Bot Help</b>\n"
        "I manage Transsion Core groups, bans, appeals, and more. Select a topic below:",
        parse_mode="HTML",
        reply_markup=keyboards.help_topics_kb(),
    )


async def on_help_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query
    await q.answer()
    topic = q.data
    if topic not in HELP_CONTENT:
        await q.edit_message_text("Topic not found.", reply_markup=keyboards.back_to_help_kb())
        return
    name, text = HELP_CONTENT[topic]
    await q.edit_message_text(
        f"<b>{name}</b>\n\n{text}",
        parse_mode="HTML",
        reply_markup=keyboards.back_to_help_kb(),
    )


_HELP_FILTER = (
    build_prefixed_filters("help")
    | build_prefixed_filters("commands")
)

__handlers__ = [
    MessageHandler(_HELP_FILTER, cmd_help),
    CallbackQueryHandler(on_menu_help, pattern=r"^menu_help$"),
    CallbackQueryHandler(on_help_topic, pattern=_HELP_TOPIC_PATTERN),
]
