#Uso de la metadata: deja solo los documentos vigentes en la fecha por la que pregunta el usuario
#El tipo no se usa para buscar es "historico" ya está representado por vigencia_hasta

import calendar
import re
from datetime import date
from agente_zoco.buscador.bm25 import normalizar

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
PATRON_MES = re.compile(r"\b(" + "|".join(MESES) + r") de (\d{4})\b")

def periodo_de_la_pregunta(pregunta: str, hoy: date) -> tuple[date, date]:
    encontrado = PATRON_MES.search(normalizar(pregunta))
    if not encontrado:
        return hoy, hoy
    mes = MESES[encontrado.group(1)]
    anio = int(encontrado.group(2))
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, 1), date(anio, mes, ultimo_dia)

def vigente_en(documento, desde: date, hasta: date) -> bool:
    return documento.vigencia_desde <= hasta and documento.vigencia_hasta >= desde

def filtrar_por_vigencia(puntajes, chunks, desde: date, hasta: date) -> list[float]:
    # los chunks de documentos no vigentes quedan en 0 asi que no entran al ranking
    return [p if vigente_en(c.documento, desde, hasta) else 0.0 for p, c in zip(puntajes, chunks)]
