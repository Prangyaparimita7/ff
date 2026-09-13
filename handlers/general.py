from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.marketplace import get_main_keyboard
from database.db import orders_collection, listings_collection, db
from config import ADMIN_IDS

router = Router()

# Define the channels collection reference
channels_collection = db["forced_channels"]

@router.message(F.text == "ℹ️ Help")
async def help_command(message: Message):
    help_text = (
        "ℹ️ **FREE FIRE MARKETPLACE HELP**\n\n"
        "Welcome to the safest peer-to-peer Free Fire account trading bot.\n\n"
        "• **🛒 Browse Accounts:** Explore active listings verified by our admins.\n"
        "• **📦 My Orders:** Track ongoing purchases and requests.\n"
        "• **👤 My Profile:** View your active submissions and account status.\n\n"
        "Need assistance? Support handle: `@Kunalssingh69`"
    )
    await message.answer(help_text, parse_mode="Markdown")

@router.message(F.text == "🛡️ Escrow Group")
async def escrow_group_command(message: Message):
    escrow_text = (
        "ʏᴏᴜʀ sᴀғᴇ ᴘʟᴀᴄᴇ ғᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ᴛʀᴀᴅᴇs. ᴡᴇ ᴘʀᴏᴛᴇᴄᴛ ʙᴏᴛʜ ʙᴜʏᴇʀs ᴀɴᴅ sᴇʟʟᴇʀs "
        "ᴛᴏ ᴇɴsᴜʀᴇ ᴇᴠᴇʀʏ ᴅᴇᴀʟ ɪs 100% sᴀғᴇ.\n\n"
        "Link:- https://t.me/+QiODdLlfpkQ0Mjk1"
    )
    await message.answer(escrow_text)

@router.message(F.text == "📦 My Orders")
async def my_orders_command(message: Message):
    user_id = message.from_user.id
    user_orders = await orders_collection.find({"buyer_id": user_id}).to_list(length=10)

    if not user_orders:
        await message.answer(
            "📦 **MY ORDERS**\n\n"
            "You have no active or past orders yet.\n"
            "Browse our marketplace to find verified Free Fire accounts!",
            parse_mode="Markdown"
        )
        return

    orders_text = "📦 **YOUR ORDERS**\n\n"
    for order in user_orders:
        orders_text += f"• ID: `{order.get('listing_id')}` | Status: **{order.get('status', 'Pending')}**\n"

    await message.answer(orders_text, parse_mode="Markdown")

@router.message(F.text == "👤 My Profile")
async def my_profile_command(message: Message):
    user = message.from_user
    is_admin = user.id in ADMIN_IDS
    listings_count = await listings_collection.count_documents({"seller_id": user.id})

    profile_text = (
        f"👤 **USER PROFILE**\n\n"
        f"• **Name:** {user.full_name}\n"
        f"• **Username:** @{user.username if user.username else 'None'}\n"
        f"• **Telegram ID:** `{user.id}`\n"
        f"• **Role:** {'👑 Admin' if is_admin else '🛒 Buyer'}\n"
        f"• **Active Listings Managed:** {listings_count}\n"
    )
    
    await message.answer(profile_text, parse_mode="Markdown")

@router.callback_query(F.data == "home")
async def return_home(callback: CallbackQuery):
    is_admin = callback.from_user.id in ADMIN_IDS
    welcome_text = (
        "🎮 **FREE FIRE ACCOUNT MARKET**\n\n"
        "Welcome back to the marketplace main menu."
    )
    
    await callback.message.answer(welcome_text, reply_markup=get_main_keyboard(is_admin), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "browse_back")
async def back_to_browse_fallback(callback: CallbackQuery):
    from handlers.marketplace_mongo import browse_marketplace
    await browse_marketplace(callback.message)
    await callback.answer()


# ==========================================
# FORCE SUBSCRIBE VERIFICATION LOGIC
# ==========================================

async def check_user_subscription(user_id: int, bot: Bot) -> list:
    """Returns a list of channels the user has NOT joined yet."""
    channels = await channels_collection.find().sort("position", 1).to_list(length=20)
    unjoined = []
    
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["channel_id"], user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                unjoined.append(ch)
        except Exception:
            # If bot can't check or user not found in channel, count as unjoined
            unjoined.append(ch)
            
    return unjoined

@router.callback_query(F.data == "check_sub_verify")
async def verify_subscription_callback(callback: CallbackQuery, bot: Bot):
    """Triggered when the user clicks '🔄 Verify Membership'"""
    # 1. Check if the user has joined all required channels
    unjoined = await check_user_subscription(callback.from_user.id, bot)
    
    if unjoined:
        # If there are still channels they haven't joined, alert them
        await callback.answer("❌ You haven't joined all required channels yet!", show_alert=True)
    else:
        # If they joined everything, grant access and show the main keyboard
        is_admin = callback.from_user.id in ADMIN_IDS
        await callback.message.delete() # Remove the force-sub message
        
        await callback.message.answer(
            "✅ **Verification Successful!**\n\n"
            "Thank you for joining. Welcome to the **Free Fire Account Marketplace**!",
            reply_markup=get_main_keyboard(is_admin),
            parse_mode="Markdown"
        )
        await callback.answer()
