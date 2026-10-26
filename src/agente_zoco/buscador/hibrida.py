#Búsqueda híbrida: Reciprocal Rank Fusion(RRF)
#RRF(c) = Σ_{r ∈ R} 1 / (k + posición_r(c)),  k = 60

def posiciones(puntajes) -> dict[int, int]:
    # posición de cada chunk (1 = el mejor); los de puntaje 0 no entran al ranking
    orden = sorted(range(len(puntajes)), key=lambda i: puntajes[i], reverse=True)
    con_puntaje = [i for i in orden if puntajes[i] > 0]
    return {i: posicion for posicion, i in enumerate(con_puntaje, start=1)}

def rrf(listas_de_puntajes, k: int = 60) -> list[float]:
    fusion = [0.0] * len(listas_de_puntajes[0])
    for puntajes in listas_de_puntajes:
        for i, posicion in posiciones(puntajes).items():
            fusion[i] += 1 / (k + posicion)
    return fusion
