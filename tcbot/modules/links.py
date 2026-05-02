# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Post TCF community links to the current chat."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler

from tcbot.config import cfg
from tcbot.modules.helper import decorators
from tcbot.modules.helper.formatter import bold, link
from tcbot.utils.prefixes import build_prefixed_filters

__module_name__ = "Links"
__help_text__ = (
    "<code>/tclinks</code> – post community links (staff only)."
)


@decorators.staff_only
async def cmd_tclinks(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    main_group_link = f"https://t.me/c/{str(cfg.main_group).replace('-100', '')}"
    channel_link = f"https://t.me/c/{str(cfg.main_channel).replace('-100', '')}"

    text = (
        f"🔗 {bold(cfg.community_name)} Links\n\n"
        f"• {link('Main Group', main_group_link)}\n"
        f"• {link('Announcement Channel', channel_link)}"
    )
    await update.effective_message.reply_text(text, parse_mode="HTML")


__handlers__ = [
    MessageHandler(build_prefixed_filters("tclinks"), cmd_tclinks),
]
