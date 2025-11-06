"""
Módulo de Detección de Amplitud Semántica
==========================================

Intercepta preguntas médicamente válidas pero demasiado amplias
antes de consumir tokens en Mistral, reformulándolas educativamente.
"""

import re
from typing import Dict, List, Tuple


# ═══════════════════════════════════════════════════════
# DICCIONARIOS DE DETECCIÓN
# ═══════════════════════════════════════════════════════

ORGANOS_AMPLIOS = [
    "corazón", "corazon", "cardiaco", "cardíaco",
    "cerebro", "cerebral", "sistema nervioso",
    "riñón", "riñon", "renal", "nefron",
    "hígado", "higado", "hepatico", "hepático",
    "pulmón", "pulmon", "pulmonar", "respiratorio",
    "estómago", "estomago", "gastrico", "gástrico",
    "intestino", "intestinal",
    "sistema cardiovascular",
    "sistema respiratorio",
    "sistema digestivo",
    "sistema nervioso",
    "sistema endocrino",
    "sistema inmune",
    "aparato locomotor",
    "sistema musculoesquelético"
]

PALABRAS_AMPLIAS = [
    "estructura de", "estructura del", "estructura de la",
    "estructura anatomica", "estructura anatómica",
    "estructura completa", "estructura del",
    "anatomía de", "anatomia de", "anatomía del", "anatomia del",
    "anatomia completa", "anatomía completa",
    "todo sobre", "toda la", "todo el",
    "completo sobre", "completa de",
    "todo acerca de", "todo lo relacionado",
    "funcionamiento de", "funcionamiento del",
    "fisiología de", "fisiologia de", "fisiología del",
    "sistema completo", "sistema entero",
    "órgano completo", "organo completo"
]

