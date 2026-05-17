# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

from __future__ import annotations

from tcbot.modules.helper.workflows.unban_conv import build_handler

__module_name__ = "Unban"
__help_text__ = (
    "<b>Commands & Aliases</b>\n"
    "<code>/tcunban</code> (alias: <code>/tcunb</code>)\n\n"

    "<b>Who can use it</b>\n"
    "Developer and above (Founder / Admin / Developer).\n\n"

    "<b>Where to use it</b>\n"
    "Exec group, any connected group, or bot PM.\n\n"

    "<b>What it does</b>\n"
    "Lifts an active federation ban on the target user. The unban is applied across "
    "<b>all connected groups</b> simultaneously - the user's Telegram ban is removed in "
    "every group so they can rejoin freely. A log entry is posted to the federation logs channel.\n\n"
    "If the user has no active federation ban, the bot will let you know and take no action.\n"
    "If the target's ban was under appeal, the appeal is also resolved as approved.\n\n"

    "<b>How to specify the target</b>\n"
    "Reply to a message, or provide a user ID / @username after the command.\n\n"

    "<b>Examples</b>\n"
    "<code>/tcunban @username</code>\n"
    "<code>/tcunb 123456789</code>\n"
    "Or reply to a message and run <code>/tcunb</code>."
)

__handlers__ = [build_handler()]
