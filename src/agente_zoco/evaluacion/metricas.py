#Métricas de recuperación recall@k y reciprocal rank 

def ranking_de_documentos(doc_ids: list[str], puntajes: list[float]) -> list[str]:
    orden = sorted(range(len(puntajes)), key=lambda i: puntajes[i], reverse=True)
    ranking = []
    for i in orden:
        if puntajes[i] <= 0:
            break  # están ordenados: desde acá todos son 0
        if doc_ids[i] not in ranking:
            ranking.append(doc_ids[i])
    return ranking

def recall_at_k(ranking: list[str], relevantes: list[str], k: int = 3) -> float:
    encontrados = set(ranking[:k]) & set(relevantes)
    return len(encontrados) / len(relevantes)


def reciprocal_rank(ranking: list[str], relevantes: list[str]) -> float:
    for posicion, doc_id in enumerate(ranking, start=1):
        if doc_id in relevantes:
            return 1 / posicion
    return 0.0
