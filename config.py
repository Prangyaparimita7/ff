import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# MongoDB Connection Details
MONGO_URL = os.getenv("MONGO_URL", "")
DB_NAME = os.getenv("DB_NAME", "ff_marketplace")

# Administrative Configuration
# Parses comma-separated Telegram IDs into an integer list for security checks
ADMIN_IDS = [int(admin_id.strip()) for admin_id in os.getenv("ADMIN_IDS", "").split(",") if admin_id.strip()]

# Marketplace Financial & Operational Settings
COMMISSION_PERCENTAGE = float(os.getenv("COMMISSION_PERCENTAGE", "5.0"))
CURRENCY = os.getenv("CURRENCY", "₹")
MIN_LISTING_PRICE = float(os.getenv("MIN_LISTING_PRICE", "100.0"))
MAX_LISTING_PRICE = float(os.getenv("MAX_LISTING_PRICE", "10000000.0"))

# Support Contact
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "RoyalEren")