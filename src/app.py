import sys
sys.path.insert(0, '/home/ray/lisabella')

from flask import Flask, request, jsonify
from flask_cors import CORS
from src.main import Lisabella

app = Flask(__name__)
CORS(app)
lisabella = Lisabella()

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'status': 'error', 'response': 'Por favor, escribe una pregunta'}), 400
    
    result = lisabella.ask(question)
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Lisabella está funcionando'})

if __name__ == '__main__':
    print("🏥 Lisabella backend iniciado en http://localhost:5000")
    app.run(debug=True, port=5000)
