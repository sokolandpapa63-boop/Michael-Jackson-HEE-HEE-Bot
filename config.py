import os
from dotenv import load_dotenv

load_dotenv()  # локально читает .env, на Railway просто ничего не найдёт

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Добавь его в .env или в Variables на Railway")

DB_PATH = "taskmaster.db"
