#Buscador final, elegido con las tablas de resultados/:
# chunking por sección + híbrida (BM25 y vectorial fusionados con RRF) + filtro de vigencia

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agente_zoco.buscador.bm25 import BM25, tokenizar
from agente_zoco.buscador.chunking import Chunk, chunks_por_seccion
from agente_zoco.buscador.corpus import cargar_documentos
from agente_zoco.buscador.embeddings import Embeddings
from agente_zoco.buscador.hibrida import rrf
from agente_zoco.buscador.metadata import filtrar_por_vigencia, periodo_de_la_pregunta
from agente_zoco.buscador.vectorial import similitud_coseno

RAIZ = Path(__file__).parents[3]  # buscador/ -> agente_zoco/ -> src/ -> raíz del proyecto
CARPETA_DOCS = RAIZ / "docs" / "docs"
CARPETA_CACHE = RAIZ / "cache" / "embeddings"


def crear_embeddings() -> Embeddings:
    # sin clave igual funciona si todos los vectores ya están en el caché
    load_dotenv(RAIZ / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key) if api_key else None
    return Embeddings(client, CARPETA_CACHE)


class Buscador:
    def __init__(self, docs=None, embeddings=None):
        # todo lo que depende solo de los documentos se arma una vez
        self.chunks = chunks_por_seccion(docs if docs is not None else cargar_documentos(CARPETA_DOCS))
        self.embeddings = embeddings if embeddings is not None else crear_embeddings()
        self.bm25 = BM25([tokenizar(c.texto) for c in self.chunks])
        self.matriz = self.embeddings.vectores([c.texto for c in self.chunks])

    def puntajes_bm25(self, consulta: str) -> list[float]:
        return self.bm25.puntajes(tokenizar(consulta))

    def puntajes_vectorial(self, consulta: str) -> list[float]:
        vector = self.embeddings.vectores([consulta])[0]
        return similitud_coseno(vector, self.matriz)

    def puntajes(self, consulta: str, hoy: date | None = None) -> list[float]:
        # un puntaje por chunk; los de documentos no vigentes en la fecha de la consulta quedan en 0
        desde, hasta = periodo_de_la_pregunta(consulta, hoy or date.today())
        return rrf([
            filtrar_por_vigencia(self.puntajes_bm25(consulta), self.chunks, desde, hasta),
            filtrar_por_vigencia(self.puntajes_vectorial(consulta), self.chunks, desde, hasta),
        ])

    def buscar(self, consulta: str, k: int = 3, hoy: date | None = None) -> list[Chunk]:
        # los k chunks con mejor puntaje; cada uno trae su documento con id, tipo y vigencia
        puntajes = self.puntajes(consulta, hoy)
        orden = sorted(range(len(puntajes)), key=lambda i: puntajes[i], reverse=True)
        return [self.chunks[i] for i in orden[:k] if puntajes[i] > 0]
