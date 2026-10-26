from agente_zoco.buscador.BM25 import tokenizar


def test_la_puntuacion_separa_palabras():
    assert tokenizar("¿Cuánto cobra ZT-PRO-2? 5,0%") == ["cuanto", "cobra", "zt", "pro", "2", "5", "0"]


def test_pregunta_y_documento_coinciden():
    assert tokenizar("mínimo de entradas") == tokenizar("MINIMO DE ENTRADAS")