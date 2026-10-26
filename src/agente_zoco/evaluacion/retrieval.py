#Evaluación de la búsqueda (retrieval) sobre las 20 preguntas de questions.jsonl
#Compara estrategias de chunking con BM25, imprime la tabla y la guarda en  resultados

import json
from pathlib import Path

from agente_zoco.buscador.bm25 import BM25, tokenizar
from agente_zoco.buscador.chunking import chunks_por_documento, chunks_por_seccion, chunks_por_ventana
from agente_zoco.buscador.corpus import cargar_documentos
from agente_zoco.evaluacion.metricas import ranking_de_documentos, recall_at_k, reciprocal_rank

RAIZ = Path(__file__).parents[3] 
CARPETA_DOCS = RAIZ / "docs" / "docs"
ARCHIVO_PREGUNTAS = RAIZ / "docs" / "questions.jsonl"
CARPETA_RESULTADOS = RAIZ / "resultados"


def cargar_preguntas(ruta) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def evaluar(chunks, preguntas, puntuar) -> tuple[float, float]:
    doc_ids = [c.doc_id for c in chunks]
    recalls, rrs = [], []
    for p in preguntas:
        ranking = ranking_de_documentos(doc_ids, puntuar(p["question"]))
        recalls.append(recall_at_k(ranking, p["relevant"], k=3))
        rrs.append(reciprocal_rank(ranking, p["relevant"]))
    return sum(recalls) / len(recalls), sum(rrs) / len(rrs)


def comparar_chunking_con_bm25(docs, preguntas) -> list[tuple[str, int, float, float]]:
    estrategias = {
        "documento": chunks_por_documento(docs),
        "seccion": chunks_por_seccion(docs),
        "ventana 20/5": chunks_por_ventana(docs, tamano=20, solapamiento=5),
        "ventana 40/10": chunks_por_ventana(docs, tamano=40, solapamiento=10),
        "ventana 80/20": chunks_por_ventana(docs, tamano=80, solapamiento=20),
    }
    filas = []
    for nombre, chunks in estrategias.items():
        bm25 = BM25([tokenizar(c.texto) for c in chunks])
        recall, mrr = evaluar(chunks, preguntas, lambda q: bm25.puntajes(tokenizar(q)))
        filas.append((nombre, len(chunks), recall, mrr))
    return filas


def tabla(filas) -> str:
    lineas = ["| chunking | chunks | recall@3 | MRR |", "|---|---:|---:|---:|"]
    for nombre, n_chunks, recall, mrr in filas:
        lineas.append(f"| {nombre} | {n_chunks} | {recall:.3f} | {mrr:.3f} |")
    return "\n".join(lineas) + "\n"


def main():
    docs = cargar_documentos(CARPETA_DOCS)
    preguntas = cargar_preguntas(ARCHIVO_PREGUNTAS)

    texto = tabla(comparar_chunking_con_bm25(docs, preguntas))
    print(texto)

    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    salida = CARPETA_RESULTADOS / "chunking_bm25.md"
    salida.write_text(texto, encoding="utf-8")
    print(f"Guardado en {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
