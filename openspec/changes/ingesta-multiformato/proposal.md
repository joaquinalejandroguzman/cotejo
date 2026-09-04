# Propuesta: ingesta multi-formato para el corpus interno

## Intent

Cotejo hoy solo lee PDF. Lo que los empleados preguntan todo el día —precios, stock, quién ve cada tema— vive en planillas, no en PDF. Mientras el producto no las lea, el dueño sigue siendo el cuello de botella y la herramienta no resuelve el dolor que promete. Excel y Sheets son el diferenciador central, no un extra.

## Scope

### In Scope

- `.csv` con separador y encoding detectados, no asumidos (es-AR usa `;` y `cp1252`).
- `.xlsx` y `.xls`, cada hoja como documento citable por separado.
- Google Sheets publicada, por URL, sin credenciales.
- Advertencia visible antes de pegar la URL: publicar deja la hoja accesible con el link, sin login; no va con sueldos, costos ni datos personales.
- Reducción de tablas grandes al presupuesto de contexto: esquema más filas relevantes.
- Límite explícito de tamaño de archivo (hoy rige el default de 200 MB de Streamlit).
- Corpus interno nuevo de una distribuidora mayorista ficticia: **Distribuidora Pampa Sureña**.
- `pandas`, `openpyxl` y `xlrd` declarados en `requirements.txt` **y** `pyproject.toml`, con el test de paridad que hoy no existe.
- Corregir el contrato de idioma de `openspec/config.yaml` a español.

### Out of Scope

- RAG híbrido con embeddings densos, arquitectura hexagonal, Docker.
- Rediseño de UX más allá de exponer los formatos y la advertencia.
- Agregación numérica (promedios, sumas) sobre las planillas.
- Los 6 PDF de `documentos/`: quedan intactos.

## Capabilities

### New Capabilities

- `ingesta-tabular`: CSV y Excel a texto de contexto, con multi-hoja y casos borde.
- `ingesta-sheets`: Google Sheets publicada por URL, con advertencia y detección de hoja no publicada.
- `seleccion-de-filas`: reducir una tabla grande al presupuesto de contexto.

### Modified Capabilities

- Ninguna. No existe `openspec/specs/` todavía.

## Approach

Un módulo de despacho por formato delega en `pdf_utils.py` sin tocarlo y en extractores tabulares nuevos. `Document = tuple[str, str]` sigue siendo el contrato de salida, así que `doc_selector.py` y `combine_documents` no cambian. La selección de filas extiende al grano de fila la misma filosofía léxica que `doc_selector.py` ya aplica al grano de documento. La lógica va en módulos, nunca en `app.py`, que no tiene tests unitarios.

## Affected Areas

| Área | Impacto | Qué cambia |
| --- | --- | --- |
| Módulos nuevos | New | Despacho, extracción tabular, Sheets, selección de filas |
| `app.py:123-130,142-150` | Modified | Uploader, input de URL, advertencia, despacho |
| `pdf_utils.py`, `doc_selector.py` | — | Intactos |
| `Makefile:12`, `pyproject.toml:41,81` | Modified | Módulos nuevos en `SRC`, `py-modules` e isort |
| `pyproject.toml:18,98-100` | Modified | Dependencias y overrides de mypy |
| `requirements.txt` | Modified | Dependencias nuevas |
| `documentos-internos/` | New | Corpus de Distribuidora Pampa Sureña |
| `openspec/config.yaml:8` | Modified | Contrato de idioma a español |

## Risks

| Riesgo | Prob. | Mitigación |
| --- | --- | --- |
| Una PyME publica una hoja con sueldos y queda expuesta | Media | Advertencia en criollo junto al input, antes de pegar la URL |
| mypy estricto contra `pandas`: retornos `Any` | Alta | Encapsular pandas detrás de una frontera tipada propia |
| Planilla grande agota la RAM del plan gratuito | Media | Límite de tamaño y de filas antes de cargar |
| Sheets compartida pero no publicada devuelve HTML de login | Media | Validar que la respuesta sea CSV, no HTML |
| CSV es-AR (`;`, `cp1252`) leído con caracteres rotos | Alta | Detección con fallback; test con archivo real acentuado |
| Desajuste entre `requirements.txt` y `pyproject.toml` | Media | El test de paridad **no existe hoy**: se construye en el PR 1 |

## Rollback Plan

