import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ✅ CARGA SEGURA DE LISABELLA
try:
    # Agregar ruta para imports en Render
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(current_dir, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    from main import Lisabella
    LISABELLA_READY = True
    print("✅ Lisabella cargada correctamente")
    
except ImportError as e:
    LISABELLA_READY = False
    print(f"❌ Error importando Lisabella: {e}")

@app.route('/ask', methods=['POST'])
def ask():
    if not LISABELLA_READY:
        return jsonify({
            'status': 'error',
            'response': '🔧 **Sistema en configuración**\n\nLisabella no pudo cargar correctamente. Error de importación.'
        })
    
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'status': 'error', 'response': 'Por favor, escribe una pregunta'}), 400
        
        lisabella = Lisabella()
        result = lisabella.ask(question)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'response': f'❌ **Error procesando pregunta**\n\nDetalle: {str(e)[:200]}'
        })

@app.route('/health', methods=['GET'])
def health():
    status = 'ready' if LISABELLA_READY else 'configuring'
    return jsonify({
        'status': status,
        'message': 'Lisabella Medical AI',
        'version': '1.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=False, port=port, host='0.0.0.0')
