from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import sys
import signal
import time
import json
from datetime import datetime

# ✅ FIX: Agregar directorio raíz al path (compatible con Render)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import Lisabella
from src.wrapper import Result

app = Flask(__name__)

# CORS: Restringir a frontend en producción
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
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
    """Endpoint principal para consultas médicas (SIN STREAMING - legacy)"""
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


@app.route('/ask_stream', methods=['POST', 'OPTIONS'])
def ask_stream():
    """Endpoint CON STREAMING - versión funcional"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if not lisabella:
        return jsonify({
            "status": "error",
            "response": "Sistema no inicializado"
        }), 500
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({"status": "error", "response": "Pregunta vacía"}), 400
        
        print(f"📥 STREAM [{datetime.now()}] Procesando: {question[:50]}...")
        
        def generate():
            """Generator que simula streaming dividiendo la respuesta"""
            try:
                # 1. Clasificar pregunta (rápido, <1s)
                classification = lisabella.wrapper.classify(question)
                result = classification["result"]
                
                # 2. Si rechazada/reformular → enviar completo (es corto)
                if result in [Result.REJECTED, Result.REFORMULATE]:
                    response_obj = lisabella.ask(question)
                    yield json.dumps({"type": "complete", "data": response_obj}) + '\n'
                    return
                
                # 3. Aprobada → enviar metadata inicial
                domain = classification.get("domain", "medicina general")
                
                yield json.dumps({
                    "type": "init",
                    "domain": domain,
                    "status": "approved"
                }) + '\n'
                
                # 4. Generar respuesta COMPLETA
                response_obj = lisabella.ask(question)
                full_response = response_obj.get("response", "")
                
                # 5. Dividir respuesta en chunks (por párrafos o líneas)
                lines = full_response.split('\n')
                chunk_size = max(3, len(lines) // 8)  # ~8 chunks
                
                for i in range(0, len(lines), chunk_size):
                    chunk = '\n'.join(lines[i:i+chunk_size])
                    if chunk.strip():
                        yield json.dumps({
                            "type": "chunk",
                            "index": i // chunk_size,
                            "content": chunk + '\n'
                        }) + '\n'
                        time.sleep(0.1)  # Pausa para simular streaming
                
                # 6. Finalizar
                yield json.dumps({"type": "done"}) + '\n'
                print(f"✅ STREAM [{datetime.now()}] Completado correctamente")
                
            except Exception as e:
                print(f"❌ Error en stream: {str(e)}")
                yield json.dumps({
                    "type": "error",
                    "message": f"Error al generar respuesta: {str(e)}"
                }) + '\n'
        
        return Response(
            generate(),
            mimetype='application/x-ndjson',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        print(f"❌ [{datetime.now()}] Error crítico en /ask_stream: {str(e)}")
        return jsonify({
            "status": "error",
            "response": f"Error del servidor: {str(e)}"
        }), 500


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
            "/ask": "POST - Consultar a Lisabella (legacy, sin streaming)",
            "/ask_stream": "POST - Consultar con streaming (RECOMENDADO)",
            "/health": "GET - Estado del servidor",
            "/": "GET - Info del API"
        },
        "frontend": "https://lisabellacorp.github.io/lisabella/"
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
