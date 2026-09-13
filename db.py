from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME

# Initialize the asynchronous Motor client
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Define your core database collections
users_collection = db["users"]
listings_collection = db["listings"]
orders_collection = db["orders"]
channels_collection = db["forced_channels"]
settings_collection = db["settings"]