#Búsqueda vectorial: similitud coseno 

import numpy as np

def similitud_coseno(consulta: np.ndarray, matriz: np.ndarray) -> np.ndarray:
    productos = matriz @ consulta                          # a · b, para cada chunk a la vez
    normas_chunks = np.sqrt(np.sum(matriz ** 2, axis=1))   # ‖a‖ de cada fila
    norma_consulta = np.sqrt(np.sum(consulta ** 2))        # ‖b‖
    denominador = normas_chunks * norma_consulta
    # un vector de ceros tiene norma 0: retornamos 0 
    return np.divide(productos, denominador, out=np.zeros_like(productos), where=denominador > 0)
