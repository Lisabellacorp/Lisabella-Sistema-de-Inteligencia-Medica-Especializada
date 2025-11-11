"""
Generador de respuestas por subsecciones
Divide preguntas complejas en partes manejables para Groq
"""

import re
from typing import List, Dict
from src.config import (
    GROQ_SUBSECTIONS_COUNT,
    GROQ_MIN_WORDS_PER_SECTION
)

class SubsectionGenerator:
    """Genera respuestas complejas dividiéndolas en subsecciones"""
    
    def __init__(self, groq_client):
        self.groq = groq_client
        self.default_subsection_count = GROQ_SUBSECTIONS_COUNT
        self.min_words_per_section = GROQ_MIN_WORDS_PER_SECTION
    
    def generate_by_subsections(self, question: str, domain: str) -> str:
        """
        Genera respuesta completa por subsecciones
        
        Args:
            question: Pregunta del usuario
            domain: Dominio médico
            
        Returns:
            str: Respuesta completa ensamblada
        """
        print(f"🔧 Generando por subsecciones - Dominio: {domain}")
        
        # Paso 1: Generar esqueleto (estructura)
        skeleton = self._generate_skeleton(question, domain)
        print(f"📋 Esqueleto generado: {len(skeleton)} subsecciones")
        
        # Paso 2: Generar cada subsección
        sections = []
        for i, section_info in enumerate(skeleton, 1):
            print(f"✍️  Generando subsección {i}/{len(skeleton)}: {section_info['title']}")
            
            section_content = self._generate_section(
                question=question,
                domain=domain,
                section_info=section_info,
                section_number=i,
                total_sections=len(skeleton),
                previous_content="\n\n".join(sections) if sections else None
            )
            
            sections.append(section_content)
        
        # Paso 3: Ensamblar respuesta completa
        full_response = "\n\n".join(sections)
        
        print(f"✅ Respuesta completa: {len(full_response.split())} palabras")
        return full_response
    
    def _generate_skeleton(self, question: str, domain: str) -> List[Dict]:
        """
        Genera estructura de subsecciones para la pregunta
        
        Returns:
            List[Dict]: [
                {"title": "## Definición", "min_words": 200, "requirements": [...]},
                ...
            ]
        """
        
        # Prompt para generar esqueleto
        skeleton_prompt = f"""Eres un planificador de contenido médico.

Para la pregunta: "{question}" (dominio: {domain})

Genera SOLO una lista de {self.default_subsection_count} títulos de subsecciones (formato markdown ##).

ESTRUCTURA OBLIGATORIA:
1. ## Definición
2. ## Detalles Clave (debe tener subtemas ###)
3-{self.default_subsection_count-2}. [Subsecciones específicas del tema]
{self.default_subsection_count}. ## Fuentes

Responde SOLO con los títulos en formato markdown, uno por línea.
NO escribas contenido, SOLO los títulos."""

        try:
            skeleton_text = self.groq.generate(
                question=skeleton_prompt,
                domain=domain,
                special_command=None
            )
            
            # Parsear títulos de secciones
            section_titles = re.findall(r'^##\s+(.+)$', skeleton_text, re.MULTILINE)
            
            if not section_titles or len(section_titles) < 4:
                # Fallback: estructura estándar
                print("⚠️  Usando estructura estándar (fallback)")
                section_titles = self._get_standard_structure(domain)
            
            # Convertir a lista de dicts con metadata
            skeleton = []
            for i, title in enumerate(section_titles):
                skeleton.append({
                    "title": f"## {title}",
                    "min_words": self._get_min_words_for_section(title, i, len(section_titles)),
                    "requirements": self._get_requirements_for_section(title)
                })
            
            return skeleton
            
        except Exception as e:
            print(f"❌ Error generando esqueleto: {str(e)}")
            # Fallback a estructura estándar
            return self._get_standard_structure_with_metadata(domain)
    
    def _generate_section(
        self,
        question: str,
        domain: str,
        section_info: Dict,
        section_number: int,
        total_sections: int,
        previous_content: str = None
    ) -> str:
        """
        Genera una subsección específica
        
        Args:
            question: Pregunta original
            domain: Dominio médico
            section_info: Dict con title, min_words, requirements
            section_number: Número de sección actual
            total_sections: Total de secciones
            previous_content: Contenido previo (para evitar repetición)
            
        Returns:
            str: Contenido de la subsección
        """
        
        # Construir prompt enfocado para esta sección
        section_prompt = f"""Desarrolla EXCLUSIVAMENTE la subsección: {section_info['title']}

Para la pregunta: "{question}" (dominio: {domain})

⚠️ RESTRICCIONES CRÍTICAS:
- Escribe SOLO sobre "{section_info['title']}"
- Mínimo {section_info['min_words']} palabras
- NO escribas introducción general
- NO escribas conclusión
- NO menciones "en resumen" o "para finalizar"
- NO repitas información de secciones anteriores

✅ REQUISITOS OBLIGATORIOS:
{self._format_requirements(section_info['requirements'])}

📊 PROGRESO:
- Esta es la subsección {section_number} de {total_sections}
- Palabras objetivo para esta sección: {section_info['min_words']}+

"""
        
        # Si hay contenido previo, indicar qué NO repetir
        if previous_content:
            # Extraer títulos previos
            previous_titles = re.findall(r'^##\s+(.+)$', previous_content, re.MULTILINE)
            if previous_titles:
                section_prompt += f"\n🚫 Ya se cubrieron: {', '.join(previous_titles)}\nNO repitas esa información.\n"
        
        section_prompt += f"\nComienza DIRECTAMENTE con el contenido de {section_info['title']}:"
        
        # Generar contenido
        content = self.groq.generate(
            question=section_prompt,
            domain=domain,
            special_command=None
        )
        
        return content
    
    def _get_min_words_for_section(self, title: str, position: int, total: int) -> int:
        """Calcula palabras mínimas según tipo de sección"""
        title_lower = title.lower()
        
        # Sección de definición (corta pero precisa)
        if "definición" in title_lower or "definicion" in title_lower:
            return 200
        
        # Detalles clave (más extensa)
        elif "detalles" in title_lower or "detalle" in title_lower:
            return 400
        
        # Fuentes (corta)
        elif "fuentes" in title_lower or "referencias" in title_lower or "bibliograf" in title_lower:
            return 100
        
        # Advertencias
        elif "advertencias" in title_lower or "precauciones" in title_lower:
            return 250
        
        # Secciones intermedias (contenido sustancial)
        else:
            return self.min_words_per_section
    
    def _get_requirements_for_section(self, title: str) -> List[str]:
        """Define requisitos específicos según tipo de sección"""
        title_lower = title.lower()
        
        if "definición" in title_lower or "definicion" in title_lower:
            return [
                "Concepto técnico completo",
                "Terminología médica precisa",
                "Clasificación si aplica"
            ]
        
        elif "detalles" in title_lower:
            return [
                "Mínimo 1 tabla con datos cuantitativos",
                "Valores numéricos con unidades (μm, %, mg/dL)",
                "Subsecciones numeradas (###)",
                "Datos de recuentos, tamaños, porcentajes"
            ]
        
        elif "advertencias" in title_lower:
            return [
                "Valores normales y rangos",
                "Patologías asociadas principales",
                "Complicaciones relevantes",
                "Técnicas diagnósticas"
            ]
        
        elif "fuentes" in title_lower:
            return [
                "Mínimo 3 referencias específicas",
                "Incluir edición y capítulo",
                "Formato: 'Libro (Xª ed.). Chapter Y: Título'"
            ]
        
        else:
            return [
                "Desarrollo exhaustivo del subtema",
                "Datos cuantitativos cuando sea posible",
                "Correlación clínica"
            ]
    
    def _format_requirements(self, requirements: List[str]) -> str:
        """Formatea lista de requisitos para prompt"""
        return "\n".join([f"□ {req}" for req in requirements])
    
    def _get_standard_structure(self, domain: str) -> List[str]:
        """Estructura estándar de fallback"""
        return [
            "Definición",
            "Composición y Clasificación",
            "Estructura Detallada",
            "Características Específicas",
            "Función y Fisiología",
            "Valores Normales",
            "Advertencias y Patologías",
            "Fuentes"
        ]
    
    def _get_standard_structure_with_metadata(self, domain: str) -> List[Dict]:
        """Estructura estándar con metadata completa"""
        titles = self._get_standard_structure(domain)
        return [
            {
                "title": f"## {title}",
                "min_words": self._get_min_words_for_section(title, i, len(titles)),
                "requirements": self._get_requirements_for_section(title)
            }
            for i, title in enumerate(titles)
        ]
