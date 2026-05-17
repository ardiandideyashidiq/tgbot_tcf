# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Ban ConversationHandler builder
"""

from __future__ import annotations

from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tcbot import cfg
from tcbot.modules.helper.workflows.proof_conv import (
    WAITING_PROOF,
    on_ban_timeout,
    on_cancel_proof,
    on_proof_received,
)
from tcbot.utils.prefixes import ALL_PREFIXES_CMD_FILTER, build_prefixed_filters


def build_handler(entry_fn) -> ConversationHandler:
    """Build the ban ConversationHandler with the given entry point function."""
    entry = (
        build_prefixed_filters("tcban")
        | build_prefixed_filters("tcb")
    )
    return ConversationHandler(
        entry_points=[MessageHandler(entry, entry_fn)],
        states={
            WAITING_PROOF: [
                CallbackQueryHandler(on_cancel_proof, pattern=r"^cancel_proof$"),
                MessageHandler(filters.PHOTO | filters.VIDEO, on_proof_received),
            ],
        },
        fallbacks=[MessageHandler(ALL_PREFIXES_CMD_FILTER, on_ban_timeout)],
        conversation_timeout=cfg.proof_timeout,
        per_chat=True,
        per_user=True,
        per_message=False,
    )