REFORMULACIONES_POR_DOMINIO = {
    "anatomía": {
        "corazón": [
            "Anatomía de las cámaras cardíacas (aurículas y ventrículos)",
            "Sistema valvular cardíaco (tricúspide, mitral, aórtica, pulmonar)",
            "Irrigación coronaria (arterias coronarias y sus ramas)",
            "Sistema de conducción cardíaco (nodo sinoauricular, nodo auriculoventricular)",
            "Inervación del corazón (simpático y parasimpático)"
        ],
        "cerebro": [
            "Anatomía de los lóbulos cerebrales (frontal, parietal, temporal, occipital)",
            "Anatomía del tronco encefálico (mesencéfalo, protuberancia, bulbo raquídeo)",
            "Sistema ventricular y circulación del líquido cefalorraquídeo",
            "Anatomía del cerebelo (corteza, núcleos profundos, pedúnculos)",
            "Arterias cerebrales principales (círculo de Willis)"
        ],
        "riñón": [
            "Anatomía macroscópica del riñón (corteza, médula, pelvis renal)",
            "Estructura de la nefrona (glomérulo, túbulos, asa de Henle)",
            "Irrigación renal (arteria renal y su distribución)",
            "Sistema colector renal (túbulos colectores, cálices, pelvis)",
            "Topografía renal (relaciones anatómicas en el retroperitoneo)"
        ],
        "hígado": [
            "Anatomía segmentaria del hígado (segmentos de Couinaud)",
            "Sistema portal hepático (vena porta y sus ramas)",
            "Irrigación hepática (arteria hepática propia)",
            "Vías biliares intrahepáticas y extrahepáticas",
            "Relaciones anatómicas del hígado (ligamentos, impresiones)"
        ],
        "pulmón": [
            "Anatomía del árbol bronquial (bronquios principales, segmentarios, subsegmentarios)",
            "Estructura del lobulillo pulmonar (alvéolos, bronquiolos terminales)",
            "Irrigación pulmonar (arterias pulmonares y arterias bronquiales)",
            "Pleura y espacios pleurales (pleura visceral, parietal, seno costodiafragmático)",
            "Segmentación pulmonar (segmentos broncopulmonares)"
        ],
        "sistema cardiovascular": [
            "Anatomía del corazón y grandes vasos",
            "Sistema arterial sistémico (aorta y sus ramas principales)",
            "Sistema venoso sistémico (vena cava superior e inferior)",
            "Circulación coronaria (arterias y venas coronarias)",
            "Circulación pulmonar (arterias y venas pulmonares)"
        ],
        "sistema respiratorio": [
            "Anatomía de las vías aéreas superiores (fosas nasales, faringe, laringe)",
            "Anatomía del árbol traqueobronquial",
            "Estructura alveolar y barrera hemato-aérea",
            "Músculos respiratorios (diafragma, intercostales, accesorios)",
            "Inervación del sistema respiratorio"
        ],
        "sistema digestivo": [
            "Anatomía del esófago (porciones cervical, torácica, abdominal)",
            "Anatomía gástrica (cardias, fondo, cuerpo, antro, píloro)",
            "Anatomía del intestino delgado (duodeno, yeyuno, íleon)",
            "Anatomía del intestino grueso (ciego, colon, recto)",
            "Anatomía del páncreas y vías biliares"
        ]
    },
    "fisiología": {
        "corazón": [
            "Mecanismo de contracción cardíaca (fase sistólica y diastólica)",
            "Ciclo cardíaco completo (sístole auricular, sístole ventricular, diástole)",
            "Regulación del gasto cardíaco (ley de Frank-Starling)",
            "Electrofisiología cardíaca (potencial de acción miocárdico)",
            "Regulación autonómica de la frecuencia cardíaca"
        ],
        "cerebro": [
            "Fisiología de la sinapsis (liberación y recaptación de neurotransmisores)",
            "Potencial de acción neuronal y propagación",
            "Fisiología del sistema límbico (emociones, memoria)",
            "Fisiología del sueño (ciclos NREM y REM)",
            "Fisiología del sistema motor (corteza motora, vías piramidales)"
        ],
        "riñón": [
            "Filtración glomerular (presiones y fuerzas de Starling)",
            "Reabsorción tubular (proximal, asa de Henle, distal)",
            "Mecanismo de concentración y dilución de la orina",
            "Regulación del balance ácido-base renal",
            "Regulación de la presión arterial (sistema renina-angiotensina-aldosterona)"
        ],
        "hígado": [
            "Metabolismo hepático de carbohidratos (glucogénesis, glucogenólisis)",
            "Metabolismo hepático de lípidos (síntesis de ácidos biliares)",
            "Metabolismo hepático de proteínas (síntesis de albúmina)",
            "Función detoxificadora del hígado (citocromo P450)",
            "Secreción biliar y función de la vesícula biliar"
        ],
        "pulmón": [
            "Mecánica ventilatoria (volúmenes y capacidades pulmonares)",
            "Intercambio gaseoso (difusión de O₂ y CO₂)",
            "Regulación de la ventilación (quimiorreceptores centrales y periféricos)",
            "Relación ventilación-perfusión (V/Q)",
            "Transporte de gases en sangre (hemoglobina, curva de disociación)"
        ]
    },
    "farmacología": {
        "sistema cardiovascular": [
            "Fármacos antihipertensivos (mecanismo de acción y dosis)",
            "Fármacos antiarrítmicos (clasificación de Vaughan Williams)",
            "Fármacos para insuficiencia cardíaca (IECA, ARA-II, betabloqueantes)",
            "Anticoagulantes y antiagregantes plaquetarios",
            "Fármacos hipolipemiantes (estatinas, fibratos, ezetimiba)"
        ]
    }
}


# ═══════════════════════════════════════════════════════
# FUNCIONES PRINCIPALES
# ═══════════════════════════════════════════════════════

