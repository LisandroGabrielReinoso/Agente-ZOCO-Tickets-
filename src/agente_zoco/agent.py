from agente_zoco.tools import ESQUEMAS, ejecutar_herramienta

MODELO = "gpt-4.1-mini"
intentos= 5

PROMPT = (
    "Sos el asistente de soporte de ZocoTickets, una plataforma de venta de entradas. "
    "Respondé en español, de forma breve y clara. "
    "Si no tenés un dato o una herramienta no devuelve resultados, decilo; no lo inventes. "
    "Si falta información (por ejemplo una fecha exacta), pedila antes de usar una herramienta. "
    "Para dudas sobre planes, tarifas, plazos o procedimientos, usá buscar_documentacion y respondé solo "
    "con lo que digan los fragmentos, citando el ID del documento entre corchetes, por ejemplo [DOC-07]. "
    "Fijate la vigencia de cada fragmento: si es histórico, aclaralo."
)

class Agente:
    def __init__(self, client, modelo=MODELO):
        self.client = client
        self.modelo = modelo
        self.historial = [{"role": "system", "content": PROMPT}]

    def responder(self, mensaje: str) -> str:
        self.historial.append({"role": "user", "content": mensaje})

        for _ in range(intentos):
            respuesta = self.client.responses.create(
                model=self.modelo,
                input=self.historial,
                **self._opciones_herramientas(),
            )
            self.historial += respuesta.output

            llamadas = [i for i in respuesta.output if i.type == "function_call"]
            if not llamadas:
                return respuesta.output_text

            for llamada in llamadas:
                self.historial.append({
                    "type": "function_call_output",
                    "call_id": llamada.call_id,
                    "output": self._ejecutar(llamada),
                })

        texto = "La consulta no se puedo completar"
        self.historial.append({"role": "assistant", "content": texto})
        return texto

    def _opciones_herramientas(self) -> dict:
        # se envía tools si hay alguna en Esquemas
        return {"tools": ESQUEMAS} if ESQUEMAS else {}

    def _ejecutar(self, llamada) -> str:
        return ejecutar_herramienta(llamada.name, llamada.arguments)