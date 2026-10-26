#Formato en Markdown de las tablas de resultados (solo arma texto, no calcula nada)


def tabla_chunking(filas) -> str:
    lineas = [
        "| chunking | chunks | BM25 recall@3 | BM25 MRR | vectorial recall@3 | vectorial MRR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for nombre, n_chunks, recall_bm25, mrr_bm25, recall_vec, mrr_vec in filas:
        lineas.append(
            f"| {nombre} | {n_chunks} | {recall_bm25:.3f} | {mrr_bm25:.3f} | {recall_vec:.3f} | {mrr_vec:.3f} |"
        )
    return "\n".join(lineas) + "\n"


def tabla_estrategias(filas) -> str:
    lineas = ["| estrategia | recall@3 | MRR |", "|---|---:|---:|"]
    for nombre, recall, mrr in filas:
        lineas.append(f"| {nombre} | {recall:.3f} | {mrr:.3f} |")
    return "\n".join(lineas) + "\n"


def tabla_detalle(filas, nombres_estrategias) -> str:
    # celda: "1" si el relevante quedó primero; si no, su posición y qué documento quedó 1°
    lineas = [
        "| id | pregunta | relevantes | " + " | ".join(nombres_estrategias) + " |",
        "|---|---|---|" + "---:|" * len(nombres_estrategias),
    ]
    for id_pregunta, pregunta, relevantes, celdas in filas:
        textos = []
        for posicion, primero in celdas:
            if posicion == 1:
                textos.append("1")
            elif posicion is None:
                textos.append(f"no aparece (1°: {primero})")
            else:
                textos.append(f"{posicion} (1°: {primero})")
        lineas.append(f"| {id_pregunta} | {pregunta} | {', '.join(relevantes)} | " + " | ".join(textos) + " |")
    return "\n".join(lineas) + "\n"
