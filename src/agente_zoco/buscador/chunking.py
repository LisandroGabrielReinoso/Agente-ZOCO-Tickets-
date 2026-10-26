"""(Estrategias para dividir documentos en chunks: por documento, por sección o por ventana)"""

from dataclasses import dataclass, field
from agente_zoco.buscador.corpus import Documento

@dataclass(frozen=True)
class Chunk:
    id: str
    texto: str
    documento: Documento = field(repr=False)

    @property
    def doc_id(self) -> str:
        return self.documento.id


def chunks_por_documento(docs: list[Documento]) -> list[Chunk]:
    return [Chunk(f"{d.id}#0", d.texto, d) for d in docs]


def secciones(texto: str) -> list[str]:
    #Corta el texto en cada línea que empieza con '#', el encabezado queda en su sección
    secciones, actual = [], []
    for linea in texto.splitlines():
        if linea.startswith("#") and actual:
            secciones.append("\n".join(actual).strip())
            actual = []
        actual.append(linea)
    if actual:
        secciones.append("\n".join(actual).strip())
    return [s for s in secciones if s]


def chunks_por_seccion(docs: list[Documento]) -> list[Chunk]:
    return [
        Chunk(f"{d.id}#{i}", seccion, d)
        for d in docs
        for i, seccion in enumerate(secciones(d.texto))
    ]


def chunks_por_ventana(docs: list[Documento], tamano: int, solapamiento: int) -> list[Chunk]:
    if not 0 <= solapamiento < tamano:
        raise ValueError("El solapamiento tiene que ser >= 0 y menor que el tamaño")
    paso = tamano - solapamiento
    lista_chunks = []
    for d in docs:
        palabras = d.texto.split()
        for i, inicio in enumerate(range(0, len(palabras), paso)):
            lista_chunks.append(Chunk(f"{d.id}#{i}", " ".join(palabras[inicio:inicio + tamano]), d))
            if inicio + tamano >= len(palabras):
                break
    return lista_chunks