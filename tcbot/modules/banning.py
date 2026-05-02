# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Federation ban – proof collection ConversationHandler."""
from __future__ import annotations

from tcbot.modules.helper.workflows.ban_flow import build_handler

__module_name__ = "Ban"
__help_text__ = (
    "<code>/tcban</code> <i>[reply or user_id]</i> – ban a user federation-wide.\n"
    "Reply or provide a user ID, then send proof (photo/video/album) with the reason in the caption.\n"
    "Alias: <code>/fban</code>"
)

__handlers__ = [build_handler()]
