from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states import SellAccountStates
from database.db import listings_collection
from config import ADMIN_IDS
import random
import datetime

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(F.text == "➕ Sell Account")
async def start_selling(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ You don't have permission to list accounts. This feature is restricted to admins.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎮 Free Fire", callback_data="type_ff", style="primary"),
            InlineKeyboardButton(text="🎮 Free Fire MAX", callback_data="type_ffmax", style="primary")
        ]
    ])
    await message.answer("🎮 **Select Account Type:**", reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(SellAccountStates.account_type)

@router.callback_query(SellAccountStates.account_type, F.data.startswith("type_"))
async def process_account_type(callback: CallbackQuery, state: FSMContext):
    acc_type = "Free Fire MAX" if "ffmax" in callback.data else "Free Fire"
    await state.update_data(account_type=acc_type)
    await callback.message.edit_text("⭐ **Enter Account Level** (e.g., 68):", parse_mode="Markdown")
    await state.set_state(SellAccountStates.level)

@router.message(SellAccountStates.level)
async def process_level(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Please enter a valid numeric level.")
        return
    await state.update_data(level=int(message.text))
    await message.answer("🏆 **Enter Current Rank** (e.g., Grandmaster):", parse_mode="Markdown")
    await state.set_state(SellAccountStates.rank)

@router.message(SellAccountStates.rank)
async def process_rank(message: Message, state: FSMContext):
    await state.update_data(rank=message.text)
    await message.answer("🌍 **Enter Account Region** (e.g., India, Europe, SG):", parse_mode="Markdown")
    await state.set_state(SellAccountStates.region)

@router.message(SellAccountStates.region)
async def process_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)
    await message.answer("👕 **Enter Number of Outfits / Vault** (e.g., 45):", parse_mode="Markdown")
    await state.set_state(SellAccountStates.outfits)

@router.message(SellAccountStates.outfits)
async def process_outfits(message: Message, state: FSMContext):
    await state.update_data(outfits=message.text)
    await message.answer("🔫 **Enter Rare Gun Skins Details** (e.g., M1887 Evo Level 4, Scar Megalodon):", parse_mode="Markdown")
    await state.set_state(SellAccountStates.gun_skins)

@router.message(SellAccountStates.gun_skins)
async def process_gun_skins(message: Message, state: FSMContext):
    await state.update_data(gun_skins=message.text)
    await message.answer("📝 **Enter full description or highlights:**", parse_mode="Markdown")
    await state.set_state(SellAccountStates.description)

@router.message(SellAccountStates.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("💰 **Enter Selling Price in INR** (e.g., 1500):", parse_mode="Markdown")
    await state.set_state(SellAccountStates.price)

@router.message(SellAccountStates.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Please enter a valid positive price.")
        return

    await state.update_data(price=price)
    await message.answer(
        "📸 **Send account screenshots**:\n\n"
        "Send one or more screenshots of the profile/items. Click the button below when finished uploading images.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Done Uploading Images", callback_data="finish_images", style="success")]
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(SellAccountStates.images)

@router.message(SellAccountStates.images, F.photo)
async def collect_screenshots(message: Message, state: FSMContext):
    data = await state.get_data()
    images = data.get("images", [])
    images.append(message.photo[-1].file_id)
    await state.update_data(images=images)
    await message.answer(f"📸 Screenshot received! Total: **{len(images)}**. Send more or click 'Done Uploading Images'.", parse_mode="Markdown")

@router.callback_query(SellAccountStates.images, F.data == "finish_images")
async def finish_images_step(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("images"):
        await callback.answer("⚠️ Please upload at least one screenshot.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Skip Video", callback_data="skip_video", style="primary")]
    ])
    await callback.message.edit_text(
        "🎥 **Send a gameplay / collection video (Optional):**\n\n"
        "You can upload a short video file or click skip below.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(SellAccountStates.video)

@router.message(SellAccountStates.video, F.video)
async def collect_video(message: Message, state: FSMContext):
    await state.update_data(video=message.video.file_id)
    await finalize_listing(message, state, is_callback=False)

@router.callback_query(SellAccountStates.video, F.data == "skip_video")
async def skip_video_step(callback: CallbackQuery, state: FSMContext):
    await state.update_data(video=None)
    await finalize_listing(callback.message, state, is_callback=True)

async def finalize_listing(message: Message, state: FSMContext, is_callback: bool = False):
    data = await state.get_data()
    listing_id = f"FF-{random.randint(10000, 99999)}"

    listing_doc = {
        "listing_id": listing_id,
        "seller_id": message.from_user.id if not is_callback else message.chat.id,
        "seller_username": message.from_user.username if hasattr(message, "from_user") and message.from_user else "Admin",
        "account_type": data.get("account_type"),
        "level": data.get("level"),
        "rank": data.get("rank"),
        "region": data.get("region"),
        "outfits": data.get("outfits"),
        "gun_skins": data.get("gun_skins"),
        "description": data.get("description"),
        "price": data.get("price"),
        "images": data.get("images", []),
        "video": data.get("video"),
        "status": "AVAILABLE",
        "created_at": datetime.datetime.utcnow()
    }

    await listings_collection.insert_one(listing_doc)
    await state.clear()

    success_text = (
        f"✅ **ACCOUNT LISTED SUCCESSFULLY!**\n\n"
        f"🆔 Listing ID: `{listing_id}`\n"
        f"💰 Price: ₹{data.get('price')}\n"
        f"📸 Images: {len(data.get('images', []))}\n\n"
        "Your account is now live in the marketplace."
    )

    if is_callback:
        await message.edit_text(success_text, parse_mode="Markdown")
    else:
        await message.answer(success_text, parse_mode="Markdown")