def detectar_amplitud(query: str, domain: str) -> int:
    """
    Detecta el nivel de amplitud semántica de una pregunta.
    
    Args:
        query: Pregunta del usuario
        domain: Dominio médico detectado
    
    Returns:
        Score de amplitud (0-10):
        - 0-3: Ultra específica (permitir Mistral)
        - 4-6: Específica/Moderada (permitir Mistral)
        - 7-8: Amplia (reformular)
        - 9-10: Ultra amplia (reformular)
    """
    query_lower = query.lower().strip()
    score = 0
    
    # DEBUG: Logging detallado
    print(f"🔍 [AMPLITUD] Query analizada: '{query_lower}'")
    print(f"🔍 [AMPLITUD] Dominio: '{domain}'")
    
    # ═══════════════════════════════════════════════════════
    # DETECCIÓN 1: Palabras amplias (alta puntuación)
    # ═══════════════════════════════════════════════════════
    palabra_detectada = None
    for palabra in PALABRAS_AMPLIAS:
        if palabra in query_lower:
            palabra_detectada = palabra
            score += 3
            print(f"🔍 [AMPLITUD] ✓ Palabra amplia detectada: '{palabra}' (+3 puntos)")
            break  # Solo contar una vez
    
    # DETECCIÓN ADICIONAL: "estructura" + órgano (patrón común)
    if not palabra_detectada:
        if "estructura" in query_lower and any(organo in query_lower for organo in ORGANOS_AMPLIOS[:15]):
            palabra_detectada = "estructura + órgano"
            score += 3
            print(f"🔍 [AMPLITUD] ✓ Patrón 'estructura + órgano' detectado (+3 puntos)")
    
    # DETECCIÓN ADICIONAL: "anatomia" / "anatomía" + órgano sin más especificación
    if not palabra_detectada:
        if ("anatomia" in query_lower or "anatomía" in query_lower) and any(organo in query_lower for organo in ORGANOS_AMPLIOS[:15]):
            # Verificar que no tenga términos muy específicos
            if not any(term in query_lower for term in ["irrigación", "irrigacion", "inervación", "inervacion", "cámara", "camara", "válvula", "valvula"]):
                palabra_detectada = "anatomia + órgano"
                score += 3
                print(f"🔍 [AMPLITUD] ✓ Patrón 'anatomía + órgano' detectado (+3 puntos)")
    
    if not palabra_detectada:
        print(f"🔍 [AMPLITUD] ✗ No se detectaron palabras amplias")
    
    # ═══════════════════════════════════════════════════════
    # DETECCIÓN 2: Órganos completos sin especificar
    # ═══════════════════════════════════════════════════════
    organos_encontrados = []
    for organo in ORGANOS_AMPLIOS:
        if organo in query_lower:
            organos_encontrados.append(organo)
    
    if organos_encontrados:
        print(f"🔍 [AMPLITUD] ✓ Órganos detectados: {organos_encontrados}")
        
        # Si menciona órgano pero no especifica parte/componente
        tiene_especificacion = any([
            "cámara" in query_lower or "camara" in query_lower,
            "válvula" in query_lower or "valvula" in query_lower,
            "arteria" in query_lower,
            "vena" in query_lower,
            "nervio" in query_lower,
            "músculo" in query_lower or "musculo" in query_lower,
            "hueso" in query_lower,
            "lóbulo" in query_lower or "lobulo" in query_lower,
            "segmento" in query_lower,
            "sistema de" in query_lower,
            "mecanismo" in query_lower,
            "proceso" in query_lower,
            "función de" in query_lower or "funcion de" in query_lower,
            "irrigación" in query_lower or "irrigacion" in query_lower,
            "inervación" in query_lower or "inervacion" in query_lower
        ])
        
        if not tiene_especificacion:
            score += 4  # Órgano completo sin especificar
            print(f"🔍 [AMPLITUD] ✗ Sin especificación (+4 puntos)")
        else:
            score += 1  # Órgano con alguna especificación (menos amplio)
            print(f"🔍 [AMPLITUD] ✓ Con especificación (+1 punto)")
    else:
        print(f"🔍 [AMPLITUD] ✗ No se detectaron órganos amplios")
    
    # ═══════════════════════════════════════════════════════
    # DETECCIÓN 3: Patrones de preguntas ultra amplias
    # ═══════════════════════════════════════════════════════
    patrones_ultra_amplios = [
        r"todo sobre",
        r"todo el",
        r"toda la",
        r"completo sobre",
        r"estructura completa",
        r"anatomía completa",
        r"fisiología completa"
    ]
    
    patron_detectado = None
    for patron in patrones_ultra_amplios:
        if re.search(patron, query_lower):
            patron_detectado = patron
            score += 5
            print(f"🔍 [AMPLITUD] ✓ Patrón ultra amplio detectado: '{patron}' (+5 puntos)")
            break
    
    if not patron_detectado:
        print(f"🔍 [AMPLITUD] ✗ No se detectaron patrones ultra amplios")
    
    # ═══════════════════════════════════════════════════════
    # DETECCIÓN 4: Longitud de pregunta (preguntas muy cortas suelen ser amplias)
    # ═══════════════════════════════════════════════════════
    palabras = query_lower.split()
    if len(palabras) <= 5 and any(organo in query_lower for organo in ORGANOS_AMPLIOS[:10]):
        score += 2
    
    # ═══════════════════════════════════════════════════════
    # DETECCIÓN 5: Ausencia de términos específicos
    # ═══════════════════════════════════════════════════════
    terminos_especificos = [
        "dosis", "mecanismo", "causa", "síntoma", "signo",
        "diagnóstico", "tratamiento", "anatomía de la",
        "anatomía del", "irrigación", "inervación",
        "ubicación", "relación", "función de", "efecto"
    ]
    
    tiene_termino_especifico = any(term in query_lower for term in terminos_especificos)
    if not tiene_termino_especifico and score > 0:
        score += 1  # Refuerza la amplitud si no hay términos específicos
        print(f"🔍 [AMPLITUD] ✗ Sin términos específicos (+1 punto refuerzo)")
    else:
        if tiene_termino_especifico:
            print(f"🔍 [AMPLITUD] ✓ Términos específicos detectados (sin refuerzo)")
    
    # Limitar score máximo a 10
    score_final = min(score, 10)
    print(f"🔍 [AMPLITUD] 📊 Score final: {score_final}/10 (threshold: 7)")
    return score_final


