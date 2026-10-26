import re
import unicodedata
import math

def normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower()) #sacamos las tildes y pasamos a minúsculas
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")

def tokenizar(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalizar(texto))

def calcular_idf(chunks_tokenizados: list[list[str]]) -> dict[str, float]:
    N = len(chunks_tokenizados)
    n = {}
    for tokens in chunks_tokenizados:
        for palabra in set(tokens):  # cada palabra cuenta una vez por chunk
            n[palabra] = n.get(palabra, 0) + 1
    idf = {}
    for palabra, n_t in n.items():
        numerador = N - n_t + 0.5
        denominador = n_t + 0.5
        idf[palabra] = math.log(numerador / denominador + 1)
    return idf


class BM25:
    def __init__(self, chunks_tokenizados: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.idf = calcular_idf(chunks_tokenizados)
        self.largos = [len(tokens) for tokens in chunks_tokenizados]
        self.largo_promedio = sum(self.largos) / len(self.largos)

        # f(t,c): cuántas veces aparece cada palabra en cada chunk
        self.frecuencias = []
        for tokens in chunks_tokenizados:
            f = {}
            for palabra in tokens:
                f[palabra] = f.get(palabra, 0) + 1
            self.frecuencias.append(f)

    def puntaje(self, consulta: list[str], i: int) -> float:
        normalizacion = 1 - self.b + self.b * self.largos[i] / self.largo_promedio
        total = 0.0
        for palabra in dict.fromkeys(consulta):  # palabras sin repetir, en orden
            f = self.frecuencias[i].get(palabra, 0)
            if f == 0:
                continue
            fraccion = f * (self.k1 + 1) / (f + self.k1 * normalizacion)
            total += self.idf[palabra] * fraccion
        return total

    def puntajes(self, consulta: list[str]) -> list[float]:
        return [self.puntaje(consulta, i) for i in range(len(self.frecuencias))]