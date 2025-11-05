import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_TEMP = float(os.getenv("MISTRAL_TEMP", "0.3"))

if not MISTRAL_KEY:
    raise ValueError("⚠️ MISTRAL_API_KEY no configurada en .env")
