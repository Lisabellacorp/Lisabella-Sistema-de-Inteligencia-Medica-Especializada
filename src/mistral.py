import time
import json
from mistralai import Mistral

# ⚠️ IMPORTANTE
# Asegúrate de tener la variable de entorno con tu clave:
# export MISTRAL_API_KEY="TU_KEY_AQUI"

class MistralClient:
    def __init__(self):
        self.client = Mistral()

        # Default del sistema
        self.model = "mistral-large-latest"

        print(f"✅ MistralClient iniciado con modelo: {self.model}")

    # 📊 Registro del uso de tokens
    def _log_token_usage(self, prompt_tokens, completion_tokens, domain):
        log_entry = {
            "timestamp": time.time(),
            "domain": domain,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total": prompt_tokens + completion_tokens
        }
        # Log en consola
        print(f"📊 Tokens usados | Prompt: {prompt_tokens} | Completion: {completion_tokens} | Domain: {domain}")

        # Guardar en archivo
        try:
            with open("logs/token_usage.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"⚠️ Error guardando log tokens: {e}")

    # ✅ Modo no-stream
    def generate(self, prompt, domain="general", special_command=None, max_tokens=32000):

        system_prompt = f"""
Eres Lisabella, asistente médico ultra riguroso. 
Responde con evidencia y precisión.

Dominio: {domain}
Comando especial: {special_command if special_command else "ninguno"}
"""

        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=max_tokens
        )

        # Log tokens
        try:
            usage = response.usage
            self._log_token_usage(usage.prompt_tokens, usage.completion_tokens, domain)
        except:
            print("⚠️ No se pudieron leer los tokens")

        return response.choices[0].message.content

    # ✅ STREAMING REAL
    def generate_stream(self, prompt, domain="general", special_command=None, max_tokens=32000):
        
        system_prompt = f"""
Eres Lisabella, asistente médico preciso, basado en evidencia.
Dominio: {domain}
Comando: {special_command if special_command else "ninguno"}
"""

        # Ejecutar stream
        stream = self.client.chat.stream(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=max_tokens
        )

        total_prompt_tokens = 0
        total_completion_tokens = 0

        for event in stream:
            if event.type == "response.refusal.delta":
                continue

            if event.type == "token":
                total_completion_tokens += 1
                yield event.token

            # Al final, log tokens
            if event.type == "response.completed":
                try:
                    total_prompt_tokens = event.response.usage.prompt_tokens
                    total_completion_tokens = event.response.usage.completion_tokens
                    self._log_token_usage(total_prompt_tokens, total_completion_tokens, domain)
                except:
                    print("⚠️ No fue posible registrar tokens")
                
                yield "__STREAM_DONE__"
                break
