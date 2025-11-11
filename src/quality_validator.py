"""
Validador de calidad de respuestas médicas
Verifica longitud, tablas, datos cuantitativos y referencias
"""

import re
from src.config import (
    VALIDATE_MIN_WORDS,
    VALIDATE_TABLES,
    VALIDATE_NUMBERS,
    VALIDATE_REFERENCES
)

class QualityValidator:
    """Valida que las respuestas cumplan estándares de calidad profesional"""
    
    def __init__(self):
        self.min_words = VALIDATE_MIN_WORDS
        self.check_tables = VALIDATE_TABLES
        self.check_numbers = VALIDATE_NUMBERS
        self.check_references = VALIDATE_REFERENCES
    
    def validate(self, text, domain=None):
        """
        Valida una respuesta completa
        
        Returns:
            dict: {
                "valid": bool,
                "score": float (0-100),
                "issues": list,
                "passed_checks": dict
            }
        """
        checks = {
            "length": self._check_length(text),
            "tables": self._check_tables(text) if self.check_tables else {"passed": True, "score": 100},
            "numbers": self._check_numbers(text) if self.check_numbers else {"passed": True, "score": 100},
            "structure": self._check_structure(text),
            "references": self._check_references(text) if self.check_references else {"passed": True, "score": 100}
        }
        
        # Calcular score total
        scores = [check["score"] for check in checks.values()]
        total_score = sum(scores) / len(scores)
        
        # Recopilar issues
        issues = []
        for check_name, result in checks.items():
            if not result["passed"]:
                issues.append(result.get("message", f"Fallo en {check_name}"))
        
        return {
            "valid": all(check["passed"] for check in checks.values()),
            "score": round(total_score, 1),
            "issues": issues,
            "passed_checks": {k: v["passed"] for k, v in checks.items()},
            "details": checks
        }
    
    def _check_length(self, text):
        """Verifica longitud mínima en palabras"""
        word_count = len(text.split())
        passed = word_count >= self.min_words
        
        return {
            "passed": passed,
            "score": min(100, (word_count / self.min_words) * 100),
            "word_count": word_count,
            "min_required": self.min_words,
            "message": f"Longitud insuficiente: {word_count}/{self.min_words} palabras" if not passed else "✓ Longitud adecuada"
        }
    
    def _check_tables(self, text):
        """Verifica presencia y calidad de tablas markdown"""
        # Detectar tablas markdown (formato: | col1 | col2 |)
        table_pattern = r'\|[^\n]+\|[\s]*\n\|[-:\s|]+\|[\s]*\n(?:\|[^\n]+\|[\s]*\n)+'
        tables = re.findall(table_pattern, text)
        
        table_count = len(tables)
        
        if table_count == 0:
            return {
                "passed": False,
                "score": 0,
                "table_count": 0,
                "message": "❌ No se encontraron tablas con datos cuantitativos"
            }
        
        # Verificar que las tablas tengan contenido (no solo headers)
        valid_tables = 0
        for table in tables:
            rows = table.strip().split('\n')
            # Debe tener al menos header + separator + 2 data rows
            if len(rows) >= 4:
                valid_tables += 1
        
        passed = valid_tables >= 1
        score = min(100, (valid_tables / 2) * 100)  # 2 tablas = score perfecto
        
        return {
            "passed": passed,
            "score": score,
            "table_count": valid_tables,
            "message": f"✓ {valid_tables} tabla(s) con datos" if passed else f"⚠️ Solo {valid_tables} tabla(s), se esperaban al menos 1"
        }
    
    def _check_numbers(self, text):
        """Verifica presencia de datos cuantitativos con unidades"""
        # Patrones de datos cuantitativos médicos
        patterns = [
            r'\d+\.?\d*\s*(?:μm|nm|mm|cm|kg|g|mg|mcg|μg|mL|L|%|°C|mmHg|lpm|rpm)',  # Unidades físicas
            r'\d+\.?\d*\s*(?:millones|miles)/mm³',  # Recuentos celulares
            r'\d+\.?\d*\s*(?:g/dL|mg/dL|mEq/L|mmol/L)',  # Concentraciones
            r'\d+-\d+\s*(?:años|días|horas|semanas|meses)',  # Rangos temporales
            r'\d+\.?\d*-\d+\.?\d*\s*(?:μm|%|mg|g)',  # Rangos de valores
        ]
        
        quantitative_data_count = 0
        for pattern in patterns:
            quantitative_data_count += len(re.findall(pattern, text))
        
        # Se esperan al menos 10 datos cuantitativos para una respuesta completa
        min_expected = 10
        passed = quantitative_data_count >= min_expected
        score = min(100, (quantitative_data_count / min_expected) * 100)
        
        return {
            "passed": passed,
            "score": score,
            "data_count": quantitative_data_count,
            "message": f"✓ {quantitative_data_count} datos cuantitativos" if passed else f"⚠️ Solo {quantitative_data_count} datos cuantitativos (mínimo {min_expected})"
        }
    
    def _check_structure(self, text):
        """Verifica estructura con secciones obligatorias"""
        required_sections = [
            r'##\s*Definición',
            r'##\s*Detalles\s+Clave',
            r'##\s*Advertencias',
            r'##\s*Fuentes'
        ]
        
        sections_found = 0
        missing_sections = []
        
        for section_pattern in required_sections:
            if re.search(section_pattern, text, re.IGNORECASE):
                sections_found += 1
            else:
                # Extraer nombre de sección del pattern
                section_name = section_pattern.replace(r'##\s*', '').replace(r'\s+', ' ')
                missing_sections.append(section_name)
        
        passed = sections_found == len(required_sections)
        score = (sections_found / len(required_sections)) * 100
        
        return {
            "passed": passed,
            "score": score,
            "sections_found": sections_found,
            "total_required": len(required_sections),
            "missing": missing_sections,
            "message": "✓ Estructura completa" if passed else f"❌ Faltan secciones: {', '.join(missing_sections)}"
        }
    
    def _check_references(self, text):
        """Verifica presencia de referencias específicas con detalles"""
        # Buscar menciones de libros médicos estándar
        reference_books = [
            r"Gray'?s?\s+Anatomy",
            r"Guyton\s*(?:&|and)?\s*Hall",
            r"Harrison'?s?",
            r"Robbins\s*(?:&|and)?\s*Cotran",
            r"Goodman\s*(?:&|and)?\s*Gilman",
            r"Goldman-Cecil",
            r"UpToDate"
        ]
        
        references_found = 0
        books_cited = []
        
        for book_pattern in reference_books:
            if re.search(book_pattern, text, re.IGNORECASE):
                references_found += 1
                books_cited.append(book_pattern.replace(r'\s*', ' ').replace(r"'?s?", "'s"))
        
        # Verificar que tengan detalles (edición, capítulo, páginas)
        detailed_refs = len(re.findall(r'\d+(?:st|nd|rd|th)?\s+ed\.?', text, re.IGNORECASE))
        
        passed = references_found >= 2  # Al menos 2 referencias
        score = min(100, (references_found / 3) * 100)  # 3 referencias = perfecto
        
        return {
            "passed": passed,
            "score": score,
            "reference_count": references_found,
            "detailed_refs": detailed_refs,
            "books_cited": books_cited,
            "message": f"✓ {references_found} fuente(s) citada(s)" if passed else f"⚠️ Solo {references_found} fuente(s), se esperan al menos 2"
        }
    
    def get_improvement_suggestions(self, validation_result):
        """Genera sugerencias concretas de mejora"""
        suggestions = []
        
        details = validation_result["details"]
        
        # Longitud
        if not details["length"]["passed"]:
            missing_words = details["length"]["min_required"] - details["length"]["word_count"]
            suggestions.append(f"📝 Agregar aproximadamente {missing_words} palabras más de contenido")
        
        # Tablas
        if not details["tables"]["passed"]:
            suggestions.append("📊 Incluir al menos 1 tabla con datos cuantitativos (tamaños, porcentajes, rangos normales)")
        
        # Datos cuantitativos
        if not details["numbers"]["passed"]:
            missing_data = 10 - details["numbers"]["data_count"]
            suggestions.append(f"🔢 Agregar {missing_data} datos cuantitativos más (μm, %, mg/dL, recuentos celulares)")
        
        # Estructura
        if not details["structure"]["passed"]:
            missing = details["structure"]["missing"]
            suggestions.append(f"📋 Agregar secciones faltantes: {', '.join(missing)}")
        
        # Referencias
        if not details["references"]["passed"]:
            suggestions.append("📚 Citar al menos 2 fuentes específicas con edición y capítulo")
        
        return suggestions


def validate_response(text, domain=None):
    """
    Función helper para validar una respuesta
    
    Args:
        text: Respuesta a validar
        domain: Dominio médico (opcional, para validaciones específicas)
    
    Returns:
        dict: Resultado de validación
    """
    validator = QualityValidator()
    return validator.validate(text, domain)
