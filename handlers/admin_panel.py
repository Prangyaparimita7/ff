from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import listings_collection, db
from config import ADMIN_IDS

router = Router()
settings_collection = db["settings"]
users_collection = db["users"]

class BroadcastStates(StatesGroup):
    waiting_for_broadcast = State()

async def get_bot_status() -> bool:
    """Returns True if bot is ON, False if OFF (Maintenance)"""
    setting = await settings_collection.find_one({"key": "maintenance_mode"})
    if setting is None:
        return True  # Default is ON
    return not setting.get("value", False)

@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ You are not authorized to access the Admin Panel.")
        return

    is_on = await get_bot_status()
    
    # Configure the toggle button look based on current status
    if is_on:
        toggle_label = "Bot Status: ON"
        toggle_style = "success"  # Green background
    else:
        toggle_label = "Bot Status: OFF"
        toggle_style = "danger"   # Red background

    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Manage / Delete accounts", callback_data="admin_manage_listings", style="primary")],
        [InlineKeyboardButton(text="📢 Manage Channels Panel", callback_data="admin_manage_channels", style="primary")],
        [InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_broadcast_start", style="success")],
        [InlineKeyboardButton(text=toggle_label, callback_data="admin_toggle_bot", style="danger")],
        [InlineKeyboardButton(text="📊 Marketplace Statistics", callback_data="admin_stats", style="primary")]
    ])

    await message.answer(
        "⚙️ **ADMIN CONTROL PANEL**\n\n"
        "Select an administrative action below:",
        reply_markup=admin_keyboard,
        parse_mode="Markdown"
    )

# --- BOT ON/OFF TOGGLE LOGIC ---
@router.callback_query(F.data == "admin_toggle_bot")
async def toggle_bot_status(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    current_status = await get_bot_status()
    new_maintenance_state = current_status  # Flips the state

    await settings_collection.update_one(
        {"key": "maintenance_mode"},
        {"$set": {"value": new_maintenance_state}},
        upsert=True
    )

    status_word = "OFFLINE" if new_maintenance_state else "ONLINE"
    await callback.answer(f"⚠️ Bot status changed to {status_word}!", show_alert=True)
    
    # Instantly refresh the admin panel message so the button color and text flip immediately
    is_on = await get_bot_status()
    if is_on:
        toggle_label = "Bot Status: ON"
        toggle_style = "success"
    else:
        toggle_label = "Bot Status: OFF"
        toggle_style = "danger"

    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Manage / Delete accounts", callback_data="admin_manage_listings", style="primary")],
        [InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_broadcast_start", style="primary")],
        [InlineKeyboardButton(text=toggle_label, callback_data="admin_toggle_bot", style=toggle_style)],
        [InlineKeyboardButton(text="📢 Manage Channels Panel", callback_data="admin_manage_channels", style="primary")],
        [InlineKeyboardButton(text="📊 Marketplace Statistics", callback_data="admin_stats", style="primary")]
    ])

    await callback.message.edit_reply_markup(reply_markup=admin_keyboard)


# --- BROADCAST LOGIC ---
@router.callback_query(F.data == "admin_broadcast_start")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    await state.set_state(BroadcastStates.waiting_for_broadcast)
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Cancel Broadcast", callback_data="back_to_admin", style="danger")]
    ])

    await callback.message.edit_text(
        "📢 **BROADCAST SYSTEM**\n\n"
        "Send the message (Text, Photo, Video, or Document) you want to broadcast to all registered users.",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(BroadcastStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.clear()
    
    users = await users_collection.find({}, {"user_id": 1}).to_list(length=100000)
    
    if not users:
        await message.answer("❌ No registered users found in the database to broadcast to.")
        return

    progress_msg = await message.answer("⏳ Broadcasting message... Please wait.")
    
    success_count = 0
    fail_count = 0

    for user in users:
        uid = user.get("user_id")
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            success_count += 1
        except Exception:
            fail_count += 1

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="back_to_admin", style="primary")]
    ])

    await progress_msg.edit_text(
        f"📢 **BROADCAST COMPLETED**\n\n"
        f"• **Successfully Sent:** {success_count}\n"
        f"• **Failed / Blocked:** {fail_count}",
        reply_markup=back_kb,
        parse_mode="Markdown"
    )


# --- EXISTING ADMIN PANELS (Manage Listings & Stats) ---
@router.callback_query(F.data == "admin_manage_listings")
async def admin_manage_listings(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized access.", show_alert=True)
        return

    listings = await listings_collection.find({"status": "AVAILABLE"}).to_list(length=20)

    if not listings:
        await callback.message.edit_text(
            "📋 **MANAGE LISTINGS**\n\nThere are currently no active listings to manage.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="back_to_admin", style="primary")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    keyboard_buttons = []
    for item in listings:
        listing_id = item["listing_id"]
        acc_type = item["account_type"]
        price = item["price"]
        
        button_text = f"Delete ID: {listing_id} ({acc_type} - ₹{price})"
        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"admin_del_{listing_id}", style="danger")])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="back_to_admin", style="primary")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(
        "📋 **MANAGE & DELETE LISTINGS**\n\n"
        "Tap any item below to instantly remove it:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_del_"))
async def admin_delete_listing(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    listing_id = callback.data.split("_")[2]
    result = await listings_collection.delete_one({"listing_id": listing_id})

    if result.deleted_count > 0:
        await callback.answer(f"✅ Listing {listing_id} deleted successfully!", show_alert=True)
    else:
        await callback.answer("❌ Listing not found or already deleted.", show_alert=True)

    await admin_manage_listings(callback)

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized access.", show_alert=True)
        return

    total_listings = await listings_collection.count_documents({})
    active_listings = await listings_collection.count_documents({"status": "AVAILABLE"})
    total_users = await users_collection.count_documents({})

    stats_text = (
        f"📊 **MARKETPLACE STATISTICS**\n\n"
        f"• **Total Registered Users:** {total_users}\n"
        f"• **Total Listings Created:** {total_listings}\n"
        f"• **Active Available Listings:** {active_listings}\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="back_to_admin", style="primary")]
    ])

    await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(callback: CallbackQuery):
    await admin_panel_command(callback.message)
    await callback.answer()
