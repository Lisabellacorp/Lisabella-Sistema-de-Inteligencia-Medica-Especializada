from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from src.main import Lisabella
import os

app = Flask(__name__)

# CORS: Permitir llamadas desde cualquier origen (cambiar en producción)
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Inicializar Lisabella
lisabella = Lisabella()

@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    """Endpoint principal para consultas médicas"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({
                "status": "error",
                "response": "Pregunta vacía"
            }), 400
        
        # Procesar pregunta con Lisabella
        result = lisabella.ask(question)
        return jsonify(result)
    
    except Exception as e:
        print(f"❌ Error en /ask: {str(e)}")
        return jsonify({
            "status": "error",
            "response": f"Error del servidor: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check para Render"""
    return jsonify({
        "status": "ok",
        "message": "Lisabella está funcionando",
        "version": "1.0"
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Página principal de Lisabella - Sirve el HTML"""
    return render_template('lisabella.html')

@app.route('/api', methods=['GET'])
def api_info():
    """Información del API"""
    return jsonify({
        "name": "Lisabella API",
        "version": "1.0",
        "endpoints": {
            "/": "GET - Interfaz web de Lisabella",
            "/ask": "POST - Consultar a Lisabella",
            "/health": "GET - Estado del servidor",
            "/api": "GET - Info del API"
        }
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
