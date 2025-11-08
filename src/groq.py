import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from groq import Groq

class GroqClient:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise Exception("GROQ_API_KEY no configurada")
        self.client = Groq(api_key=api_key)
        self.model = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")
        self.temp = float(os.environ.get("GROQ_TEMP", "0.3"))
        self.max_retries = 3
        self.base_retry_delay = 2
        self.api_timeout = 300

    def _classify_question_type(self, question: str) -> str:
        q_lower = (question or "").lower()
        if any(word in q_lower for word in ["dosis", "calcular", "cuanto", "cuánto", "que es", "qué es", "define", "definición", "definicion", "posologia", "posología"]):
            return "operativa"
        if q_lower.count("•") >= 3 or q_lower.count("\n") >= 3 or any(kw in q_lower for kw in ["incluyendo:", "incluye:"]):
            return "academica"
        return "estandar"

    def _log_token_usage(self, prompt_tokens, completion_tokens, domain):
        total = (prompt_tokens or 0) + (completion_tokens or 0)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"📊 [{timestamp}] Tokens: P={prompt_tokens} + C={completion_tokens} = {total} | Dominio: {domain}")
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/token_usage.log", "a", encoding="utf-8") as f:
                f.write(f"{timestamp}|{domain}|{prompt_tokens}|{completion_tokens}|{total}\n")
        except Exception:
            pass

    def generate_stream(self, question, domain, special_command=None):
        system_msg = self._build_system_prompt(domain, special_command)
        user_msg = self._build_user_prompt(question, domain, special_command)
        question_type = self._classify_question_type(question)
        if question_type == "operativa":
            max_tokens, temperature = 800, 0.1
        elif question_type == "academica":
            max_tokens, temperature = 8000, 0.3
        else:
            max_tokens, temperature = 3000, 0.3
        if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
            max_tokens, temperature = 12000, 0.1
        try:
            stream = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}], temperature=temperature, max_tokens=max_tokens, stream=True)
            chunk_count, accumulated_content = 0, ""
            for event in stream:
                choices = getattr(event, "choices", [])
                if choices:
                    delta = getattr(choices[0].delta, "content", None)
                    if delta:
                        chunk_count += 1
                        accumulated_content += delta
                        yield delta
            self._log_token_usage(len(system_msg + user_msg) // 4, len(accumulated_content) // 4, domain)
            yield "__STREAM_DONE__"
        except Exception as e:
            error_str, error_lower = str(e), str(e).lower()
            if "429" in error_str or "rate" in error_lower:
                yield "\n\n⏳ **Sistema Saturado**\n\nEspera 1-2 minutos."
            elif "timeout" in error_lower:
                yield "\n\n⏱️ **Timeout**\n\nIntenta con pregunta más breve."
            elif "401" in error_str or "auth" in error_lower:
                yield "\n\n⚠️ **Error autenticación**\n\nContacta administrador."
            else:
                yield f"\n\n⚠️ **Error**\n\n{error_str[:200]}"
            yield "__STREAM_DONE__"

    def generate(self, question, domain, special_command=None):
        question_type = self._classify_question_type(question)
        max_tokens = 800 if question_type == "operativa" else (8000 if question_type == "academica" else 3000)
        if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
            max_tokens = 12000
        for attempt in range(self.max_retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    return executor.submit(self._call_groq_api, question, domain, special_command, max_tokens).result(timeout=self.api_timeout)
            except TimeoutError:
                if attempt < self.max_retries - 1:
                    time.sleep(self.base_retry_delay)
                else:
                    return "⏱️ **Timeout**\nReformula tu pregunta."
            except Exception as e:
                if attempt < self.max_retries - 1 and ("429" in str(e) or "rate" in str(e).lower()):
                    time.sleep(self.base_retry_delay * (2 ** attempt))
                else:
                    return f"⚠️ **Error**: {str(e)[:200]}"
        return "⏳ **Sistema Saturado**"

    def _call_groq_api(self, question, domain, special_command, max_tokens=3000):
        system_msg = self._build_system_prompt(domain, special_command)
        user_msg = self._build_user_prompt(question, domain, special_command)
        temperature = 0.1 if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"] else self.temp
        response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}], temperature=temperature, max_tokens=max_tokens)
        usage = getattr(response, "usage", None)
        if usage:
            try:
                self._log_token_usage(getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0), domain)
            except:
                pass
        return response.choices[0].message.content

    def generate_chunk(self, prompt: str, domain: str, max_tokens: int = 1200):
        system_msg = self._get_base_prompt(domain)
        response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}], temperature=self.temp, max_tokens=max_tokens)
        return response.choices[0].message.content

    def _build_system_prompt(self, domain, special_command=None):
        if special_command == "revision_nota":
            return """Eres auditor médico JCI/COFEPRIS. Evalúa nota con estándares completos: datos paciente, motivo consulta, padecimiento, antecedentes, exploración, diagnóstico, plan, legal. Formato: Componentes Presentes, Faltantes, Errores, Cumplimiento %, Recomendaciones."""
        elif special_command == "correccion_nota":
            return """Corrector notas médicas JCI/COFEPRIS. Detecta errores formato, ortografía médica, dosis, claridad. Formato: Errores Detectados, Nota Corregida, Sugerencias. NO inventes datos."""
        elif special_command == "elaboracion_nota":
            return """Genera plantilla SOAP completa: Datos Documento, Datos Paciente, Subjetivo (motivo/padecimiento/antecedentes), Objetivo (vitales/exploración), Análisis (diagnóstico/justificación), Plan (estudios/tratamiento/pronóstico/seguimiento). Marca [COMPLETAR] si falta info."""
        elif special_command == "valoracion":
            return """Médico consultor Mayo/UpToDate. Proporciona: Resumen Caso, Hipótesis Diagnósticas (probable + 3 diferenciales con justificación), Estudios Sugeridos, Abordaje Terapéutico (dosis), Signos Alarma, Fuentes."""
        elif special_command == "study_mode":
            return self._get_base_prompt(domain) + "\n\n**MODO EDUCATIVO**: Usa analogías, ejemplos clínicos, explica 'por qué', divide conceptos, casos prácticos, errores comunes, correlación clínica. Objetivo: ENTENDER profundamente."
        else:
            return self._get_base_prompt(domain)

    def _get_base_prompt(self, domain):
        return f"""Eres Lisabella, asistente médico en {domain}.\n\n**ESTRUCTURA**: Definición, Detalles Clave (tablas/listas), Advertencias, Fuentes.\n\n**REGLAS**: Rigor científico, terminología precisa, NO inventes.\n\n**FUENTES VÁLIDAS**: Gray's, Netter, Guyton, Robbins, Harrison's, UpToDate, Mayo, ESC/AHA/COFEPRIS, NEJM, Lancet, JAMA.\n\nConciso pero completo. Profundidad académica con claridad."""

    def _build_user_prompt(self, question, domain, special_command=None):
        if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
            return question
        return f"""PREGUNTA MÉDICA ({domain}):\n{question}\n\nEstructura: Definición, Detalles Clave, Advertencias, Fuentes"""

    def _generate_rate_limit_message(self):
        return "⏳ **Sistema Saturado**\n\nEspera 1-2 minutos. Límite técnico del servicio."