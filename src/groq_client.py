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
        
        # 🚀 ESTRATEGIA DE TOKENS OPTIMIZADA PARA RESPUESTAS COMPLETAS
        self.token_strategy = {
            "nota_medica_completa": 16000,    # Notas médicas exhaustivas
            "caso_clinico_detallado": 12000,  # Casos clínicos complejos
            "ultra_compleja": 10000,          # Mecanismos moleculares
            "alta_complejidad": 8000,         # Fisiopatología avanzada
            "complejidad_media": 4000,        # Conceptos médicos
            "basica": 2000                    # Definiciones simples
        }
        
        print(f"🚀 GroqClient OPTIMIZADO - Tokens máximos: {self.token_strategy}")

    def _classify_question_complexity(self, question: str) -> dict:
        """Clasificación INTELIGENTE basada en contexto y tipo de contenido"""
        q_lower = question.lower()
        
        # 🎯 DETECCIÓN DE NOTAS MÉDICAS - MÁXIMA LONGITUD
        nota_medica_terms = [
            "nota médica", "elaborar nota", "historia clínica", "formato soap",
            "nota de evolución", "nota de ingreso", "expediente clínico"
        ]
        if any(term in q_lower for term in nota_medica_terms):
            return {"level": "nota_medica_completa", "max_tokens": self.token_strategy["nota_medica_completa"], "temperature": 0.1}
        
        # 🎯 DETECCIÓN DE CASOS CLÍNICOS COMPLEJOS
        caso_clinico_terms = [
            "caso clínico", "paciente de", "años con", "presenta", "exploración física",
            "diagnóstico diferencial", "abordaje terapéutico", "manejo de", "tratamiento de"
        ]
        if any(term in q_lower for term in caso_clinico_terms):
            return {"level": "caso_clinico_detallado", "max_tokens": self.token_strategy["caso_clinico_detallado"], "temperature": 0.2}
        
        # 🎯 TÉRMINOS DE ULTRA COMPLEJIDAD
        ultra_complex_terms = [
            "mecanismo molecular", "transducción de señales", "cascada de fosforilación",
            "receptor tirosina quinasa", "expresión génica", "farmacocinética avanzada",
            "anatomía segmentaria", "irrigación arterial", "drenaje linfático específico",
            "ultraestructura", "microscopía electrónica", "análisis multivariado",
            "fisiopatología completa", "mecanismo de acción", "vía de señalización"
        ]
        if any(term in q_lower for term in ultra_complex_terms):
            return {"level": "ultra_compleja", "max_tokens": self.token_strategy["ultra_compleja"], "temperature": 0.1}
        
        # 🎯 TÉRMINOS DE ALTA COMPLEJIDAD
        high_complex_terms = [
            "fisiopatología", "farmacodinámica", "farmacocinética", 
            "diagnóstico diferencial", "criterios diagnósticos", "protocolo de tratamiento",
            "técnicas quirúrgicas", "abordaje laparoscópico", "procedimientos endoscópicos",
            "estudios clínicos", "meta-análisis", "ensayos randomizados", "manejo integral"
        ]
        if any(term in q_lower for term in high_complex_terms):
            return {"level": "alta_complejidad", "max_tokens": self.token_strategy["alta_complejidad"], "temperature": 0.2}
        
        # 🎯 COMPLEJIDAD MEDIA
        if "anatomía" in q_lower or "farmacología" in q_lower or "fisiología" in q_lower:
            return {"level": "complejidad_media", "max_tokens": self.token_strategy["complejidad_media"], "temperature": 0.3}
        
        # 🎯 BÁSICA
        return {"level": "basica", "max_tokens": self.token_strategy["basica"], "temperature": 0.3}

    def _log_token_usage(self, prompt_tokens, completion_tokens, domain, complexity):
        """Log mejorado para monitorear uso real"""
        total = (prompt_tokens or 0) + (completion_tokens or 0)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # ✅ SISTEMA DE ALERTAS MEJORADO
        warning = ""
        if total > 14000:
            warning = " 🔥 CONSUMO MÁXIMO"
        elif total > 8000:
            warning = " ⚡ ALTO CONSUMO"
        elif total > 4000:
            warning = " 📈 CONSUMO MEDIO"
        
        print(f"📊 [{timestamp}] {complexity.upper()}: {total}tokens{warning} | {domain}")
        
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/token_usage.log", "a", encoding="utf-8") as f:
                f.write(f"{timestamp}|{domain}|{complexity}|{prompt_tokens}|{completion_tokens}|{total}\n")
        except Exception:
            pass

    def generate_stream(self, question, domain, special_command=None):
        """Generar respuesta en streaming CON MÁXIMA CAPACIDAD"""
        
        # ✅ ANÁLISIS DE COMPLEJIDAD OPTIMIZADO
        complexity_analysis = self._classify_question_complexity(question)
        max_tokens = complexity_analysis["max_tokens"]
        temperature = complexity_analysis["temperature"]
        
        print(f"🎯 Estrategia: {complexity_analysis['level']} - Tokens: {max_tokens}")
        
        # ✅ PROMPTS OPTIMIZADOS PARA RESPUESTAS COMPLETAS
        system_msg = self._build_comprehensive_prompt(domain, special_command, complexity_analysis["level"])
        user_msg = self._build_detailed_user_prompt(question, domain, special_command)
        
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
            
            # ✅ LOG MEJORADO
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
        """API legacy optimizada"""
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
        """Llamada directa a API Groq optimizada"""
        complexity_analysis = self._classify_question_complexity(question)
        
        system_msg = self._build_comprehensive_prompt(domain, special_command, complexity_analysis["level"])
        user_msg = self._build_detailed_user_prompt(question, domain, special_command)
        
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

    def generate_chunk(self, prompt: str, domain: str, max_tokens: int = 4000):
        """Método para generación por chunks optimizado"""
        system_msg = self._build_comprehensive_prompt(domain)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
            temperature=self.temp,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _build_comprehensive_prompt(self, domain, special_command=None, complexity_level="basica"):
        """PROMPT COMPLETAMENTE REDISEÑADO PARA RESPUESTAS DETALLADAS"""
        
        base_prompt = f"""Eres Lisabella, sistema médico especializado en {domain}.

**INSTRUCCIÓN PRINCIPAL**: Proporciona respuestas MÉDICAMENTE PRECISAS, EXHAUSTIVAS y ESTRUCTURADAS. 

**NIVEL: {complexity_level.upper()}** - Desarrolla el contenido apropiadamente:

{'**📋 NOTA MÉDICA COMPLETA (16K tokens):**' if complexity_level == 'nota_medica_completa' else ''}
{'**🩺 CASO CLÍNICO DETALLADO (12K tokens):**' if complexity_level == 'caso_clinico_detallado' else ''}
{'**🔬 ANÁLISIS ULTRACOMPLETO (10K tokens):**' if complexity_level == 'ultra_compleja' else ''}
{'**📊 ALTA COMPLEJIDAD (8K tokens):**' if complexity_level == 'alta_complejidad' else ''}

**DIRECTRICES CRÍTICAS:**
1. 🚨 **EVITA RESUMIR** - Desarrolla cada concepto completamente
2. 📝 **PROPORCIONA EJEMPLOS** - Incluye casos, dosis, protocolos
3. 🔍 **SÉ EXHAUSTIVO** - Cubre todos los aspectos relevantes
4. 💡 **EXPLICA MECANISMOS** - No solo menciones, explica el "cómo" y "por qué"
5. 🏥 **CONTEXTO CLÍNICO** - Siempre relaciona con práctica médica real

**ESTRUCTURA RECOMENDADA:**
1. **CONCEPTO CLAVE Y DEFINICIÓN**
2. **BASES FISIOPATOLÓGICAS/MOLECULARES DETALLADAS**
3. **MANIFESTACIONES CLÍNICAS COMPLETAS**
4. **DIAGNÓSTICO Y DIAGNÓSTICO DIFERENCIAL**
5. **TRATAMIENTO ESPECÍFICO CON DOSIS**
6. **COMPLICACIONES Y MANEJO**
7. **PRONÓSTICO Y SEGUIMIENTO**
8. **REFERENCIAS ACTUALIZADAS**

Responde con el rigor de un médico especialista, priorizando COMPLETITUD sobre brevedad."""

        # 🔥 PROMPTS ESPECIALES COMPLETAMENTE REDISEÑADOS
        if special_command == "revision_nota":
            return """Eres auditor médico JCI/COFEPRIS/Mayo Clinic. Evalúa exhaustivamente la nota médica:

**EVALUACIÓN COMPLETA:**
1. **COMPONENTES PRESENTES** - Lista detallada de cada elemento incluido
2. **COMPONENTES FALTANTES** - Especifica exactamente qué falta y por qué es importante
3. **ERRORES DETECTADOS** - Errores médicos, de formato, legales, técnicos
4. **NIVEL DE CUMPLIMIENTO** - Porcentaje exacto de cumplimiento de estándares
5. **RECOMENDACIONES ESPECÍFICAS** - Correcciones puntuales y mejoras
6. **RIESGOS IDENTIFICADOS** - Posibles problemas legales o clínicos
7. **PLAN DE MEJORA** - Pasos concretos para corregir deficiencias

Sé exhaustivo en cada punto, proporcionando ejemplos específicos y justificación técnica."""
        
        elif special_command == "correccion_nota":
            return """Eres corrector médico especializado JCI/COFEPRIS. Proporciona corrección completa:

**ANÁLISIS DE CORRECCIÓN:**
1. **ERRORES DETECTADOS** - Lista exhaustiva de errores: ortografía médica, terminología, formato, estructura, contenido médico, dosis, legal
2. **NOTA CORREGIDA COMPLETA** - Versión completamente corregida y mejorada
3. **EXPLICACIÓN DE CAMBIOS** - Justificación médica/técnica de cada corrección
4. **SUGERENCIAS DE MEJORA** - Recomendaciones para evitar errores futuros
5. **ESTÁNDARES APLICADOS** - Normativas JCI, COFEPRIS, NOM, estándares internacionales

NO uses placeholders. Si falta información, sugiere contenido médicamente apropiado."""
        
        elif special_command == "elaboracion_nota":
            return """Eres médico redactor especializado. Genera notas médicas COMPLETAS y REALISTAS:

**INSTRUCCIONES CRÍTICAS:**
🚨 **NUNCA** uses [COMPLETAR] o placeholders
🚨 **GENERA** información médicamente plausible y realista
🚨 **SÉ** exhaustivo en cada sección
🚨 **INCLUYE** todos los detalles: dosificaciones exactas, tiempos, seguimientos

**ESTRUCTURA SOAP COMPLETA:**
**I. DATOS DEL DOCUMENTO**
- Fecha y hora realista
- Médico responsable con nombre completo
- Institución médica específica
- Servicio/Departamento

**II. DATOS DEL PACIENTE**
- Nombre completo realista
- Edad, sexo, fecha nacimiento
- Dirección, teléfono, seguro médico
- Ocupación, estado civil

**III. SUBJETIVO**
- Motivo de consulta detallado
- Padecimiento actual completo (inicio, evolución, tratamientos previos)
- Antecedentes personales patológicos y no patológicos
- Antecedentes familiares
- Hábitos y estilo de vida

**IV. OBJETIVO**
- Signos vitales completos
- Exploración física por sistemas DETALLADA
- Escalas aplicadas (si corresponde)
- Hallazgos positivos y negativos relevantes

**V. ANÁLISIS**
- Diagnóstico principal y secundarios
- Justificación diagnóstica completa
- Diagnósticos diferenciales
- Fisiopatología aplicada al caso
- Gravedad y pronóstico

**VI. PLAN**
- Estudios de gabinete y laboratorio específicos
- Tratamiento farmacológico con DOSIS EXACTAS
- Tratamiento no farmacológico
- Educación al paciente
- Seguimiento y criterios de egreso
- Pronóstico

Genera información REALISTA y MÉDICAMENTE VÁLIDA en cada sección."""
        
        elif special_command == "valoracion":
            return """Eres médico consultor especializado (Mayo Clinic/UpToDate). Proporciona valoración completa:

**VALORACIÓN MÉDICA INTEGRAL:**
1. **RESUMEN DEL CASO** - Síntesis exhaustiva del caso clínico
2. **HIPÓTESIS DIAGNÓSTICAS** 
   - Diagnóstico principal (probabilidad, justificación)
   - 3-5 diagnósticos diferenciales completos (probabilidad, elementos a favor/en contra)
3. **ESTUDIOS COMPLEMENTARIOS**
   - Estudios inmediatos (justificación, utilidad diagnóstica)
   - Estudios de seguimiento (cronología, interpretación esperada)
4. **ABORDAJE TERAPÉUTICO COMPLETO**
   - Tratamiento farmacológico (medicamentos, dosis exactas, vías, frecuencia)
   - Tratamiento no farmacológico
   - Medidas de soporte
5. **CRITERIOS DE HOSPITALIZACIÓN/ALTA**
6. **SIGNOS DE ALARMA Y COMPLICACIONES**
7. **PRONÓSTICO Y SEGUIMIENTO**
8. **FUENTES BIBLIOGRÁFICAS ACTUALIZADAS**

Sé exhaustivo en cada sección, proporcionando fundamento médico para cada recomendación."""
        
        elif special_command == "study_mode":
            return base_prompt + """

**🎓 MODO ESTUDIO ACTIVADO:**
- Enseña como profesor universitario especialista
- Usa analogías clínicas relevantes
- Explica mecanismos fisiopatológicos completos
- Proporciona casos clínicos prácticos
- Incluye "tips" de memorización
- Relaciona con práctica clínica real
- Desarrolla razonamiento diagnóstico
- Proporciona ejercicios de aplicación"""
        
        else:
            return base_prompt

    def _build_detailed_user_prompt(self, question, domain, special_command=None):
        """User prompt optimizado para respuestas completas"""
        if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
            return f"""
{question}

**INSTRUCCIÓN: Proporciona una respuesta COMPLETA y EXHAUSTIVA. Desarrolla todos los puntos en detalle, no resumas.**"""
        
        return f"""PREGUNTA MÉDICA ESPECIALIZADA ({domain}):

{question}

**RESPONDE CON:** 
- Profundidad académica nivel especialización
- Desarrollo completo de conceptos
- Ejemplos clínicos específicos
- Aplicación práctica detallada
- Fundamentación científica actualizada

**NO RESUMAS - SÉ EXHAUSTIVO EN TU EXPLICACIÓN**"""

    def _generate_rate_limit_message(self):
        return "⏳ **Sistema optimizado para respuestas completas** - Procesando consulta con máximo detalle"