def generar_reformulacion(query: str, domain: str) -> str:
    """
    Genera mensaje educativo con reformulaciones específicas.
    
    Args:
        query: Pregunta original del usuario
        domain: Dominio médico detectado
    
    Returns:
        Mensaje markdown con opciones de reformulación
    """
    query_lower = query.lower().strip()
    
    # Identificar órgano/sistema mencionado
    organo_detectado = None
    for organo in ORGANOS_AMPLIOS:
        if organo in query_lower:
            organo_detectado = organo
            break
    
    # Si no se detecta órgano específico, usar dominio general
    if not organo_detectado:
        organo_detectado = "tema general"
    
    # Buscar reformulaciones predefinidas
    reformulaciones = None
    
    if domain in REFORMULACIONES_POR_DOMINIO:
        dominio_dict = REFORMULACIONES_POR_DOMINIO[domain]
        
        # Buscar coincidencia exacta o parcial
        for key, value in dominio_dict.items():
            if key in query_lower or any(part in query_lower for part in key.split()):
                reformulaciones = value
                organo_detectado = key
                break
    
    # Si no hay reformulaciones predefinidas, generar genéricas
    if not reformulaciones:
        reformulaciones = _generar_reformulaciones_genericas(query_lower, domain, organo_detectado)
    
    # Construir mensaje educativo
    mensaje = f"""💡 **Tu pregunta requiere mayor precisión clínica**

Tu consulta sobre **"{query}"** es médicamente válida, pero abarca un tema demasiado amplio que requeriría una respuesta extensa (potencialmente >3000 tokens).

**🎓 Formulación de preguntas clínicas precisas:**

En medicina, la precisión en la formulación de preguntas es fundamental. Preguntas muy amplias dificultan obtener respuestas prácticas y aplicables.

**📋 Reformulaciones sugeridas:**

"""
    
    # Agregar opciones numeradas
    for i, reformulacion in enumerate(reformulaciones[:5], 1):
        mensaje += f"{i}. {reformulacion}\n"
    
    mensaje += f"""
**💡 Tip educativo:**

Lisabella está diseñada para enseñarte a formular preguntas como un médico experto. Las preguntas específicas permiten:
- Respuestas más precisas y aplicables
- Mejor comprensión de conceptos complejos
- Desarrollo de habilidades clínicas

**📚 Referencia bibliográfica:**

Este enfoque educativo se basa en metodologías de aprendizaje clínico descritas en:
- "Evidence-Based Medicine: How to Practice and Teach EBM" (Sackett et al.)
- "Clinical Reasoning: Learning to Think Like a Physician" (Norman & Eva)
- Guías de educación médica de la AMA (American Medical Association)

¿Cuál de estas opciones te interesa explorar? Puedes copiar y pegar cualquiera de ellas."""
    
    return mensaje


