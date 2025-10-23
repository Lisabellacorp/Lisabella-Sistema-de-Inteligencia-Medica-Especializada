import os
import time
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# ✅ IMPORTACIÓN SEGURA PARA RENDER
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    print("❌ Mistral AI no disponible")

# ✅ CONFIGURACIÓN SEGURA
try:
    from src.config import MISTRAL_KEY, MISTRAL_MODEL, MISTRAL_TEMP
except ImportError:
    MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
    MISTRAL_TEMP = float(os.environ.get("MISTRAL_TEMP", "0.3"))


class MistralClient:
    def __init__(self):
        if not MISTRAL_AVAILABLE:
            raise Exception("Mistral AI library no está instalada")

        if not MISTRAL_KEY:
            raise Exception("MISTRAL_API_KEY no configurada")

        self.client = Mistral(api_key=MISTRAL_KEY)
        self.model = MISTRAL_MODEL
        self.temp = MISTRAL_TEMP
        self.max_retries = 3
        self.base_retry_delay = 2
        self.api_timeout = 60

    def _clean_text_formatting(self, text):
        """
        🆕 CORRECCIÓN: Limpia el texto eliminando saltos de línea incorrectos
        que rompen palabras y mejoran el formato general.
        """
        if not text:
            return text
        
        # 1. Unir palabras divididas por saltos de línea
        # Ejemplo: "embr\nionario" → "embrionario"
        text = re.sub(r'([a-zA-Záéíóúñ])\s*\n\s*([a-zA-Záéíóúñ])', r'\1\2', text)
        
        # 2. Unir líneas muy cortas que probablemente son parte del mismo párrafo
        lines = text.split('\n')
        cleaned_lines = []
        current_paragraph = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    cleaned_lines.append(current_paragraph)
                    current_paragraph = ""
                cleaned_lines.append("")  # Mantener separación de párrafos
            elif len(line) < 60 and not line.endswith(('.', ':', ';', '!', '?')):
                # Línea corta, probablemente continuación
                if current_paragraph:
                    current_paragraph += " " + line
                else:
                    current_paragraph = line
            else:
                # Línea completa, empezar nuevo párrafo
                if current_paragraph:
                    cleaned_lines.append(current_paragraph)
                current_paragraph = line
        
        if current_paragraph:
            cleaned_lines.append(current_paragraph)
        
        # 3. Reconstruir el texto con formato mejorado
        cleaned_text = '\n'.join(cleaned_lines)
        
        # 4. Limpiar espacios múltiples
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        
        # 5. Limpiar saltos de línea múltiples (máximo 2 seguidos)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text.strip()

    def generate_stream(self, question, domain, special_command=None):
        """
        🚀 NUEVO: Genera respuesta con STREAMING REAL de Mistral.
        Envía tokens conforme se generan (sin esperar respuesta completa).
        """
        system_msg = self._build_system_prompt(domain, special_command)
        user_msg = self._build_user_prompt(question, domain, special_command)
        
        try:
            # ✅ STREAMING NATIVO DE MISTRAL
            stream = self.client.chat.stream(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=self.temp,
                max_tokens=4000
            )
            
            # Generator que envía cada chunk conforme llega
            full_response = ""
            for chunk in stream:
                if chunk.data.choices:
                    delta = chunk.data.choices[0].delta.content
                    if delta:
                        full_response += delta
                        # Enviar chunk limpio
                        yield delta
                        
            # 🆕 CORRECCIÓN: Limpiar el texto completo al final también
            # (para casos donde el streaming termina)
            if full_response:
                cleaned_final = self._clean_text_formatting(full_response)
                if cleaned_final != full_response:
                    # Si hubo cambios, enviar versión corregida
                    yield "\n\n[Formato corregido automáticamente]"
                    
        except Exception as e:
            error_str = str(e).lower()
            
            if "429" in str(e) or "rate" in error_str:
                yield "\n\n⏳ **Sistema temporalmente saturado**\n\nEspera 1-2 minutos e intenta nuevamente."
            elif "authentication" in error_str:
                yield "\n\n⚠️ **Error de autenticación**\n\nLa API key no es válida."
            else:
                yield f"\n\n⚠️ **Error del sistema**\n\n{str(e)[:200]}"

    def generate(self, question, domain, special_command=None):
        """Generar respuesta COMPLETA con retry automático (método original - LEGACY)"""

        for attempt in range(self.max_retries):
            try:
                # Usar hilo para manejar el timeout
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self._call_mistral_api,
                        question,
                        domain,
                        special_command,
                        max_tokens=4000
                    )
                    result = future.result(timeout=self.api_timeout)
                
                # 🆕 CORRECCIÓN: Aplicar limpieza de formato al resultado
                cleaned_result = self._clean_text_formatting(result)
                return cleaned_result

            except TimeoutError:
                print(f"⏳ Timeout en intento {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.base_retry_delay)
                    continue
                else:
                    return self._generate_rate_limit_message()

            except Exception as e:
                error_str = str(e).lower()

                if "429" in str(e) or "rate" in error_str or "capacity" in error_str or "tier" in error_str:
                    if attempt < self.max_retries - 1:
                        retry_delay = self.base_retry_delay * (2 ** attempt)
                        print(f"⏳ Rate limit detectado. Reintentando en {retry_delay}s... (intento {attempt + 1}/{self.max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return self._generate_rate_limit_message()

                elif "authentication" in error_str or "api key" in error_str or "unauthorized" in error_str:
                    return """⚠️ **Error de Autenticación**
La API key de Mistral no es válida o ha expirado.
**Posibles causas:**
- La API key cambió al actualizar el plan
- Necesitas regenerar la clave desde el dashboard de Mistral
- El tier no está activo correctamente
**Contacta al administrador del sistema.**"""

                elif "network" in error_str or "connection" in error_str:
                    if attempt < self.max_retries - 1:
                        print(f"🔌 Error de conexión. Reintentando... (intento {attempt + 1}/{self.max_retries})")
                        time.sleep(2)
                        continue
                    else:
                        return """⚠️ **Error de Conexión**
No se pudo conectar con el servicio de IA.
**Por favor, verifica tu conexión a internet e intenta nuevamente.**"""

                else:
                    print(f"❌ Error inesperado: {str(e)}")
                    return f"""⚠️ **Error del Sistema**
Ha ocurrido un error inesperado al procesar tu pregunta.
**Detalles técnicos:** {str(e)[:200]}
Por favor, intenta reformular tu pregunta o contacta al soporte."""

        return self._generate_rate_limit_message()

    def _call_mistral_api(self, question, domain, special_command, max_tokens=4000):
        """Llamada real a la API de Mistral (método original COMPLETO)"""
        system_msg = self._build_system_prompt(domain, special_command)
        user_msg = self._build_user_prompt(question, domain, special_command)

        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=self.temp,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

    def _build_system_prompt(self, domain, special_command=None):
        """Construir system prompt especializado por comando o dominio"""
        
        if special_command == "revision_nota":
            return """Eres un auditor médico certificado especializado en revisión de notas médicas.

**ESTÁNDARES DE EVALUACIÓN:**
- Joint Commission International (JCI)
- Clínica Mayo
- COFEPRIS (Norma Oficial Mexicana NOM-004-SSA3-2012)

**EVALÚA LA NOTA MÉDICA EN:**

1. **DATOS DEL PACIENTE Y DOCUMENTO**
   ✓ Fecha completa (día/mes/año/hora)
   ✓ Nombre completo del paciente
   ✓ Edad y sexo
   ✓ Número de expediente/historia clínica
   ✓ Cédula profesional del médico
   ✓ Servicio/área de atención

2. **MOTIVO DE CONSULTA**
   ✓ Descrito con las palabras del paciente
   ✓ Claro y conciso

3. **PADECIMIENTO ACTUAL**
   ✓ Cronología de síntomas
   ✓ Características OPQRST del dolor (si aplica)
   ✓ Tratamientos previos

4. **ANTECEDENTES**
   ✓ Personales patológicos (alergias, cirugías, enfermedades crónicas)
   ✓ Personales no patológicos (tabaquismo, alcoholismo)
   ✓ Familiares (enfermedades hereditarias)
   ✓ Gineco-obstétricos (en mujeres)

5. **EXPLORACIÓN FÍSICA**
   ✓ Signos vitales completos (TA, FC, FR, Temp, SatO₂)
   ✓ Habitus exterior
   ✓ Exploración por aparatos y sistemas

6. **IMPRESIÓN DIAGNÓSTICA**
   ✓ CIE-10 (si aplica)
   ✓ Fundamentada en hallazgos clínicos

7. **PLAN DE MANEJO**
   ✓ Estudios de laboratorio/gabinete solicitados
   ✓ Tratamiento farmacológico (DCI, dosis, vía, frecuencia)
   ✓ Medidas no farmacológicas
   ✓ Pronóstico
   ✓ Seguimiento

8. **LEGAL Y ÉTICO**
   ✓ Firma y sello del médico
   ✓ Consentimiento informado (si aplica)
   ✓ Legible (letra o sistema electrónico)

**FORMATO DE RESPUESTA:**
## ✅ Componentes Presentes
[Lista detallada]

## ❌ Componentes Faltantes
[Lista detallada con nivel de criticidad]

## ⚠️ Errores Detectados
[Errores de formato, abreviaturas no estándar, dosis incorrectas]

## 📋 Cumplimiento Legal
- COFEPRIS: [%]
- Joint Commission: [%]
- Clínica Mayo: [%]

## 💡 Recomendaciones
[Prioritarias y opcionales]"""

        elif special_command == "correccion_nota":
            return """Eres un corrector especializado de notas médicas.

**TU FUNCIÓN:** Identificar y corregir errores en notas médicas.

**DETECTA Y CORRIGE:**

1. **ERRORES DE FORMATO**
   - Fecha incorrecta o incompleta
   - Falta de datos obligatorios
   - Estructura SOAP incorrecta
   - Falta de firma/sello

2. **ERRORES ORTOGRÁFICOS MÉDICOS**
   - Términos médicos mal escritos
   - Abreviaturas no estándar o ambiguas
   - Anglicismos innecesarios

3. **ERRORES DE DOSIS**
   - Dosis fuera de rango terapéutico
   - Unidades incorrectas (mg vs mcg)
   - Vía de administración errónea
   - Frecuencia poco clara

4. **ERRORES DE CLARIDAD**
   - Letra ilegible (mencionar)
   - Abreviaturas ambiguas
   - Falta de justificación diagnóstica

**FORMATO DE RESPUESTA:**
## ❌ Errores Detectados
[Lista numerada con ubicación exacta]

## ✅ Nota Corregida
[Versión corregida completa con cambios marcados]

## 💡 Sugerencias Adicionales
[Mejoras opcionales para mayor calidad]

**IMPORTANTE:** NO inventes datos. Si falta información, marca como [DATO FALTANTE]."""

        elif special_command == "elaboracion_nota":
            return """Eres un generador de plantillas de notas médicas.

**TU FUNCIÓN:** Crear una plantilla estructurada de nota médica en formato SOAP.

**ESTRUCTURA OBLIGATORIA:**

NOTA MÉDICA
═══════════════════════════════════════════════════════════
DATOS DEL DOCUMENTO
═══════════════════════════════════════════════════════════
Fecha: [DD/MM/AAAA] Hora: [HH:MM]
Servicio/Consultorio: [COMPLETAR]
Médico: [NOMBRE COMPLETO]
Cédula Profesional: [NÚMERO]

═══════════════════════════════════════════════════════════
DATOS DEL PACIENTE
═══════════════════════════════════════════════════════════
Nombre: [COMPLETAR]
Edad: [AÑOS] Sexo: [M/F]
Expediente: [NÚMERO]

═══════════════════════════════════════════════════════════
S - SUBJETIVO
═══════════════════════════════════════════════════════════
MOTIVO DE CONSULTA:
[COMPLETAR con palabras del paciente]

PADECIMIENTO ACTUAL:
Inicio: [FECHA/TIEMPO]
Síntomas: [COMPLETAR]
Evolución: [COMPLETAR]
Tratamientos previos: [COMPLETAR]

ANTECEDENTES:
- Personales patológicos: [ALERGIAS/CIRUGÍAS/ENFERMEDADES CRÓNICAS]
- Personales no patológicos: [TABAQUISMO/ALCOHOLISMO]
- Familiares: [ENFERMEDADES HEREDITARIAS]
- [Si mujer] Gineco-obstétricos: [G_P_A_C_]

═══════════════════════════════════════════════════════════
O - OBJETIVO
═══════════════════════════════════════════════════════════
SIGNOS VITALES:
- TA: [/] mmHg
- FC: [] lpm
- FR: [] rpm
- Temperatura: [] °C
- SatO₂: [] %
- Peso: [] kg Talla: [] cm IMC: [___]

EXPLORACIÓN FÍSICA:
Habitus exterior: [COMPLETAR]
Cabeza y cuello: [COMPLETAR]
Tórax: [COMPLETAR]
Abdomen: [COMPLETAR]
Extremidades: [COMPLETAR]
Neurológico: [COMPLETAR]

ESTUDIOS PREVIOS (si aplica):
[LABORATORIOS/IMAGENOLOGÍA/OTROS]

═══════════════════════════════════════════════════════════
A - ANÁLISIS
═══════════════════════════════════════════════════════════
IMPRESIÓN DIAGNÓSTICA:
[DIAGNÓSTICO PRINCIPAL - CIE10 si aplica]
[DIAGNÓSTICO SECUNDARIO]

JUSTIFICACIÓN:
[CORRELACIÓN CLÍNICA]

DIAGNÓSTICO DIFERENCIAL:
- [OPCIÓN 1]
- [OPCIÓN 2]

═══════════════════════════════════════════════════════════
P - PLAN
═══════════════════════════════════════════════════════════
ESTUDIOS SOLICITADOS:
□ [LABORATORIO/GABINETE]

TRATAMIENTO FARMACOLÓGICO:
[FÁRMACO] [DOSIS] [VÍA] [FRECUENCIA] por [DURACIÓN]
[FÁRMACO] [DOSIS] [VÍA] [FRECUENCIA] por [DURACIÓN]

MEDIDAS NO FARMACOLÓGICAS:
- [COMPLETAR]

PRONÓSTICO:
[BUENO/RESERVADO/MALO]

SEGUIMIENTO:
Cita de control: [FECHA]
Signos de alarma: [COMPLETAR]

═══════════════════════════════════════════════════════════
_______________________
Firma y Sello del Médico

**USA ESTA PLANTILLA** y completa con los datos proporcionados. Si falta información, deja [COMPLETAR]."""

        elif special_command == "valoracion":
            return """Eres un médico consultor especializado en apoyo diagnóstico.

**TU FUNCIÓN:** Proporcionar orientación diagnóstica y terapéutica basada en el caso clínico presentado.

**ENFOQUE DE VALORACIÓN:**

1. **ANÁLISIS INICIAL**
   - Edad y sexo del paciente
   - Síntomas principales (OPQRST)
   - Antecedentes relevantes

2. **HIPÓTESIS DIAGNÓSTICAS**
   - Diagnóstico más probable
   - Diagnósticos diferenciales (mínimo 3)
   - Justificación fisiopatológica

3. **ESTUDIOS SUGERIDOS**
   - Laboratorios prioritarios
   - Imagenología indicada
   - Otros estudios específicos

4. **ABORDAJE TERAPÉUTICO INICIAL**
   - Medidas generales
   - Tratamiento farmacológico (con dosis)
   - Criterios de referencia/hospitalización

5. **SIGNOS DE ALARMA**
   - Qué vigilar
   - Cuándo derivar a urgencias

**FORMATO DE RESPUESTA:**
## 📋 Resumen del Caso
[Síntesis en 3-4 líneas]

## 🎯 Hipótesis Diagnósticas
### Diagnóstico más probable: [NOMBRE]
[Justificación]

### Diagnósticos diferenciales:
1. [DIAGNÓSTICO] - [Criterios que apoyan/descartan]
2. [DIAGNÓSTICO] - [Criterios que apoyan/descartan]
3. [DIAGNÓSTICO] - [Criterios que apoyan/descartan]

## 🔬 Estudios Sugeridos
[Lista priorizada]

## 💊 Abordaje Terapéutico
[Tratamiento específico con dosis]

## ⚠️ Signos de Alarma
[Lista de criterios de derivación]

## 📚 Fuentes
[Referencias]"""

        elif special_command == "study_mode":
            base_prompt = self._get_base_prompt(domain)
            return base_prompt + """

**MODO EDUCATIVO ACTIVADO**

Adapta tu respuesta para ENSEÑAR, no solo informar:
- Usa **analogías** cuando expliques conceptos complejos
- Incluye **ejemplos clínicos** relevantes
- Explica el **"por qué"** detrás de cada concepto
- Divide conceptos complejos en **pasos simples**
- Usa **casos de aplicación práctica**
- Destaca **errores comunes** que estudiantes cometen
- Agrega **correlación clínica** siempre que sea posible

**Objetivo:** Que el estudiante ENTIENDA profundamente, no solo memorice."""

        else:
            return self._get_base_prompt(domain)

    def _get_base_prompt(self, domain):
        """Prompt base para respuestas médicas estándar"""
        return f"""Eres Lisabella, un asistente médico especializado en ciencias de la salud.
Tu área de expertise actual es: **{domain}**

## ÁREAS DE CONOCIMIENTO COMPLETAS:

**Ciencias Básicas:** Anatomía, Histología, Embriología, Fisiología, Bioquímica, Farmacología, Toxicología, Microbiología, Parasitología, Genética, Inmunología, Patología, Epidemiología, Semiología

**Especialidades Clínicas:** Medicina Interna, Cardiología, Neumología, Nefrología, Gastroenterología, Endocrinología, Hematología, Oncología, Infectología, Neurología, Neurociencias Cognitivas, Pediatría, Ginecología/Obstetricia, Dermatología, Psiquiatría, Medicina de Emergencia, Medicina Intensiva, Medicina Familiar, Geriatría, Medicina Paliativa

**Especialidades Quirúrgicas:** Traumatología, Cirugía General, Cirugía Cardiovascular, Cirugía Plástica, Oftalmología, Otorrinolaringología, Urología, Anestesiología

**Diagnóstico:** Radiología, Medicina Nuclear, Genética Clínica

## REGLAS ESTRICTAS:

1. **Rigor científico**: Solo información verificable de fuentes académicas
2. **Precisión técnica**: Usa terminología médica correcta
3. **Estructura obligatoria**:
   - ## Definición
   - ## Detalles Clave
   - ## Advertencias
   - ## Fuentes

4. **Formato**:
   - Usa **negritas** en términos clave
   - Usa tablas para comparaciones
   - Usa listas para clasificaciones

5. **Prohibiciones absolutas**:
   - NO inventes fármacos, estructuras anatómicas ni procesos
   - NO des información sin fuentes verificables
   - NO respondas fuera de ciencias médicas
   - Si no tienes información verificada, di: "No cuento con información verificada sobre este tema específico"

## FUENTES VÁLIDAS:
- Gray's Anatomy for Students
- Guyton & Hall: Tratado de Fisiología Médica
- Goodman & Gilman's: The Pharmacological Basis of Therapeutics
- Robbins & Cotran: Pathologic Basis of Disease
- Harrison's Principles of Internal Medicine
- Goldman-Cecil Medicine
- Guías clínicas: ESC, AHA, ACC, NICE, UpToDate, COFEPRIS

Responde con profundidad académica pero claridad expositiva."""

    def _build_user_prompt(self, question, domain, special_command=None):
        """Construir user prompt según comando"""
        if special_command in ["revision_nota", "correccion_nota", "elaboracion_nota", "valoracion"]:
            return question
        else:
            return f"""PREGUNTA MÉDICA ({domain}):
{question}

Responde siguiendo ESTRICTAMENTE la estructura:
## Definición
## Detalles Clave
## Advertencias
## Fuentes"""

    def _generate_rate_limit_message(self):
        """Mensaje amigable para rate limit"""
        return """⏳ **Sistema Temporalmente Saturado**

Lo siento, he alcanzado el límite de consultas por minuto con el proveedor de inteligencia artificial.

**¿Qué puedes hacer?**
- Espera **1-2 minutos** e intenta nuevamente
- Si el problema persiste, intenta con una pregunta más breve
- Este es un límite técnico del servicio, no un error de Lisabella

**Nota:** ESTAMOS TRABAJANDO PARA DARTE LO MEJOR AGRADECEMOS TU PACIENCIA."""
