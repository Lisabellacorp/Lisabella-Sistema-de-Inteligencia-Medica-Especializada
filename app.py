from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime

# ✅ FIX: Agregar directorio raíz al path (compatible con Render)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import Lisabella
from src.wrapper import Result

# ✅ Flask configurado para servir HTML desde templates/
app = Flask(__name__, static_folder='templates', static_url_path='')

# CORS abierto
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


@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    """Endpoint legacy (sin streaming) - mantener por compatibilidad"""
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
            return jsonify({
                "status": "error",
                "response": "Pregunta vacía"
            }), 400
        
        print(f"📥 [{datetime.now()}] /ask: {question[:50]}...")
        result = lisabella.ask(question)
        return jsonify(result)
    
    except Exception as e:
        print(f"❌ [{datetime.now()}] Error en /ask: {str(e)}")
        return jsonify({
            "status": "error",
            "response": f"Error: {str(e)}"
        }), 500


@app.route('/ask_stream', methods=['POST', 'OPTIONS'])
def ask_stream():
    """🚀 Endpoint CON STREAMING REAL (tokens en tiempo real)"""
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
            """Generator con streaming REAL de Mistral"""
            try:
                # 1. Clasificar pregunta (rápido, <1s)
                classification = lisabella.wrapper.classify(question)
                result = classification["result"]
                
                # 2. Si rechazada/reformular → enviar completo
                if result in [Result.REJECTED, Result.REFORMULATE]:
                    response_obj = lisabella.ask(question)
                    yield json.dumps({"type": "complete", "data": response_obj}) + '\n'
                    return
                
                # 3. Aprobada → enviar metadata
                domain = classification.get("domain", "medicina general")
                special_cmd = classification.get("special_command")
                
                yield json.dumps({
                    "type": "init",
                    "domain": domain,
                    "special_command": special_cmd,
                    "status": "approved"
                }) + '\n'
                
                # 4. 🚀 STREAMING REAL: Tokens conforme llegan de Mistral
                chunk_index = 0
                
                for token in lisabella.mistral.generate_stream(question, domain, special_cmd):
                    # 🆕 CORRECCIÓN: Enviar inmediatamente cada token sin acumular
                    # Esto evita que se rompan palabras artificialmente
                    yield json.dumps({
                        "type": "chunk",
                        "index": chunk_index,
                        "content": token  # 🆕 Cambio: enviar token directamente, no buffer
                    }) + '\n'
                    chunk_index += 1
                
                # 5. Finalizar
                yield json.dumps({"type": "done"}) + '\n'
                print(f"✅ STREAM [{datetime.now()}] Completado")
                
            except Exception as e:
                print(f"❌ Error en stream: {str(e)}")
                yield json.dumps({
                    "type": "error",
                    "message": f"Error: {str(e)}"
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
            "response": f"Error: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    status = "ok" if lisabella else "error"
    return jsonify({
        "status": status,
        "message": "Lisabella funcionando" if lisabella else "Sistema no inicializado",
        "version": "1.0-streaming",
        "timestamp": str(datetime.now())
    }), 200 if lisabella else 500


@app.route('/', methods=['GET'])
def home():
    """Servir HTML"""
    try:
        return app.send_static_file('lisabella.html')
    except Exception as e:
        return jsonify({
            "error": "Frontend no encontrado",
            "message": str(e),
            "endpoints": {
                "/ask": "POST - Consultar (legacy)",
                "/ask_stream": "POST - Consultar con streaming REAL",
                "/health": "GET - Estado"
            }
        }), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
