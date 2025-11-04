from flask import Flask, render_template, request, jsonify, Response
import time, json
from datetime import datetime
from mistral import MistralClient

app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Inicializar cliente ---
mistral_client = MistralClient()

# --- Healthcheck ---
@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": str(datetime.now())})

# --- Frontend principal ---
@app.route('/')
def index():
    return render_template('lisabella.html')

# --- API Legacy (no stream) ---
@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    return jsonify({"answer": mistral_client.generate(question)})

# --- API Streaming ---
@app.route('/ask_stream', methods=['POST'])
def ask_stream():
    data = request.get_json()
    question = data.get("question", "")

    def generate():
        try:
            for chunk in mistral_client.generate_stream(question):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype='text/event-stream')

# --- Favicon (evitar 404) ---
@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
