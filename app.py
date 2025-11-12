from flask import Flask, render_template, request, jsonify, Response
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# ✅ Cargar variables de entorno ANTES de importar clientes
load_dotenv()

# ✅ Importaciones corregidas (SIN amplitud_detector)
from src.openai_client import OpenAIClient
from src.wrapper import Wrapper, Result

app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Inicializar clientes ---
try:
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY no encontrada en variables de entorno")
    
    openai_client = OpenAIClient()
    wrapper = Wrapper()
    print("✅ Lisabella iniciada correctamente con OpenAI")
    print(f"📊 Wrapper stats: {wrapper.get_stats()}")
    print(f"🤖 Modelo: {openai_client.model}")
except ValueError as ve:
    print(f"❌ Error de configuración: {str(ve)}")
    print("⚠️ SOLUCIÓN: Configura OPENAI_API_KEY en Render → Environment Variables")
    openai_client = None
    wrapper = None
except Exception as e:
    print(f"❌ Error inesperado al inicializar: {str(e)}")
    import traceback
    traceback.print_exc()
    openai_client = None
    wrapper = None

# --- Ruta principal ---
@app.route('/')
def index():
    return render_template('lisabella.html')

# --- Healthcheck ---
@app.route('/health')
def health():
    if not openai_client or not wrapper:
        return jsonify({
            "status": "error",
            "message": "Sistema no inicializado - verifica OPENAI_API_KEY en Environment Variables",
            "timestamp": str(datetime.now())
        }), 500
    
    return jsonify({
        "status": "ok",
        "timestamp": str(datetime.now()),
        "wrapper_stats": wrapper.get_stats(),
        "model": openai_client.model,
        "provider": "OpenAI"
    })

# --- API Legacy (no stream) - DEPRECATED pero funcional ---
@app.route('/ask', methods=['POST'])
def ask():
    """API sin streaming - mantener por compatibilidad"""
    if not openai_client or not wrapper:
        return jsonify({
            "status": "error",
            "response": "⚠️ Sistema no inicializado. Verifica OPENAI_API_KEY en Render."
        }), 500
    
    try:
        data = request.get_json()
        question = data.get("question", "")
        
        if not question:
            return jsonify({
                "status": "rejected",
                "response": "❌ Pregunta vacía"
            }), 400
        
        # ✅ Clasificar pregunta con Wrapper
        classification = wrapper.classify(question)
        
        if classification["result"] == Result.REJECTED:
            return jsonify({
                "status": "rejected",
                "response": f"**❌ {classification['reason']}**\n\n{classification.get('suggestion', '')}"
            })
        
        elif classification["result"] == Result.REFORMULATE:
            return jsonify({
                "status": "reformulate",
                "response": f"**💡 {classification['reason']}**\n\n{classification.get('suggestion', '')}"
            })
        
        # APPROVED - Generar respuesta
        domain = classification.get("domain", "medicina general")
        special_command = classification.get("special_command", None)
        
        response = openai_client.generate(question, domain, special_command)
        
        return jsonify({
            "status": "approved",
            "response": response,
            "domain": domain
        })
    
    except Exception as e:
        print(f"❌ Error en /ask: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "response": f"⚠️ Error del servidor: {str(e)[:200]}"
        }), 500

# --- API Streaming (PRINCIPAL) ---
@app.route('/ask_stream', methods=['POST'])
def ask_stream():
    """API con streaming en tiempo real usando OpenAI"""
    if not openai_client or not wrapper:
        return jsonify({
            "status": "error",
            "response": "⚠️ Sistema no inicializado. Verifica OPENAI_API_KEY en Render."
        }), 500
    
    try:
        data = request.get_json()
        question = data.get("question", "")
        
        if not question:
            def error_gen():
                yield json.dumps({"type": "error", "message": "Pregunta vacía"}) + "\n"
            return Response(error_gen(), mimetype='application/json')
        
        def generate():
            try:
                # ✅ Clasificar pregunta primero
                classification = wrapper.classify(question)
                
                # Enviar metadata inicial
                yield json.dumps({
                    "type": "metadata",
                    "domain": classification.get("domain", "medicina general"),
                    "confidence": classification.get("confidence", 0.5),
                    "provider": "OpenAI"
                }) + "\n"
                
                # Si rechazada o reformular, enviar respuesta completa
                if classification["result"] == Result.REJECTED:
                    yield json.dumps({
                        "type": "complete",
                        "data": {
                            "status": "rejected",
                            "response": f"**❌ {classification['reason']}**\n\n{classification.get('suggestion', '')}"
                        }
                    }) + "\n"
                    return
                
                elif classification["result"] == Result.REFORMULATE:
                    yield json.dumps({
                        "type": "complete",
                        "data": {
                            "status": "reformulate",
                            "response": f"**💡 {classification['reason']}**\n\n{classification.get('suggestion', '')}"
                        }
                    }) + "\n"
                    return
                
                # APPROVED - Proceder con streaming
                domain = classification.get("domain", "medicina general")
                special_command = classification.get("special_command", None)
                
                # Iniciar streaming
                yield json.dumps({"type": "init"}) + "\n"
                
                # ✅ Streaming nativo de OpenAI
                for chunk in openai_client.generate_stream(question, domain, special_command):
                    if chunk == "__STREAM_DONE__":
                        yield json.dumps({"type": "done"}) + "\n"
                        break
                    else:
                        yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
                
            except Exception as e:
                print(f"❌ Error en streaming: {str(e)}")
                import traceback
                traceback.print_exc()
                yield json.dumps({
                    "type": "error",
                    "message": f"Error del sistema: {str(e)[:200]}"
                }) + "\n"
        
        # ✅ Response optimizado para streaming continuo
        response = Response(
            generate(),
            mimetype='application/json',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
        return response
    
    except Exception as e:
        print(f"❌ Error crítico en /ask_stream: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Favicon (evitar 404) ---
@app.route('/favicon.ico')
def favicon():
    return '', 204

# --- Crear directorio de logs si no existe ---
os.makedirs('logs', exist_ok=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Iniciando Lisabella con OpenAI en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
