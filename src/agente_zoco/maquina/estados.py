#Estados de la conversación y qué puede hacer el agente en cada uno

from typing import NamedTuple

TODAS = frozenset({"buscar_documentacion", "consultar_ventas", "crear_reclamo"})


class Estado(NamedTuple):
    nombre: str
    respuesta: str  # "enviar", "borrador" (la aprueba un operador) o "ninguna"
    herramientas: frozenset  # las que el modelo puede usar en este estado
    reclamo_con_operador: bool  # crear_reclamo necesita además la aprobación del operador


AUTO = Estado("AUTO", "enviar", TODAS, False)
SUGGEST = Estado("SUGGEST", "borrador", TODAS, True)  # reglas 2 y 6
HUMAN = Estado("HUMAN", "ninguna", frozenset(), False)  # regla 1: no envía ni ejecuta
BLOCKED = Estado("BLOCKED", "ninguna", frozenset(), False)

ESTADOS = {e.nombre: e for e in (AUTO, SUGGEST, HUMAN, BLOCKED)}
