#!/usr/bin/env python3
"""
Test unitario rápido del detector de amplitud (sin llamar a Mistral)
"""

import sys
import os

# Agregar el directorio raíz al path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

from src.amplitud_detector import detectar_amplitud, evaluar_y_reformular

def test_amplitud_simple():
    """Prueba la lógica de detección sin llamar a Mistral"""
    
    tests = [
        {
            "nombre": "TEST 1: Pregunta específica (score debe ser < 7)",
            "query": "Irrigación arterial del hueso coxal",
            "domain": "anatomía",
            "max_score_permitido": 6
        },
        {
            "nombre": "TEST 2: Pregunta amplia (score debe ser >= 7)",
            "query": "Estructura anatómica del corazón",
            "domain": "anatomía",
            "min_score_esperado": 7
        },
        {
            "nombre": "TEST 3: Pregunta específica (score debe ser < 7)",
            "query": "Mecanismo de acción del ácido acetilsalicílico",
            "domain": "farmacología",
            "max_score_permitido": 6
        },
        {
            "nombre": "TEST 4: Pregunta ultra amplia (score debe ser >= 7)",
            "query": "Todo sobre el sistema cardiovascular",
            "domain": "cardiología",
            "min_score_esperado": 7
        }
    ]
    
    print("=" * 80)
    print("🧪 PRUEBAS UNITARIAS - DETECTOR DE AMPLITUD")
    print("=" * 80)
    print()
    
    resultados = []
    
    for i, test in enumerate(tests, 1):
        print(f"\n{'='*80}")
        print(f"{test['nombre']}")
        print(f"{'='*80}")
        print(f"📝 Pregunta: \"{test['query']}\"")
        print(f"📊 Dominio: {test['domain']}")
        
        try:
            score = detectar_amplitud(test['query'], test['domain'])
            print(f"📈 Score obtenido: {score}/10")
            
            # Validar según criterio
            if 'max_score_permitido' in test:
                if score <= test['max_score_permitido']:
                    print(f"✅ TEST PASÓ: Score {score} <= {test['max_score_permitido']} (específica)")
                    resultados.append(True)
                else:
                    print(f"❌ TEST FALLÓ: Score {score} > {test['max_score_permitido']} (debería ser específica)")
                    resultados.append(False)
            
            elif 'min_score_esperado' in test:
                if score >= test['min_score_esperado']:
                    print(f"✅ TEST PASÓ: Score {score} >= {test['min_score_esperado']} (amplia)")
                    resultados.append(True)
                else:
                    print(f"❌ TEST FALLÓ: Score {score} < {test['min_score_esperado']} (debería ser amplia)")
                    resultados.append(False)
            
            # Probar función de reformulación
            es_amplia, reformulacion = evaluar_y_reformular(test['query'], test['domain'])
            print(f"🔍 ¿Requiere reformulación? {es_amplia}")
            
            if es_amplia:
                print(f"📝 Reformulación generada ({len(reformulacion)} caracteres)")
                print("-" * 80)
                print(reformulacion[:300])
                if len(reformulacion) > 300:
                    print("...")
                print("-" * 80)
            
        except Exception as e:
            print(f"❌ ERROR en test: {str(e)}")
            resultados.append(False)
            import traceback
            traceback.print_exc()
    
    # Resumen final
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 80)
    pasados = sum(resultados)
    total = len(resultados)
    print(f"✅ Tests pasados: {pasados}/{total}")
    print(f"❌ Tests fallidos: {total - pasados}/{total}")
    
    if all(resultados):
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        return 0
    else:
        print("\n⚠️ ALGUNOS TESTS FALLARON")
        return 1

if __name__ == "__main__":
    exit_code = test_amplitud_simple()
    sys.exit(exit_code)

