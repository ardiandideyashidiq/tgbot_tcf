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
    "<b>Help — Warnings</b>\n\n"

    "<b>Commands & Aliases</b>\n"
    f"<code>/tcwarn</code> — alias: <code>/tcw</code>\n"
    f"<code>/tcunwarn</code> — alias: <code>/tcunw</code>\n"
    "<code>/warns</code> — alias: <code>/warnlist</code>\n"
    "<code>/resetwarns</code> — alias: <code>/clearwarns</code>\n\n"

    "<b>Who can use it</b>\n"
    f"<code>/tcwarn</code>, <code>/tcunwarn</code>, <code>/resetwarns</code> — TC Staff only.\n"
    "<code>/warns</code> — anyone.\n\n"

    "<b>Where to use it</b>\n"
    "Inside any connected group.\n\n"

    "<b>What it does</b>\n"
    f"<code>/tcwarn</code> — warns a user with a reason. Warnings are tracked per-group. "
    f"At <b>{WARN_LIMIT} warnings</b>, the user is automatically banned from the group and their "
    f"warnings are cleared.\n\n"
    "<code>/tcunwarn</code> — removes the user's most recent warning.\n\n"
    "<code>/warns</code> — shows the current warning count and list of reasons for a user.\n\n"
    "<code>/resetwarns</code> — clears all warnings for a user at once.\n\n"

    "<b>How to specify the target</b>\n"
    "Reply to a message, or provide a user ID / @username.\n\n"

    "<b>Examples</b>\n"
    "<code>/tcwarn @username spamming</code>\n"
    "<code>/tcw 123456789 off-topic flood</code>\n"
    "<code>/tcunwarn @username</code>\n"
    "<code>/warns @username</code>\n"
    "<code>/resetwarns @username</code>"
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
        await msg.reply_text("Specify a target — reply to a message or provide a user ID.")
        return
    if not reason:
        await msg.reply_text("A reason is required. Usage: /tcwarn <target> <reason>")
        return
    await execute_warn(update, ctx, target_id, target_name or str(target_id), reason)


@decorators.staff_only
async def cmd_unwarn(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_cmd_args(update.effective_message.text)
    target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
    if not target_id:
        await update.effective_message.reply_text(
            "Specify a target — reply to a message or provide a user ID."
        )
        return
    await execute_unwarn(update, ctx, target_id, target_name or str(target_id))


async def cmd_warnlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_cmd_args(update.effective_message.text)
    target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
    if not target_id:
        await update.effective_message.reply_text(
            "Specify a target — reply to a message or provide a user ID."
        )
        return
    await execute_warnlist(update, ctx, target_id, target_name or str(target_id))


@decorators.staff_only
async def cmd_resetwarns(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_cmd_args(update.effective_message.text)
    target_id, target_name = await extraction.extract_target(update, args, ctx.bot)
    if not target_id:
        await update.effective_message.reply_text(
            "Specify a target — reply to a message or provide a user ID."
        )
        return
    await execute_resetwarns(update, ctx, target_id, target_name or str(target_id))


_WARN_FILTER    = build_prefixed_filters("tcwarn")  | build_prefixed_filters("tcw")
_UNWARN_FILTER  = build_prefixed_filters("tcunwarn") | build_prefixed_filters("tcunw")
_WARNLIST_FILTER = build_prefixed_filters("warns")  | build_prefixed_filters("warnlist")
_RESET_FILTER   = build_prefixed_filters("resetwarns") | build_prefixed_filters("clearwarns")

__handlers__ = [
    MessageHandler(_WARN_FILTER,    cmd_warn),
    MessageHandler(_UNWARN_FILTER,  cmd_unwarn),
    MessageHandler(_WARNLIST_FILTER, cmd_warnlist),
    MessageHandler(_RESET_FILTER,   cmd_resetwarns),
]
