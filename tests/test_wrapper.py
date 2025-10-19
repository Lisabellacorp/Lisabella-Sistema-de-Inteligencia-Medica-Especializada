import pytest
from src.wrapper import Wrapper, Result

@pytest.fixture
def wrapper():
    return Wrapper()

class TestWrapper:
    
    def test_anatomy_approved(self, wrapper):
        """Anatomía debe ser APROBADA"""
        result = wrapper.classify("¿Dónde se ubica la arteria braquial?")
        assert result["result"] == Result.APPROVED
        assert result["domain"] == "anatomía"
    
    def test_pharmacology_approved(self, wrapper):
        """Farmacología debe ser APROBADA"""
        result = wrapper.classify("¿Cuál es el mecanismo de acción del ibuprofeno?")
        assert result["result"] == Result.APPROVED
        assert result["domain"] == "farmacología"
    
    def test_emotional_rejected(self, wrapper):
        """Pregunta emocional debe ser RECHAZADA"""
        result = wrapper.classify("Estoy triste, ¿qué hago?")
        assert result["result"] == Result.REJECTED
    
    def test_financial_rejected(self, wrapper):
        """Pregunta financiera debe ser RECHAZADA"""
        result = wrapper.classify("¿Cómo invierto en Pfizer?")
        assert result["result"] == Result.REJECTED
    
    def test_ambiguous_reformulate(self, wrapper):
        """Pregunta ambigua debe REFORMULAR"""
        result = wrapper.classify("¿Qué es la salud?")
        assert result["result"] == Result.REFORMULATE
