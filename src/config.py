import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TEMP = float(os.getenv("DEEPSEEK_TEMP", "0.3"))

if not DEEPSEEK_KEY:
    raise ValueError("⚠️ DEEPSEEK_KEY no configurada en .env")

