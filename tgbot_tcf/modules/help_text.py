# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Help system catalogue.

The interactive help menu and the ``/help`` command both render the same
content. Defining the catalogue once here keeps button labels, callback
identifiers, and the longer detail text in lock-step.

The detail text is intentionally verbose: it tells users which command
aliases are available, who may use them, where they may be used, and any
behavioural notes (for example the proof-collection step for ``/tcban``).
The wording is taken verbatim from PROMPT Feature 31 so the contract with
the federation tooling stays intact.
"""
from __future__ import annotations

from typing import Final


HELP_MODULE_ROWS: Final[list[list[tuple[str, str]]]] = [
    [("Ban", "help_ban"), ("Unban", "help_unban")],
    [("Check Ban", "help_check"), ("Ban Info", "help_baninfo")],
    [("Promote/Demote", "help_admin"), ("Transfer Owner", "help_transfer")],
    [("Broadcast", "help_broadcast"), ("Group Connected", "help_connected")],
    [("Disaffiliate", "help_defed"), ("Appeal", "help_appeal")],
    [("Join/Leave", "help_join"), ("Statistics", "help_stats")],
    [("Cleanup", "help_cleanup")],
]


HELP_DETAILS: Final[dict[str, str]] = {
    "help_ban": (
        "<b>Here Help for Ban</b>\n\n"
        "Commands: /tcban, /ban, /tcfban\n"
        "Usage: /tcban &lt;target&gt; &lt;reason&gt;\n\n"
        "Who can use? Transsion Core Owner and Admins.\n"
        "Where? Any affiliated group, the main forum, exec group, or PM.\n"
        "Example: /tcban @johndoe spam | /tcban 123456789 spam\n\n"
        "<b>NOTE</b>:\n"
        " - A reason and proof is required. After issuing the command, you'll be asked to upload photo/video evidence.\n"
        " - &lt;target&gt; can be reply, user ID, or @username.\n"
        " - U just upload a images or videos as proof (reply message bot is not required)."
    ),
    "help_unban": (
        "<b>Here Help for Unban</b>\n\n"
        "Commands: /tcunban, /unban, /tcfunban\n"
        "Usage: /tcunban &lt;target&gt; [optional reason]\n\n"
        "Who can use? Transsion Core Owner and Admins.\n"
        "Where? Any affiliated group, main forum, exec group, or PM.\n"
        "Example: /tcunban @johndoe mistake\n\n"
        "<b>NOTE</b>:\n"
        " - If an appeal was pending for this user, it will be automatically closed upon unban."
    ),
    "help_check": (
        "<b>Here Help for Check Ban</b>\n\n"
        "Commands: /checkme, /myban, /amibanned\n"
        "Usage: /checkme\n\n"
        "Who can use? Everyone.\n"
        "Where? Anywhere (Groups or PM).\n\n"
        "<b>NOTE</b>:\n"
        " - If you are banned, the bot will display your ban details and provide a button to start an appeal."
    ),
    "help_baninfo": (
        "<b>Here Help for Ban Info</b>\n\n"
        "Commands: /baninfo, /checkban, /banstatus\n"
        "Usage: /baninfo &lt;target&gt;\n\n"
        "Who can use? Everyone.\n"
        "Where? Anywhere (Groups or PM).\n"
        "Example: /baninfo @johndoe\n\n"
        "<b>NOTE</b>:\n"
        " - This command shows the detailed global ban status of a specific user."
    ),
    "help_admin": (
        "<b>Here Help for Promote/Demote</b>\n\n"
        "Commands: /tcpromote, /promote | /tcdemote, /demote\n"
        "Usage: /tcpromote &lt;target&gt; | /tcdemote &lt;target&gt;\n\n"
        "Who can use? Owner (Immediate) or Admins (Creates Request).\n"
        "Where? Main forum, exec group, or PM.\n\n"
        "<b>NOTE</b>:\n"
        " - Only the Transsion Core Owner can perform a direct demote.\n"
        " - Self-demotion will trigger a special notification regarding your administrative status."
    ),
    "help_transfer": (
        "<b>Here Help for Transfer Owner</b>\n\n"
        "Commands: /tctransfer, /transfer, /tcowner\n"
        "Usage: /tctransfer &lt;target&gt;\n\n"
        "Who can use? Transsion Core Owner only.\n"
        "Where? Private Message (PM) recommended for security.\n\n"
        "<b>NOTE</b>:\n"
        " - This action is permanent. The current owner will be downgraded to a regular admin after the transfer."
    ),
    "help_broadcast": (
        "<b>Here Help for Broadcast</b>\n\n"
        "Commands: /tcbroadcast, /broadcast, /tcannounce\n"
        "Usage: /tcbroadcast &lt;message&gt;\n\n"
        "Who can use? Transsion Core Owner and Admins.\n"
        "Where? PM or Exec Group.\n\n"
        "<b>NOTE</b>:\n"
        " - The message will be sent to all affiliated groups within the Transsion Core network."
    ),
    "help_connected": (
        "<b>Here Help for Group Connected</b>\n\n"
        "Commands: /jointc, /requestjoin, /applytc\n"
        "Usage: /jointc (inside the group)\n\n"
        "Who can use? Group Owner.\n"
        "Where? The group you wish to affiliate.\n\n"
        "<b>NOTE</b>:\n"
        " - When the bot is added to a new group, it will automatically prompt the owner to join the federation."
    ),
    "help_defed": (
        "<b>Here Help for Disaffiliate</b>\n\n"
        "Commands: /detc, /leavetc, /rmtc &lt;group_id&gt;\n"
        "Usage: /detc (in-group) or /rmtc -100xxx (by ID)\n\n"
        "Who can use? Group Owner, TC Owner, or TC Admins.\n"
        "Where? Target group or PM (for ID removal).\n\n"
        "<b>NOTE</b>:\n"
        " - /rmtc using group ID is strictly for TC Owner/Admins only."
    ),
    "help_appeal": (
        "<b>Here Help for Appeal</b>\n\n"
        "Commands: /start appeal_&lt;ban_id&gt;\n"
        "Usage: Click 'Submit Appeal' on the log or use the start command.\n\n"
        "Who can use? Banned Users.\n"
        "Where? Bot PM.\n\n"
        "<b>NOTE</b>:\n"
        " - You must reply with #appeal including: Log Link, Clarification, and Agreement.\n"
        " - Reviewers have a 12-hour window for the banning admin before other admins can decide."
    ),
    "help_join": (
        "<b>Here Help for Join/Leave</b>\n\n"
        "Commands: /jointc, /leavetc\n"
        "Usage: /jointc (to join) | /leavetc (to leave)\n\n"
        "Who can use? Group Owner or TC Admins (for leaving).\n"
        "Where? Inside the group.\n\n"
        "<b>NOTE</b>:\n"
        " - Joining requires the group to meet Transsion Core federation standards."
    ),
    "help_stats": (
        "<b>Here Help for Statistics</b>\n\n"
        "Commands: /tcstats, /stats, /tcinfo\n"
        "Usage: /tcstats\n\n"
        "Who can use? Everyone.\n"
        "Where? Anywhere.\n\n"
        "<b>NOTE</b>:\n"
        " - Shows real-time data: Owner, Admin counts, total groups, and active global bans."
    ),
    "help_cleanup": (
        "<b>Here Help for Cleanup</b>\n\n"
        "Commands: /cleanup, /purge, /tcclean\n"
        "Usage: /cleanup\n\n"
        "Who can use? Transsion Core Owner and Admins.\n"
        "Where? Exec group or PM.\n\n"
        "<b>NOTE</b>:\n"
        " - This scans the database and removes groups where the bot is no longer an administrator or has been kicked."
    ),
}
