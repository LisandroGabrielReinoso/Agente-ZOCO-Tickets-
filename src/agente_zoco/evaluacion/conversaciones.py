import importlib
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agente_zoco.agent import MODELO, Agente
from agente_zoco.buscador.bm25 import normalizar
from agente_zoco.buscador.buscador import RAIZ
from agente_zoco.evaluacion.casos import CASOS
from agente_zoco.maquina import TransicionInvalida
from agente_zoco.tools import consultar_ventas, crear_reclamo

REPETICIONES = 3
HOY = date(2026, 10, 26)
CARPETA_RESULTADOS = RAIZ / "resultados"


class FechaFija(date):
    @classmethod
    def today(cls):
        return cls(HOY.year, HOY.month, HOY.day)


def fijar_hoy():
    consultar_ventas.date = FechaFija
    importlib.import_module("agente_zoco.buscador.buscador").date = FechaFija


def ejecutar_paso(agente, paso, eventos_fallidos):
    if isinstance(paso, str):
        return agente.responder(paso)
    if paso[0] == "evento":
        try:
            return agente.evento(paso[1], paso[2])
        except TransicionInvalida:
            eventos_fallidos.append(paso[1])
            return None
    if paso[0] == "aprobar":
        return agente.aprobar_borrador()
    agente.rechazar_borrador()
    return None


def correr(caso, client) -> dict:
    sortear_original = crear_reclamo.sortear_falla
    archivo_original = crear_reclamo.ARCHIVO_RECLAMOS
    fallas = iter(caso.fallas_reclamo)
    observado = {
        "llamadas": [], "llamadas_por_paso": [], "respuestas": [], "reclamos": [],
        "estado": None, "eventos_fallidos": [], "error": None,
    }

    with tempfile.TemporaryDirectory() as carpeta:
        crear_reclamo.ARCHIVO_RECLAMOS = Path(carpeta) / "reclamos.json"
        crear_reclamo.sortear_falla = lambda: next(fallas, None)
        os.environ["TOOL_FAILURE_RATE"] = str(caso.tasa_de_falla)
        try:
            agente = Agente(client)
            for paso in caso.pasos:
                antes = len(agente.llamadas)
                respuesta = ejecutar_paso(agente, paso, observado["eventos_fallidos"])
                observado["respuestas"].append(None if respuesta is None else (respuesta.tipo, respuesta.texto))
                observado["llamadas_por_paso"].append([nombre for nombre, _ in agente.llamadas[antes:]])
            observado["llamadas"] = list(agente.llamadas)
            observado["estado"] = agente.maquina.actual
            if crear_reclamo.ARCHIVO_RECLAMOS.exists():
                observado["reclamos"] = json.loads(crear_reclamo.ARCHIVO_RECLAMOS.read_text(encoding="utf-8"))
        except Exception as error:
            observado["error"] = f"{type(error).__name__}: {error}"
        finally:
            crear_reclamo.ARCHIVO_RECLAMOS = archivo_original
            crear_reclamo.sortear_falla = sortear_original
            os.environ["TOOL_FAILURE_RATE"] = "0"
    return observado


def argumentos_de(texto_json: str) -> dict:
    try:
        return json.loads(texto_json)
    except json.JSONDecodeError:
        return {}


def verificar(caso, observado) -> list[str]:
    if observado["error"]:
        return [f"la conversación se cortó: {observado['error']}"]

    fallas = []
    herramientas = [nombre for nombre, _ in observado["llamadas"]]
    for nombre in caso.debe_llamar:
        if nombre not in herramientas:
            fallas.append(f"no llamó a {nombre}")
    for nombre in caso.no_debe_llamar:
        if nombre in herramientas:
            fallas.append(f"llamó a {nombre}")
    for herramienta, campo, valor in caso.argumentos:
        llamadas = [argumentos_de(a) for n, a in observado["llamadas"] if n == herramienta]
        if not any(a.get(campo) == valor for a in llamadas):
            fallas.append(f"no llamó a {herramienta} con {campo}={valor}")
    if caso.fechas_consultadas:
        fechas = {argumentos_de(a).get("fecha") for n, a in observado["llamadas"] if n == "consultar_ventas"}
        if fechas != set(caso.fechas_consultadas):
            fallas.append(f"consultó las fechas {sorted(fechas)}, se esperaban {sorted(caso.fechas_consultadas)}")
    for paso, nombre in caso.no_llama_en_paso:
        if nombre in observado["llamadas_por_paso"][paso]:
            fallas.append(f"llamó a {nombre} en el paso {paso + 1}")

    if caso.reclamos_esperados is not None and len(observado["reclamos"]) != caso.reclamos_esperados:
        fallas.append(f"quedaron {len(observado['reclamos'])} reclamos, se esperaban {caso.reclamos_esperados}")
    if caso.motivo_reclamo and [r["motivo"] for r in observado["reclamos"]] != [caso.motivo_reclamo]:
        fallas.append(f"el reclamo no tiene motivo {caso.motivo_reclamo}")
    if caso.estado_final and observado["estado"] != caso.estado_final:
        fallas.append(f"terminó en {observado['estado']}, se esperaba {caso.estado_final}")
    if sorted(observado["eventos_fallidos"]) != sorted(caso.eventos_fallidos):
        fallas.append(f"eventos rechazados: {observado['eventos_fallidos']}, se esperaban {list(caso.eventos_fallidos)}")
    for i in caso.pasos_sin_respuesta:
        respuesta = observado["respuestas"][i]
        if respuesta is None or respuesta[0] != "ninguna":
            fallas.append(f"el paso {i + 1} tuvo respuesta y no debía")

    texto = normalizar(" ".join(r[1] for r in observado["respuestas"] if r and r[1]))
    digitos = re.sub(r"\D", "", texto)
    for buscado in caso.texto_contiene:
        if normalizar(buscado) not in texto:
            fallas.append(f"la respuesta no dice '{buscado}'")
    if caso.texto_contiene_alguno and not any(normalizar(t) in texto for t in caso.texto_contiene_alguno):
        fallas.append("la respuesta no explica lo esperado")
    for numero in caso.numeros_en_texto:
        if numero not in digitos:
            fallas.append(f"la respuesta no menciona {numero}")
    for numero in caso.numeros_prohibidos:
        if numero in digitos:
            fallas.append(f"la respuesta menciona {numero} y no debía")
    return fallas


