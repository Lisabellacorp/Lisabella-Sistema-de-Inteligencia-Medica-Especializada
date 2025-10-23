# app.py TEMPORAL para debug
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        # Respuesta temporal mínima
        return jsonify({
            'status': 'success',
            'response': f'✅ **Debug Mode**\n\nPregunta recibida: {question[:100]}...\n\nEl sistema está en mantenimiento técnico. Volveremos pronto.'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'response': f'❌ Error: {str(e)}'
        })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Server running'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
