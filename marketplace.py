from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False):
    # Base layout for regular users including the Escrow Group button
    keyboard = [
        [KeyboardButton(text="🛒 Browse Accounts", style="danger"), KeyboardButton(text="📦 My Orders", style="success")],
        [KeyboardButton(text="🛡️ Escrow Group", style="primary"), KeyboardButton(text="👤 My Profile", style="danger")],
        [KeyboardButton(text="ℹ️ Help", style="success")]
    ]
    
    # Add Sell Account and Admin Panel side-by-side at the bottom strictly for admins
    if is_admin:
        keyboard.append([KeyboardButton(text="➕ Sell Account", style="primary"), KeyboardButton(text="⚙️ Admin Panel", style="danger")])
        
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)