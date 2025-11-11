import os
from dotenv import load_dotenv

load_dotenv()

# ════════════════════════════════════════════════════════════
# DEBUG COMPLETO (AGREGAR ESTO AL PRINCIPIO)
# ════════════════════════════════════════════════════════════
print("=" * 60)
print("🔍 DEBUG COMPLETO - OPENAI CONFIG")
print("=" * 60)

# 1. Verificar si la variable existe
print(f"1. OPENAI_API_KEY en os.environ: {'✅ SÍ' if 'OPENAI_API_KEY' in os.environ else '❌ NO'}")

# 2. Verificar el valor
if 'OPENAI_API_KEY' in os.environ:
    api_key = os.environ['OPENAI_API_KEY']
    print(f"2. Longitud de API Key: {len(api_key)} caracteres")
    print(f"3. Primeros 20 chars: {api_key[:20]}...")
    print(f"4. ¿Key vacía?: {'❌ SÍ' if not api_key else '✅ NO'}")
    print(f"5. ¿Tiene espacios?: {'❌ SÍ' if ' ' in api_key else '✅ NO'}")
else:
    print("❌ OPENAI_API_KEY NO encontrada en variables de entorno")
    print("📋 Variables disponibles:")
    for key in sorted(os.environ.keys()):
        if any(x in key.lower() for x in ['openai', 'api', 'key']):
            print(f"   - {key}: {os.environ[key][:20]}...")

print("=" * 60)

# ════════════════════════════════════════════════════════════
# OPENAI API (MANTENER LO QUE YA TENÍAS)
# ════════════════════════════════════════════════════════════
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4-turbo")
OPENAI_TEMP = float(os.environ.get("OPENAI_TEMP", "0.3"))

print(f"6. OPENAI_API_KEY después de get(): {'✅ CARGADA' if OPENAI_API_KEY else '❌ NULA'}")
print(f"7. OPENAI_MODEL: {OPENAI_MODEL}")
print(f"8. OPENAI_TEMP: {OPENAI_TEMP}")
print("=" * 60)

# ════════════════════════════════════════════════════════════
# CONFIGURACIONES EXISTENTES (MANTENER TODO LO DEMÁS)
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
