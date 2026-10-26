#Fallas simuladas: con probabilidad TOOL_FAILURE_RATE la herramienta tira un timeout o un error

import os
import random


def tasa_de_falla() -> float:
    try:
        return float(os.getenv("TOOL_FAILURE_RATE", "0"))
    except ValueError:
        return 0.0  # si la variable tiene cualquier cosa, no se simulan fallas


def sortear_falla() -> str | None:
    # None si no falla; si falla, "timeout" o "error" con la misma probabilidad
    if random.random() >= tasa_de_falla():
        return None
    return "timeout" if random.random() < 0.5 else "error"


def simular_falla():
    falla = sortear_falla()
    if falla == "timeout":
        raise TimeoutError("timeout simulado")
    if falla == "error":
        raise RuntimeError("error simulado")
