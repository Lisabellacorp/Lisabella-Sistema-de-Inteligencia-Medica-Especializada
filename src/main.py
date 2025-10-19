import sys
sys.path.insert(0, '/home/ray/lisabella')

from src.wrapper import Wrapper, Result
from src.mistral import MistralClient

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
    
    def analyze_note(self, note_text):
        """Analizar nota médica completa (método legacy, ahora se usa clasificación automática)"""
        
        try:
            # Usar el flujo normal de ask() que detecta notas automáticamente
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
    
    # Modo CLI interactivo
    lisabella.cli()
