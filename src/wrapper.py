import json
import os
import re
from enum import Enum

class Result(Enum):
    APPROVED = "APROBADA"
    REJECTED = "RECHAZADA"
    REFORMULATE = "REFORMULAR"

class Wrapper:
    def __init__(self):
        self.domains = self._load_json("data/domains.json")
        self.prohibited = self._load_json("data/prohibited.json")
        
    def _load_json(self, path):
        """Cargar archivo JSON con manejo de errores"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Archivo no encontrado: {path}")
            return {}
        except json.JSONDecodeError:
            print(f"⚠️ Error al decodificar JSON: {path}")
            return {}
    
    def classify(self, question):
        """
        Clasificar pregunta médica con comandos especiales
        - APPROVED: Pregunta válida y procesable
        - REJECTED: Contiene términos prohibidos o no médicos
        - REFORMULATE: Ambigua o demasiado vaga
        """
        
        if not question or len(question.strip()) < 3:
            return {
                "result": Result.REJECTED,
                "reason": "Pregunta vacía o demasiado corta"
            }
        
        q_lower = question.lower().strip()
        q_words = q_lower.split()
        
        # ═══════════════════════════════════════════════════════
        # NIVEL 0: Detectar COMANDOS ESPECIALES (prioridad máxima)
        # ═══════════════════════════════════════════════════════
        special_command = self._detect_special_command(question)
        
        if special_command:
            # Comandos de notas médicas (siempre aprobados)
            if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
                return {
                    "result": Result.APPROVED,
                    "domain": "análisis clínico",
                    "confidence": 0.95,
                    "special_command": special_command
                }
            
            # Comando "apoyo en estudio" - verificar keywords médicos
            elif special_command == "apoyo_estudio":
                domain_scores = self._get_domain_scores(q_lower)
                if domain_scores:
                    best_domain = max(domain_scores, key=domain_scores.get)
                    return {
                        "result": Result.APPROVED,
                        "domain": best_domain,
                        "confidence": 0.85,
                        "special_command": "study_mode"
                    }
                else:
                    return {
                        "result": Result.REJECTED,
                        "reason": "El modo 'apoyo en estudio' requiere un tema médico válido",
                        "suggestion": "Ejemplo: 'apoyo en estudio ciclo de Krebs' o 'apoyo en estudio anatomía del tórax'"
                    }
        
        # ═══════════════════════════════════════════════════════
        # NIVEL 1: Detectar notas médicas completas
        # ═══════════════════════════════════════════════════════
        if self._is_medical_note(question):
            return {
                "result": Result.APPROVED,
                "domain": "análisis clínico",
                "confidence": 0.95,
                "note_analysis": True
            }
        
        # ═══════════════════════════════════════════════════════
        # NIVEL 2: Rechazar términos prohibidos
        # ═══════════════════════════════════════════════════════
        prohibited_found = [term for term in self.prohibited.get("terms", []) if term in q_lower]
        if prohibited_found:
            return {
                "result": Result.REJECTED,
                "reason": f"Contiene términos no médicos: {', '.join(prohibited_found)}",
                "suggestion": "Lisabella solo responde preguntas de ciencias médicas"
            }
        
        # ═══════════════════════════════════════════════════════
        # NIVEL 3: Detectar preguntas ultra-cortas (1-2 palabras)
        # ═══════════════════════════════════════════════════════
        if len(q_words) <= 2:
            medical_term = self._extract_medical_term(q_lower)
            if medical_term:
                return {
                    "result": Result.REFORMULATE,
                    "reason": f"Término médico detectado: '{medical_term}', pero la pregunta es muy breve",
                    "suggestion": self._generate_term_suggestions(medical_term)
                }
            else:
                return {
                    "result": Result.REFORMULATE,
                    "reason": "Pregunta demasiado corta",
                    "suggestion": "Especifica qué deseas saber:\n• ¿Estructura anatómica?\n• ¿Función fisiológica?\n• ¿Tratamiento farmacológico?\n• ¿Diagnóstico diferencial?"
                }
        
        # ═══════════════════════════════════════════════════════
        # NIVEL 4: Buscar keywords médicas por dominio
        # ═══════════════════════════════════════════════════════
        domain_scores = self._get_domain_scores(q_lower)
        detected_keywords = self._get_detected_keywords(q_lower)
        
        # ═══════════════════════════════════════════════════════
        # NIVEL 5: Detectar patrones de preguntas válidas
        # ═══════════════════════════════════════════════════════
        valid_patterns = [
            r'\b(qué|que|cual|cuales|cuál|cuáles|como|cómo|donde|dónde|por qué|porque|por que)\b',
            r'\b(explique|explica|describe|detalla|detalle|menciona|lista|enumera)\b',
            r'\b(diferencia|comparación|comparacion|relación|relacion|asociación|asociacion)\b',
            r'\b(mecanismo|proceso|función|funcion|estructura|ubicación|ubicacion)\b',
            r'\b(causas|síntomas|sintomas|signos|diagnóstico|diagnostico|tratamiento)\b'
        ]
        
        has_valid_pattern = any(re.search(pattern, q_lower) for pattern in valid_patterns)
        
        # ═══════════════════════════════════════════════════════
        # DECISIÓN FINAL CON LÓGICA MEJORADA
        # ═══════════════════════════════════════════════════════
        
        total_keywords = sum(domain_scores.values())
        
        # REGLA CRÍTICA: Si tiene ≥3 keywords médicos, APROBAR sin importar la estructura
        if total_keywords >= 3:
            best_domain = max(domain_scores, key=domain_scores.get)
            confidence = min(0.92, 0.70 + (total_keywords * 0.06))
            return {
                "result": Result.APPROVED,
                "domain": best_domain,
                "confidence": round(confidence, 2)
            }
        
        # Si encontró keywords Y tiene patrón válido → APROBADA
        if domain_scores and has_valid_pattern:
            best_domain = max(domain_scores, key=domain_scores.get)
            confidence = min(0.95, 0.70 + (domain_scores[best_domain] * 0.08))
            return {
                "result": Result.APPROVED,
                "domain": best_domain,
                "confidence": round(confidence, 2)
            }
        
        # Si encontró keywords pero sin patrón claro → Aceptar con confianza media si tiene suficientes
        if domain_scores:
            best_domain = max(domain_scores, key=domain_scores.get)
            if domain_scores[best_domain] >= 2:
                return {
                    "result": Result.APPROVED,
                    "domain": best_domain,
                    "confidence": 0.75
                }
        
        # Si tiene patrón válido pero sin keywords → Reformular suave
        if has_valid_pattern:
            return {
                "result": Result.REFORMULATE,
                "reason": "Pregunta con estructura válida pero sin términos médicos específicos",
                "suggestion": "Agrega términos médicos específicos:\n• Nombres de órganos, tejidos o estructuras\n• Fármacos o grupos farmacológicos\n• Enfermedades o síndromes\n• Procesos bioquímicos o fisiológicos"
            }
        
        # ═══════════════════════════════════════════════════════
        # DEFAULT: REFORMULAR (pregunta ambigua)
        # ═══════════════════════════════════════════════════════
        return {
            "result": Result.REFORMULATE,
            "reason": "No se detectaron términos médicos específicos",
            "suggestion": """**Para obtener una respuesta precisa, reformula usando:**

