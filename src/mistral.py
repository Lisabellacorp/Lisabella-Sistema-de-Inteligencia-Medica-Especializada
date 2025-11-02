import os
import time
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

        self.client = Mistral(api_key=MISTRAL_KEY)
        self.model = MISTRAL_MODEL
        self.temp = MISTRAL_TEMP
        self.max_retries = 3
        self.base_retry_delay = 2
        self.api_timeout = 30  # ⬅️ REDUCIDO a 30s para forzar rapidez

    def generate(self, question, domain, special_command=None):
        """Generar respuesta COMPLETA (SIN streaming) con 4000 tokens"""

        for attempt in range(self.max_retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self._call_mistral_api,
                        question,
                        domain,
                        special_command,
                        max_tokens=4000
                    )
                    result = future.result(timeout=self.api_timeout)
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

                if "429" in str(e) or "rate" in error_str or "capacity" in error_str:
                    if attempt < self.max_retries - 1:
                        retry_delay = self.base_retry_delay * (2 ** attempt)
                        print(f"⏳ Rate limit. Reintentando en {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return self._generate_rate_limit_message()

                elif "authentication" in error_str or "api key" in error_str:
                    return "⚠️ Error de autenticación. Contacta al administrador."

                elif "network" in error_str or "connection" in error_str:
                    if attempt < self.max_retries - 1:
                        print(f"🔌 Error de conexión. Reintentando...")
                        time.sleep(2)
                        continue
                    else:
                        return "⚠️ Error de conexión. Verifica tu internet."

                else:
                    print(f"❌ Error: {str(e)}")
                    return f"⚠️ Error del sistema: {str(e)[:200]}"

        return self._generate_rate_limit_message()

    def _call_mistral_api(self, question, domain, special_command, max_tokens=4000):
        """Llamada directa a Mistral API"""
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

        return response.choices[0].message.content

    def _build_system_prompt(self, domain, special_command=None):
        """System prompt por comando especial o dominio"""
        
        if special_command == "revision_nota":
            return """Eres un auditor médico certificado.

**ESTÁNDARES:** JCI, Clínica Mayo, COFEPRIS (NOM-004-SSA3-2012), UpToDate.

**EVALÚA:**
1. Datos del paciente y documento
2. Motivo de consulta
3. Padecimiento actual
4. Antecedentes
5. Exploración física
6. Impresión diagnóstica
7. Plan de manejo
8. Legal y ético

**FORMATO:**
## ✅ Componentes Presentes
## ❌ Componentes Faltantes
## ⚠️ Errores Detectados
## 📋 Cumplimiento Legal
## 💡 Recomendaciones"""

        elif special_command == "elaboracion_nota":
            return """Eres un generador de plantillas de notas médicas en formato SOAP.

Genera plantilla COMPLETA con:
- Datos del documento
- Datos del paciente
- S - SUBJETIVO (motivo, padecimiento, antecedentes)
- O - OBJETIVO (signos vitales, exploración física)
- A - ANÁLISIS (impresión diagnóstica, justificación, diferenciales)
- P - PLAN (estudios, tratamiento, pronóstico, seguimiento)

Marca campos faltantes como [COMPLETAR]."""

        elif special_command == "valoracion":
            return """Eres un médico consultor de apoyo diagnóstico.

**FORMATO:**
## 📋 Resumen del Caso
## 🎯 Hipótesis Diagnósticas
## 🔬 Estudios Sugeridos
## 💊 Abordaje Terapéutico
## ⚠️ Signos de Alarma
## 📚 Fuentes"""

        elif special_command == "calculo_dosis":
            return """Eres un farmacólogo especializado en cálculo de dosis.

Calcula dosis según:
- Peso corporal
- Edad
- Función renal/hepática
- Interacciones medicamentosas

Proporciona:
- Dosis inicial
- Dosis de mantenimiento
- Vía de administración
- Frecuencia
- Ajustes necesarios"""

        elif special_command == "study_mode":
            base = self._get_base_prompt(domain)
            return base + """

**MODO EDUCATIVO:**
- Usa analogías
- Ejemplos clínicos
- Explica el "por qué"
- Pasos simples
- Errores comunes
- Correlación clínica"""

        else:
            return self._get_base_prompt(domain)

    def _get_base_prompt(self, domain):
        """Prompt base para respuestas médicas"""
        return f"""Eres Lisabella, asistente médico especializado en ciencias de la salud.
Tu área actual: **{domain}**

## REGLAS:
1. Rigor científico
2. Terminología médica correcta
3. Estructura obligatoria:
   - ## Definición
   - ## Detalles Clave
   - ## Advertencias
   - ## Fuentes
4. Usa **negritas**, tablas y listas
5. NO inventes información

## FUENTES VÁLIDAS:
Gray's Anatomy, Guyton & Hall, Goodman & Gilman's, Robbins, Harrison's, 
Goldman-Cecil, UpToDate, ESC, AHA, ACC, NICE, COFEPRIS

Responde con profundidad académica y claridad."""

    def _build_user_prompt(self, question, domain, special_command=None):
        """User prompt según comando"""
        if special_command in ["revision_nota", "elaboracion_nota", "valoracion", "calculo_dosis"]:
            return question
        else:
            return f"""PREGUNTA MÉDICA ({domain}):
{question}

Estructura:
## Definición
## Detalles Clave
## Advertencias
## Fuentes"""

    def _generate_rate_limit_message(self):
        return """⏳ Sistema saturado. Espera 1-2 minutos e intenta nuevamente."""

    def _generate_timeout_message(self):
        return """⏳ La consulta está tomando mucho tiempo. 
        
Intenta:
• Reformular de manera más específica
• Dividir en preguntas más pequeñas"""
