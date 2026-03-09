"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — File Action KB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def project_actions_kb(project_id: str, is_favorite: bool = False, is_pinned: bool = False) -> InlineKeyboardMarkup:
    """Inline keyboard for a single project card (admin view)."""
    fav_text = "💛 Unfavorite" if is_favorite else "⭐ Favorite"
    pin_text = "📍 Unpin" if is_pinned else "📌 Pin"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬇ Download", callback_data=f"dl:{project_id}"),
                InlineKeyboardButton(text="🔗 Share", callback_data=f"share:{project_id}"),
            ],
            [
                InlineKeyboardButton(text="👁 Preview", callback_data=f"preview:{project_id}"),
                InlineKeyboardButton(text="🧠 AI Summary", callback_data=f"ai:{project_id}"),
            ],
            [
                InlineKeyboardButton(text=fav_text, callback_data=f"fav:{project_id}"),
                InlineKeyboardButton(text=pin_text, callback_data=f"pin:{project_id}"),
            ],
            [
                InlineKeyboardButton(text="✏ Edit", callback_data=f"edit:{project_id}"),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"del:{project_id}"),
            ],
            [
                InlineKeyboardButton(text="◀️ Back", callback_data="my_projects:0"),
            ],
        ]
    )


def confirm_delete_kb(project_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Yes, Delete", callback_data=f"confirm_del:{project_id}"),
                InlineKeyboardButton(text="❌ Cancel", callback_data=f"project:{project_id}"),
            ],
        ]
    )


def public_project_kb(project_id: str) -> InlineKeyboardMarkup:
    """Keyboard shown to public users for shared projects."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬇ Download File", callback_data=f"pub_dl:{project_id}")],
            [InlineKeyboardButton(text="👁 Preview Code", callback_data=f"pub_preview:{project_id}")],
            [InlineKeyboardButton(text="🧠 AI Summary", callback_data=f"pub_ai:{project_id}")],
        ]
    )
