import os
from dotenv import load_dotenv
from openai import OpenAI
from agente_zoco.agent import Agente

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Falta OPENAI_API_KEY en el .env")

    agente = Agente(OpenAI(api_key=api_key))

    while True:
        men = input("Escribe un mensaje (o 'salir' para terminar): ")
        if men.lower() == "salir": break
        print("Agente:", agente.responder(men))
