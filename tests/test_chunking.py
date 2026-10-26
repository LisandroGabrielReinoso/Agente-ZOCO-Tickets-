from datetime import date
import pytest

from agente_zoco.buscador.chunking import (chunks_por_documento, chunks_por_seccion,chunks_por_ventana)
from agente_zoco.buscador.corpus import Documento

def hacer_doc(texto: str, id: str = "DOC-99") -> Documento:
    return Documento(id, "Título", "prueba", date(2026, 1, 1), date(2026, 12, 31), texto)


def test_por_documento_un_chunk_por_documento():
    chunks = chunks_por_documento([hacer_doc("hola"), hacer_doc("chau", "DOC-98")])
    assert [c.id for c in chunks] == ["DOC-99#0", "DOC-98#0"]


def test_por_seccion_corta_en_cada_encabezado(): 
    doc = hacer_doc("# Uno\ntexto uno\n# Dos\ntexto dos")
    chunks = chunks_por_seccion([doc])
    assert [c.texto for c in chunks] == ["# Uno\ntexto uno", "# Dos\ntexto dos"]
    assert all(c.doc_id == "DOC-99" for c in chunks)


def test_por_ventana_con_solapamiento():
    # prueba con 10 palabras, tamaño 4, solapa 2 -> paso 2 -> empieza en 0, 2, 4, 6
    doc = hacer_doc("a b c d e f g h i j")
    chunks = chunks_por_ventana([doc], tamano=4, solapamiento=2)
    assert [c.texto for c in chunks] == ["a b c d", "c d e f", "e f g h", "g h i j"]


def test_por_ventana_rechaza_solapamiento_invalido():
    with pytest.raises(ValueError):
        chunks_por_ventana([hacer_doc("a b c")], tamano=4, solapamiento=4)