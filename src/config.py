import os
from dotenv import load_dotenv

load_dotenv()

# ════════════════════════════════════════════════════════════
# MISTRAL API
# ════════════════════════════════════════════════════════════
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_TEMP = float(os.environ.get("MISTRAL_TEMP", "0.4"))
MISTRAL_TIMEOUT = int(os.environ.get("MISTRAL_TIMEOUT", "28"))

# ════════════════════════════════════════════════════════════
# GROQ API
# ════════════════════════════════════════════════════════════
GROQ_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMP = float(os.environ.get("GROQ_TEMP", "0.4"))
GROQ_MAX_TOKENS = int(os.environ.get("GROQ_MAX_TOKENS", "8000"))

# ════════════════════════════════════════════════════════════
# SISTEMA HÍBRIDO
# ════════════════════════════════════════════════════════════
# Dominios que usarán Mistral (calidad máxima)
MISTRAL_DOMAINS_RAW = os.environ.get(
    "MISTRAL_DOMAINS", 
    "anatomía,histología,fisiología,bioquímica,farmacología,patología"
)
MISTRAL_DOMAINS = [d.strip().lower() for d in MISTRAL_DOMAINS_RAW.split(",")]

# Modo subsecciones para Groq
GROQ_USE_SUBSECTIONS = os.environ.get("GROQ_USE_SUBSECTIONS", "true").lower() == "true"
GROQ_SUBSECTIONS_COUNT = int(os.environ.get("GROQ_SUBSECTIONS_COUNT", "8"))
GROQ_MIN_WORDS_PER_SECTION = int(os.environ.get("GROQ_MIN_WORDS_PER_SECTION", "250"))

# ════════════════════════════════════════════════════════════
# VALIDACIÓN DE CALIDAD
# ════════════════════════════════════════════════════════════
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
