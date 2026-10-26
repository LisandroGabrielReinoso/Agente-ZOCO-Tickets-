import pytest

from agente_zoco.buscador.hibrida import posiciones, rrf

BM25 = [3.0, 1.0, 0.0]        # posiciones: c0 = 1, c1 = 2, c2 no entra (puntaje 0)
VECTORIAL = [0.2, 0.9, 0.5]   # posiciones: c1 = 1, c2 = 2, c0 = 3

def test_posiciones_saca_los_de_puntaje_cero():
    assert posiciones(BM25) == {0: 1, 1: 2}


def test_rrf_calculado():
    # c0 = 1/61 + 1/63 , c1 = 1/62 + 1/61 , c2 = 0 + 1/62
    assert rrf([BM25, VECTORIAL]) == pytest.approx([0.03227, 0.03252, 0.01613], abs=0.00001)


def test_gana_el_mas_parejo_en_los_dos_rankings():
    fusion = rrf([BM25, VECTORIAL])
    assert max(range(3), key=lambda i: fusion[i]) == 1
