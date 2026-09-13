from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import db
from config import ADMIN_IDS

router = Router()
channels_collection = db["forced_channels"]

class AddChannelStates(StatesGroup):
    waiting_for_channel = State()

@router.callback_query(F.data == "admin_manage_channels")
async def open_manage_channels(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    channels = await channels_collection.find().sort("position", 1).to_list(length=50)
    
    keyboard_rows = []
    
    # Render channel buttons with appropriate styles
    for ch in channels:
        ch_title = ch.get("title", "Channel")
        ch_id = ch.get("channel_id")
        display_name = f"@{ch.get('username')}" if ch.get('username') else f"📢 {ch_title[:10]}"
        
        keyboard_rows.append([
            InlineKeyboardButton(text=display_name, callback_data=f"ch_info_{ch_id}", style="primary"),
            InlineKeyboardButton(text="🗑️", callback_data=f"ch_del_{ch_id}", style="danger"),
            InlineKeyboardButton(text="⬆️", callback_data=f"ch_up_{ch_id}", style="primary"),
            InlineKeyboardButton(text="⬇️", callback_data=f"ch_down_{ch_id}", style="primary")
        ])

    keyboard_rows.append([InlineKeyboardButton(text="➕ Add Checked Channel", callback_data="admin_add_channel", style="success")])
    keyboard_rows.append([InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="back_to_admin", style="primary")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    text = (
        "📋 **Manage Channels Panel**\n\n"
        "✅ **Checked Channels** (Active Force-Sub)\n\n"
        "🔎 Click to view info, 🔼 or 🔽 to reorder, ❌ to delete.\n"
        "🟢 Click on a Checked Channel to set an Invite Link."
    )
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_add_channel")
async def prompt_add_channel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    await state.set_state(AddChannelStates.waiting_for_channel)
    
    text = (
        "➕ **Add Checked Channel**\n\n"
        "🔎 Please send the new channel you want to add.\n"
        "You can do this in 3 simple ways:\n\n"
        "1️⃣ Forward a message from the channel.\n"
        "2️⃣ Send the Channel Username (with @).\n"
        "3️⃣ Send the Channel Chat ID (e.g., -100...). \n\n"
        "⚠️ **Note:** Make sure the bot is already an Admin in the channel before adding it!"
    )
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="admin_manage_channels", style="danger")]
    ])
    
    await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="Markdown")
    await callback.answer()

@router.message(AddChannelStates.waiting_for_channel)
async def process_new_channel(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return

    target_chat = None

    # Method 1: Forwarded message from channel
    if message.forward_from_chat:
        target_chat = message.forward_from_chat
    else:
        text = message.text.strip()
        try:
            # Method 2 or 3: Username or Chat ID
            if text.startswith("@") or text.startswith("-100") or text.isdigit() or text.startswith("-"):
                target_chat = await bot.get_chat(text)
            else:
                await message.answer("❌ Invalid format. Please send a valid Username (`@channel`), Chat ID (`-100...`), or forward a post.")
                return
        except Exception as e:
            await message.answer(
                f"❌ **Could not find or access channel!**\n\n"
                f"Error: `{str(e)}`\n\n"
                f"Make sure the bot is added as an **Administrator** in the channel and try again.",
                parse_mode="Markdown"
            )
            return

    # Check if bot is admin in the target channel
    try:
        bot_member = await bot.get_chat_member(chat_id=target_chat.id, user_id=bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            raise ValueError("Bot is not an admin")
    except Exception:
        await message.answer(
            f"❌ **Action Failed!**\n\n"
            f"🎉 Bot is **NOT** Admin in `{target_chat.title or target_chat.username}`.\n\n"
            f"Please promote the bot to an **Administrator** inside the channel first, then try adding it again.",
            parse_mode="Markdown"
        )
        return

    # Automatically grab invite link if available, else generate/fallback
    invite_link = target_chat.invite_link
    if not invite_link:
        try:
            invite_link = await bot.export_chat_invite_link(target_chat.id)
        except Exception:
            invite_link = f"https://t.me/{target_chat.username}" if target_chat.username else ""

    # Save to database
    count = await channels_collection.count_documents({})
    channel_data = {
        "channel_id": target_chat.id,
        "title": target_chat.title or "Channel",
        "username": target_chat.username,
        "invite_link": invite_link,
        "position": count + 1
    }

    # Upsert to prevent duplicates
    await channels_collection.update_one(
        {"channel_id": target_chat.id},
        {"$set": channel_data},
        upsert=True
    )

    await state.clear()

    success_text = (
        f"🎉 **Bot is Admin in {target_chat.title}**\n\n"
        f"📋 **ID:** `{target_chat.id}`\n"
        f"🔗 **Invite link grabbed automatically!**\n\n"
        f"Channel has been successfully added to force-subscription checks."
    )
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Channels Panel", callback_data="admin_manage_channels", style="primary")]
    ])
    
    await message.answer(success_text, reply_markup=back_kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("ch_del_"))
async def delete_channel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    ch_id = int(callback.data.split("_")[2])
    await channels_collection.delete_one({"channel_id": ch_id})
    await callback.answer("✅ Channel removed successfully!", show_alert=True)
    
    # Refresh panel
    await open_manage_channels(callback)

@router.callback_query(F.data.startswith("ch_up_"))
async def move_channel_up(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    ch_id = int(callback.data.split("_")[2])
    current = await channels_collection.find_one({"channel_id": ch_id})
    if current and current["position"] > 1:
        prev = await channels_collection.find_one({"position": current["position"] - 1})
        if prev:
            await channels_collection.update_one({"_id": current["_id"]}, {"$set": {"position": current["position"] - 1}})
            await channels_collection.update_one({"_id": prev["_id"]}, {"$set": {"position": prev["position"] + 1}})
            
    await open_manage_channels(callback)

@router.callback_query(F.data.startswith("ch_down_"))
async def move_channel_down(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Unauthorized.", show_alert=True)
        return

    ch_id = int(callback.data.split("_")[2])
    current = await channels_collection.find_one({"channel_id": ch_id})
    if current:
        nxt = await channels_collection.find_one({"position": current["position"] + 1})
        if nxt:
            await channels_collection.update_one({"_id": current["_id"]}, {"$set": {"position": current["position"] + 1}})
            await channels_collection.update_one({"_id": nxt["_id"]}, {"$set": {"position": current["position"]}})
            
    await open_manage_channels(callback)