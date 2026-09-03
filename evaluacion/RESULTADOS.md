# Evaluación de recuperación

Medición sobre el corpus de Distribuidora Pampa Sur, 54 preguntas escritas como las hace un empleado real.

Reproducible con:

```bash
python evaluacion/ejecutar.py
```

---

## Qué se mide y por qué así

**Se mide recuperación, no respuesta.** Para cada pregunta está declarado qué documento contiene la respuesta, así que verificar si el sistema lo trajo no requiere ningún juicio subjetivo, no cuesta cuota de API y corre en milisegundos. Es una métrica que se puede volver a correr mil veces y da lo mismo.

La calidad de la respuesta del modelo también se mide (`--con-llm`), pero es más lenta, cuesta cuota y depende de un juicio más blando. La recuperación es el piso: **si el documento correcto no llega al contexto, ninguna respuesta puede ser buena.**

---

## El resultado

| Recuperador | Documento correcto recuperado | Primero en el ranking |
| --- | --- | --- |
| **TF-IDF** (el que tenía el proyecto) | **47/54 — 87%** | 46 — 85% |
| **BM25** (el estándar de la industria) | **47/54 — 87%** | 45 — 83% |

**Empataron.**

Eso no era lo esperado. La literatura que respalda hacer recuperación léxica sin base vectorial —incluido un paper de AWS que muestra más del 90% del rendimiento de RAG sin embeddings— habla siempre de BM25, no de TF-IDF, que es su antecesor y no tiene ni saturación de frecuencia ni normalización por longitud.

Cambiar al estándar era la decisión obvia. **Medirla mostró que, en este corpus, no cambia nada.**

### Por categoría

| Categoría | TF-IDF | BM25 |
| --- | --- | --- |
| facturas | 10/10 | 10/10 |
| licencias | 11/11 | 11/11 |
| conflicto entre documentos | 1/1 | 1/1 |
| stock | 9/10 | 9/10 |
| reglamento | 8/10 | 8/10 |
| **precios** | **8/12** | **8/12** |

---

## Por qué empataron: el hallazgo real

El informe imprime los tamaños del corpus contra el presupuesto de contexto, y ahí está la respuesta:

```
Presupuesto de contexto: 14.000 caracteres

  stock_depositos.csv          14.471   (103% del presupuesto)  <-- no entra con ningún otro
  lista_precios.csv            13.903    (99% del presupuesto)  <-- no entra con ningún otro
  politica_licencias.pdf        6.226    (44% del presupuesto)
  reglamento_interno.pdf        6.077    (43% del presupuesto)
  procedimiento_facturas.pdf    5.762    (41% del presupuesto)
```

**Una sola planilla consume todo el presupuesto.** La de stock ni siquiera entra completa.

Eso convierte la selección en un dilema binario: o entra la planilla sola, o entran dos PDF y la planilla queda afuera. Los siete fallos son exactamente eso:

```
PRE-06  ¿el descuento por volumen y el de contado se suman o van en cascada?
        esperaba lista_precios.csv — trajo reglamento_interno.pdf, procedimiento_facturas.pdf

PRE-07  ¿qué productos tenemos con IVA al 10,5?
        esperaba lista_precios.csv — trajo procedimiento_facturas.pdf, politica_licencias.pdf

PRE-10  ¿qué proveedor nos vende el queso cremoso?
        esperaba lista_precios.csv — trajo procedimiento_facturas.pdf, reglamento_interno.pdf

STK-05  ¿cuánto hay comprometido de la Coca de 354?
        esperaba stock_depositos.csv — trajo lista_precios.csv

REG-06  me lastimé cargando un pallet, ¿a quién aviso?
        esperaba reglamento_interno.pdf — trajo politica_licencias.pdf, procedimiento_facturas.pdf

REG-10  ¿cuándo pagan el aguinaldo?
        esperaba reglamento_interno.pdf — trajo lista_precios.csv
```

**Cuatro de los siete fallos son sobre la lista de precios**, que es justamente el documento más grande y el que más se consulta.

### La conclusión

El cuello de botella **no es el algoritmo de ranking**. Por eso cambiarlo no movió el número.

El cuello de botella es la **granularidad**: el sistema elige bien, pero entre unidades del tamaño equivocado. Una lista de precios de 77 artículos entra al contexto entera o no entra, cuando la pregunta *"¿cuánto sale el queso cremoso?"* necesita **una fila**, no las 77.

Es la misma conclusión a la que llega la literatura reciente sobre RAG y datos tabulares: recuperar más fragmentos mejora el *recall* pero no la precisión, porque el problema no es cuánto se recupera sino en qué unidades.

---

## Qué hacer con esto

**Lo que NO hay que hacer:** cambiar a BM25 porque es el estándar. Está medido: no cambia nada acá. Sí cambiaría con un corpus de decenas de documentos, donde la normalización por longitud empieza a discriminar. Con cinco, no.

**Lo que sí mueve la aguja**, en orden de impacto:

1. **Selección a nivel de fila para las planillas.** Que la lista de precios aporte al contexto solo las filas que mencionan lo que se preguntó, con el esquema de la tabla como encabezado. Las cuatro preguntas de precios que fallan hoy pasarían, y quedaría presupuesto libre para que entre además el documento de texto que corresponda.

2. **Ruta de cómputo para preguntas agregadas.** *"¿Qué productos están bajo el punto de reposición?"* no se responde recuperando texto: se responde calculando sobre la tabla. Recuperar más filas no lo arregla.

Ambas son extensiones del router que el proyecto ya tiene, no piezas nuevas.

---

## Nota de honestidad

Las preguntas y el corpus los escribió la misma persona que escribió el sistema. Eso es un sesgo real y conviene decirlo antes de que lo diga otro.

Lo que lo compensa en parte: el corpus está construido contra fuentes primarias verificables —la especificación del SEPA, el texto de la Ley de Contrato de Trabajo, el CCT 130/75 y un catálogo mayorista real— y las preguntas salieron de un relevamiento de qué consulta realmente un empleado, no de mirar el código y escribir preguntas que sabía que iban a pasar.

La prueba está en el resultado: **el sistema falla en 7 de 54.** Un set escrito para lucirse no falla.
