"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Status Buttons
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def status_selection_kb() -> InlineKeyboardMarkup:
    """Status picker during upload flow."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Complete", callback_data="status:complete"),
                InlineKeyboardButton(text="⚠️ Incomplete", callback_data="status:incomplete"),
            ],
            [
                InlineKeyboardButton(text="🧪 Experimental", callback_data="status:experimental"),
                InlineKeyboardButton(text="🚧 Work in Progress", callback_data="status:wip"),
            ],
        ]
    )


def confirm_upload_kb() -> InlineKeyboardMarkup:
    """Confirm / cancel after metadata review."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Save Project", callback_data="upload_confirm"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="upload_cancel"),
            ],
        ]
    )
