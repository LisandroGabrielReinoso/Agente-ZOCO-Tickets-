#Evaluación de la búsqueda (retrieval) sobre las 20 preguntas de questions.jsonl
#Compara estrategias de chunking y de búsqueda, imprime las tablas y las guarda en  resultados

import json
from datetime import date

from agente_zoco.buscador import Buscador
from agente_zoco.buscador.bm25 import BM25, tokenizar
from agente_zoco.buscador.buscador import CARPETA_DOCS, RAIZ, crear_embeddings
from agente_zoco.buscador.chunking import chunks_por_documento, chunks_por_seccion, chunks_por_ventana
from agente_zoco.buscador.corpus import cargar_documentos
from agente_zoco.buscador.hibrida import rrf
from agente_zoco.buscador.vectorial import similitud_coseno
from agente_zoco.evaluacion.metricas import ranking_de_documentos, recall_at_k, reciprocal_rank
from agente_zoco.evaluacion.tablas import tabla_chunking, tabla_detalle, tabla_estrategias

ARCHIVO_PREGUNTAS = RAIZ / "docs" / "questions.jsonl"
CARPETA_RESULTADOS = RAIZ / "resultados"
# "hoy" fijo para la evaluación: con la fecha real, la tabla cambiaría sola cuando venzan DOC-05 y DOC-07
FECHA_EVALUACION = date(2026, 10, 26)


def cargar_preguntas(ruta) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def buscadores(chunks, vector_de, embeddings):
    # BM25 y vectorial para cualquier chunking (el Buscador está fijo en "por sección")
    bm25 = BM25([tokenizar(c.texto) for c in chunks])
    matriz = embeddings.vectores([c.texto for c in chunks])

    def puntuar_bm25(q):
        return bm25.puntajes(tokenizar(q))

    def puntuar_vectorial(q):
        return similitud_coseno(vector_de[q], matriz)

    return puntuar_bm25, puntuar_vectorial


def evaluar(chunks, preguntas, puntuar) -> tuple[float, float]:
    doc_ids = [c.doc_id for c in chunks]
    recalls, rrs = [], []
    for p in preguntas:
        ranking = ranking_de_documentos(doc_ids, puntuar(p["question"]))
        recalls.append(recall_at_k(ranking, p["relevant"], k=3))
        rrs.append(reciprocal_rank(ranking, p["relevant"]))
    return sum(recalls) / len(recalls), sum(rrs) / len(rrs)


def comparar_chunking(docs, preguntas, vector_de, embeddings) -> list[tuple]:
    estrategias = {
        "documento": chunks_por_documento(docs),
        "seccion": chunks_por_seccion(docs),
        "ventana 20/5": chunks_por_ventana(docs, tamano=20, solapamiento=5),
        "ventana 40/10": chunks_por_ventana(docs, tamano=40, solapamiento=10),
        "ventana 80/20": chunks_por_ventana(docs, tamano=80, solapamiento=20),
    }
    filas = []
    for nombre, chunks in estrategias.items():
        puntuar_bm25, puntuar_vectorial = buscadores(chunks, vector_de, embeddings)
        recall_bm25, mrr_bm25 = evaluar(chunks, preguntas, puntuar_bm25)
        recall_vec, mrr_vec = evaluar(chunks, preguntas, puntuar_vectorial)
        filas.append((nombre, len(chunks), recall_bm25, mrr_bm25, recall_vec, mrr_vec))
    return filas


def armar_estrategias(docs, embeddings):
    # las cuatro estrategias salen del mismo Buscador que usa el agente
    buscador = Buscador(docs, embeddings)

    def puntuar_hibrida(q):
        return rrf([buscador.puntajes_bm25(q), buscador.puntajes_vectorial(q)])

    def puntuar_hibrida_metadata(q):
        return buscador.puntajes(q, hoy=FECHA_EVALUACION)

    estrategias = {
        "BM25": buscador.puntajes_bm25,
        "vectorial": buscador.puntajes_vectorial,
        "híbrida (RRF)": puntuar_hibrida,
        "híbrida + metadata": puntuar_hibrida_metadata,
    }
    return buscador.chunks, estrategias


def comparar_estrategias(chunks, preguntas, estrategias) -> list[tuple]:
    return [(nombre, *evaluar(chunks, preguntas, puntuar)) for nombre, puntuar in estrategias.items()]


def detalle_por_pregunta(chunks, preguntas, estrategias) -> list[tuple]:
    # para cada pregunta y estrategia: posición del primer documento relevante y qué documento quedó 1°
    doc_ids = [c.doc_id for c in chunks]
    filas = []
    for p in preguntas:
        celdas = []
        for puntuar in estrategias.values():
            ranking = ranking_de_documentos(doc_ids, puntuar(p["question"]))
            posicion = next((i for i, d in enumerate(ranking, start=1) if d in p["relevant"]), None)
            celdas.append((posicion, ranking[0] if ranking else None))
        filas.append((p["id"], p["question"], p["relevant"], celdas))
    return filas


def guardar(nombre_archivo: str, texto: str):
    print(texto)
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    salida = CARPETA_RESULTADOS / nombre_archivo
    salida.write_text(texto, encoding="utf-8")
    print(f"Guardado en {salida.relative_to(RAIZ)}\n")


def main():
    docs = cargar_documentos(CARPETA_DOCS)
    preguntas = cargar_preguntas(ARCHIVO_PREGUNTAS)
    embeddings = crear_embeddings()
    # el vector de cada pregunta se calcula una sola vez para comparar los chunkings
    textos_preguntas = [p["question"] for p in preguntas]
    vector_de = dict(zip(textos_preguntas, embeddings.vectores(textos_preguntas)))

    guardar("chunking.md", tabla_chunking(comparar_chunking(docs, preguntas, vector_de, embeddings)))

    chunks, estrategias = armar_estrategias(docs, embeddings)
    guardar("estrategias.md", tabla_estrategias(comparar_estrategias(chunks, preguntas, estrategias)))
    guardar(
        "detalle_por_pregunta.md",
        tabla_detalle(detalle_por_pregunta(chunks, preguntas, estrategias), list(estrategias)),
    )


if __name__ == "__main__":
    main()
