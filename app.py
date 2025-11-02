from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import Lisabella

app = Flask(__name__, static_folder='templates', static_url_path='')

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
    print(f"✅ [{datetime.now()}] Lisabella inicializada")
except Exception as e:
    print(f"❌ [{datetime.now()}] Error: {str(e)}")
    lisabella = None


@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    """Endpoint principal (SIN streaming)"""
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
        
        print(f"📥 [{datetime.now()}] {question[:50]}...")
        
        # Procesar con Lisabella (sin streaming)
        result = lisabella.ask(question)
        
        print(f"✅ [{datetime.now()}] Respuesta generada")
        return jsonify(result)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
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
        "message": "Lisabella funcionando" if lisabella else "Error",
        "version": "2.0-no-streaming",
        "timestamp": str(datetime.now())
    }), 200 if lisabella else 500


@app.route('/', methods=['GET'])
def home():
    """Servir HTML"""
    try:
        return app.send_static_file('lisabella.html')
    except Exception as e:
        return jsonify({
            "name": "Lisabella API",
            "version": "2.0-no-streaming",
            "endpoints": {
                "/ask": "POST - Consultar",
                "/health": "GET - Estado"
            }
        }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
