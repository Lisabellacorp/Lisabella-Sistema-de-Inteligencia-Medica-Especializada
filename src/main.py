import sys
sys.path.insert(0, '/home/ray/lisabella')

from src.wrapper import Wrapper, Result
from src.mistral import MistralClient
from src.amplitud_detector import evaluar_y_reformular

class Lisabella:
    def __init__(self):
        self.wrapper = Wrapper()
        self.mistral = MistralClient()
    
    def ask(self, question):
        """Procesar pregunta end-to-end con manejo robusto de errores y comandos especiales"""
        
        try:
            # Clasificar pregunta
            classification = self.wrapper.classify(question)
            result = classification["result"]
            
            # ═══════════════════════════════════════════════════════
            # CASO 1: PREGUNTA RECHAZADA
            # ═══════════════════════════════════════════════════════
            if result == Result.REJECTED:
                return {
                    "status": "rejected",
                    "response": f"""❌ **Pregunta Rechazada**

**Razón**: {classification.get('reason', 'No cumple con los criterios médicos')}

{classification.get('suggestion', '')}"""
                }
            
            # ═══════════════════════════════════════════════════════
            # CASO 2: REFORMULACIÓN REQUERIDA
            # ═══════════════════════════════════════════════════════
            if result == Result.REFORMULATE:
                return {
                    "status": "reformulate",
                    "response": f"""💡 **Reformulación Sugerida**

**Razón**: {classification.get('reason', 'La pregunta es ambigua')}

{classification.get('suggestion', 'Reformula de manera más técnica y específica')}"""
                }
            
            # ═══════════════════════════════════════════════════════
            # CASO 3: PREGUNTA APROBADA
            # ═══════════════════════════════════════════════════════
            
            # Validar dominio (nunca debe ser None o undefined)
            domain = classification.get("domain")
            
            if not domain or domain == "undefined" or domain == "None":
                domain = "medicina general"
                print(f"⚠️ Domain no definido, usando fallback: {domain}")
            
            # Detectar comando especial
            special_command = classification.get("special_command")
            note_analysis = classification.get("note_analysis", False)
            
            # Si es análisis de nota médica (detección automática)
            if note_analysis and not special_command:
                special_command = "valoracion"  # Por defecto, valorar la nota
            
            # ═══════════════════════════════════════════════════════
            # DETECCIÓN DE AMPLITUD SEMÁNTICA (antes de consumir tokens)
            # ═══════════════════════════════════════════════════════
            # NO aplicar a comandos especiales (notas médicas, valoraciones)
            if not special_command and not note_analysis:
                es_amplia, reformulacion = evaluar_y_reformular(question, domain)
                
                if es_amplia:
                    return {
                        "status": "reformulate",
                        "domain": domain,
                        "confidence": classification.get("confidence", 0.80),
                        "response": reformulacion
                    }
            
            # Generar respuesta
            try:
                response = self.mistral.generate(
                    question=question,
                    domain=domain,
                    special_command=special_command
                )
                
                return {
                    "status": "success",
                    "domain": domain,
                    "confidence": classification.get("confidence", 0.80),
                    "special_command": special_command,
                    "response": response
                }
                
            except Exception as mistral_error:
                # Error específico de Mistral API
                print(f"❌ Error en Mistral API: {str(mistral_error)}")
                return {
                    "status": "error",
                    "domain": domain,
                    "response": f"""⚠️ **Error al Generar Respuesta**

Ocurrió un problema al comunicarse con el servicio de inteligencia artificial.

**Detalles técnicos**: {str(mistral_error)[:150]}

**Sugerencias**:
• Intenta reformular tu pregunta
• Espera unos minutos si hay sobrecarga del sistema
• Contacta al administrador si el problema persiste"""
                }
        
        except Exception as general_error:
            # Error general no esperado
            print(f"❌ Error crítico en Lisabella.ask(): {str(general_error)}")
            return {
                "status": "error",
                "response": f"""⚠️ **Error Crítico del Sistema**

Ha ocurrido un error inesperado al procesar tu pregunta.

**Detalles técnicos**: {str(general_error)[:150]}

Por favor, reporta este error al equipo de desarrollo incluyendo:
• La pregunta que intentaste hacer
• Este mensaje de error completo"""
            }
    
    # ═══════════════════════════════════════════════════════
    # MÉTODOS DE CHUNKING (NUEVO - Para evitar timeout)
    # ═══════════════════════════════════════════════════════
    
    def generate_standard_chunks(self, question, domain):
        """
        Genera respuesta estándar en 4 CHUNKS COMPLETOS.
        CADA CHUNK tiene calidad completa, no se reduce información.
        """
        sections = [
            {
                'title': '## 📖 Definición',
                'prompt': f"""Proporciona la DEFINICIÓN MÉDICA COMPLETA de: {question}

Incluye:
- Concepto fundamental
- Clasificación (si aplica)
- Terminología técnica precisa

Responde con rigor académico y cita fuentes al final.""",
                'max_tokens': 1200  # Espacio completo para definición detallada
            },
            {
                'title': '## 🔬 Detalles Clínicos',
                'prompt': f"""Sobre {question}, proporciona DETALLES CLÍNICOS COMPLETOS:

- Etiología y factores de riesgo
- Fisiopatología detallada
- Características diagnósticas clave
- Cuadro clínico típico

Usa tablas, listas y formato markdown. Cita fuentes.""",
                'max_tokens': 1500  # Más espacio para detalles complejos
            },
            {
                'title': '## 💊 Aplicación Práctica',
                'prompt': f"""Sobre {question}, explica la APLICACIÓN CLÍNICA COMPLETA:

- Diagnóstico (criterios, estudios)
- Tratamiento farmacológico (dosis específicas)
- Tratamiento no farmacológico
- Pronóstico y seguimiento

Sé específico con dosis, vías y duraciones. Cita guías clínicas.""",
                'max_tokens': 1500  # Espacio para detalles terapéuticos
            },
            {
                'title': '## ⚠️ Advertencias y Referencias',
                'prompt': f"""Sobre {question}, proporciona:

**ADVERTENCIAS IMPORTANTES:**
- Contraindicaciones absolutas
- Efectos adversos críticos
- Interacciones peligrosas
- Signos de alarma

**FUENTES BIBLIOGRÁFICAS:**
Lista las fuentes específicas usadas (Gray's Anatomy, Guyton, Harrison's, guías ESC/AHA, UpToDate, etc.)""",
                'max_tokens': 1000  # Advertencias y fuentes
            }
        ]
        
        for section in sections:
            try:
                # Generar contenido COMPLETO de la sección
                content = self.mistral.generate_chunk(
                    prompt=section['prompt'],
                    domain=domain,
                    max_tokens=section['max_tokens']
                )
                
                # Devolver título + contenido
                yield f"{section['title']}\n\n{content}"
                
            except Exception as e:
                print(f"❌ Error generando chunk: {str(e)}")
                yield f"{section['title']}\n\n⚠️ Error al generar esta sección."
    
    def generate_special_chunks(self, question, domain, special_command):
        """
        Genera respuesta para COMANDOS ESPECIALES en chunks.
        Mantiene la CALIDAD COMPLETA de cada sección.
        """
        
        if special_command == "revision_nota":
            sections = [
                ('## ✅ Componentes Presentes', 
                 f"Analiza QUÉ COMPONENTES SÍ ESTÁN en esta nota médica:\n\n{question}\n\nLista detallada con ejemplos específicos.", 
                 1200),
                ('## ❌ Componentes Faltantes', 
                 f"Identifica QUÉ FALTA en esta nota médica según JCI/COFEPRIS:\n\n{question}\n\nPrioriza por criticidad.", 
                 1200),
                ('## ⚠️ Errores Detectados', 
                 f"Identifica ERRORES de formato, dosis, abreviaturas en:\n\n{question}", 
                 1000),
                ('## 📋 Cumplimiento Legal', 
                 f"Evalúa cumplimiento de normas (COFEPRIS, JCI, Clínica Mayo) en:\n\n{question}", 
                 800),
                ('## 💡 Recomendaciones', 
                 f"Da recomendaciones PRIORITARIAS y opcionales para mejorar:\n\n{question}", 
                 1000)
            ]
        
        elif special_command == "correccion_nota":
            sections = [
                ('## ❌ Errores Detectados', 
                 f"Identifica TODOS los errores (formato, ortografía, dosis) en:\n\n{question}", 
                 1500),
                ('## ✅ Nota Corregida', 
                 f"Proporciona versión CORREGIDA COMPLETA de:\n\n{question}\n\nMarca cambios claramente.", 
                 2000),
                ('## 💡 Sugerencias Adicionales', 
                 f"Da sugerencias para MEJORAR la calidad de:\n\n{question}", 
                 800)
            ]
        
        elif special_command == "elaboracion_nota":
            # Para elaboración, generar secciones SOAP completas
            sections = [
                ('## DATOS Y SUBJETIVO (S)', 
                 f"Genera sección completa de DATOS DEL PACIENTE y SUBJETIVO para:\n\n{question}\n\nUsa formato profesional con todos los campos.", 
                 1200),
                ('## OBJETIVO (O)', 
                 f"Genera sección completa OBJETIVO (signos vitales, exploración física) para:\n\n{question}", 
                 1200),
                ('## ANÁLISIS (A)', 
                 f"Genera sección completa de ANÁLISIS (impresión diagnóstica, justificación) para:\n\n{question}", 
                 1000),
                ('## PLAN (P)', 
                 f"Genera sección completa de PLAN (estudios, tratamiento, pronóstico) para:\n\n{question}", 
                 1200)
            ]
        
        elif special_command == "valoracion":
            sections = [
                ('## 📋 Resumen del Caso', 
                 f"Resume el caso clínico en 3-4 líneas:\n\n{question}", 
                 600),
                ('## 🎯 Hipótesis Diagnósticas', 
                 f"Proporciona diagnóstico más probable y 3 diferenciales COMPLETOS con justificación para:\n\n{question}", 
                 1500),
                ('## 🔬 Estudios Sugeridos', 
                 f"Lista COMPLETA de laboratorios e imagenología prioritarios para:\n\n{question}", 
                 1000),
                ('## 💊 Abordaje Terapéutico', 
                 f"Plan terapéutico COMPLETO (medidas generales, fármacos con dosis, criterios de referencia) para:\n\n{question}", 
                 1500),
                ('## ⚠️ Signos de Alarma', 
                 f"Lista completa de signos de alarma y criterios de derivación urgente para:\n\n{question}", 
                 800)
            ]
        
        elif special_command == "study_mode":
            sections = [
                ('## 📚 Conceptos Fundamentales', 
                 f"Explica los CONCEPTOS BÁSICOS COMPLETOS de: {question}\n\nCon definiciones claras.", 
                 1200),
                ('## 🧠 Analogías y Memorización', 
                 f"Crea ANALOGÍAS DETALLADAS y técnicas de memorización para: {question}", 
                 1200),
                ('## 🔗 Correlación Clínica', 
                 f"Explica la APLICACIÓN CLÍNICA COMPLETA con casos prácticos de: {question}", 
                 1200),
                ('## 💡 Tips de Estudio', 
                 f"Proporciona estrategias COMPLETAS para estudiar efectivamente: {question}", 
                 800)
            ]
        
        else:
            # Fallback a estándar
            yield from self.generate_standard_chunks(question, domain)
            return
        
        # Generar cada sección
        for title, prompt, max_tok in sections:
            try:
                content = self.mistral.generate_chunk(
                    prompt=prompt,
                    domain=domain,
                    max_tokens=max_tok
                )
                yield f"{title}\n\n{content}"
            except Exception as e:
                print(f"❌ Error en chunk especial: {str(e)}")
                yield f"{title}\n\n⚠️ Error al generar esta sección."
    
    # ═══════════════════════════════════════════════════════
    # MÉTODOS LEGACY (mantener compatibilidad)
    # ═══════════════════════════════════════════════════════
    
    def analyze_note(self, note_text):
        """Analizar nota médica completa (método legacy, ahora se usa clasificación automática)"""
        try:
            return self.ask(note_text)
        except Exception as e:
            print(f"❌ Error al analizar nota: {str(e)}")
            return {
                "status": "error",
                "response": f"Error al analizar la nota médica: {str(e)[:150]}"
            }
    
    def get_help(self):
        """Obtener ayuda sobre comandos especiales"""
        return {
            "status": "success",
            "response": """## 🏥 **Comandos Especiales de Lisabella**

### 📋 **NOTAS MÉDICAS**

**1. REVISIÓN DE NOTA MÉDICA**
```
revisar nota médica [pegar nota aquí]
```
Evalúa completitud según estándares JCI, Clínica Mayo y COFEPRIS.

---

**2. CORRECCIÓN DE NOTA MÉDICA**
```
corregir nota médica [pegar nota aquí]
```
Identifica y corrige errores de formato, ortografía, dosis y abreviaturas.

---

**3. ELABORACIÓN DE NOTA MÉDICA**
```
elaborar nota médica [datos del paciente]
```
Genera plantilla SOAP completa con campos obligatorios.

---

**4. VALORACIÓN DE PACIENTE**
```
valoracion de paciente [caso clínico]
```
Orienta diagnóstico diferencial y abordaje terapéutico.

---

### 📚 **MODO ESTUDIO**

**APOYO EN ESTUDIO**
```
apoyo en estudio [tema médico]
```
Modo educativo con analogías, ejemplos clínicos y correlación práctica.

**Ejemplos:**
- "apoyo en estudio ciclo de Krebs"
- "apoyo en estudio anatomía del plexo braquial"
- "apoyo en estudio farmacología de betabloqueantes"

---

### 💡 **TIPS**

• Puedes hacer preguntas normales sin comandos
• Los comandos no distinguen mayúsculas/minúsculas
• Si detecta una nota médica completa, se activa valoración automática
"""
        }
    
    def cli(self):
        """Modo interactivo para pruebas locales"""
        print("\n🏥 Lisabella - Asistente Médico IA")
        print("=" * 60)
        print("Comandos disponibles:")
        print("  • Pregunta médica normal")
        print("  • 'revisar nota' + [nota médica]")
        print("  • 'corregir nota' + [nota médica]")
        print("  • 'elaborar nota' + [datos]")
        print("  • 'valoracion' + [caso clínico]")
        print("  • 'apoyo en estudio' + [tema]")
        print("  • 'ayuda' - ver todos los comandos")
        print("  • 'salir' - terminar")
        print("=" * 60 + "\n")
        
        while True:
            try:
                question = input("💬 Tu pregunta: ").strip()
                
                if question.lower() in ["salir", "exit", "quit"]:
                    print("✋ ¡Hasta luego!")
                    break
                
                if question.lower() in ["ayuda", "help", "comandos"]:
                    help_result = self.get_help()
                    print("\n" + "=" * 60)
                    print(help_result["response"])
                    print("=" * 60 + "\n")
                    continue
                
                if not question:
                    continue
                
                result = self.ask(question)
                
                print("\n" + "=" * 60)
                
                # Mostrar dominio solo en modo debug
                if result.get("special_command"):
                    print(f"🔧 Comando: {result['special_command']}")
                
                print(result["response"])
                print("=" * 60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n✋ Interrupción detectada. ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")


# ═══════════════════════════════════════════════════════
# TESTING (opcional, comentar en producción)
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    lisabella = Lisabella()
    lisabella.cli()
