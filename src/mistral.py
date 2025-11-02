import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError

try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    print("❌ Mistral AI no disponible")

try:
    from src.config import MISTRAL_KEY, MISTRAL_MODEL, MISTRAL_TEMP
except ImportError:
    MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
    MISTRAL_TEMP = float(os.environ.get("MISTRAL_TEMP", "0.3"))


class MistralClient:
    def __init__(self):
        if not MISTRAL_AVAILABLE:
            raise Exception("Mistral AI library no está instalada")

        if not MISTRAL_KEY:
            raise Exception("MISTRAL_API_KEY no configurada")

        # ✅ CONFIGURAR TIMEOUT EN EL CLIENTE
        self.client = Mistral(
            api_key=MISTRAL_KEY
        )
        self.model = MISTRAL_MODEL
        self.temp = MISTRAL_TEMP
        self.max_retries = 2  # ⬅️ REDUCIDO
        self.base_retry_delay = 1
        self.api_timeout = 25  # ⬅️ CRÍTICO: 25s MÁXIMO

    def generate(self, question, domain, special_command=None):
        """Generar respuesta con timeout AGGRESIVO"""
        
        # ✅ TIMEOUT DINÁMICO - MÁS CORTO PARA PREGUNTAS COMPLEJAS
        if len(question) > 200:
            current_timeout = 20  # 20s para preguntas largas
        else:
            current_timeout = 25  # 25s para preguntas normales

        for attempt in range(self.max_retries):
            try:
                # ✅ LLAMADA DIRECTA SIN ThreadPoolExecutor
                result = self._call_mistral_api_with_timeout(
                    question, domain, special_command, 
                    max_tokens=3500,  # ⬅️ REDUCIDO de 4000
                    timeout=current_timeout
                )
                return result

            except TimeoutError:
                print(f"⏳ Timeout en intento {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.base_retry_delay)
                    continue
                else:
                    return self._generate_timeout_message()

            except Exception as e:
                error_str = str(e).lower()

                if "429" in str(e) or "rate" in error_str:
                    if attempt < self.max_retries - 1:
                        retry_delay = self.base_retry_delay * (2 ** attempt)
                        print(f"⏳ Rate limit. Reintentando en {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return self._generate_rate_limit_message()

                elif "timeout" in error_str or "timed out" in error_str:
                    return self._generate_timeout_message()

                elif "authentication" in error_str:
                    return "⚠️ Error de autenticación. Verifica la API key."

                else:
                    print(f"❌ Error: {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        return f"⚠️ Error del sistema: {str(e)[:150]}"

        return self._generate_timeout_message()

    def _call_mistral_api_with_timeout(self, question, domain, special_command, max_tokens=3500, timeout=25):
        """Llamada a Mistral API con timeout REAL"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Mistral API timeout")
        
        # ✅ TIMEOUT REAL con signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            system_msg = self._build_system_prompt(domain, special_command)
            user_msg = self._build_user_prompt(question, domain, special_command)

            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=self.temp,
                max_tokens=max_tokens
            )
            
            signal.alarm(0)  # Cancelar timeout
            return response.choices[0].message.content
            
        except Exception as e:
            signal.alarm(0)  # Siempre cancelar timeout
            raise e

    # ... (el resto de tus métodos _build_system_prompt, _get_base_prompt, etc. se mantienen igual)
    def _build_system_prompt(self, domain, special_command=None):
        # TUS MÉTODOS ACTUALES - NO CAMBIAR
        pass

    def _get_base_prompt(self, domain):
        # TUS MÉTODOS ACTUALES - NO CAMBIAR  
        pass

    def _build_user_prompt(self, question, domain, special_command=None):
        # TUS MÉTODOS ACTUALES - NO CAMBIAR
        pass

    def _generate_rate_limit_message(self):
        return """⏳ Sistema temporalmente saturado. Espera 1-2 minutos."""

    def _generate_timeout_message(self):
        return """⏳ La consulta está tardando más de lo esperado.

**Sugerencias:**
• Reformula tu pregunta de manera más específica
• Divide consultas complejas en varias preguntas
• Intenta nuevamente en unos momentos"""
