"""
Ejemplos de CALIDAD ESPERADA para mostrar al LLM
Estos fragmentos sirven como "plantilla" de longitud y detalle
"""

HISTOLOGY_EXAMPLE = """
**Eritrocitos (Glóbulos Rojos):**

Células anucleadas bicóncavas de 7-8 μm de diámetro y 2 μm de espesor en el centro. 
Cada eritrocito contiene aproximadamente 280 millones de moléculas de hemoglobina 
(Hb A1: α₂β₂, representa 98% del total; Hb A2: α₂δ₂, 2%; Hb F: α₂γ₂, trazas en adultos).

La membrana eritrocitaria posee un citoesqueleto formado por:
- Espectrina (tetrámeros α₂β₂): proteína principal del citoesqueleto
- Actina (filamentos cortos): puntos de anclaje
- Proteína 4.1: une espectrina con glucoforina C
- Ankirina: conecta espectrina con banda 3 (intercambiador Cl⁻/HCO₃⁻)

Esta estructura le confiere flexibilidad para atravesar capilares de 3-4 μm de diámetro 
sin fragmentarse. Vida media: 120 días. Destrucción: sistema reticuloendotelial 
(bazo 90%, hígado 10%).

| Parámetro Eritrocitario | Hombres | Mujeres | Unidad |
|-------------------------|---------|---------|--------|
| Recuento | 4.5-5.5 | 4.0-5.0 | millones/mm³ |
| Hemoglobina (Hb) | 13.5-17.5 | 12.0-16.0 | g/dL |
| Hematocrito (Hto) | 41-53 | 36-46 | % |
| VCM | 80-100 | 80-100 | fL |
| HCM | 27-31 | 27-31 | pg |
| CHCM | 32-36 | 32-36 | g/dL |

**Correlación clínica:** VCM <80 fL sugiere anemia microcítica (ferropénica, talasemia); 
VCM >100 fL sugiere anemia macrocítica (déficit B12/folato, alcoholismo).
"""

ANATOMY_EXAMPLE = """
**Bazo - Relaciones Topográficas Detalladas:**

Órgano linfoide secundario de forma ovoide aplanada, localizado en hipocondrio izquierdo. 
Dimensiones: 12 cm (longitud, eje mayor) × 7 cm (ancho) × 4 cm (espesor máximo). 
Peso: 150-200 g en adultos (varía: 100 g en ancianos, hasta 1000 g en esplenomegalia masiva).

**Relaciones anatómicas por cara:**

*Cara diafragmática (posterolateral):*
- Superficie: Lisa, convexa, cóncava adaptándose al diafragma
- Contacto: Hemidiafragma izquierdo a nivel de costillas 9ª, 10ª y 11ª
- Separación: Receso costodiafragmático del espacio pleural izquierdo (2-3 cm)
- Proyección: Desde T11 hasta L1 en proyección posterior
- Relación indirecta: Pulmón izquierdo (lóbulo inferior) a través del diafragma

*Cara visceral (anteromedial):*
Superficie cóncava con tres impresiones específicas:

1. **Impresión gástrica** (superior, ocupa 2/3 de la cara):
   - Contacto: Fundus y porción superior del cuerpo gástrico
   - Separación: Ligamento gastroesplénico (epiplón gastroesplénico)
   - Contenido del ligamento: Vasos gástricos cortos (4-6 ramas), nervio vago

2. **Impresión renal** (posteromedial, ocupa 1/3):
   - Contacto: Polo superior del riñón izquierdo y glándula suprarrenal izquierda
   - Separación: Ligamento esplenorrenal (línea de reflexión peritoneal)
   - Contenido del ligamento: Arteria esplénica, vena esplénica, cola del páncreas

3. **Impresión cólica** (inferior, pequeña):
   - Contacto: Flexura cólica izquierda (ángulo esplénico del colon)
   - Ligamento: Ligamento frenocólico (sostén del bazo desde abajo)

**Hilio esplénico:**
- Localización: Tercio medio de cara visceral
- Longitud: 3-4 cm
- Contenido (de anterior a posterior):
  • Vena esplénica (anterior, 8-10 mm diámetro)
  • Arteria esplénica (posterior, 6-8 mm diámetro, tortuosa)
  • Cola del páncreas (puede alcanzar el hilio en 30% de casos)
  • Linfáticos esplénicos
  • Nervios autonómicos (plexo celíaco)
"""

PHARMACOLOGY_EXAMPLE = """
**Metoprolol - Farmacocinética Detallada:**

Betabloqueador cardioselectivo (β₁ > β₂, ratio 20:1 a dosis terapéuticas).

**Absorción:**
- Vía oral: Biodisponibilidad 50% (tartrato), 77% (succinato liberación prolongada)
- Efecto de primer paso hepático: 50% metabolizado antes de circulación sistémica
- Tmax: 1.5-2 horas (tartrato), 6-8 horas (succinato LP)
- Alimentos: ↑ biodisponibilidad 20-40% (tomar con comidas)

**Distribución:**
- Volumen de distribución (Vd): 3.2-5.6 L/kg (distribución amplia)
- Unión a proteínas plasmáticas: 12% (baja, mayor fracción libre)
- Liposolubilidad moderada: atraviesa barrera hematoencefálica
- Paso placentario: Sí (categoría C en embarazo)

**Metabolismo:**
- Hígado (>95%): CYP2D6 principalmente
- Metabolitos:
  • α-hidroximetoprolol (activo, 10% de potencia del fármaco original)
  • O-desmetilmetoprolol (inactivo)
- Polimorfismo CYP2D6:
  • Metabolizadores lentos (7% caucásicos): ↑ niveles plasmáticos 5x, ↑ riesgo bradicardia
  • Metabolizadores ultrarrápidos (2-3%): ↓ eficacia, requieren dosis mayores

**Excreción:**
- Renal: 95% (5% sin cambios, 90% como metabolitos)
- Biliar: <5%
- Vida media (t½): 3-7 horas (tartrato), 15-19 horas (succinato LP)
- Clearance: 1000 mL/min
- Tiempo hasta steady-state: 15-24 horas (4-5 vidas medias)

| Parámetro | Valor | Ajuste en Disfunción |
|-----------|-------|----------------------|
| Biodisponibilidad | 50% (tartrato) | Sin cambio en IR |
| Vd | 4 L/kg | ↑ en ICC (7 L/kg) |
| t½ | 3-7 h | ↑ hasta 9 h en IR severa |
| Unión proteínas | 12% | Sin cambio |
| Dosis usual | 50-200 mg/día | Reducir 50% en cirrosis |

**Relevancia clínica:** En metabolizadores lentos CYP2D6, iniciar con 25 mg/día 
y titular lentamente. En insuficiencia hepática Child-Pugh C, reducir dosis 75%.
"""

def get_example_for_domain(domain):
    """Retorna ejemplo apropiado según dominio"""
    domain_lower = domain.lower()
    
    if "histolog" in domain_lower:
        return HISTOLOGY_EXAMPLE
    elif "anatom" in domain_lower:
        return ANATOMY_EXAMPLE
    elif "farmacolog" in domain_lower or "farmac" in domain_lower:
        return PHARMACOLOGY_EXAMPLE
    else:
        # Usar ejemplo de histología como genérico (es el más completo)
        return HISTOLOGY_EXAMPLE
