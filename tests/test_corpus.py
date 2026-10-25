from datetime import date
from pathlib import Path
import pytest
from agente_zoco.buscador.corpus import cargar_documentos, parsear_documento

carpeta = Path(__file__).parent.parent / "docs" / "docs"

documento_ejemplo = """---
id: DOC-07
titulo: "Planes comerciales y requisitos"
tipo: tarifario
vigencia_desde: 2026-09-01
vigencia_hasta: 2027-03-31
---

# Planes ficticios
ZT-PRO-2: requiere al menos 400 entradas pagadas por mes calendario.
"""


def test_parsea_la_metadata():
    doc = parsear_documento(documento_ejemplo)
    assert doc.id == "DOC-07"
    assert doc.titulo == "Planes comerciales y requisitos"
    assert doc.tipo == "tarifario"
    assert doc.vigencia_desde == date(2026, 9, 1)
    assert doc.vigencia_hasta == date(2027, 3, 31)


def test_el_texto_no_incluye_el_encabezado():
    doc = parsear_documento(documento_ejemplo)
    assert doc.texto.startswith("# Planes ficticios")
    assert "vigencia_desde" not in doc.texto


def test_sin_encabezado_falla_explicitamente():
    with pytest.raises(ValueError):
        parsear_documento("# Solo texto, sin encabezado")


def test_carga_los_12_documentos_reales():
    docs = cargar_documentos(carpeta)
    assert [d.id for d in docs] == [f"DOC-{i:02d}" for i in range(1, 13)]
    for d in docs:
        assert d.texto
        assert d.vigencia_desde <= d.vigencia_hasta


def test_doc12_es_historico():
    doc12 = cargar_documentos(carpeta)[11]
    assert doc12.tipo == "historico"
    assert doc12.vigencia_hasta == date(2026, 8, 31)
