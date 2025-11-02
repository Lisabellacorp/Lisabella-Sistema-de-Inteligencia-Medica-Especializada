from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import Lisabella
from src.wrapper import Result

app = Flask(__name__, static_folder='templates', static_url_path='')

CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

try:
    lisabella = Lisabella()
    print(f"✅ [{datetime.now()}] Lisabella inicializada correctamente")
except Exception as e:
    print(f"❌ [{datetime.now()}] Error al inicializar Lisabella: {str(e)}")
    lisabella = None


@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    """Endpoint legacy (sin streaming)"""
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
    """🚀 Endpoint con streaming optimizado para Render"""
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
            """Generator optimizado para evitar timeout de Render"""
            try:
                # ✅ RESPUESTA INMEDIATA (antes de 30s de Render)
                yield json.dumps({
                    "type": "init",
                    "message": "🔍 Analizando tu pregunta médica..."
                }) + '\n'
                sys.stdout.flush()
                
                # Clasificar pregunta (rápido, <2s)
                classification = lisabella.wrapper.classify(question)
                result = classification["result"]
                
                # Si rechazada/reformular → enviar completo
                if result in [Result.REJECTED, Result.REFORMULATE]:
                    response_obj = lisabella.ask(question)
                    yield json.dumps({"type": "complete", "data": response_obj}) + '\n'
                    sys.stdout.flush()
                    return
                
                # Aprobada → enviar metadata
                domain = classification.get("domain", "medicina general")
                special_cmd = classification.get("special_command")
                
                yield json.dumps({
                    "type": "metadata",
                    "domain": domain,
                    "special_command": special_cmd,
                    "status": "approved"
                }) + '\n'
                sys.stdout.flush()
                
                # 🚀 STREAMING de tokens
                buffer = ""
                chunk_index = 0
                stream_done = False
                last_activity = time.time()
                CHUNK_SIZE = 200  # Chunks más grandes para menos overhead
                
                for token in lisabella.mistral.generate_stream(question, domain, special_cmd):
                    # Detectar señales de finalización
                    if token in ["__STREAM_DONE__", "[STREAM_COMPLETE]"]:
                        if buffer:
                            yield json.dumps({
                                "type": "chunk",
                                "index": chunk_index,
                                "content": buffer
                            }) + '\n'
                            sys.stdout.flush()
                        
                        yield json.dumps({"type": "done"}) + '\n'
                        sys.stdout.flush()
                        print(f"✅ STREAM [{datetime.now()}] Completado correctamente")
                        stream_done = True
                        return
                    
                    buffer += token
                    
                    # Enviar chunks cuando sea razonable
                    if len(buffer) >= CHUNK_SIZE or token in ['.', '\n\n', '\n##']:
                        yield json.dumps({
                            "type": "chunk",
                            "index": chunk_index,
                            "content": buffer
                        }) + '\n'
                        sys.stdout.flush()
                        chunk_index += 1
                        buffer = ""
                        last_activity = time.time()
                
                # Fallback: enviar buffer final si quedó algo
                if not stream_done:
                    if buffer:
                        yield json.dumps({
                            "type": "chunk",
                            "index": chunk_index,
                            "content": buffer
                        }) + '\n'
                        sys.stdout.flush()
                    
                    yield json.dumps({"type": "done"}) + '\n'
                    sys.stdout.flush()
                    print(f"⚠️ STREAM [{datetime.now()}] Completado sin señal explícita")
                
            except Exception as e:
                print(f"❌ Error en stream: {str(e)}")
                import traceback
                traceback.print_exc()
                yield json.dumps({
                    "type": "error",
                    "message": f"Error: {str(e)[:150]}"
                }) + '\n'
                sys.stdout.flush()
        
        return Response(
            generate(),
            mimetype='application/x-ndjson',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-ndjson; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"❌ [{datetime.now()}] Error crítico: {str(e)}")
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
        "version": "1.2-render-optimized",
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
                "/ask_stream": "POST - Consultar con streaming",
                "/health": "GET - Estado"
            }
        }), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
