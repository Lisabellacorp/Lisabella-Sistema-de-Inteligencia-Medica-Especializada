import re
from mistralai import Mistral
from dotenv import load_dotenv
import os

load_dotenv()

IS_SAFE = True

mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", None))

def is_legal_or_medical(input_text):
    legal_keywords = [
        "contrato", "ley", "demanda", "sentencia", "jurídic", "abogado", 
        "litigio", "constitución", "normativa", "amparo"
    ]
    medical_keywords = [
        "diagnóst", "tratamiento", "síntoma", "patología", "enfermedad",
        "farmac", "cirugía", "medicina", "histología", "tejido"
    ]
    return any(re.search(k, input_text, re.IGNORECASE) for k in legal_keywords + medical_keywords)

def is_safe_question(input_text):
    # Legal/medicina = lo dejamos pasar
    if is_legal_or_medical(input_text):
        return True
    
    # Preguntas abiertas tipo política actual → bloqueadas
    politics_pattern = r"(elección|candidato|partido|votar|política)"
    if re.search(politics_pattern, input_text, re.IGNORECASE):
        return False
    
    return True

def generate_stream(prompt: str, system_prompt: str = None):
    if not IS_SAFE or is_safe_question(prompt):
        try:
            stream = mistral_client.chat.stream(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system_prompt or "Eres un asistente útil."},
                    {"role": "user", "content": prompt}
                ],
            )

            full_text = ""
            completion_tokens = 0

            for event in stream:
                if event.type == "token":
                    completion_tokens += 1
                    token = event.token
                    full_text += token

                    # ✅ formato compatible con tu UI
                    yield {"type": "chunk", "content": token}

            # ✅ finalizar stream
            yield {"type": "done"}

        except Exception as e:
            yield {"type": "chunk", "content": f"[Error usando Mistral: {e}]\nUsando fallback..."}
    else:
        # ❌ pregunta no permitida → respuesta ética
        fallback = "Lo siento, no puedo ayudar con esa consulta."
        for char in fallback:
            yield {"type": "chunk", "content": char}
        yield {"type": "done"}