Cada PR se revierte solo; revertir el último deja la app leyendo los formatos de los previos. Revertir todo vuelve al estado PDF: `pdf_utils.py` y `doc_selector.py` nunca se tocan, no hay estado persistido ni migración que deshacer. Se quitan las dependencias de ambos archivos y Streamlit Cloud reconstruye.

## Dependencies

- `pandas` (ya presente vía streamlit, se declara explícito), `openpyxl` (`.xlsx`), `xlrd` (`.xls`; verificado con pandas 3.0.5, sin transitivas).
- Una Google Sheets publicada para el corpus.

## Success Criteria

- [ ] Un `.xlsx` de 100+ filas responde el precio de un producto puntual.
- [ ] Un `.csv` exportado por Excel es-AR se lee sin caracteres rotos.
- [ ] Un `.xls` viejo se lee sin pedir que se reexporte.
- [ ] Una Sheets publicada responde; una solo compartida da error claro, no datos falsos.
- [ ] La advertencia de exposición es visible antes de pegar la URL.
- [ ] `make lint`, `make format-check`, `make typecheck`, `make test`, `make test-e2e` en verde.
- [ ] Cada test nuevo falló primero (TDD estricto).

## Pronóstico de tamaño

**Excede el presupuesto de 400 líneas.** Estimado 900-1300 líneas con tests. Cadena de 5 PR, cada uno con entrega visible y reversible solo:

| PR | Entrega | Est. |
| --- | --- | --- |
| 1 | CSV punta a punta: deps, paridad, despacho, encoding, uploader | ~300 |
| 2 | Excel `.xlsx` y `.xls`, hojas como documentos separados | ~280 |
| 3 | Selección de filas y límite de tamaño | ~320 |
| 4 | Google Sheets por URL y advertencia | ~250 |
| 5 | Corpus de Distribuidora Pampa Sureña y README | ~200 |

`Decision needed before apply: Yes`
`Chained PRs recommended: Yes`
`400-line budget risk: High`

## Decisiones resueltas

Preguntas de la ronda de propuesta, ya respondidas por el usuario el 2026-09-02.

| Tema | Decisión |
| --- | --- |
| Nombre de la PyME ficticia | **Distribuidora Pampa Sureña** |
| Techo de tamaño por archivo | **5 MB**, muy por debajo de los 200 MB de Streamlit |
| Cabeceras decorativas | **Se detecta la fila de encabezado real.** Una planilla de PyME tiene título y fecha arriba de la tabla; exigir planilla limpia es diseñar para un caso que no existe |
| Idioma | **Se unifica todo a español**, incluidos `openspec/config.yaml`, `Makefile`, `tests/e2e/test_smoke.py` y los comentarios de `pyproject.toml` |
| Entrega | **Cadena de 5 PR**, según el pronóstico de tamaño de la sección anterior |

### Cuando ninguna fila matchea la pregunta

**Se manda el esquema de la tabla sin ninguna fila de datos.**

Se descartó la simetría con `select_relevant_docs`, que ante un documento sin coincidencias devuelve los primeros en orden original. Esa regla es inofensiva para documentos: el modelo lee algo irrelevante y responde que no tiene la información.

Para una tabla es peligrosa. Si el empleado pregunta por el artículo 4021 y ese artículo no está en la planilla, mandar las primeras filas le pone al modelo datos con la forma exacta de la respuesta esperada — SKU, producto, precio — y lo empuja a contestar con el precio de otro artículo. El empleado cotiza mal y el error llega a un cliente.

Con el esquema solo, el agente puede responder algo útil y verdadero a la vez: «tengo la lista de precios cargada, pero no encuentro el artículo 4021». Eso sostiene la promesa central del producto, que es no inventar nunca.

## Corrección a la premisa de entrada

La fase de propuesta reportó que el test de paridad entre `requirements.txt` y `pyproject.toml` no existe. **Es un falso positivo**: el test existe en la rama `test/sincronia-de-dependencias` (PR #6), que todavía no está mergeada a `main`. No hay que construirlo; hay que mergear ese PR antes de sumar dependencias nuevas.

## Trampa detectada: un módulo nuevo se registra en tres lugares

Hallazgo válido de la fase de propuesta, verificado contra el repositorio. Omitir cualquiera de los tres rompe una compuerta distinta:

| Lugar | Qué rompe si falta |
| --- | --- |
| `Makefile:12` (`SRC`) | `make lint`, `make format-check` y `make typecheck` ignoran el módulo |
| `pyproject.toml:41` (`py-modules`) | `pip install -e .` no lo instala |
| `pyproject.toml:81` (`known-first-party`) | El orden de imports queda mal y falla el lint |
