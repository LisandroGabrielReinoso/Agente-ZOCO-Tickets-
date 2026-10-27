# Agente de soporte ZocoTickets

Es un agente de consola que atiende a un comercio de ZocoTickets: responde con la documentación, consulta ventas, registra reclamos y respeta quién tiene el control de la conversación (el agente o un operador)

## Cómo correrlo

Necesitás [uv](https://docs.astral.sh/uv/) y Python 3.13 o superior

1. Instalar las dependencias:
   ```bash
   uv sync
   ```
2. Crear el `.env` a partir del ejemplo y poner tu `OPENAI_API_KEY` (en PowerShell: `Copy-Item .env.example .env`):
   ```bash
   cp .env.example .env
   ```
3. Correr los tests:
   ```bash
   uv run pytest
   ```
4. Evaluar el buscador (genera las tablas de `resultados/`). Funciona sin API key porque el caché de embeddings viene en el repo:
   ```bash
   uv run evaluar-buscador
   ```
5. Usar el agente por consola:
   ```bash
   uv run agente-zoco
   ```
6. Evaluar el agente con las 15 conversaciones (usa la API, tarda unos minutos):
   ```bash
   uv run evaluar-agente
   ```

En `.env` también está `TOOL_FAILURE_RATE`. Con 0 las herramientas no fallan; con 0.3, `consultar_ventas` y `crear_reclamo` fallan el 30% de las veces

---

## Parte 1: buscador

Las preguntas dicen qué documento las responde, no qué fragmento. Entonces paso del ranking de chunks a un ranking de documentos: cada documento aparece una sola vez, en la posición de su mejor chunk. Los chunks con puntaje 0 no cuentan como encontrados

- recall@3 = de los documentos relevantes, qué fracción aparece en el top 3. Si una pregunta tiene dos relevantes y encontré uno, vale 0,5. Elegí la fracción y no "acertó al menos uno" porque una pregunta con dos documentos relevantes necesita los dos para responderse bien
- MRR = promedio de 1 / posición del primer documento relevante (0 si no aparece)

Con 20 preguntas, una sola pregunta mueve el recall@3 en 0,05 (o 0,025 si tiene dos relevantes). Por eso tomo diferencias de ese tamaño como empates

### Chunking

BM25 penaliza a los fragmentos que son más largos que el promedio. Como los DOC de ejemplo son cortos, de entre 127 y 161 palabras, y todos miden más o menos lo mismo, esa penalización casi no cambia nada y dividir por documento completo termina siendo una opción viable

los documentos .md, que vienen separados por encabezados (#), es una opción que permite mantener el contexto de un tema que se delimita muy bien. Cada fragmento queda con su título y con el tema completo

#### Ventanas fijas
Fragmentar los textos en ventanas fijas + solapamiento permite organizar la información, pero corre el riesgo de que temas diferentes queden mezclados. El solapamiento repite las últimas palabras de una ventana al principio de la siguiente, así si una frase quedó cortada aparece entera en alguna de las dos, pero eso no evita que una ventana mezcle el final de una sección con el principio de otra. Sección y ventana de 20 empatan dentro del margen de una pregunta. Elegí sección porque usa la mitad de chunks y porque cada fragmento es un tema completo con su título. Una ventana de 20 palabras puede cortar a mitad de frase

cinco formas de cortar los documentos, con BM25 y con la búsqueda vectorial (`resultados/chunking.md`):

| chunking | chunks | BM25 recall@3 | BM25 MRR | vectorial recall@3 | vectorial MRR |
|---|---:|---:|---:|---:|---:|
| documento | 12 | 0.975 | 0.917 | 0.975 | 0.925 |
| seccion | 49 | 1.000 | 0.925 | 1.000 | 0.900 |
| ventana 20/5 | 102 | 1.000 | 0.925 | 1.000 | 0.925 |
| ventana 40/10 | 51 | 1.000 | 0.875 | 0.950 | 0.863 |
| ventana 80/20 | 26 | 0.975 | 0.917 | 0.975 | 0.917 |

Me quedé con por sección

- Los fragmentos grandes (documento entero y ventana de 80) pierden recall en Q01, que tiene dos documentos relevantes: la frase de DOC-01 que responde queda diluida en un chunk largo y DOC-01 sale del top 3
- La ventana de 40 tiene casi la misma cantidad de chunks que sección (51 contra 49) y es la peor. Con un tamaño parecido, cortar a ciegas mezcla el final de una sección con el principio de otra. O sea, respetar la estructura importa más que el tamaño

### Resultados por estrategia

Con chunking por sección (`resultados/estrategias.md`):

| estrategia | recall@3 | MRR |
|---|---:|---:|
| BM25 | 1.000 | 0.925 |
| vectorial | 1.000 | 0.900 |
| híbrida (RRF) | 1.000 | 0.925 |
| híbrida + metadata | 1.000 | 0.950 |

El agente usa híbrida + metadata. La evaluación mide la misma clase `Buscador` que usa el agente

### Qué gana cada estrategia

El detalle de las 20 preguntas está en `resultados/detalle_por_pregunta.md`. Estas son las que explican las diferencias (el número es la posición del documento correcto):

| pregunta | BM25 | vectorial | híbrida | híbrida + metadata |
|---|---:|---:|---:|---:|
| Q01 ¿Qué rol puede publicar eventos una vez aprobado? | 1 | 2 (1°: DOC-03) | 1 | 1 |
| Q03 ¿Qué pasa si los lotes superan la capacidad del recinto? | 1 | 2 (1°: DOC-04) | 2 | 2 |
| Q06 ¿En cuántos días hábiles se liquida… en octubre de 2026? | 1 | 2 (1°: DOC-12) | 1 | 1 |
| Q07 ¿Cuál es el mínimo de entradas por mes del plan ZT-PRO-2? | 2 (1°: DOC-12) | 2 (1°: DOC-12) | 2 | 1 |
| Q13 ¿Qué estados devuelve la validación de un QR? | 2 (1°: DOC-11) | 1 | 1 | 1 |
| Q15 ¿Puede abrirse un reclamo sin que el usuario confirme sus datos? | 2 (1°: DOC-06) | 1 | 2 | 2 |

BM25 gana cuando la pregunta usa las mismas palabras que el documento. En Q03, DOC-03 dice literalmente "capacidad" y "recinto", mientras que la vectorial se va a DOC-04, que habla de lotes en general

La vectorial gana cuando se dice lo mismo con otras palabras. En Q15 la pregunta dice "confirme" y DOC-11 dice "confirmación": para BM25 son tokens distintos. La sección "Reclamos" de DOC-06 tiene "reclamo", "usuario" y "sin", y BM25 la pone primera. La vectorial compara significados y acierta

La híbrida junta los aciertos (arregla Q13, que fallaba BM25, y Q01 y Q06, que fallaba la vectorial), pero hereda algunos errores: en Q03 y Q15 un buscador acierta y el otro pone primero un documento equivocado, y con solo dos rankings RRF decide por diferencias mínimas

¿Son errores de mi código o límites de la técnica? Los tests de BM25, coseno y RRF pasan con valores calculados a mano, así que las cuentas están bien. Lo que queda son límites:

- Q15: BM25 sin stemming no relaciona distintas formas de la misma palabra
- Q03: la vectorial premia el tema más parecido por sobre la regla puntual, y además la respuesta de DOC-03 está repartida entre dos secciones (la regla y un ejemplo)
- Q07 y Q06: DOC-12 es un archivo histórico que repite los mismos temas que DOC-07, DOC-05 y DOC-06 pero con los valores que ya son viejos. Como usan casi las mismas palabras, el buscador no puede distinguirlos y en vez de traer el vigente trae DOC-12: en Q07 pasó con las tres estrategias (trae el mínimo de 250 en vez de 400) y en Q06 con la vectorial (7 días hábiles en vez de 5). Ninguna búsqueda por texto puede saber cuál está vigente, eso lo resuelve usando la metadata

### Metadata

**Vigencia: la uso según la fecha de la pregunta.** Lo primero que pensé fue descartar DOC-12 siempre, pero eso rompe Q17 ("¿Cuál era el mínimo… en julio de 2026?") y Q18 ("¿Cuánto cobraba… en agosto de 2026?"), que tienen a DOC-12 como respuesta. Un documento no está vencido en general, sino respecto de una fecha. Entonces:

1. Busco en la pregunta un "mes de año" (por ejemplo, "octubre de 2026"). Si no hay, uso la fecha de hoy
2. Un documento cuenta como vigente si comparte al menos un día con ese período. Esto cubre agosto de 2026, cuando conviven DOC-12 (hasta el 31/08) y DOC-06 (desde el 01/08)
3. En cada ranking (BM25 y vectorial) saco los chunks no vigentes y después fusiono con RRF

Con eso Q07 pasa al primer lugar, Q17 y Q18 siguen bien, y el MRR sube de 0,925 a 0,950

La evaluación usa una fecha de hoy fija (26/10/2026). Si usara la real, la tabla cambiaría sola cuando venzan DOC-05 y DOC-07 (31/03/2027). El agente sí usa la fecha del sistema

**Tipo: no lo uso para buscar.** `historico` ya está representado por `vigencia_hasta`, y los otros tipos (`guia`, `procedimiento`, `politica`…) no dicen nada sobre qué preguntas responde cada documento. Igual el agente lo recibe con cada fragmento

---

## Parte 2: agente con herramientas

El agente usa `gpt-4.1-mini` con tool calling nativo de la API de OpenAI (Responses). Mantiene el historial de la conversación y cita el documento entre corchetes, por ejemplo [DOC-07]

`ventas.json` tiene 34 días (del 21/09 al 25/10/2026) y, a propósito, un día sin ventas (05/10), uno con neto negativo por un evento cancelado (12/10) y uno en 2030. La fecha futura tiene datos en el archivo, pero la herramienta la rechaza por la fecha: un día que todavía no pasó no puede tener ventas

Para los reclamos usé JSON y no SQLite porque es más simple de leer y alcanza para un agente de consola. La protección contra duplicados la hago en código (ver abajo)

### Políticas

Las reglas están en código y tienen tests (`tests/test_politicas.py`, `tests/test_tools.py`, `tests/test_ventas.py`). Los tests usan un modelo falso que puede portarse mal, por ejemplo llamar a `crear_reclamo` sin preguntar, para ver que el código lo frena

- Cuando el modelo llama a `crear_reclamo`, no se ejecuta: el reclamo queda pendiente y el código le muestra al usuario un texto fijo con el motivo y la descripción exactos ("¿Confirmás? (sí/no)"). El texto lo arma el código y no el modelo, así el usuario confirma exactamente lo que se va a guardar. Solo cuenta como confirmación una respuesta como "sí", "confirmo" o "dale". "Sí, pero cambiá la descripción" no confirma: el modelo vuelve a proponer y se vuelve a preguntar
- Cada reclamo se guarda con una clave (hash de conversación + motivo + descripción). Si la clave ya está, devuelvo el mismo número sin crear otro
- El registro rechaza herramientas que no existen, argumentos de más o de menos, tipos incorrectos y valores fuera de los permitidos. `consultar_ventas` tiene un parámetro `hoy` para los tests, pero como no está en el esquema el modelo no lo puede mandar
- No inventar datos, pedir lo que falta, explicar las fallas y tratar lo que devuelven las herramientas como datos y no como órdenes (regla 7) están en el prompt. Para la regla 7, aunque el modelo se dejara engañar, sigue protegida por la confirmación en código

---

## Parte 4: evaluación

`uv run evaluar-agente` corre 15 conversaciones de varios turnos, cada una 3 veces, contra el modelo real. Los casos están en `src/agente_zoco/evaluacion/casos.py` y el detalle de cada uno en `resultados/conversaciones.md`

Para decidir si un caso cumple se ve los hechos: qué herramientas se llamaron y con qué argumentos, cuántos reclamos quedaron en la base, en qué estado terminó y si la respuesta tiene o no ciertos datos. Cada repetición usa una base de reclamos temporal y la fecha fija en 26/10/2026

### Resultados

1. Primera corrida 33/45 (`conversaciones_v1.md`): el modelo pedía confirmación por su cuenta y después el código volvía a preguntar, el usuario tenía que decir "sí" dos veces. Se corrigio en el prompt
2. Segunda 45/45 (`conversaciones_v2.md`): pero 10 casos tenían un solo mensaje y la consigna pide varios turnos
3. Final con todos de varios turnos: 43/45 (`conversaciones.md`)

En la final el C12 (regla 7) al principio daba 0/3 pero era error mío en el caso: el modelo nunca obedeció la instrucción escondida, en el segundo turno el usuario le pide el reclamo él mismo y ahí está bien proponerlo. El C03 da 1/3 porque a veces pregunta si "el día anterior" es el 14 de octubre, lo dejé así porque es una fecha relativa y la regla 5 pide preguntar

En ninguna corrida se registró un reclamo sin el sí de confirmacion

## Limitaciones

- Si la pregunta no dice el mes (¿cuánto cobraba antes?) el buscador usa la fecha de hoy y el histórico queda afuera, ahí el agente tiene que pedir la fecha
- La regla 7 la probé con la instrucción en el mensaje del usuario, no dentro de un documento
- Los mensajes del operador no quedan en el historial, al volver de HUMAN el modelo no sabe qué se habló
- El registro de transiciones vive en memoria y el horario se maneja con eventos, no con el reloj
- Los reclamos en JSON se pueden romper si el programa se corta justo cuando escribe

## mejoras

- Stemming en BM25 (arreglaría Q15)
- RRF con pesos y anteponer el título del documento a cada sección
- Detectores reales de abuso y baja confianza
- Más casos de evaluación, y que no sean los mismos que usé para ajustar el prompt

## Uso de asistentes de IA y documentación

Usé Claude Code en todo el proyecto: para entender los conceptos antes de implementarlos (BM25, IDF, coseno, RRF, las métricas), para discutir el diseño, para escribir buena parte del código y los tests, y para depurar. También para verificar si mis cálculos daban igual o casi igual que los tests

Las decisiones las tomé yo discutiéndolas con el asistente, por ejemplo el chunking por sección después de ver la tabla como salieron los resultados, no usar el tipo para buscar, JSON para los reclamos, los estados como tuplas con una función de transición y los 15 casos de evaluación

Para verificar hice algunas cuentas a mano (BM25, coseno), corrí los tests y las evaluaciones después de cada cambio, probé el agente por consola y revisé el código hasta poder enterderlo 

consulté la documentación de OpenAI (Responses API, function calling y embeddings) para armar el agente y las herramientas