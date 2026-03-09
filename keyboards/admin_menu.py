"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Admin Menu KB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_dashboard_kb() -> InlineKeyboardMarkup:
    """Main admin dashboard keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Upload Project", callback_data="upload_start"),
                InlineKeyboardButton(text="📂 My Projects", callback_data="my_projects:0"),
            ],
            [
                InlineKeyboardButton(text="🔎 Smart Search", callback_data="search_start"),
                InlineKeyboardButton(text="📊 Statistics", callback_data="stats"),
            ],
            [
                InlineKeyboardButton(text="⭐ Favorites", callback_data="favorites:0"),
                InlineKeyboardButton(text="📌 Pinned Projects", callback_data="pinned:0"),
            ],
            [
                InlineKeyboardButton(text="🔗 Shared Links", callback_data="shared_links:0"),
                InlineKeyboardButton(text="📋 Activity Log", callback_data="activity_log"),
            ],
            [
                InlineKeyboardButton(text="🌐 Import from GitHub", callback_data="github_import"),
            ],
        ]
    )


def back_to_dashboard_kb() -> InlineKeyboardMarkup:
    """Single 'Back' button to return to dashboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="dashboard")],
        ]
    )
