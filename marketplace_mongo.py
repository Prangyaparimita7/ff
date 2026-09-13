from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from database.db import listings_collection

router = Router()

@router.message(F.text == "🛒 Browse Accounts")
async def browse_marketplace(message: Message):
    available_listings = await listings_collection.find({"status": "AVAILABLE"}).to_list(length=20)

    if not available_listings:
        await message.answer(
            "🛒 **MARKETPLACE**\n\nThere are currently no Free Fire accounts available for sale. Check back later!",
            parse_mode="Markdown"
        )
        return

    keyboard_buttons = []
    for item in available_listings:
        listing_id = item["listing_id"]
        acc_type = item["account_type"]
        level = item["level"]
        price = item["price"]
        
        button_text = f"🎮 {acc_type} | Lvl {level} | ₹{price} ({listing_id})"
        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"view_item_{listing_id}", style="success")])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Home", callback_data="home", style="primary")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        "🛒 **AVAILABLE FREE FIRE ACCOUNTS**\n\nClick on any account below to view full details, screenshots, and purchase options:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("view_item_"))
async def view_account_details(callback: CallbackQuery):
    listing_id = callback.data.split("_")[2]
    
    item = await listings_collection.find_one({"listing_id": listing_id})

    if not item or item.get("status") != "AVAILABLE":
        await callback.answer("❌ This account is no longer available or has been sold.", show_alert=True)
        return

    acc_type = item.get("account_type", "Free Fire")
    level = item.get("level", "N/A")
    rank = item.get("rank", "N/A")
    region = item.get("region", "N/A")
    outfits = item.get("outfits", "N/A")
    gun_skins = item.get("gun_skins", "N/A")
    description = item.get("description", "No description provided.")
    price = item.get("price", 0)
    seller_username = item.get("seller_username", "Admin")
    images = item.get("images", [])

    details_text = (
        f"🔥 **ACCOUNT DETAILS** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ID:** `{listing_id}`\n"
        f"🎮 **Type:** {acc_type}\n"
        f"⭐ **Level:** {level}\n"
        f"🏆 **Rank:** {rank}\n"
        f"🌍 **Region:** {region}\n"
        f"👕 **Outfits/Passes:** {outfits}\n"
        f"🔫 **Gun Skins:** {gun_skins}\n"
        f"📝 **Description:** {description}\n"
        f"💰 **Price:** **₹{price}**\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    if seller_username and seller_username != "Admin" and not seller_username.startswith("@"):
        buy_url = f"https://t.me/{seller_username}"
    elif seller_username and seller_username.startswith("@"):
        buy_url = f"https://t.me/{seller_username.lstrip('@')}"
    else:
        seller_id = item.get("seller_id")
        buy_url = f"tg://user?id={seller_id}"

    # Added Escrow Group button here
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Buy / Contact Owner", url="https://t.me/Kunalssingh69", style="success")],
        [InlineKeyboardButton(text="🛡️ Escrow Group", url="https://t.me/+QiODdLlfpkQ0Mjk1", style="primary")],
        [InlineKeyboardButton(text="🔙 Back to Marketplace", callback_data="back_to_browse", style="success")]
    ])

    if images:
        if len(images) > 1:
            media_group = [InputMediaPhoto(media=images[0], caption=details_text, parse_mode="Markdown")]
            for img in images[1:]:
                media_group.append(InputMediaPhoto(media=img))
            await callback.message.answer_media_group(media=media_group)
            await callback.message.answer("👇 Click below to purchase or browse back:", reply_markup=keyboard)
        else:
            await callback.message.answer_photo(photo=images[0], caption=details_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.message.answer(details_text, reply_markup=keyboard, parse_mode="Markdown")

    await callback.answer()

@router.callback_query(F.data == "back_to_browse")
async def back_to_browse_marketplace(callback: CallbackQuery):
    available_listings = await listings_collection.find({"status": "AVAILABLE"}).to_list(length=20)

    if not available_listings:
        await callback.message.edit_text(
            "🛒 **MARKETPLACE**\n\nThere are currently no Free Fire accounts available for sale.",
            parse_mode="Markdown"
        )
        return

    keyboard_buttons = []
    for item in available_listings:
        listing_id = item["listing_id"]
        acc_type = item["account_type"]
        level = item["level"]
        price = item["price"]
        
        button_text = f"🎮 {acc_type} | Lvl {level} | ₹{price} ({listing_id})"
        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"view_item_{listing_id}")])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Home", callback_data="home")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(
        "🛒 **AVAILABLE FREE FIRE ACCOUNTS**\n\nClick on any account below to view full details, screenshots, and purchase options:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()