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
    """🚀 SSE Streaming - Sin límite de timeout"""
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
        
        print(f"📥 SSE [{datetime.now()}] Procesando: {question[:50]}...")
        
        def generate():
            """Generator en formato SSE"""
            try:
                # Respuesta inmediata
                yield f"data: {json.dumps({'type': 'init', 'message': '🔍 Analizando tu pregunta médica...'})}\n\n"
                
                # Clasificar pregunta
                classification = lisabella.wrapper.classify(question)
                result = classification["result"]
                
                # Si rechazada/reformular
                if result in [Result.REJECTED, Result.REFORMULATE]:
                    response_obj = lisabella.ask(question)
                    yield f"data: {json.dumps({'type': 'complete', 'data': response_obj})}\n\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return
                
                # Aprobada - enviar metadata
                domain = classification.get("domain", "medicina general")
                special_cmd = classification.get("special_command")
                
                yield f"data: {json.dumps({'type': 'metadata', 'domain': domain, 'special_command': special_cmd, 'status': 'approved'})}\n\n"
                
                # Streaming de tokens
                buffer = ""
                chunk_index = 0
                CHUNK_SIZE = 200
                
                for token in lisabella.mistral.generate_stream(question, domain, special_cmd):
                    # Detectar finalización
                    if token in ["__STREAM_DONE__", "[STREAM_COMPLETE]"]:
                        if buffer:
                            yield f"data: {json.dumps({'type': 'chunk', 'index': chunk_index, 'content': buffer})}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        print(f"✅ SSE [{datetime.now()}] Completado correctamente")
                        return
                    
                    buffer += token
                    
                    # Enviar chunks
                    if len(buffer) >= CHUNK_SIZE or token in ['.', '\n\n', '\n##']:
                        yield f"data: {json.dumps({'type': 'chunk', 'index': chunk_index, 'content': buffer})}\n\n"
                        chunk_index += 1
                        buffer = ""
                
                # Fallback
                if buffer:
                    yield f"data: {json.dumps({'type': 'chunk', 'index': chunk_index, 'content': buffer})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                print(f"⚠️ SSE [{datetime.now()}] Completado sin señal explícita")
                
            except Exception as e:
                print(f"❌ Error en SSE: {str(e)}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(e)[:150]}'})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
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
        "version": "1.3-sse-optimized",
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
                "/ask_stream": "POST - Consultar con SSE streaming",
                "/health": "GET - Estado"
            }
        }, 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
