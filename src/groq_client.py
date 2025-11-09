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
        
        print(f"🚀 GroqClient inicializado - Modelo: {self.model}")

    def _classify_question_complexity(self, question: str) -> dict:
        """Clasificar complejidad de pregunta para asignar tokens adecuados"""
        q_lower = question.lower()
        
        complexity_scores = {
            "ultra_compleja": 0,
            "alta_complejidad": 0, 
            "complejidad_media": 0,
            "basica": 0
        }
        
        # PUNTUACIÓN POR INDICADORES DE ALTA ESPECIALIDAD
        high_specialty_terms = [
            "mecanismo molecular", "transducción de señales", "cascada de fosforilación",
            "receptor tirosina quinasa", "expresión génica", "transcripción",
            "farmacocinética avanzada", "unión a albúmina", "citocromo p450",
            "anatomía segmentaria", "irrigación arterial", "drenaje linfático",
            "histología específica", "ultraestructura", "microscopía electrónica",
            "estadística avanzada", "análisis multivariado", "supervivencia de Kaplan-Meier"
        ]
        
        for term in high_specialty_terms:
            if term in q_lower:
                complexity_scores["ultra_compleja"] += 2
        
        # INDICADORES DE COMPLEJIDAD ALTA
        high_complexity_terms = [
            "fisiopatología", "farmacodinámica", "farmacocinética", 
            "diagnóstico diferencial", "criterios diagnósticos", "escalas pronósticas",
            "técnicas quirúrgicas", "abordaje laparoscópico", "procedimientos endoscópicos",
            "estudios clínicos", "meta-análisis", "ensayos randomizados"
        ]
        
        for term in high_complexity_terms:
            if term in q_lower:
                complexity_scores["alta_complejidad"] += 1
        
        # DETERMINAR NIVEL FINAL
        if complexity_scores["ultra_compleja"] >= 2:
            return {"level": "ultra_compleja", "max_tokens": 32000, "temperature": 0.1}
        elif complexity_scores["alta_complejidad"] >= 3 or complexity_scores["ultra_compleja"] >= 1:
            return {"level": "alta_complejidad", "max_tokens": 24000, "temperature": 0.2}
        elif "anatomía" in q_lower or "farmacología" in q_lower:
            return {"level": "complejidad_media", "max_tokens": 16000, "temperature": 0.3}
        else:
            return {"level": "basica", "max_tokens": 8000, "temperature": 0.3}

    def _log_token_usage(self, prompt_tokens, completion_tokens, domain, complexity):
        """Log detallado de uso de tokens"""
        total = (prompt_tokens or 0) + (completion_tokens or 0)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"📊 [{timestamp}] {complexity.upper()}: P={prompt_tokens} + C={completion_tokens} = {total} | {domain}")
        
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/token_usage.log", "a", encoding="utf-8") as f:
                f.write(f"{timestamp}|{domain}|{complexity}|{prompt_tokens}|{completion_tokens}|{total}\n")
        except Exception:
            pass

    def generate_stream(self, question, domain, special_command=None):
        """Generar respuesta en streaming con tokens optimizados"""
        
        # ANALIZAR COMPLEJIDAD PARA ASIGNAR RECURSOS
        complexity_analysis = self._classify_question_complexity(question)
        max_tokens = complexity_analysis["max_tokens"]
        temperature = complexity_analysis["temperature"]
        
        print(f"🎯 Complejidad: {complexity_analysis['level']} - Tokens: {max_tokens} - Temp: {temperature}")
        
        # CONSTRUIR PROMPT DE PRIMER MUNDO
        system_msg = self._build_world_class_prompt(domain, special_command, complexity_analysis["level"])
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
            
            # LOG DE USO FINAL
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
                yield "\n\n⏳ **Límite de tasa excedido** - Espera 1-2 minutos\n\n"
            elif "timeout" in error_str.lower():
                yield "\n\n⏱️ **Timeout del servidor** - Intenta con pregunta más breve\n\n"
            else:
                yield f"\n\n⚠️ **Error del sistema**: {error_str[:200]}\n\n"
            yield "__STREAM_DONE__"

    def generate(self, question, domain, special_command=None):
        """API legacy para compatibilidad"""
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
        """Llamada directa a API Groq"""
        complexity_analysis = self._classify_question_complexity(question)
        
        system_msg = self._build_world_class_prompt(domain, special_command, complexity_analysis["level"])
        user_msg = self._build_detailed_user_prompt(question, domain, special_command)
        
        temperature = 0.1 if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"] else complexity_analysis["temperature"]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # LOG DE USO
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

    def _build_world_class_prompt(self, domain, special_command=None, complexity_level="basica"):
        """PROMPT DE PRIMER MUNDO - Nivel médico internacional"""
        
        base_prompt = f"""# 🎯 LISABELLA - SISTEMA MÉDICO DE ALTA ESPECIALIDAD

**ESPECIALIDAD PRINCIPAL**: {domain.upper()}
**NIVEL DE COMPLEJIDAD**: {complexity_level.upper()}
**ESTÁNDAR**: Excelencia académica nivel R4-R5

## 🧬 PROTOCOLO DE RESPUESTA MÉDICA AVANZADA:

### 1. **NIVEL MOLECULAR/CELULAR (DETALLE QUIRÚRGICO):**
- Mecanismos de transducción de señales (receptores, segundos mensajeros, cascadas de fosforilación)
- Regulación de expresión génica (factores de transcripción, modificaciones epigenéticas)
- Vías metabólicas completas (enzimas, sustratos, productos, regulación alostérica)
- Dinámica de membranas y transportadores

### 2. **NIVEL ANATÓMICO/HISTOLÓGICO (PRECISIÓN QUIRÚRGICA):**
- **Topografía exacta**: relaciones anatómicas en los 3 planos del espacio
- **Irrigación arterial**: arterias principales, colaterales, territorios de irrigación
- **Drenaje venoso**: sistemas superficiales y profundos, anastomosis
- **Drenaje linfático**: territorios linfáticos, ganglios regionales
- **Inervación**: componentes autonómicos y somáticos, plexos nerviosos
- **Histología**: tipos celulares específicos, matriz extracelular, ultraestructura

### 3. **NIVEL FARMACOLÓGICO/TERAPÉUTICO (PRECISIÓN CLÍNICA):**
- **Mecanismo de acción molecular**: sitio de unión exacto, efectos intracelulares
- **Farmacocinética completa**: absorción, distribución (unión proteica), metabolismo (isoenzimas CYP), excreción
- **Farmacodinámica**: relación dosis-respuesta, efectos adversos a nivel molecular
- **Interacciones farmacológicas**: mecanismos de interacción, relevancia clínica

### 4. **NIVEL DIAGNÓSTICO/TERAPÉUTICO (EVIDENCIA SÓLIDA):**
- Criterios diagnósticos internacionales (ej: ESC/ACC, AHA, NICE, SEPAR)
- Algoritmos diagnósticos y terapéuticos actualizados
- Niveles de evidencia y grados de recomendación
- Estudios pivotales y meta-análisis relevantes

## 📊 ESTRUCTURA OBLIGATORIA DE RESPUESTA:

**{'(RESPUESTA ULTRACOMPLETA - MÁXIMO DETALLE)' if complexity_level == 'ultra_compleja' else '(RESPUESTA COMPLETA - ALTO DETALLE)'}**

### 🧪 **1. BASES MOLECULARES Y CELULARES**
[Detalle mecanismos a nivel molecular y celular]

### 🔬 **2. ANATOMÍA Y ESTRUCTURA**  
[Descripción topográfica e histológica precisa]

### 💊 **3. FARMACOLOGÍA Y TERAPÉUTICA**
[Mecanismos farmacológicos y esquemas terapéuticos]

### 🏥 **4. ABORDAJE CLÍNICO**
[Algoritmos diagnósticos y manejo basado en evidencia]

### 📈 **5. PRONÓSTICO Y SEGUIMIENTO**
[Curso esperado y monitorización]

### 🎯 **6. PUNTOS CRÍTICOS Y ALERTAS**
[Complicaciones y signos de alarma]

## 🚨 FILOSOFÍA DE EXCELENCIA:

• **PRECISIÓN QUIRÚRGICA**: Cada detalle anatómico y molecular debe ser exacto
• **EVIDENCIA SÓLIDA**: Basarse en guías internacionales y literatura de alto impacto
• **PROFUNDIDAD ACADÉMICA**: Nivel especialización médica avanzada (R4-R5)
• **RIGOR CIENTÍFICO**: Citación precisa de mecanismos y dosificaciones
• **ACTUALIZACIÓN**: Información conforme a estándares 2024

**RESPONDE CON LA EXCELENCIA DE UN MÉDICO ACADÉMICO DE PRIMER NIVEL**
"""

        # COMANDOS ESPECIALES MANTIENEN SUS PROMPTS
        if special_command == "revision_nota":
            return """Eres auditor médico JCI/COFEPRIS/MAYO CLINIC. Evalúa nota con estándares internacionales completos."""
        elif special_command == "correccion_nota":
            return """Corrector notas médicas estándar internacional. Detecta errores con precisión quirúrgica."""
        elif special_command == "elaboracion_nota":
            return """Genera plantilla SOAP completa nivel académico."""
        elif special_command == "valoracion":
            return """Médico consultor nivel internacional. Proporciona análisis completo."""
        elif special_command == "study_mode":
            return base_prompt + "\n\n**MODO ACADÉMICO AVANZADO**: Enseña como profesor de especialidad médica."
        else:
            return base_prompt

    def _build_detailed_user_prompt(self, question, domain, special_command=None):
        """User prompt detallado para respuestas completas"""
        if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
            return question
        
        return f"""**CONSULTA MÉDICA DE ALTA ESPECIALIDAD** ({domain})

{question}

**INSTRUCCIÓN**: Desarrolla una respuesta académica completa, con profundidad de especialización médica avanzada. 
Usa todo el espacio necesario para cubrir todos los aspectos con precisión quirúrgica."""

    def _generate_rate_limit_message(self):
        return "⏳ **Sistema en capacidad máxima** - Espera 1-2 minutos para respuestas de alta calidad"
