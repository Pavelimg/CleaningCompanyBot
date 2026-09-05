import os

from dotenv import load_dotenv

load_dotenv()

tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
db_path = os.getenv("DATABASE_PATH", "DB.db")
admins = [
    int(value)
    for value in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
    if value.strip()
]
timezone = int(os.getenv("TIMEZONE_OFFSET_HOURS", "2"))

if not tg_token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

__all__ = ["tg_token", "db_path", "admins", "timezone"]

