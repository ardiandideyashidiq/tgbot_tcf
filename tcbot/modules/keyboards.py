# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Public inline-keyboard factory functions for the TCF bot."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_menu() -> InlineKeyboardMarkup:
    """Main /start menu – four rows of navigation buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("About",      callback_data="menu_about"),
            InlineKeyboardButton("Help",       callback_data="menu_help"),
        ],
        [
            InlineKeyboardButton("Stats",      callback_data="menu_stats"),
            InlineKeyboardButton("Additional", callback_data="menu_additional"),
        ],
        [
            InlineKeyboardButton("Information", callback_data="menu_information"),
            InlineKeyboardButton("Groups",      callback_data="menu_groups"),
        ],
        [
            InlineKeyboardButton("Privacy", callback_data="menu_privacy"),
        ],
    ])


def back_to_start() -> InlineKeyboardMarkup:
    """Single Back button that returns the user to the start menu."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Back", callback_data="menu_back_start"),
    ]])


def appeal_review(ban_id: str) -> InlineKeyboardMarkup:
    """Approve / Reject row for an appeal review message."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Approve", callback_data=f"appeal_approve_{ban_id}"),
        InlineKeyboardButton("Reject",  callback_data=f"appeal_reject_{ban_id}"),
    ]])


def promotion_request(request_id: str) -> InlineKeyboardMarkup:
    """Approve / Reject row for a promotion request."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Approve", callback_data=f"approve_promote_{request_id}"),
        InlineKeyboardButton("Reject",  callback_data=f"reject_promote_{request_id}"),
    ]])


def ban_log_new(
    target_id: int,
    proof_link: str,
    appeal_url: str,
) -> InlineKeyboardMarkup:
    """Keyboard for a newly created ban-log entry."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Proof {target_id}", url=proof_link)],
        [InlineKeyboardButton("Submit Appeal",       url=appeal_url)],
    ])


def ban_log_update(
    target_id: int,
    proof_link: str,
    previous_proof_link: str,
    appeal_url: str,
) -> InlineKeyboardMarkup:
    """Keyboard for an updated ban-log entry (includes previous-proof button)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"Proof {target_id}",          url=proof_link),
            InlineKeyboardButton(f"Previous Proof {target_id}", url=previous_proof_link),
        ],
        [InlineKeyboardButton("Submit Appeal", url=appeal_url)],
    ])


def help_modules(
    rows: list[list[tuple[str, str]]],
    *,
    with_back_to_start: bool = False,
) -> InlineKeyboardMarkup:
    """Build a help menu keyboard from (text, callback_data) tuples.

    Args:
        rows: Each inner list is a button row; each element is (text, callback_data).
        with_back_to_start: Append a Back button pointing to the start menu.
    """
    kb_rows = [
        [InlineKeyboardButton(text, callback_data=cb) for text, cb in row]
        for row in rows
    ]
    if with_back_to_start:
        kb_rows.append([InlineKeyboardButton("Back", callback_data="menu_back_start")])
    return InlineKeyboardMarkup(kb_rows)
