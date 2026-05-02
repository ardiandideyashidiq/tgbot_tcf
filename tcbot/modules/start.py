# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Start command, main menu, and auto-discover help system."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

import tcbot.modules as _modules_pkg
from tcbot.config import cfg
from tcbot.modules.helper.formatter import bold, esc
from tcbot.utils.prefixes import build_prefixed_filters

log = logging.getLogger(__name__)

__module_name__ = None  ## Not shown in help listing

_MENU_TEXT = (
    f"👋 Welcome to the {bold(esc(cfg.community_name))} Federation Bot.\n\n"
    "Use the buttons below to explore what this bot can do, "
    "or send /help for a full command reference."
)


## Auto-discover all modules that expose __module_name__ and __help_text__
def _discover_help() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    pkg_path = str(Path(_modules_pkg.__file__).parent)

    for finder, mod_name, _ in pkgutil.iter_modules([pkg_path]):
        if mod_name in ("start", "greeting"):
            continue
        try:
            mod = importlib.import_module(f"tcbot.modules.{mod_name}")
        except Exception as exc:
            log.warning("Could not import module %s: %s", mod_name, exc)
            continue
        mname = getattr(mod, "__module_name__", None)
        htext = getattr(mod, "__help_text__", None)
        if mname and htext:
            entries.append((mname, htext))

    return sorted(entries, key=lambda x: x[0])


def _build_help_text() -> str:
    entries = _discover_help()
    lines = [f"📖 {bold('Command Reference')}\n"]
    for mname, htext in entries:
        lines.append(f"• {bold(esc(mname))}\n{htext}")
    return "\n\n".join(lines) if entries else "No modules loaded."


def _main_menu_kb() -> InlineKeyboardMarkup:
    entries = _discover_help()
    btns = [
        [InlineKeyboardButton(name, callback_data=f"help_module:{name}")]
        for name, _ in entries
    ]
    return InlineKeyboardMarkup(btns)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        _MENU_TEXT, parse_mode="HTML", reply_markup=_main_menu_kb(),
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = ctx.args or []
    if args:
        ## Specific module help
        target = " ".join(args).strip().lower()
        for mname, htext in _discover_help():
            if mname.lower() == target:
                await update.effective_message.reply_text(
                    f"• {bold(esc(mname))}\n{htext}", parse_mode="HTML",
                )
                return
        await update.effective_message.reply_text(f"No module named '{target}' found.")
    else:
        await update.effective_message.reply_text(
            _build_help_text(), parse_mode="HTML", reply_markup=_main_menu_kb(),
        )


async def on_help_module_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query
    await q.answer()
    _, mname = q.data.split(":", 1)

    for name, htext in _discover_help():
        if name == mname:
            await q.edit_message_text(
                f"• {bold(esc(name))}\n\n{htext}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="menu_main"),
                ]]),
            )
            return
    await q.edit_message_text("Module not found.")


async def on_menu_main_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query
    await q.answer()
    await q.edit_message_text(
        _MENU_TEXT, parse_mode="HTML", reply_markup=_main_menu_kb(),
    )


__handlers__ = [
    MessageHandler(build_prefixed_filters("start"), cmd_start),
    MessageHandler(build_prefixed_filters("help"), cmd_help),
    CallbackQueryHandler(on_help_module_callback, pattern=r"^help_module:"),
    CallbackQueryHandler(on_menu_main_callback, pattern=r"^menu_main$"),
]
