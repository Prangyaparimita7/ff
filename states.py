from aiogram.fsm.state import State, StatesGroup

class SellAccountStates(StatesGroup):
    account_type = State()
    level = State()
    rank = State()
    region = State()
    outfits = State()
    gun_skins = State()
    description = State()
    price = State()
    images = State()
    video = State()
    preview = State()

class FilterStates(StatesGroup):
    custom_price = State()

class PaymentStates(StatesGroup):
    upload_proof = State()