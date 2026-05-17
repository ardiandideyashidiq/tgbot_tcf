# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

from __future__ import annotations

import asyncio
import importlib
import logging

from telegram import CallbackQuery, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler

from tcbot import cfg
from tcbot.modules import ALL_MODULES
from tcbot.modules.helper import keyboards
from tcbot.utils.prefixes import build_prefixed_filters

log = logging.getLogger(__name__)


## ── Build help content ─────────────────────────────────────────────────────

def _build_help_content() -> dict[str, tuple[str, str]]:
    """
    Iterate over ALL_MODULES and collect modules that expose both
    __module_name__ (not None) and __help_text__.
    Key format: "help_<mod_filename>"  e.g. "help_banning", "help_admins"
    """
    content: dict[str, tuple[str, str]] = {}
    for mod_name in ALL_MODULES:
        try:
            mod = importlib.import_module(f"tcbot.modules.{mod_name}")
            name = getattr(mod, "__module_name__", None)
            text = getattr(mod, "__help_text__", None)
            if name and text:
                content[f"help_{mod_name}"] = (name, text)
        except Exception as exc:
            log.warning("Could not read help from %s: %s", mod_name, exc)
    return content


HELP_CONTENT = _build_help_content()

## Sorted automatically by display name
_TOPICS_SORTED: list[tuple[str, str]] = sorted(
    ((name, key) for key, (name, _) in HELP_CONTENT.items()),
    key=lambda t: t[0].lower(),
)

## Menu-path topics - callback keys stay as "help_<mod>"
HELP_TOPICS_MENU: list[tuple[str, str]] = _TOPICS_SORTED

## Command-path topics - callback keys become "helpc_<mod>"
HELP_TOPICS_CMD: list[tuple[str, str]] = [
    (name, "helpc_" + key[5:]) for name, key in _TOPICS_SORTED
]


## ── Prefix note ────────────────────────────────────────────────────────────

def _prefix_note() -> str:
    """Return an HTML footer listing every configured command prefix."""
    codes = " ".join(f"<code>{p}</code>" for p in cfg.prefixes)
    return f"\n<b>INFO!! Prefixes:</b> All commands also work with {codes}"


## ── Shared text ────────────────────────────────────────────────────────────

_HELP_INDEX_TEXT = (
    "<b>{botname} Help</b>\n\n"
    f"I manages groups connected on {cfg.community_name}. "
    "Select a topic below."
)


## ── Shared rendering helper ────────────────────────────────────────────────

async def _render_help_index(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    *,
    with_back_to_start: bool,
) -> None:
    """
    Edit (or send) the help index message on the appropriate callback query.
    """
    q: CallbackQuery = update.callback_query
    botname = ctx.bot.first_name
    kb = keyboards.help_topics_menu_kb(HELP_TOPICS_MENU) if with_back_to_start else keyboards.help_topics_kb(HELP_TOPICS_CMD)
    await asyncio.gather(
        q.answer(),
        q.edit_message_text(
            _HELP_INDEX_TEXT.format(botname=botname),
            parse_mode="HTML",
            reply_markup=kb,
        ),
    )


## ── /help command ──────────────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    botname = ctx.bot.first_name
    await update.effective_message.reply_text(
        _HELP_INDEX_TEXT.format(botname=botname),
        parse_mode="HTML",
        reply_markup=keyboards.help_topics_kb(HELP_TOPICS_CMD),
    )


## ── Help from menu ─────────────────────────────────────────────────────────

async def on_help_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_help_index(update, ctx, with_back_to_start=True)


## ── Help in group ──────────────────────────────────────────────────────────

async def on_help_menu_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Help tapped from group /start inline - answer with alert, no edit.
    """
    q: CallbackQuery = update.callback_query
    await q.answer(
        "Use /help in this group to browse all commands.",
        show_alert=True,
    )


## ── Help index callback ────────────────────────────────────────────────────

async def on_helpc_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_help_index(update, ctx, with_back_to_start=False)


## ── Shared topic renderer ──────────────────────────────────────────────────

async def _show_topic(q: CallbackQuery, menu_key: str, back_kb) -> None:
    """Render a help topic and edit the current message in place."""
    if menu_key not in HELP_CONTENT:
        await asyncio.gather(
            q.answer(),
            q.edit_message_text("Topic not found.", reply_markup=back_kb),
        )
        return
    name, text = HELP_CONTENT[menu_key]
    await asyncio.gather(
        q.answer(),
        q.edit_message_text(
            f"<b>Help for {name}</b>\n\n{text}\n{_prefix_note()}",
            parse_mode="HTML",
            reply_markup=back_kb,
        ),
    )


## ── Help topic - menu path ─────────────────────────────────────────────────

async def on_help_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query
    await _show_topic(q, q.data, keyboards.back_to_help_kb())


## ── Help topic - command path ──────────────────────────────────────────────

async def on_help_topic_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query
    ## "helpc_banning" → "help_banning"
    await _show_topic(q, "help_" + q.data[6:], keyboards.back_to_help_cmd_kb())


## ── Handler list ───────────────────────────────────────────────────────────

_HELP_FILTER = build_prefixed_filters("help") | build_prefixed_filters("commands")

__handlers__ = [
    MessageHandler(_HELP_FILTER, cmd_help),
    CallbackQueryHandler(on_help_menu,        pattern=r"^help_menu$"),
    CallbackQueryHandler(on_help_menu_group,  pattern=r"^help_menu_group$"),
    CallbackQueryHandler(on_helpc_main,      pattern=r"^helpc_main$"),
    CallbackQueryHandler(on_help_topic,       pattern=r"^help_\w+$"),
    CallbackQueryHandler(on_help_topic_cmd,   pattern=r"^helpc_\w+$"),
]
