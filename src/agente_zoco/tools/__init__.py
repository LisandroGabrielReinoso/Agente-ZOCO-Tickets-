import json

MODULOS = []

herramientas = {}
ESQUEMAS = []

for m in MODULOS:
    nombre = m.ESQUEMA["name"]
    herramientas[nombre] = m  
    ESQUEMAS.append(m.ESQUEMA)

def ejecutar_herramienta(nombre: str, argumentos_json: str) -> str:
    modulo = herramientas.get(nombre)
    if modulo is None:
        return print(f"La herramienta '{nombre}' no existe")

    try:
        argumentos = json.loads(argumentos_json)
    except json.JSONDecodeError:
        return "Los parametros no son un JSON válido"

    problema = validar_parametros(modulo.ESQUEMA, argumentos)
    if problema:
        return problema

    try:
        resultado = modulo.ejecutar(**argumentos)
    except Exception:
        return "La herramienta falló. Se puede reintentar más tarde."

    return json.dumps(resultado, ensure_ascii=False)


def validar_parametros(esquema: dict, argumentos) -> str | None:
    if not isinstance(argumentos, dict):
        return "Los argumentos deben ser un objeto JSON"
    params = esquema["parameters"]
    extra = set(argumentos) - set(params["properties"])
    faltan = set(params.get("required", [])) - set(argumentos)
    if extra:
        return f"Argumentos no permitidos: {sorted(extra)}."
    if faltan:
        return f"Faltan argumentos obligatorios: {sorted(faltan)}."
    return None
