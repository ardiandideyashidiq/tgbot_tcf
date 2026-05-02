# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Appeal system – DM conversation and admin decision callbacks."""
from __future__ import annotations

from telegram.ext import CallbackQueryHandler

from tcbot.modules.helper.workflows.appeal_flow import build_handler, on_appeal_decision

__module_name__ = "Appeal"
__help_text__ = (
    "<code>/appeal</code> – submit a federation ban appeal (DM only).\n"
    "Staff can accept or reject via inline buttons in the appeals topic."
)

__handlers__ = [
    build_handler(),
    CallbackQueryHandler(on_appeal_decision, pattern=r"^(appeal_accept|appeal_reject):"),
]