def _generar_reformulaciones_genericas(query_lower: str, domain: str, organo: str) -> List[str]:
    """Genera reformulaciones genéricas cuando no hay predefinidas"""
    
    reformulaciones = []
    
    if "anatomía" in query_lower or domain == "anatomía":
        reformulaciones = [
            f"Anatomía macroscópica del {organo} (estructura general)",
            f"Anatomía microscópica del {organo} (estructura histológica)",
            f"Irrigación arterial y venosa del {organo}",
            f"Inervación del {organo} (nervios principales)",
            f"Relaciones anatómicas del {organo} (topografía)"
        ]
    elif "fisiología" in query_lower or domain == "fisiología":
        reformulaciones = [
            f"Mecanismo de funcionamiento del {organo}",
            f"Regulación de la función del {organo}",
            f"Integración del {organo} en sistemas corporales",
            f"Fisiopatología de las disfunciones del {organo}",
            f"Homeostasis y el {organo}"
        ]
    elif "farmacología" in query_lower or domain == "farmacología":
        reformulaciones = [
            f"Mecanismo de acción de fármacos que actúan en el {organo}",
            f"Farmacocinética de fármacos relacionados con el {organo}",
            f"Interacciones farmacológicas en el {organo}",
            f"Dosis y vías de administración de fármacos para el {organo}",
            f"Efectos adversos de fármacos que afectan al {organo}"
        ]
    else:
        reformulaciones = [
            f"Estructura específica del {organo}",
            f"Función principal del {organo}",
            f"Relación del {organo} con otros sistemas",
            f"Patologías más comunes del {organo}",
            f"Diagnóstico y tratamiento relacionado con el {organo}"
        ]
    
    return reformulaciones


# ═══════════════════════════════════════════════════════
# FUNCIÓN DE INTEGRACIÓN
# ═══════════════════════════════════════════════════════

def evaluar_y_reformular(query: str, domain: str) -> Tuple[bool, str]:
    """
    Evalúa si la pregunta es demasiado amplia y retorna reformulación si es necesario.
    
    Args:
        query: Pregunta del usuario
        domain: Dominio médico detectado
    
    Returns:
        Tuple (es_amplia: bool, respuesta: str)
        - Si es_amplia=True: respuesta contiene reformulación educativa
        - Si es_amplia=False: respuesta es vacía (proceder a Mistral)
    """
    amplitud_score = detectar_amplitud(query, domain)
    
    # Threshold: score >= 7 requiere reformulación
    if amplitud_score >= 7:
        reformulacion = generar_reformulacion(query, domain)
        return (True, reformulacion)
    
    # Score < 7: pregunta específica, permitir Mistral
    return (False, "")

