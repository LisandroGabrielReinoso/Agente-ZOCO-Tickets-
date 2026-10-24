import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key: raise SystemExit("falta la OPENAI_API_KEY en .env")

client = OpenAI(api_key=api_key)

while True:
    men = input("Escriba un mensaje (o 'salir' para terminar): ")

    if men.lower() == "salir".lower(): break

    respuesta = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": men}],
    )
    print(respuesta.choices[0].message.content)