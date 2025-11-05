# Lisabella - AI Medical Assistant

## Overview
Lisabella is a specialized medical AI assistant powered by Mistral AI. It provides rigorous, evidence-based answers to medical science questions, validated against international standards (Joint Commission, AHA/ESC, Mayo Clinic, COFEPRIS).

## Purpose
- Answer medical questions with scientific rigor
- Support medical students and healthcare professionals
- Provide structured, hierarchical responses
- Validate medical domain expertise
- Avoid hallucinations through intelligent question filtering

## Tech Stack
- **Backend**: Flask (Python 3.11)
- **AI Engine**: Mistral AI (mistral-large-latest)
- **Frontend**: Single-page HTML/CSS/JavaScript application
- **Production Server**: Gunicorn
- **Port**: 5000

## Project Structure
```
├── app.py                 # Main Flask application
├── src/
│   ├── config.py         # Configuration (API keys, model settings)
│   ├── mistral.py        # Mistral AI client with streaming support
│   ├── wrapper.py        # Question classification and validation
│   └── main.py           # CLI interface (optional)
├── templates/
│   └── lisabella.html    # Frontend interface
├── data/
│   ├── domains.json      # Medical domain keywords
│   └── prohibited.json   # Non-medical term filters
├── tests/                # Test suite
└── requirements.txt      # Python dependencies
```

## Features
- ✅ Intelligent question filtering (approves, rejects, or requests reformulation)
- ✅ Structured hierarchical responses
- ✅ Medical domain validation (46 medical specialties)
- ✅ Real-time streaming responses
- ✅ Special commands for medical notes analysis
- ✅ Token usage tracking
- ✅ Retry logic with exponential backoff

## Medical Domains Supported
Anatomy, Physiology, Pharmacology, Biochemistry, Pathology, Microbiology, Genetics, Surgery, Radiology, Cardiology, Neurology, Pediatrics, Gynecology/Obstetrics, Dermatology, Psychiatry, Emergency Medicine, and 30+ more specialties.

## Special Commands
- **Revision de nota**: Audit medical notes against JCI/Mayo standards
- **Elaboración de nota**: Generate SOAP format medical note templates
- **Valoración de paciente**: Provide diagnostic orientation for clinical cases
- **Cálculo de dosis**: Dosage calculations with safety checks
- **Apoyo en estudio**: Educational mode with analogies and clinical examples

## Environment Variables
- `MISTRAL_API_KEY`: API key for Mistral AI (required)
- `MISTRAL_MODEL`: Model to use (default: mistral-large-latest)
- `MISTRAL_TEMP`: Temperature for responses (default: 0.3)
- `PORT`: Server port (default: 5000)

## Deployment
The application is configured for autoscale deployment using Gunicorn with:
- 1 worker process
- 120 second timeout
- Port reuse enabled
- Binding to 0.0.0.0:5000

## Recent Changes
- **2025-11-05**: Initial Replit setup completed
  - Installed Python 3.11 and dependencies
  - Configured MISTRAL_API_KEY secret
  - Set up Flask development workflow
  - Configured deployment for production use
  - Application running successfully on port 5000

## Development
To run locally:
```bash
python app.py
```

To run tests:
```bash
pytest tests/ -v
```

## User Preferences
None documented yet.

## Notes
- The application uses streaming responses for better user experience
- Question classification happens before AI processing to save tokens
- All responses are validated against medical domain expertise
- Frontend is fully self-contained in lisabella.html
- Logs are stored in `logs/` directory (token usage tracking)
