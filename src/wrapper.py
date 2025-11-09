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
            if special_command in ["revision_nota", "elaboracion_nota", "valoracion", "calculo_dosis"]:
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
        
        # REGLA CRÍTICA 1: Detectar términos técnicos específicos de alta especialización
        technical_terms = [
            "electrocardiográfic", "electrocardiografic", "derivaciones", "fibrinólisis", "fibrinolisis",
            "angioplastia", "biomarcadores", "fisiopatología", "fisiopatologia", "farmacocinética",
            "farmacocinetica", "farmacodinámica", "farmacodinamica", "mecanismo de acción",
            "cascada", "isquemia", "oclusión", "oclusion", "ligamentos", "irrigación", "irrigacion",
            "inervación", "inervacion", "drenaje linfático", "drenaje linfatico", "ventanas temporales",
            "criterios diagnósticos", "criterios diagnosticos", "diagnóstico diferencial",
            "diagnostico diferencial", "signos de alarma", "contraindicaciones"
        ]
        
        has_technical_term = any(term in q_lower for term in technical_terms)
        
        if has_technical_term and domain_scores:
            best_domain = max(domain_scores, key=domain_scores.get)
            return {
                "result": Result.APPROVED,
                "domain": best_domain,
                "confidence": 0.88
            }
        
        # REGLA CRÍTICA 2: Si tiene ≥3 keywords médicos (o patrones técnicos), APROBAR sin importar la estructura
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
        
        # ✅ NUEVA REGLA: Si tiene patrones técnicos detectados (macroscópica, microscópica, etc.)
        # aunque no tenga keywords exactos, APROBAR si tiene ≥2 patrones técnicos
        technical_patterns_detected = self._detect_technical_patterns(q_lower)
        if technical_patterns_detected >= 2:
            inferred_domain = self._infer_domain_from_context(q_lower)
            if inferred_domain:
                return {
                    "result": Result.APPROVED,
                    "domain": inferred_domain,
                    "confidence": 0.80  # Buena confianza por patrones técnicos
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
        
        # ✅ NUEVA REGLA: Si tiene 1 patrón técnico + órgano anatómico, APROBAR
        if technical_patterns_detected >= 1:
            # Verificar si menciona órgano anatómico
            organos = ["corazón", "corazon", "pulmón", "pulmon", "riñón", "riñon", 
                      "hígado", "higado", "estómago", "estomago", "cerebro"]
            if any(organo in q_lower for organo in organos):
                inferred_domain = self._infer_domain_from_context(q_lower) or "anatomía"
                return {
                    "result": Result.APPROVED,
                    "domain": inferred_domain,
                    "confidence": 0.75
                }
        
        # Si tiene patrón válido pero sin keywords → Reformular suave
        if has_valid_pattern:
            return {
                "result": Result.REFORMULATE,
                "reason": "Pregunta con estructura válida pero poco específica",
                "suggestion": self._generate_smart_suggestions()
            }
        
        # ═══════════════════════════════════════════════════════
        # DEFAULT: REFORMULAR (pregunta ambigua)
        # ═══════════════════════════════════════════════════════
        return {
            "result": Result.REFORMULATE,
            "reason": "Pregunta demasiado general",
            "suggestion": self._generate_smart_suggestions()
        }
    
    # ═══════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES
    # ═══════════════════════════════════════════════════════
    
    def _detect_special_command(self, question):
        """Detecta comandos especiales para notas médicas y estudio"""
        q_lower = question.lower()
        
        # Comandos unificados y nuevos
        command_patterns = {
            "revision_nota": [
                "revisar nota", "corregir nota", "auditar nota", "evaluar nota",
                "analizar nota", "revision de nota", "correccion de nota"
            ],
            "elaboracion_nota": [
                "elaborar nota", "crear nota", "generar nota", "hacer nota",
                "redactar nota", "nota medica"
            ],
            "valoracion": [
                "valoracion de paciente", "valoración paciente", "evaluar paciente",
                "abordaje de paciente", "orientacion diagnostica", "orientación diagnóstica"
            ],
            "calculo_dosis": [
                "calcular dosis", "calculo de dosis", "cálculo de dosis",
                "dosis por peso", "dosis por edad", "ajuste de dosis",
                "dosificacion", "dosificación"
            ],
            "apoyo_estudio": [
                "apoyo en estudio", "ayuda para estudiar", "modo estudio"
            ]
        }
        
        for command_type, triggers in command_patterns.items():
            if any(trigger in q_lower for trigger in triggers):
                return command_type
        
        return None
    
    def _get_domain_scores(self, q_lower):
        """Calcula scores por dominio basado en keywords Y patrones técnicos médicos"""
        domain_scores = {}
        
        # ═══════════════════════════════════════════════════════
        # DETECCIÓN 1: Keywords exactos (sistema original)
        # ═══════════════════════════════════════════════════════
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
        
        # ═══════════════════════════════════════════════════════
        # DETECCIÓN 2: Patrones técnicos médicos (sin listas exhaustivas)
        # ═══════════════════════════════════════════════════════
        technical_patterns_score = self._detect_technical_patterns(q_lower)
        if technical_patterns_score:
            # Asignar a dominio más probable según contexto
            best_domain = self._infer_domain_from_context(q_lower)
            if best_domain:
                domain_scores[best_domain] = domain_scores.get(best_domain, 0) + technical_patterns_score
        
        return domain_scores
    
    def _detect_technical_patterns(self, q_lower):
        """
        Detecta términos técnicos médicos por PATRONES, no solo listas.
        Esto permite reconocer términos como 'macroscópica', 'microscópica', etc.
        """
        score = 0
        
        # Patrones de sufijos médicos técnicos
        medical_suffixes = [
            r'\b\w*(scópica|scopica|scópico|scopico)\b',  # macroscópica, microscópica
            r'\b\w*(logía|logia|logías|logias)\b',       # anatomía, fisiología, patología
            r'\b\w*(patía|patia|patías|patias)\b',       # miocardiopatía, neuropatía
            r'\b\w*(emia|emias)\b',                      # anemia, hipoglucemia
            r'\b\w*(itis|itis)\b',                       # gastritis, hepatitis
            r'\b\w*(osis|osis)\b',                       # cirrosis, tuberculosis
            r'\b\w*(plásia|plasia|plásias|plasias)\b',  # displasia, hiperplasia
            r'\b\w*(tropía|tropia|tropías|tropias)\b',  # hipertrofia, atrofia
        ]
        
        for pattern in medical_suffixes:
            if re.search(pattern, q_lower):
                score += 1
        
        # Patrones de términos técnicos compuestos
        technical_compounds = [
            r'\b(irrigación|irrigacion|inervación|inervacion)\b',
            r'\b(topografía|topografia|relación|relacion)\s+anatómica',
            r'\b(estructura|composición|composicion)\s+(anatómica|anatomica|histológica|histologica)',
            r'\b(mecanismo|fisiopatología|fisiopatologia|fisiopatológico|fisiopatologico)\b',
            r'\b(farmacocinética|farmacocinetica|farmacodinámica|farmacodinamica)\b',
            r'\b(diagnóstico|diagnostico)\s+diferencial',
            r'\b(criterios|parámetros|parametros)\s+diagnósticos',
        ]
        
        for pattern in technical_compounds:
            if re.search(pattern, q_lower):
                score += 1
        
        # Patrones de términos anatómicos específicos
        anatomical_terms = [
            r'\b(cámara|camara|válvula|valvula|ventrículo|ventriculo|aurícula|auricula)\b',
            r'\b(arteria|vena|nervio|plexo|ganglio|músculo|musculo)\b',
            r'\b(lóbulo|lobulo|segmento|fascia|ligamento|tendón|tendon)\b',
            r'\b(órgano|organo|sistema|aparato)\s+\w+',  # "órgano cardiaco", "sistema cardiovascular"
        ]
        
        for pattern in anatomical_terms:
            if re.search(pattern, q_lower):
                score += 1
                # Si tiene términos anatómicos, es probablemente anatomía
                if "anatomía" not in q_lower and "anatomia" not in q_lower:
                    score += 0.5  # Bonus por términos anatómicos sin mencionar "anatomía"
        
        return int(score)
    
    def _infer_domain_from_context(self, q_lower):
        """
        Infiere el dominio más probable basado en contexto y patrones,
        no solo keywords exactos.
        """
        # Detectar contexto por palabras clave de dominio
        domain_indicators = {
            "anatomía": [
                "anatomía", "anatomia", "anatómica", "anatomica", "anatómico", "anatomico",
                "estructura", "ubicación", "ubicacion", "topografía", "topografia",
                "macroscópica", "macroscopica", "microscópica", "microscopica",
                "irrigación", "irrigacion", "inervación", "inervacion", "relación", "relacion"
            ],
            "fisiología": [
                "fisiología", "fisiologia", "fisiológica", "fisiologica", "fisiológico", "fisiologico",
                "función", "funcion", "mecanismo", "proceso", "regulación", "regulacion",
                "homeostasis", "fisiopatología", "fisiopatologia"
            ],
            "farmacología": [
                "farmacología", "farmacologia", "fármaco", "farmaco", "medicamento",
                "dosis", "farmacocinética", "farmacocinetica", "farmacodinámica", "farmacodinamica",
                "mecanismo de acción", "efectos adversos", "contraindicaciones"
            ],
            "patología": [
                "patología", "patologia", "enfermedad", "etiología", "etiologia",
                "fisiopatología", "fisiopatologia", "diagnóstico", "diagnostico",
                "cuadro clínico", "síntomas", "sintomas", "signos"
            ]
        }
        
        for domain, indicators in domain_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in q_lower)
            if matches > 0:
                return domain
        
        # Si no hay indicadores claros pero tiene términos técnicos, asumir anatomía por defecto
        # (es el dominio más común en preguntas médicas)
        if re.search(r'\b(corazón|corazon|pulmón|pulmon|riñón|riñon|hígado|higado|estómago|estomago|cerebro)\b', q_lower):
            return "anatomía"
        
        return None
    
    def _get_detected_keywords(self, q_lower):
        """Obtiene lista de keywords detectados"""
        detected = []
        
        for keywords in self.domains.get("keywords", {}).values():
            for kw in keywords:
                if kw in q_lower and kw not in detected:
                    detected.append(kw)
        
        return detected[:5]
    
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
        return f"""Preguntas sugeridas sobre '{term}':

• ¿Cuál es la estructura anatómica del {term}?
• ¿Cuál es la función fisiológica del {term}?
• ¿Dónde se ubica el {term}?
• ¿Qué irrigación tiene el {term}?
• ¿Qué patologías afectan al {term}?"""
    
    def _generate_smart_suggestions(self):
        """Genera sugerencias inteligentes con ejemplos variados"""
        return """Usa lenguaje médico más específico.

Ejemplos bien formulados:

ANATOMÍA:
"Describe la estructura anatómica de pleura y pulmones, incluyendo irrigación arterial y venosa"

FARMACOLOGÍA:
"¿Cuál es el mecanismo de acción del losartán en hipertensión arterial y su dosis usual?"

FISIOLOGÍA:
"Explica la ley de los grandes números aplicada al riesgo cardiovascular en poblaciones"

PATOLOGÍA:
"¿Cuáles son los criterios diagnósticos de SIRS y su relación con sepsis según Sepsis-3?"

Tip: Entre más técnica y detallada tu pregunta, mejor responde Lisabella."""
    
    def get_stats(self):
        """Obtener estadísticas del wrapper (para debugging)"""
        return {
            "domains": len(self.domains.get("domains", [])),
            "keywords_total": sum(len(kw) for kw in self.domains.get("keywords", {}).values()),
            "anatomical_regions": len(self.domains.get("anatomical_regions", [])),
            "prohibited_terms": len(self.prohibited.get("terms", []))
        }
