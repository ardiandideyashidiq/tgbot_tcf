# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Inline keyboard builders used across modules."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_ban_kb(ban_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm", callback_data=f"ban_confirm:{ban_id}"),
        InlineKeyboardButton("✏️ Edit", callback_data=f"ban_edit:{ban_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"ban_cancel:{ban_id}"),
    ]])


def appeal_review_kb(ban_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Accept", callback_data=f"appeal_accept:{ban_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"appeal_reject:{ban_id}"),
    ]])


def appeal_confirm_kb(ban_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📨 Submit Appeal", callback_data=f"appeal_submit:{ban_id}"),
        InlineKeyboardButton("✏️ Edit", callback_data=f"appeal_edit:{ban_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"appeal_cancel:{ban_id}"),
    ]])


def promo_decision_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"promo_accept:{user_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"promo_reject:{user_id}"),
    ]])


def join_decision_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Accept", callback_data=f"join_accept:{chat_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"join_reject:{chat_id}"),
    ]])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("« Back", callback_data="menu_main"),
    ]])
