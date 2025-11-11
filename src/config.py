import os
from dotenv import load_dotenv

load_dotenv()

# ════════════════════════════════════════════════════════════
# OPENAI API (NUEVO - REEMPLAZA MISTRAL)
# ════════════════════════════════════════════════════════════
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4-turbo")
OPENAI_TEMP = float(os.environ.get("OPENAI_TEMP", "0.3"))

# ════════════════════════════════════════════════════════════
# CONFIGURACIONES EXISTENTES (MANTENER)
# ════════════════════════════════════════════════════════════
# VALIDACIÓN DE CALIDAD
VALIDATE_MIN_WORDS = int(os.environ.get("VALIDATE_MIN_WORDS", "1500"))
VALIDATE_TABLES = os.environ.get("VALIDATE_TABLES", "true").lower() == "true"
VALIDATE_NUMBERS = os.environ.get("VALIDATE_NUMBERS", "true").lower() == "true"
VALIDATE_REFERENCES = os.environ.get("VALIDATE_REFERENCES", "false").lower() == "true"
VALIDATION_RETRIES = int(os.environ.get("VALIDATION_RETRIES", "2"))

# ════════════════════════════════════════════════════════════
# LOGS
# ════════════════════════════════════════════════════════════
SAVE_GENERATION_LOGS = os.environ.get("SAVE_GENERATION_LOGS", "true").lower() == "true"
LOGS_DIR = os.environ.get("LOGS_DIR", "./logs")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# ════════════════════════════════════════════════════════════
# GROQ (MANTENER POR SI ACASO, PERO YA NO SE USA)
# ════════════════════════════════════════════════════════════
GROQ_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMP = float(os.environ.get("GROQ_TEMP", "0.4"))
GROQ_MAX_TOKENS = int(os.environ.get("GROQ_MAX_TOKENS", "8000"))
