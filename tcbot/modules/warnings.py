# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Per-group warning commands."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot.modules.helper import decorators, extraction
from tcbot.modules.helper.workflows.warning_flow import (
    WARN_LIMIT,
    execute_resetwarns,
    execute_unwarn,
    execute_warn,
    execute_warnlist,
)
from tcbot.utils.prefixes import build_prefixed_filters, parse_cmd_args

__module_name__ = "Warnings"
__help_text__ = (
    "<code>/warn</code> <i>&lt;target&gt; &lt;reason&gt;</i> – warn a user in this group.\n"
    f"At {WARN_LIMIT} warnings the user is automatically banned.\n"
    "Aliases: <code>/tcwarn</code>\n\n"
    "<code>/unwarn</code> <i>&lt;target&gt;</i> – remove the most recent warning.\n"
    "Aliases: <code>/tcunwarn</code>\n\n"
    "<code>/warns</code> <i>&lt;target&gt;</i> – show a user's current warning count and reasons.\n"
    "Aliases: <code>/warnlist</code>\n\n"
    "<code>/resetwarns</code> <i>&lt;target&gt;</i> – clear all warnings for a user.\n"
    "Aliases: <code>/clearwarns</code>"
)


@decorators.staff_only
async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    args = parse_cmd_args(msg.text)

    if msg.reply_to_message:
        target_id, target_name = await extraction.extract_target(update, [], ctx.bot)
        reason = " ".join(args).strip()
    else:
        target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
        reason = " ".join(args[1:]).strip()

    if not target_id:
        await msg.reply_text("Specify a target – reply to a message or provide a user ID.")
        return
    if not reason:
        await msg.reply_text("A reason is required. Usage: /warn <target> <reason>")
        return

    await execute_warn(update, ctx, target_id, target_name or str(target_id), reason)


@decorators.staff_only
async def cmd_unwarn(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_cmd_args(update.effective_message.text)
    target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
    if not target_id:
        await update.effective_message.reply_text(
            "Specify a target – reply to a message or provide a user ID."
        )
        return
    await execute_unwarn(update, ctx, target_id, target_name or str(target_id))


@decorators.staff_only
async def cmd_warnlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_cmd_args(update.effective_message.text)
    target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
    if not target_id:
        await update.effective_message.reply_text(
            "Specify a target – reply to a message or provide a user ID."
        )
        return
    await execute_warnlist(update, ctx, target_id, target_name or str(target_id))


@decorators.staff_only
async def cmd_resetwarns(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_cmd_args(update.effective_message.text)
    target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
    if not target_id:
        await update.effective_message.reply_text(
            "Specify a target – reply to a message or provide a user ID."
        )
        return
    await execute_resetwarns(update, ctx, target_id, target_name or str(target_id))


_WARN_FILTER = build_prefixed_filters("warn") | build_prefixed_filters("tcwarn")
_UNWARN_FILTER = build_prefixed_filters("unwarn") | build_prefixed_filters("tcunwarn")
_WARNLIST_FILTER = (
    build_prefixed_filters("warns")
    | build_prefixed_filters("warnlist")
)
_RESETWARNS_FILTER = (
    build_prefixed_filters("resetwarns")
    | build_prefixed_filters("clearwarns")
)

__handlers__ = [
    MessageHandler(_WARN_FILTER, cmd_warn),
    MessageHandler(_UNWARN_FILTER, cmd_unwarn),
    MessageHandler(_WARNLIST_FILTER, cmd_warnlist),
    MessageHandler(_RESETWARNS_FILTER, cmd_resetwarns),
]
