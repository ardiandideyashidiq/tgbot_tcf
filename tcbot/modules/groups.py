# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation groups listing with pagination."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler

from tcbot import database as db
from tcbot.modules.helper.formatter import code, esc
from tcbot.utils.prefixes import build_prefixed_filters

__module_name__ = "Groups"
__help_text__ = (
    "<b>Help — Groups List</b>\n\n"

    "<b>Commands & Aliases</b>\n"
    "<code>/tcfgroups</code> — alias: <code>/tcg</code>\n\n"

    "<b>Who can use it</b>\n"
    "Anyone — no special permissions needed.\n\n"

    "<b>Where to use it</b>\n"
    "Anywhere — bot PM, exec group, or any connected group.\n\n"

    "<b>What it does</b>\n"
    "Shows a paginated list of all groups currently connected to the Transsion Core Federation. "
    "Each entry shows the group name and its chat ID. "
    "Results are shown 10 per page with Prev/Next navigation.\n\n"

    "<b>Example</b>\n"
    "<code>/tcfgroups</code>\n"
    "<code>/tcg</code>"
)

_PAGE_SIZE = 10


def _groups_page(groups: list[dict], page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    total = len(groups)
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    start = page * _PAGE_SIZE
    chunk = groups[start: start + _PAGE_SIZE]

    lines = [f"<b>Connected Groups ({total})</b>  Page {page + 1}/{total_pages}\n"]
    for grp in chunk:
        lines.append(f"- {esc(grp['title'])} {code(str(grp['chat_id']))}")

    rows = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("Prev", callback_data=f"groups_page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next", callback_data=f"groups_page:{page + 1}"))
    if nav:
        rows.append(nav)
    kb = InlineKeyboardMarkup(rows) if rows else None
    return "\n".join(lines), kb


async def cmd_tcfgroups(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    groups = await db.groups_db.active_groups()
    if not groups:
        await update.effective_message.reply_text("No groups are currently connected to TCF.")
        return
    text, kb = _groups_page(groups, 0)
    ctx.user_data["groups_list"] = groups
    await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def on_groups_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    page = int(q.data.split(":")[1])
    groups = ctx.user_data.get("groups_list")
    if not groups:
        groups = await db.groups_db.active_groups()
        ctx.user_data["groups_list"] = groups
    text, kb = _groups_page(groups, page)
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


_GROUPS_FILTER = (
    build_prefixed_filters("tcfgroups")
    | build_prefixed_filters("tcg")
)

__handlers__ = [
    MessageHandler(_GROUPS_FILTER, cmd_tcfgroups),
    CallbackQueryHandler(on_groups_page, pattern=r"^groups_page:\d+$"),
]
