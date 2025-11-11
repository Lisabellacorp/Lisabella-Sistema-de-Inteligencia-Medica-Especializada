from flask import Flask, render_template, request, jsonify, Response
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# ✅ Cargar variables de entorno ANTES de importar clientes
load_dotenv()

# ✅ CAMBIADO: src.mistral (no src.groq_client)
from src.mistral import MistralClient
from src.wrapper import Wrapper, Result
from src.amplitud_detector import evaluar_y_reformular

app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Inicializar clientes ---
try:
    mistral_client = MistralClient()  # ✅ CAMBIADO: mistral_client
    wrapper = Wrapper()
    print("✅ Lisabella iniciada correctamente con Mistral")  # ✅ CAMBIADO
    print(f"📊 Wrapper stats: {wrapper.get_stats()}")
    print(f"🤖 Modelo: {mistral_client.model}")  # ✅ CAMBIADO
except Exception as e:
    print(f"❌ Error al inicializar: {str(e)}")
    print("⚠️ Verifica que MISTRAL_KEY esté configurada en Render")  # ✅ CAMBIADO
    mistral_client = None  # ✅ CAMBIADO
    wrapper = None

# --- Ruta principal ---
@app.route('/')
def index():
    return render_template('lisabella.html')

# --- Healthcheck ---
@app.route('/health')
def health():
    if not mistral_client or not wrapper:  # ✅ CAMBIADO
        return jsonify({
            "status": "error",
            "message": "Sistema no inicializado - verifica MISTRAL_KEY en Environment Variables",  # ✅ CAMBIADO
            "timestamp": str(datetime.now())
        }), 500
    
    return jsonify({
        "status": "ok",
        "timestamp": str(datetime.now()),
        "wrapper_stats": wrapper.get_stats(),
        "model": mistral_client.model,  # ✅ CAMBIADO
        "provider": "Mistral"  # ✅ CAMBIADO
    })

# --- API Legacy (no stream) - DEPRECATED pero funcional ---
@app.route('/ask', methods=['POST'])
def ask():
    """API sin streaming - mantener por compatibilidad"""
    if not mistral_client or not wrapper:  # ✅ CAMBIADO
        return jsonify({
            "status": "error",
            "response": "⚠️ Sistema no inicializado. Verifica MISTRAL_KEY en Render."  # ✅ CAMBIADO
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
        
        response = mistral_client.generate(question, domain, special_command)  # ✅ CAMBIADO
        
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
    """API con streaming en tiempo real usando Mistral"""  # ✅ CAMBIADO
    if not mistral_client or not wrapper:  # ✅ CAMBIADO
        return jsonify({
            "status": "error",
            "response": "⚠️ Sistema no inicializado. Verifica MISTRAL_KEY en Render."  # ✅ CAMBIADO
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
                    "provider": "Mistral"  # ✅ CAMBIADO
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
                
                # APPROVED - Verificar amplitud ANTES de consumir tokens
                domain = classification.get("domain", "medicina general")
                special_command = classification.get("special_command", None)
                note_analysis = classification.get("note_analysis", False)
                
                # ═══════════════════════════════════════════════════════
                # DETECCIÓN DE AMPLITUD SEMÁNTICA (antes de consumir tokens)
                # ═══════════════════════════════════════════════════════
                # NO aplicar a comandos especiales (notas médicas, valoraciones)
                if not special_command and not note_analysis:
                    es_amplia, reformulacion = evaluar_y_reformular(question, domain)
                    
                    if es_amplia:
                        yield json.dumps({
                            "type": "complete",
                            "data": {
                                "status": "reformulate",
                                "response": reformulacion
                            }
                        }) + "\n"
                        return
                
                # Pregunta específica - proceder con streaming
                yield json.dumps({"type": "init"}) + "\n"
                
                # ✅ IMPORTANTE: Mistral no tiene streaming nativo, usar generate normal
                response = mistral_client.generate(question, domain, special_command)  # ✅ CAMBIADO
                
                # Simular streaming dividiendo la respuesta
                chunk_size = 100
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i + chunk_size]
                    yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
                    time.sleep(0.01)  # Pequeña pausa para efecto streaming
                
                yield json.dumps({"type": "done"}) + "\n"
                
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
    print(f"🚀 Iniciando Lisabella con Mistral en puerto {port}")  # ✅ CAMBIADO
    app.run(host="0.0.0.0", port=port, debug=False)
