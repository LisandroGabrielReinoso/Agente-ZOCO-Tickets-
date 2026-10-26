import re
import unicodedata

def normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower()) #sacamos las tildes y pasamos a minúsculas
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")

def tokenizar(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalizar(texto))