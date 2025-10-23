from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import signal
import time
from datetime import datetime

# ✅ FIX: Agregar directorio raíz al path (compatible con Render)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import Lisabella

app = Flask(__name__)

# CORS: Restringir a frontend en producción
CORS(app, resources={
    r"/*": {
        "origins": ["https://lisabella.vercel.app"],  # 🔐 Cambiar a tu URL de Vercel
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Inicializar Lisabella
try:
    lisabella = Lisabella()
    print(f"✅ [{datetime.now()}] Lisabella inicializada correctamente")
except Exception as e:
    print(f"❌ [{datetime.now()}] Error al inicializar Lisabella: {str(e)}")
    lisabella = None

# Manejador de timeout
def timeout_handler(signum, frame):
    raise TimeoutError("Request excedió el tiempo máximo")

@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    """Endpoint principal para consultas médicas"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if not lisabella:
        return jsonify({
            "status": "error",
            "response": "Sistema no inicializado correctamente"
        }), 500
    
    try:
        # Establecer timeout de 110s (menor que el de Gunicorn: 120s)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(110)
        
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({
                "status": "error",
                "response": "Pregunta vacía"
            }), 400
        
        # Log de inicio para debug
        start_time = time.time()
        print(f"📥 [{datetime.now()}] Procesando pregunta: {question[:50]}...")
        
        # Procesar pregunta con Lisabella
        result = lisabella.ask(question)
        
        # Log de éxito
        print(f"✅ [{datetime.now()}] Respuesta generada en {time.time() - start_time:.2f}s")
        return jsonify(result)
    
    except TimeoutError:
        print(f"⏰ [{datetime.now()}] Timeout en /ask para: {question[:50]}")
        return jsonify({
            "status": "error",
            "response": "Consulta demasiado compleja. Simplifica la pregunta."
        }), 408
    except Exception as e:
        print(f"❌ [{datetime.now()}] Error en /ask: {str(e)}")
        return jsonify({
            "status": "error",
            "response": f"Error del servidor: {str(e)}"
        }), 500
    finally:
        signal.alarm(0)  # Desactivar timeout

@app.route('/health', methods=['GET'])
def health():
    """Health check para Render"""
    status = "ok" if lisabella else "error"
    return jsonify({
        "status": status,
        "message": "Lisabella está funcionando" if lisabella else "Sistema no inicializado",
        "version": "1.0",
        "timestamp": str(datetime.now())
    }), 200 if lisabella else 500

@app.route('/', methods=['GET'])
def home():
    """Redirigir a documentación"""
    return jsonify({
        "name": "Lisabella API",
        "version": "1.0",
        "status": "online",
        "endpoints": {
            "/ask": "POST - Consultar a Lisabella (envía JSON: {\"question\": \"tu pregunta\"})",
            "/health": "GET - Estado del servidor",
            "/": "GET - Info del API"
        },
        "frontend": "Despliega lisabella.html en Vercel y apunta a esta URL"
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
