from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.marketplace import get_main_keyboard
from config import ADMIN_IDS
from database.db import db
from handlers.general import check_user_subscription

router = Router()

users_collection = db["users"]
settings_collection = db["settings"]

async def get_bot_status() -> bool:
    setting = await settings_collection.find_one({"key": "maintenance_mode"})
    if setting is None:
        return True 
    return not setting.get("value", False)

@router.message(F.text == "/start")
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    is_admin = user.id in ADMIN_IDS

    is_online = await get_bot_status()
    if not is_online and not is_admin:
        await message.answer(
            "🛠️ **MAINTENANCE MODE**\n\n"
            "The bot is currently undergoing scheduled maintenance or updates. Please check back soon!",
            parse_mode="Markdown"
        )
        return

    await users_collection.update_one(
        {"user_id": user.id},
        {"$set": {"username": user.username, "full_name": user.full_name}},
        upsert=True
    )

    if not is_admin:
        unjoined_channels = await check_user_subscription(user.id, bot)
        
        if unjoined_channels:
            channel_buttons = []
            for ch in unjoined_channels:
                link = ch.get("invite_link") or f"https://t.me/{ch.get('username')}"
                title = ch.get("title", "Required Channel")
                channel_buttons.append([InlineKeyboardButton(text=f"📢 Join {title}", url=link)])
            
            channel_buttons.append([InlineKeyboardButton(text="🔄 Verify Membership", callback_data="check_sub_verify")])
            
            force_sub_markup = InlineKeyboardMarkup(inline_keyboard=channel_buttons)
            
            await message.answer(
                "🔒 **Access Restricted!**\n\n"
                "To use the **Free Fire Account Marketplace**, you must subscribe to our official channels below:\n\n"
                "After joining all channels, tap **Verify Membership** to unlock the bot.",
                reply_markup=force_sub_markup,
                parse_mode="Markdown"
            )
            return

    await message.answer(
        "👋 Welcome to the **Free Fire Account Marketplace**!\n\n"
        "🌟 Use the buttons below to browse available Free Fire accounts.",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "check_sub_verify")
async def verify_subscription_callback(callback: CallbackQuery, bot: Bot):
    """Triggered when the user clicks '🔄 Verify Membership'"""
    # 1. Immediately acknowledge the callback query so it never expires!
    await callback.answer("Checking your membership...")

    # 2. Check if the user has joined all required channels
    unjoined = await check_user_subscription(callback.from_user.id, bot)
    
    if unjoined:
        # If there are still channels they haven't joined, refresh text/buttons or alert them
        channel_buttons = []
        for ch in unjoined:
            link = ch.get("invite_link") or f"https://t.me/{ch.get('username')}"
            title = ch.get("title", "Required Channel")
            channel_buttons.append([InlineKeyboardButton(text=f"📢 Join {title}", url=link)])
        
        channel_buttons.append([InlineKeyboardButton(text="🔄 Verify Membership", callback_data="check_sub_verify")])
        force_sub_markup = InlineKeyboardMarkup(inline_keyboard=channel_buttons)

        try:
            await callback.message.edit_text(
                "🔒 **Access Restricted!**\n\n"
                "❌ You still haven't joined all required channels. Please join them and tap **Verify Membership** again:",
                reply_markup=force_sub_markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass
    else:
        # If they joined everything, grant access and show the main keyboard
        is_admin = callback.from_user.id in ADMIN_IDS
        try:
            await callback.message.delete() # Remove the force-sub message
        except Exception:
            pass
        
        await callback.message.answer(
            "✅ **Verification Successful!**\n\n"
            "Thank you for joining. Welcome to the **Free Fire Account Marketplace**!",
            reply_markup=get_main_keyboard(is_admin),
            parse_mode="Markdown"
        )
