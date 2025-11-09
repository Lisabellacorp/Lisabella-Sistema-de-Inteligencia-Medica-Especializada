import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from groq import Groq
from typing import Optional

class GroqClient:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise Exception("GROQ_API_KEY no configurada")
        
        self.client = Groq(api_key=api_key)
        self.model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.temp = float(os.environ.get("GROQ_TEMP", "0.3"))
        self.max_retries = 3
        self.base_retry_delay = 2
        self.api_timeout = 300
        
        # ✅ STRATEGIA DE TOKENS RESPETANDO RATE LIMITS
        self.token_strategy = {
            "ultra_compleja": 8000,    # 8K tokens máximo
            "alta_complejidad": 4000,  # 4K tokens
            "complejidad_media": 2000, # 2K tokens  
            "basica": 1000            # 1K tokens
        }
        
        print(f"🚀 GroqClient inicializado - Estrategia tokens: {self.token_strategy}")

    def _classify_question_complexity(self, question: str) -> dict:
        """Clasificar complejidad RESPETANDO rate limits de Groq"""
        q_lower = question.lower()
        
        # ✅ TÉRMINOS DE ULTRA COMPLEJIDAD (8K tokens)
        ultra_complex_terms = [
            "mecanismo molecular", "transducción de señales", "cascada de fosforilación",
            "receptor tirosina quinasa", "expresión génica", "farmacocinética avanzada",
            "anatomía segmentaria", "irrigación arterial", "drenaje linfático específico",
            "ultraestructura", "microscopía electrónica", "análisis multivariado"
        ]
        
        if any(term in q_lower for term in ultra_complex_terms):
            return {"level": "ultra_compleja", "max_tokens": self.token_strategy["ultra_compleja"], "temperature": 0.1}
        
        # ✅ TÉRMINOS DE ALTA COMPLEJIDAD (4K tokens)
        high_complex_terms = [
            "fisiopatología", "farmacodinámica", "farmacocinética", 
            "diagnóstico diferencial", "criterios diagnósticos",
            "técnicas quirúrgicas", "abordaje laparoscópico", "procedimientos endoscópicos",
            "estudios clínicos", "meta-análisis", "ensayos randomizados"
        ]
        
        if any(term in q_lower for term in high_complex_terms):
            return {"level": "alta_complejidad", "max_tokens": self.token_strategy["alta_complejidad"], "temperature": 0.2}
        
        # ✅ COMPLEJIDAD MEDIA (2K tokens) - Preguntas anatómicas/farmacológicas básicas
        if "anatomía" in q_lower or "farmacología" in q_lower or "fisiología" in q_lower:
            return {"level": "complejidad_media", "max_tokens": self.token_strategy["complejidad_media"], "temperature": 0.3}
        
        # ✅ BÁSICA (1K tokens) - Preguntas generales
        return {"level": "basica", "max_tokens": self.token_strategy["basica"], "temperature": 0.3}

    def _log_token_usage(self, prompt_tokens, completion_tokens, domain, complexity):
        """Log detallado con advertencias de límites"""
        total = (prompt_tokens or 0) + (completion_tokens or 0)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # ✅ ADVERTENCIA SI NOS ACERCAMOS A LÍMITES
        warning = ""
        if total > 7000:
            warning = " ⚠️ ALTO CONSUMO"
        elif total > 3000:
            warning = " ⚠️ CONSUMO MEDIO"
        
        print(f"📊 [{timestamp}] {complexity.upper()}: {total}tokens{warning} | {domain}")
        
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/token_usage.log", "a", encoding="utf-8") as f:
                f.write(f"{timestamp}|{domain}|{complexity}|{prompt_tokens}|{completion_tokens}|{total}\n")
        except Exception:
            pass

    def generate_stream(self, question, domain, special_command=None):
        """Generar respuesta en streaming CON LÍMITES INTELIGENTES"""
        
        # ✅ ANALIZAR COMPLEJIDAD CON ESTRATEGIA DE TOKENS
        complexity_analysis = self._classify_question_complexity(question)
        max_tokens = complexity_analysis["max_tokens"]
        temperature = complexity_analysis["temperature"]
        
        print(f"🎯 Estrategia: {complexity_analysis['level']} - Tokens: {max_tokens}")
        
        # ✅ PROMPT OPTIMIZADO PARA TOKENS LIMITADOS
        system_msg = self._build_optimized_prompt(domain, special_command, complexity_analysis["level"])
        user_msg = self._build_efficient_user_prompt(question, domain, special_command)
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            
            chunk_count, accumulated_content = 0, ""
            for event in stream:
                choices = getattr(event, "choices", [])
                if choices:
                    delta = getattr(choices[0].delta, "content", None)
                    if delta:
                        chunk_count += 1
                        accumulated_content += delta
                        yield delta
            
            # ✅ LOG CON CONCIENCIA DE LÍMITES
            self._log_token_usage(
                len(system_msg + user_msg) // 4, 
                len(accumulated_content) // 4, 
                domain, 
                complexity_analysis["level"]
            )
            
            yield "__STREAM_DONE__"
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                yield "\n\n⏳ **Límite de tasa alcanzado** - Espera 1-2 minutos antes de nueva consulta\n\n"
            elif "rate" in error_str.lower():
                yield "\n\n🚫 **Límite de uso diario** - Intenta mañana\n\n"
            elif "timeout" in error_str.lower():
                yield "\n\n⏱️ **Timeout del servidor** - Intenta con pregunta más breve\n\n"
            else:
                yield f"\n\n⚠️ **Error del sistema**: {error_str[:150]}\n\n"
            yield "__STREAM_DONE__"

    def generate(self, question, domain, special_command=None):
        """API legacy para compatibilidad - CON GESTIÓN DE TOKENS"""
        complexity_analysis = self._classify_question_complexity(question)
        max_tokens = complexity_analysis["max_tokens"]
        
        for attempt in range(self.max_retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    return executor.submit(
                        self._call_groq_api, question, domain, special_command, max_tokens
                    ).result(timeout=self.api_timeout)
            except TimeoutError:
                if attempt < self.max_retries - 1:
                    time.sleep(self.base_retry_delay)
                else:
                    return "⏱️ **Timeout** - Reformula tu pregunta o intenta más tarde"
            except Exception as e:
                if attempt < self.max_retries - 1 and ("429" in str(e) or "rate" in str(e).lower()):
                    time.sleep(self.base_retry_delay * (2 ** attempt))
                else:
                    return f"⚠️ **Error**: {str(e)[:200]}"
        return "⏳ **Sistema saturado** - Intenta en 1-2 minutos"

    def _call_groq_api(self, question, domain, special_command, max_tokens):
        """Llamada directa a API Groq con gestión completa"""
        complexity_analysis = self._classify_question_complexity(question)
        
        system_msg = self._build_optimized_prompt(domain, special_command, complexity_analysis["level"])
        user_msg = self._build_efficient_user_prompt(question, domain, special_command)
        
        temperature = 0.1 if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"] else complexity_analysis["temperature"]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # LOG DE USO COMPLETO
        usage = getattr(response, "usage", None)
        if usage:
            try:
                self._log_token_usage(
                    getattr(usage, "prompt_tokens", 0),
                    getattr(usage, "completion_tokens", 0),
                    domain,
                    complexity_analysis["level"]
                )
            except Exception:
                pass
        
        return response.choices[0].message.content

    def generate_chunk(self, prompt: str, domain: str, max_tokens: int = 1200):
        """Método para generación por chunks (compatibilidad)"""
        system_msg = self._build_optimized_prompt(domain)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
            temperature=self.temp,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _build_optimized_prompt(self, domain, special_command=None, complexity_level="basica"):
        """PROMPT OPTIMIZADO para tokens limitados pero alta calidad"""
        
        base_prompt = f"""Eres Lisabella, sistema médico especializado en {domain}.

**INSTRUCCIÓN PRINCIPAL**: Proporciona respuestas MÉDICAMENTE PRECISAS y ESTRUCTURADAS, optimizando el uso de tokens.

**NIVEL: {complexity_level.upper()}** - Usa estructura apropiada:

{'**🎯 ESTRUCTURA ULTRACOMPLETA (8K tokens):**' if complexity_level == 'ultra_compleja' else '**📋 ESTRUCTURA EFICIENTE:**'}

1. **CONCEPTO CLAVE**: Definición precisa
2. **BASES MOLECULARES/ANATÓMICAS**: Mecanismos esenciales
3. **APLICACIÓN CLÍNICA**: Diagnóstico y tratamiento
4. **PUNTOS CRÍTICOS**: Alertas y consideraciones
5. **REFERENCIAS**: Fuentes verificables

**CALIDAD > CANTIDAD**: Sé conciso pero completo. Precisión sobre extensión.

Responde con rigor académico nivel especialización médica."""

        # Comandos especiales mantienen lógica existente
        if special_command == "revision_nota":
            return """Eres auditor médico JCI/COFEPRIS. Evalúa nota con estándares completos: datos paciente, motivo consulta, padecimiento, antecedentes, exploración, diagnóstico, plan, legal. Formato: Componentes Presentes, Faltantes, Errores, Cumplimiento %, Recomendaciones."""
        elif special_command == "correccion_nota":
            return """Corrector notas médicas JCI/COFEPRIS. Detecta errores formato, ortografía médica, dosis, claridad. Formato: Errores Detectados, Nota Corregida, Sugerencias. NO inventes datos."""
        elif special_command == "elaboracion_nota":
            return """Genera plantilla SOAP completa: Datos Documento, Datos Paciente, Subjetivo (motivo/padecimiento/antecedentes), Objetivo (vitales/exploración), Análisis (diagnóstico/justificación), Plan (estudios/tratamiento/pronóstico/seguimiento). Marca [COMPLETAR] si falta info."""
        elif special_command == "valoracion":
            return """Médico consultor Mayo/UpToDate. Proporciona: Resumen Caso, Hipótesis Diagnósticas (probable + 3 diferenciales con justificación), Estudios Sugeridos, Abordaje Terapéutico (dosis), Signos Alarma, Fuentes."""
        elif special_command == "study_mode":
            return base_prompt + "\n\n**MODO ESTUDIO**: Enseña como profesor especialista. Usa analogías, ejemplos clínicos, explica 'por qué', divide conceptos, casos prácticos."
        else:
            return base_prompt

    def _build_efficient_user_prompt(self, question, domain, special_command=None):
        """User prompt eficiente para optimizar tokens"""
        if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
            return question
        
        return f"""PREGUNTA MÉDICA ({domain}):

{question}

Responde con PRECISIÓN MÉDICA y ESTRUCTURA CLARA. Optimiza el contenido para máximo valor clínico."""

    def _generate_rate_limit_message(self):
        return "⏳ **Sistema en capacidad máxima** - Espera 1-2 minutos para respuestas de alta calidad"
