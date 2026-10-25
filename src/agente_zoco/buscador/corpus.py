from dataclasses import dataclass
from datetime import date
from pathlib import Path

@dataclass(frozen=True)
class Documento:
    id: str
    titulo: str
    tipo: str
    vigencia_desde: date
    vigencia_hasta: date
    texto: str

def parsear_documento(contenido: str) -> Documento:
    partes = contenido.split("---", 2)
    if len(partes) != 3 or partes[0].strip():
        raise ValueError("El documento no tiene un encabezado válido entre '---'.")
    _, encabezado, cuerpo = partes

    meta = {}
    for linea in encabezado.strip().splitlines():
        clave, _, valor = linea.partition(":")
        meta[clave.strip()] = valor.strip().strip('"')

    return Documento(
        id=meta["id"],
        titulo=meta["titulo"],
        tipo=meta["tipo"],
        vigencia_desde=date.fromisoformat(meta["vigencia_desde"]),
        vigencia_hasta=date.fromisoformat(meta["vigencia_hasta"]),
        texto=cuerpo.strip(),
    )

def cargar_documentos(carpeta) -> list[Documento]:
    archivos = sorted(Path(carpeta).glob("DOC-*.md"))
    if not archivos:
        raise FileNotFoundError(f"No hay archivos DOC-*.md en {carpeta}")
    return [parsear_documento(a.read_text(encoding="utf-8-sig")) for a in archivos]