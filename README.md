# 🏥 Lisabella

Asistente médico basado en IA. Responde preguntas sobre ciencias de la salud exactas con rigor científico.

## Características

- ✅ Wrapper inteligente (filtra, rechaza, reformula)
- ✅ Respuestas estructuradas jerárquicamente
- ✅ Validación de dominio médico
- ✅ Evita alucinaciones
- ✅ CLI interactivo

## Dominios Permitidos

Anatomía, Fisiología, Farmacología, Bioquímica, Patología, Microbiología, Genética, Cirugía, Radiología

## Instalación
```bash
git clone https://github.com/YOU/lisabella.git
cd lisabella
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tu MISTRAL_API_KEY
```

## Uso
```bash
python src/main.py
```

Ejemplos:
```
💬 ¿Dónde se ubica la arteria braquial?
✅ [Respuesta estructurada con definición, anatomía, advertencias, fuentes]

💬 Estoy triste, ¿qué hago?
❌ Lisabella no responde preguntas psicológicas

💬 ¿Qué es la diabetes?
💡 Tu pregunta es ambigua. Sé más específico: ¿fisiopatología? ¿parámetros?
```

## Tests
```bash
pytest tests/ -v
```

## Roadmap

- Fase 1 (Semana 1): MVP
- Fase 2 (Semana 2): Refinamiento + usuarios
- Fase 3 (Semana 3-4): Interfaz HTML/Web

## Licencia

MIT
