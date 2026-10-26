import numpy as np
import pytest

from agente_zoco.buscador.vectorial import similitud_coseno

def test_coseno():
    consulta = np.array([1.0, 2.0, 2.0])
    matriz = np.array([[2.0, 1.0, 2.0]])
    assert similitud_coseno(consulta, matriz) == pytest.approx([8 / 9])

def test_casos():
    consulta = np.array([1.0, 0.0])
    matriz = np.array([
        [2.0, 0.0],    # misma dirección, otro largo -> 1
        [0.0, 1.0],    # perpendicular               -> 0
        [-1.0, 0.0],   # opuesto                     ->-1
    ])
    assert similitud_coseno(consulta, matriz) == pytest.approx([1.0, 0.0, -1.0])

def test_vector_cero():
    assert similitud_coseno(np.array([1.0, 0.0]), np.array([[0.0, 0.0]])) == pytest.approx([0.0])
