from agente_zoco.buscador.bm25 import tokenizar
from agente_zoco.buscador.bm25 import calcular_idf
from agente_zoco.buscador.bm25 import BM25
import pytest

def test_la_puntuacion_separa_palabras():
    assert tokenizar("¿Cuánto cobra ZT-PRO-2? 5,0%") == ["cuanto", "cobra", "zt", "pro", "2", "5", "0"]

def test_pregunta_y_documento_coinciden():
    assert tokenizar("mínimo de entradas") == tokenizar("MINIMO DE ENTRADAS")

CHUNKS = [
    ["plan", "pro", "minimo"],
    ["plan", "start"],
    ["liquidacion", "dias"],
]

def test_idf_calculado_a_mano():
    idf = calcular_idf(CHUNKS)
    assert idf["plan"] == pytest.approx(0.470, abs=0.001)
    assert idf["pro"] == pytest.approx(0.981, abs=0.001)


def test_palabra_repetida_cuenta_una_vez_por_chunk():
    assert calcular_idf([["plan", "plan"], ["otro"]]) == calcular_idf([["plan"], ["otro"]])


def test_puntaje_calculado_a_mano():
    puntajes = BM25(CHUNKS).puntajes(["plan", "pro"])
    assert puntajes == pytest.approx([1.286, 0.502, 0.0], abs=0.001)


def test_palabra_desconocida_no_suma_ni_falla():
    assert BM25(CHUNKS).puntajes(["hola"]) == [0.0, 0.0, 0.0]


def test_chunk_mas_largo_puntua_menos():
    # mismas palabras de la consulta, pero el segundo chunk tiene relleno
    bm25 = BM25([["plan"], ["plan", "x", "y", "z"]])
    corto, largo = bm25.puntajes(["plan"])
    assert corto > largo