def describir_paso(paso) -> str:
    if isinstance(paso, str):
        return f"Cliente: {paso}"
    if paso[0] == "evento":
        return f"Evento `{paso[1]}` ({paso[2]})"
    if paso[0] == "aprobar":
        return "Operador: aprueba el borrador"
    return "Operador: rechaza el borrador"


def describir_llamadas(llamadas) -> str:
    if not llamadas:
        return "ninguna"
    return ", ".join(f"`{n}({a})`" for n, a in llamadas)


def ultima_respuesta(observado) -> str:
    textos = [r[1] for r in observado["respuestas"] if r and r[1]]
    if not textos:
        return "(sin respuesta)"
    return " ".join(textos[-1].split())[:300]


def informe(resultados) -> str:
    total = sum(len([f for f in reps if not f[1]]) for _, reps in resultados)
    lineas = [
        "# Evaluación de conversaciones",
        "",
        f"Generado con `uv run evaluar-agente`: {len(resultados)} casos × {REPETICIONES} repeticiones, "
        f"modelo `{MODELO}`, fecha del sistema fija en {HOY.isoformat()}. "
        "El cumplimiento se decide con aserciones sobre hechos observables: herramientas llamadas y sus "
        "argumentos, reclamos en la base, estado final de la conversación y datos presentes en la respuesta. "
        "No se usa un LLM como juez.",
        "",
        "| caso | categoría | descripción | cumplimiento |",
        "|---|---|---|---:|",
    ]
    for caso, reps in resultados:
        cumplidas = len([f for f in reps if not f[1]])
        lineas.append(f"| {caso.id} | {caso.categoria} | {caso.descripcion} | {cumplidas}/{len(reps)} |")
    lineas += ["", f"**Total: {total}/{len(resultados) * REPETICIONES} repeticiones cumplidas.**", ""]

    for caso, reps in resultados:
        cumplidas = len([f for f in reps if not f[1]])
        lineas += [
            f"## {caso.id} — {caso.descripcion}",
            "",
            f"**Categoría:** {caso.categoria}",
            "",
            "**Mensajes:**",
            "",
        ]
        lineas += [f"{i}. {describir_paso(p)}" for i, p in enumerate(caso.pasos, start=1)]
        lineas += [
            "",
            f"**Comportamiento esperado:** {caso.esperado}",
            "",
            f"**Herramientas que debería usar:** {', '.join(caso.debe_llamar) or '—'}  ",
            f"**Herramientas que no debería usar:** {', '.join(caso.no_debe_llamar) or '—'}",
            "",
            "**Resultado observado:**",
            "",
        ]
        for i, (observado, fallas) in enumerate(reps, start=1):
            veredicto = "cumple" if not fallas else "no cumple: " + "; ".join(fallas)
            lineas.append(
                f"- Repetición {i}: **{veredicto}**. Herramientas: {describir_llamadas(observado['llamadas'])}. "
                f"Reclamos en la base: {len(observado['reclamos'])}. Estado final: {observado['estado']}. "
                f"Última respuesta: \"{ultima_respuesta(observado)}\""
            )
        lineas += ["", f"**Tasa de cumplimiento:** {cumplidas}/{len(reps)}", ""]
    return "\n".join(lineas)


def main():
    load_dotenv(RAIZ / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Falta OPENAI_API_KEY en el .env")
    client = OpenAI(api_key=api_key)
    fijar_hoy()

    resultados = []
    for caso in CASOS:
        reps = []
        for i in range(1, REPETICIONES + 1):
            observado = correr(caso, client)
            fallas = verificar(caso, observado)
            reps.append((observado, fallas))
            print(f"{caso.id} repetición {i}: {'cumple' if not fallas else 'no cumple: ' + '; '.join(fallas)}")
        resultados.append((caso, reps))

    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    salida = CARPETA_RESULTADOS / "conversaciones.md"
    salida.write_text(informe(resultados), encoding="utf-8")
    print(f"Guardado en {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
