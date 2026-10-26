import json
import re
from datetime import date
from pathlib import Path

from agente_zoco.tools.fallas import simular_falla

ARCHIVO_VENTAS = Path(__file__).parents[3] / "datos" / "ventas.json"

ESQUEMA = {
    "type": "function",
    "name": "consultar_ventas",
    "description": (
        "Devuelve las ventas del comercio para un día: entradas vendidas, monto bruto, devoluciones "
        "y monto neto. Necesita una fecha exacta; si el usuario dice 'ayer', 'el viernes' o una fecha "
        "ambigua como '03/04', pedile la fecha exacta antes de llamar."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "fecha": {"type": "string", "description": "Fecha exacta en formato AAAA-MM-DD."},
        },
        "required": ["fecha"],
        "additionalProperties": False,
    },
    "strict": True,
}


def ejecutar(fecha: str, hoy: date | None = None) -> dict:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        return {"error": "La fecha tiene que tener el formato AAAA-MM-DD, por ejemplo 2026-10-15."}
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        return {"error": f"{fecha} no es una fecha válida."}

    if dia > (hoy or date.today()):
        return {"fecha": fecha, "error": "Es una fecha futura: todavía no puede haber ventas registradas."}

    simular_falla()

    ventas = json.loads(ARCHIVO_VENTAS.read_text(encoding="utf-8"))
    for venta in ventas:
        if venta["fecha"] == fecha:
            return {
                "fecha": fecha,
                "entradas": venta["entradas"],
                "monto_bruto": venta["monto_bruto"],
                "devoluciones": venta["devoluciones"],
                "monto_neto": venta["monto_bruto"] - venta["devoluciones"],
            }
    return {"fecha": fecha, "sin_registros": True}
