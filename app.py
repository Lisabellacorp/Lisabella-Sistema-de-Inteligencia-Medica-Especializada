from flask import Flask, render_template, request, jsonify, Response
import time
import json
from datetime import datetime

# ✅ Imports corregidos
from src.mistral import MistralClient
from src.wrapper import Wrapper, Result

app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Inicializar clientes ---
mistral_client = MistralClient()
wrapper = Wrapper()

print("✅ Lisabella iniciada correctamente")
print(f"📊 Wrapper stats: {wrapper.get_stats()}")

# --- Healthcheck ---
@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "timestamp": str(datetime.now()),
        "wrapper_stats": wrapper.get_stats()
    })

# --- Frontend principal ---
@app.route('/')
def index():
    return render_template('lisabella.html')

# --- API Legacy (no stream) - DEPRECATED pero funcional ---
@app.route('/ask', methods=['POST'])
def ask():
    """API sin streaming - mantener por compatibilidad"""
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
        
        response = mistral_client.generate(question, domain, special_command)
        
        return jsonify({
            "status": "approved",
            "response": response,
            "domain": domain
        })
    
    except Exception as e:
        print(f"❌ Error en /ask: {str(e)}")
        return jsonify({
            "status": "error",
            "response": f"⚠️ Error del servidor: {str(e)[:200]}"
        }), 500

# --- API Streaming (PRINCIPAL) ---
@app.route('/ask_stream', methods=['POST'])
def ask_stream():
    """API con streaming en tiempo real"""
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
                    "confidence": classification.get("confidence", 0.5)
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
                
                # APPROVED - Streaming real
                domain = classification.get("domain", "medicina general")
                special_command = classification.get("special_command", None)
                
                yield json.dumps({"type": "init"}) + "\n"
                
                # ✅ Stream de Mistral con domain y special_command
                for chunk in mistral_client.generate_stream(question, domain, special_command):
                    if chunk == "__STREAM_DONE__":
                        yield json.dumps({"type": "done"}) + "\n"
                        break
                    else:
                        yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
                
                # Ping final para mantener conexión
                yield json.dumps({"type": "ping"}) + "\n"
                
            except Exception as e:
                print(f"❌ Error en streaming: {str(e)}")
                yield json.dumps({
                    "type": "error",
                    "message": f"Error del sistema: {str(e)[:200]}"
                }) + "\n"
        
        return Response(generate(), mimetype='application/json')
    
    except Exception as e:
        print(f"❌ Error crítico en /ask_stream: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- Favicon (evitar 404) ---
@app.route('/favicon.ico')
def favicon():
    return '', 204

# --- Crear directorio de logs si no existe ---
import os
os.makedirs('logs', exist_ok=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)  # ✅ debug=False en producción
