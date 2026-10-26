#Herramienta crear_reclamo: guarda reclamos en datos/reclamos.json
#El modelo solo la propone; el agente registra después de que el usuario confirma (ver politicas.py)

import hashlib
import json
from pathlib import Path

from agente_zoco.tools.fallas import sortear_falla

ARCHIVO_RECLAMOS = Path(__file__).parents[3] / "datos" / "reclamos.json"
MOTIVOS = ["PAGO", "ENTRADA", "LIQUIDACION", "ACCESO", "OTROS"]  # categorías de DOC-11

ESQUEMA = {
    "type": "function",
    "name": "crear_reclamo",
    "description": (
        "Registra un reclamo del comercio. El sistema le muestra al usuario el motivo y la descripción "
        "y le pide confirmación antes de guardarlo: no digas que el reclamo está creado hasta que el "
        "sistema lo confirme con un número REC-."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "motivo": {"type": "string", "enum": MOTIVOS, "description": "Categoría del reclamo."},
            "descripcion": {"type": "string", "description": "Qué pasó, con las palabras del usuario."},
        },
        "required": ["motivo", "descripcion"],
        "additionalProperties": False,
    },
    "strict": True,
}


def ejecutar(motivo: str, descripcion: str) -> dict:
    # nunca registra: guardar un reclamo necesita la confirmación del usuario, que maneja el agente
    return {"error": "El reclamo no se registró: falta la confirmación del usuario."}


def clave_de(conversacion: str, motivo: str, descripcion: str) -> str:
    # mismo reclamo en la misma conversación = misma clave
    return hashlib.sha256(f"{conversacion}\n{motivo}\n{descripcion}".encode("utf-8")).hexdigest()


def registrar(motivo: str, descripcion: str, clave: str) -> tuple[str, bool]:
    # devuelve (id, nuevo); si la clave ya estaba, devuelve el mismo id sin guardar otro
    falla = sortear_falla()
    if falla == "error":
        raise RuntimeError("error simulado")

    reclamos = []
    if ARCHIVO_RECLAMOS.exists():
        reclamos = json.loads(ARCHIVO_RECLAMOS.read_text(encoding="utf-8"))
    for reclamo in reclamos:
        if reclamo["clave"] == clave:
            return reclamo["id"], False

    nuevo = {
        "id": f"REC-{len(reclamos) + 1:06d}",
        "motivo": motivo,
        "descripcion": descripcion,
        "clave": clave,
    }
    reclamos.append(nuevo)
    ARCHIVO_RECLAMOS.write_text(json.dumps(reclamos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if falla == "timeout":
        # el caso más traicionero: el reclamo quedó guardado pero la respuesta se perdió
        raise TimeoutError("timeout simulado")
    return nuevo["id"], True
