"""
Router Híbrido Inteligente
Decide cuándo usar Mistral vs Groq según dominio y complejidad
"""

from src.config import MISTRAL_DOMAINS, GROQ_USE_SUBSECTIONS
from src.mistral_client import MistralClient
from src.groq_client import GroqClient
from src.subsection_generator import SubsectionGenerator
from src.quality_validator import validate_response
from src.prompt_examples import get_example_for_domain

class HybridRouter:
    """
    Enrutador inteligente que selecciona el mejor proveedor según:
    - Dominio médico
    - Complejidad de la pregunta
    - Comandos especiales
    """
    
    def __init__(self):
        self.mistral = MistralClient()
        self.groq = GroqClient()
        self.subsection_generator = SubsectionGenerator(self.groq)
    
    def generate(self, question: str, domain: str, special_command: str = None) -> dict:
        """
        Genera respuesta usando el proveedor óptimo
        
        Args:
            question: Pregunta del usuario
            domain: Dominio médico clasificado
            special_command: Comando especial si aplica
            
        Returns:
            dict: {
                "response": str,
                "provider": str,
                "method": str,
                "quality_score": float,
                "word_count": int
            }
        """
        
        # ═══════════════════════════════════════════════════════
        # DECISIÓN 1: Comandos especiales → Groq directo
        # ═══════════════════════════════════════════════════════
        if special_command:
            print(f"🎯 Comando especial detectado: {special_command} → Groq directo")
            response = self.groq.generate(question, domain, special_command)
            return {
                "response": response,
                "provider": "Groq",
                "method": "direct",
                "special_command": special_command,
                "word_count": len(response.split())
            }
        
        # ═══════════════════════════════════════════════════════
        # DECISIÓN 2: Ciencias básicas → Mistral (calidad máxima)
        # ═══════════════════════════════════════════════════════
        if self._should_use_mistral(domain):
            print(f"🔬 Ciencias básicas ({domain}) → Mistral (calidad máxima)")
            return self._generate_with_mistral(question, domain)
        
        # ═══════════════════════════════════════════════════════
        # DECISIÓN 3: Otras preguntas → Groq con subsecciones
        # ═══════════════════════════════════════════════════════
        else:
            print(f"⚡ Pregunta clínica ({domain}) → Groq con subsecciones")
            return self._generate_with_groq_subsections(question, domain)
    
    def _should_use_mistral(self, domain: str) -> bool:
        """
        Decide si usar Mistral según dominio
        
        Mistral para:
        - Anatomía, Histología, Fisiología, Bioquímica, Farmacología, Patología
        - Cualquier tema de ciencias básicas
        
        Returns:
            bool: True si debe usar Mistral
        """
        domain_lower = domain.lower()
        
        # Comparar con lista de dominios configurados
        for mistral_domain in MISTRAL_DOMAINS:
            if mistral_domain in domain_lower:
                return True
        
        return False
    
    def _generate_with_mistral(self, question: str, domain: str) -> dict:
        """
        Genera respuesta con Mistral optimizado
        
        Estrategia:
        1. Usar prompt mejorado con ejemplo de calidad
        2. Timeout de 28 segundos (antes del corte)
        3. Validar calidad
        4. Si falla, intentar con Groq subsecciones como fallback
        """
        
        try:
            # Obtener ejemplo de calidad para este dominio
            quality_example = get_example_for_domain(domain)
            
            # Generar con Mistral (usa el cliente existente)
            # El cliente ya tiene el prompt optimizado
            response = self.mistral.generate(
                question=question,
                domain=domain,
                special_command=None
            )
            
            # Validar calidad
            validation = validate_response(response, domain)
            
            return {
                "response": response,
                "provider": "Mistral",
                "method": "direct",
                "quality_score": validation["score"],
                "word_count": len(response.split()),
                "validation": validation
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Si Mistral falla (timeout, rate limit), usar Groq como fallback
            if "timeout" in error_msg or "429" in error_msg or "rate" in error_msg:
                print(f"⚠️  Mistral no disponible, usando Groq como fallback")
                return self._generate_with_groq_subsections(question, domain)
            else:
                # Error inesperado
                raise e
    
    def _generate_with_groq_subsections(self, question: str, domain: str) -> dict:
        """
        Genera respuesta con Groq usando subsecciones
        
        Estrategia:
        1. Dividir en 8 subsecciones
        2. Generar cada una independientemente
        3. Ensamblar respuesta completa
        4. Validar calidad
        5. Si falla validación, regenerar secciones débiles
        """
        
        if not GROQ_USE_SUBSECTIONS:
            # Modo subsecciones desactivado, usar Groq directo
            response = self.groq.generate(question, domain, None)
            validation = validate_response(response, domain)
            
            return {
                "response": response,
                "provider": "Groq",
                "method": "direct",
                "quality_score": validation["score"],
                "word_count": len(response.split()),
                "validation": validation
            }
        
        # Generar por subsecciones
        response = self.subsection_generator.generate_by_subsections(question, domain)
        
        # Validar calidad
        validation = validate_response(response, domain)
        
        # Si la calidad es baja, intentar mejorar
        if validation["score"] < 70:
            print(f"⚠️  Calidad baja ({validation['score']}/100), intentando mejorar...")
            response = self._improve_response(response, validation, question, domain)
            # Re-validar
            validation = validate_response(response, domain)
        
        return {
            "response": response,
            "provider": "Groq",
            "method": "subsections",
            "quality_score": validation["score"],
            "word_count": len(response.split()),
            "validation": validation
        }
    
    def _improve_response(self, response: str, validation: dict, question: str, domain: str) -> str:
        """
        Mejora una respuesta que no pasó validación de calidad
        
        Estrategia:
        1. Identificar qué falla (longitud, tablas, números)
        2. Generar contenido adicional específico
        3. Insertar en la respuesta original
        """
        
        issues = validation["issues"]
        
        if not validation["passed_checks"].get("tables", True):
            # Faltan tablas, generar una tabla específica
            print("📊 Agregando tabla con datos cuantitativos...")
            table_prompt = f"""Para el tema "{question}" ({domain}), 
genera UNA TABLA en formato markdown con datos cuantitativos.

Debe tener:
- Mínimo 5 filas de datos
- Columnas con valores numéricos y unidades
- Datos reales y verificables

Responde SOLO con la tabla markdown, sin texto adicional."""

            table = self.groq.generate(table_prompt, domain, None)
            
            # Insertar tabla en la sección "Detalles Clave"
            if "## Detalles Clave" in response:
                response = response.replace(
                    "## Detalles Clave",
                    f"## Detalles Clave\n\n{table}"
                )
        
        if not validation["passed_checks"].get("length", True):
            # Respuesta muy corta, expandir
            print("📝 Expandiendo contenido...")
            expansion_prompt = f"""La siguiente respuesta sobre "{question}" es demasiado corta.

Agrega 300 palabras más de contenido técnico con:
- Datos cuantitativos específicos
- Detalles adicionales relevantes
- Correlación clínica

Contenido actual:
{response[:500]}...

Escribe SOLO el contenido adicional a agregar (300+ palabras):"""

            additional_content = self.groq.generate(expansion_prompt, domain, None)
            
            # Insertar antes de "Fuentes"
            if "## Fuentes" in response:
                response = response.replace(
                    "## Fuentes",
                    f"{additional_content}\n\n## Fuentes"
                )
            else:
                response += f"\n\n{additional_content}"
        
        return response
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas de uso"""
        return {
            "mistral_domains": MISTRAL_DOMAINS,
            "groq_subsections_enabled": GROQ_USE_SUBSECTIONS,
            "mistral_available": self.mistral is not None,
            "groq_available": self.groq is not None
        }