• **Términos anatómicos**: estructura, ubicación, función de órganos
• **Términos farmacológicos**: mecanismo de acción, dosis, efectos adversos
• **Términos patológicos**: etiología, fisiopatología, diagnóstico
• **Términos clínicos**: síntomas, signos, tratamiento, pronóstico

**Ejemplo de pregunta bien formulada:**
"¿Cuál es el mecanismo de acción del losartán en hipertensión arterial?"""
        }
    
    # ═══════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES
    # ═══════════════════════════════════════════════════════
    
    def _detect_special_command(self, question):
        """Detecta comandos especiales para notas médicas y estudio"""
        q_lower = question.lower()
        
        special_commands = self.domains.get("special_commands", {})
        
        for command_type, triggers in special_commands.items():
            if any(trigger in q_lower for trigger in triggers):
                return command_type
        
        return None
    
    def _get_domain_scores(self, q_lower):
        """Calcula scores por dominio basado en keywords"""
        domain_scores = {}
        
        for domain, keywords in self.domains.get("keywords", {}).items():
            matches = sum(1 for kw in keywords if kw in q_lower)
            if matches > 0:
                domain_scores[domain] = matches
        
        # Búsqueda adicional en regiones anatómicas
        if "anatomical_regions" in self.domains:
            anatomical_matches = sum(1 for term in self.domains["anatomical_regions"] if term in q_lower)
            if anatomical_matches > 0:
                domain_scores["anatomía"] = domain_scores.get("anatomía", 0) + anatomical_matches
        
        # Detectar fármacos específicos
        detected_drugs = self._detect_specific_drugs(q_lower)
        if detected_drugs:
            domain_scores["farmacología"] = domain_scores.get("farmacología", 0) + len(detected_drugs)
        
        return domain_scores
    
    def _get_detected_keywords(self, q_lower):
        """Obtiene lista de keywords detectados"""
        detected = []
        
        for keywords in self.domains.get("keywords", {}).values():
            for kw in keywords:
                if kw in q_lower and kw not in detected:
                    detected.append(kw)
        
        return detected[:5]  # Máximo 5 para no saturar
    
    def _detect_specific_drugs(self, text):
        """Detectar fármacos específicos comunes"""
        common_drugs = [
            'espironolactona', 'metformina', 'losartán', 'losartan', 'enalapril',
            'omeprazol', 'ibuprofeno', 'paracetamol', 'aspirina', 'atorvastatina',
            'simvastatina', 'amlodipino', 'metoprolol', 'atenolol', 'furosemida',
            'hidroclorotiazida', 'levotiroxina', 'insulina', 'warfarina', 'heparina',
            'amoxicilina', 'azitromicina', 'ciprofloxacino', 'diclofenaco', 'vancomicina'
        ]
        
        detected = []
        for drug in common_drugs:
            if drug in text:
                detected.append(drug)
        
        return detected
    
    def _is_medical_note(self, text):
        """Detectar si el texto es una nota médica completa"""
        indicators = [
            r'\bfecha[:\s]',
            r'\bmotivo de consulta[:\s]',
            r'\bexploración física[:\s]',
            r'\bimpresión diagnóstica[:\s]',
            r'\bplan[:\s]',
            r'\bedad[:\s]\s*\d+',
            r'\bvo\b.*\bcada\b',
            r'\b\d+\s*mg\b',
            r'\b\d+\s*mmhg\b',
            r'\bfc[:\s]\s*\d+',
            r'\bta[:\s]\s*\d+/\d+'
        ]
        
        matches = sum(1 for ind in indicators if re.search(ind, text.lower()))
        return matches >= 3
    
    def _extract_medical_term(self, text):
        """Extraer término médico principal de la pregunta"""
        medical_terms = self.domains.get("anatomical_regions", [])
        
        for term in medical_terms:
            if term in text:
                return term
        
        return None
    
    def _generate_term_suggestions(self, term):
        """Generar sugerencias para un término médico específico"""
        return f"""**Preguntas sugeridas sobre '{term}':**

• ¿Cuál es la **estructura anatómica** del {term}?
• ¿Cuál es la **función fisiológica** del {term}?
• ¿Dónde se **ubica** el {term}?
• ¿Qué **irrigación** tiene el {term}?
• ¿Qué **patologías** afectan al {term}?"""
    
    def get_stats(self):
        """Obtener estadísticas del wrapper (para debugging)"""
        return {
            "domains": len(self.domains.get("domains", [])),
            "keywords_total": sum(len(kw) for kw in self.domains.get("keywords", {}).values()),
            "anatomical_regions": len(self.domains.get("anatomical_regions", [])),
            "prohibited_terms": len(self.prohibited.get("terms", []))
        }
