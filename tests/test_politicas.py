import json
from types import SimpleNamespace

import pytest

from agente_zoco.agent import Agente
from agente_zoco.tools import crear_reclamo, ejecutar_herramienta


class ModeloFalso:
    # devuelve las respuestas que le da el test, en orden: así se lo puede obligar a saltear las reglas
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.responses = self

    def create(self, **kwargs):
        return self.respuestas.pop(0)


def llama_crear_reclamo(motivo, descripcion):
    llamada = SimpleNamespace(
        type="function_call", name="crear_reclamo", call_id="c1",
        arguments=json.dumps({"motivo": motivo, "descripcion": descripcion}),
    )
    return SimpleNamespace(output=[llamada], output_text="")


@pytest.fixture(autouse=True)
def base_de_prueba(tmp_path, monkeypatch):
    # cada test usa su propia base vacía y sin fallas
    monkeypatch.setattr(crear_reclamo, "ARCHIVO_RECLAMOS", tmp_path / "reclamos.json")
    monkeypatch.setenv("TOOL_FAILURE_RATE", "0")


def reclamos_guardados():
    if not crear_reclamo.ARCHIVO_RECLAMOS.exists():
        return []
    return json.loads(crear_reclamo.ARCHIVO_RECLAMOS.read_text(encoding="utf-8"))


# regla 2: no registrar sin confirmación explícita, y la confirmación vale para esos datos exactos

def test_si_el_modelo_llama_sin_preguntar_no_se_registra():
    agente = Agente(ModeloFalso(llama_crear_reclamo("PAGO", "Me cobraron dos veces")))
    respuesta = agente.responder("Me cobraron dos veces la misma entrada")
    assert reclamos_guardados() == []
    assert "Motivo: PAGO" in respuesta and "Descripción: Me cobraron dos veces" in respuesta


def test_con_si_se_registra_con_los_datos_mostrados():
    agente = Agente(ModeloFalso(llama_crear_reclamo("PAGO", "Me cobraron dos veces")))
    agente.responder("Me cobraron dos veces la misma entrada")
    respuesta = agente.responder("Sí")
    assert [(r["motivo"], r["descripcion"]) for r in reclamos_guardados()] == [("PAGO", "Me cobraron dos veces")]
    assert "REC-000001" in respuesta


def test_si_el_usuario_cambia_algo_hay_que_volver_a_confirmar():
    agente = Agente(ModeloFalso(
        llama_crear_reclamo("PAGO", "Me cobraron dos veces"),
        llama_crear_reclamo("PAGO", "Me cobraron tres veces"),
    ))
    agente.responder("Me cobraron dos veces")
    respuesta = agente.responder("Sí, pero poné que fueron tres veces")
    assert reclamos_guardados() == []  # "sí, pero..." no confirma
    assert "Descripción: Me cobraron tres veces" in respuesta
    agente.responder("sí")
    assert [r["descripcion"] for r in reclamos_guardados()] == ["Me cobraron tres veces"]


def test_si_el_usuario_dice_no_no_se_registra():
    agente = Agente(ModeloFalso(llama_crear_reclamo("ACCESO", "El QR no funciona")))
    agente.responder("El QR no me funciona")
    agente.responder("no")
    assert reclamos_guardados() == []


def test_la_herramienta_sola_nunca_registra():
    ejecutar_herramienta("crear_reclamo", json.dumps({"motivo": "PAGO", "descripcion": "x"}))
    assert reclamos_guardados() == []


# regla 3: un reclamo confirmado no se registra dos veces

def test_repetir_si_no_duplica():
    agente = Agente(ModeloFalso(
        llama_crear_reclamo("PAGO", "Me cobraron dos veces"),
        llama_crear_reclamo("PAGO", "Me cobraron dos veces"),  # el modelo lo propone otra vez
    ))
    agente.responder("Me cobraron dos veces")
    agente.responder("sí")
    agente.responder("sí")  # ya no hay pendiente: va al modelo, que lo vuelve a proponer
    respuesta = agente.responder("sí")
    assert len(reclamos_guardados()) == 1
    assert "ya estaba registrado" in respuesta and "REC-000001" in respuesta


def test_timeout_despues_de_guardar_y_reintento_no_duplica(monkeypatch):
    fallas = iter(["timeout", None])  # primer intento: se guarda pero la respuesta se pierde
    monkeypatch.setattr(crear_reclamo, "sortear_falla", lambda: next(fallas))
    agente = Agente(ModeloFalso(llama_crear_reclamo("PAGO", "Me cobraron dos veces")))
    agente.responder("Me cobraron dos veces")
    assert "reintente" in agente.responder("sí")
    respuesta = agente.responder("sí")
    assert len(reclamos_guardados()) == 1
    assert "REC-000001" in respuesta
