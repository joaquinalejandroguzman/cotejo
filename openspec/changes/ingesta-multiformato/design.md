# Diseño: Ingesta multi-formato

> Fase `sdd-design` del cambio `ingesta-multiformato`. Satisface
> `specs/ingesta/spec.md`. Artefacto en español: el contrato de idioma en
> inglés de `openspec/config.yaml:8` está desactualizado y se corrige en el PR 1.

## Enfoque técnico

Cuatro módulos planos nuevos, siguiendo el layout existente (sin paquete ni
`src/`). `ingesta.py` es el único punto de entrada y despacha por extensión.
`tabla_utils.py` es el único módulo que importa pandas. `fila_selector.py`
reduce tablas grandes al presupuesto de contexto. `sheets_client.py` baja una
Google Sheets publicada. `pdf_utils.py` y `doc_selector.py` quedan
byte-idénticos: el contrato `Document = tuple[str, str]` no se toca.

## Decisiones de arquitectura

### D1 — El puerto de extracción es `list[Document]`; `pdf_utils` se adapta en el borde

**Elección.** `ingesta.extraer_documentos(nombre, origen) -> list[Document]`.
La rama PDF llama a `extract_text_from_pdf(origen)` y envuelve el `str` en
`[(nombre, texto)]`. Excel devuelve una tupla por hoja.

**Alternativas descartadas.**

| Opción | Por qué no |
| --- | --- |
| Unificar todas las firmas: `extract_text_from_pdf -> list[Document]` | Reescribe los 4 tests de `TestExtractTextFromPdf` (`tests/test_pdf_utils.py:12-35`), que hoy comparan `str` con `str`, y obliga a `pdf_utils` a inventar un nombre legible que no conoce: el nombre viene de `DEFAULT_DOCS` o de `UploadedFile.name`, no del PDF. Cambia el único camino que ya está en producción para beneficiar a los que todavía no existen. |
| Que cada extractor devuelva lo suyo y el despacho normalice | Deja `str \| list[Document]` en el puerto. Bajo mypy `strict` cada consumidor tiene que estrechar el tipo, y el estrechamiento termina en `app.py`, que no tiene tests unitarios. |

**Fundamento.** El costo de D1 es un adaptador de tres líneas dentro de
`ingesta.py`. A cambio: `pdf_utils.py` no se toca, sus tests siguen verdes sin
una sola línea de churn, `app.py` ve una única forma (`docs.extend(...)`) y no
hay ningún `isinstance` en el camino. La heterogeneidad de firmas es real pero
es un detalle del motor, no del puerto; se absorbe donde es barata.

### D2 — Todo cruza la frontera de pandas como `str`

`tabla_utils.py` lee con `dtype=str, keep_default_na=False, header=None` y
expone solo `Tabla` (dataclass congelada de `list[str]` / `list[list[str]]`).
Ningún valor de pandas se devuelve directo: pasa por
`_celda(valor: object) -> str`.

Verificado: **pandas 3.0.5 no trae `py.typed`**, así que necesita
`ignore_missing_imports` y todos sus símbolos son `Any`. Con `warn_return_any`
(parte de `strict`), devolver una expresión de pandas desde una función anotada
es un error. La coerción explícita es lo que impide que ese `Any` se propague.

La misma decisión satisface el requisito de decimales con coma: leyendo como
texto, `1234,50` nunca se parsea a float ni se re-renderiza como `1234.5`.
Alcance honesto de la garantía: las celdas guardadas como texto se conservan
verbatim; una celda que Excel guardó como número binario ya perdió la coma en
origen y no hay nada que preservar.

Descartado: parsear CSV con el `csv` de la stdlib y Excel con openpyxl/xlrd
directo, evitando pandas. Da tipos nativos y cero `Any`, pero la spec obliga a
declarar pandas igual, y son tres parsers a mantener en vez de uno. El riesgo
de `Any` queda contenido en una función de cinco líneas.

### D3 — La reducción de filas es un round-trip del formato renderizado

La pregunta no se conoce al extraer (la extracción está cacheada con
`st.cache_data`), así que la reducción corre después. `tabla_utils.renderizar`
y `tabla_utils.parsear` son inversas y se testean como round-trip.
`fila_selector.reducir_tablas` parsea cada `Document`, y si no matchea el
formato (un PDF) lo devuelve intacto.

Descartado: llevar las `Tabla` por un canal paralelo (`dict[str, Tabla]` o una
dataclass más rica). Es más limpio en teoría, pero obliga a `app.py` a
transportar y sincronizar dos estructuras a través del caché — lógica no
trivial en el único archivo sin tests unitarios. El round-trip cuesta un
`parsear` testeado y reduce el cambio en `app.py` a una línea.

Guarda contra falsos positivos: `parsear` exige que el texto empiece con la
línea literal `Tabla: `, seguida de `Columnas: ... (N filas)` y de una tabla de
pipes. Un PDF que cumpla las tres es prácticamente imposible; el caracter `|`
en las celdas se escapa al renderizar para que el round-trip sea unívoco.

### D4 — Sin coincidencias no hay filas, y no existe el código que las agregaría

`seleccionar_filas` devuelve `[]` cuando ninguna fila puntúa. `renderizar`
emite exactamente las filas que recibe. **En `fila_selector.py` no hay ninguna
rama de «rellenar hasta el presupuesto» ni «primeras N filas»**: la garantía es
la ausencia de ese camino, no una condición que alguien pueda invertir.

Salida sin coincidencias: las dos líneas de esquema más
`Sin filas que coincidan con la consulta.` Esa frase es la que habilita la
respuesta útil y verdadera («tengo la lista, no encuentro el artículo 4021»).

Interacción con `doc_selector`: su fallback de «primeros documentos en orden
original» sigue vivo, pero opera a grano de documento y **después** de que la
tabla ya quedó sin filas. Las dos capas componen sin filtrar nada.

### D5 — Decisiones menores

| Tema | Elección | Por qué |
| --- | --- | --- |
| Hojas ocultas | Visibilidad leída del motor: `openpyxl` `worksheet.sheet_state == "visible"`, `xlrd` `sheet.visibility == 0` | `pd.read_excel(sheet_name=None)` devuelve las ocultas también. Requiere `origen.seek(0)` entre la pasada de visibilidad y la de datos |
| Encoding CSV | `utf-8-sig` → `cp1252` → `latin-1` | `utf-8-sig` cubre UTF-8 con y sin BOM; `latin-1` nunca falla y cierra la cadena |
| Separador CSV | `csv.Sniffer` sobre el texto ya decodificado, con fallback a conteo de `;` vs `,` | Sniffer es stdlib pero inestable en muestras cortas; el conteo es determinista y testeable |
| Encabezado real | Leer con `header=None` y elegir la primera fila cuyo ancho de celdas no vacías iguale al ancho modal de las filas siguientes; fallback a la fila 0 | Una fila de título es angosta y no coincide con el ancho de la tabla |
| Límite de 5 MB | En `ingesta.py`, antes de cualquier llamada a pandas | Descartado `maxUploadSize = 5` en `.streamlit/config.toml`: es global y rompería la subida de PDF grandes, que están fuera de alcance |
| Tokenizador de filas | `fila_selector` importa `_tokens` de `doc_selector` | Duplicar el stemmer y las ~120 stopwords es deuda con deriva garantizada. `tests/test_doc_selector.py:8-9` ya sienta el precedente de importar ese privado. `doc_selector.py` queda intacto; promoverlo a público es un follow-up de una línea si molesta |
| URL de Sheets | Se extrae `{ID}` y `{GID}` y se **reconstruye** la URL canónica `https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}` | El usuario no controla el host ni el esquema. Sin redirecciones cross-host, con timeout y tope de bytes |
| Presupuesto por tabla | `MAX_CONTEXT_CHARS` importado de `doc_selector` | Una sola fuente de verdad; el total lo sigue resolviendo `select_relevant_docs` |

## Flujo de datos

```
subida de archivo / URL de Sheets
   │
   ▼
ingesta.extraer_documentos(nombre, origen)      ← valida 5 MB acá
   ├─ .pdf  → pdf_utils.extract_text_from_pdf → [(nombre, texto)]
   ├─ .csv  → tabla_utils.leer_csv    ─┐
   ├─ .xlsx → tabla_utils.leer_excel  ─┼→ [Tabla] → renderizar → [(nombre, texto)]
   └─ .xls  → tabla_utils.leer_excel  ─┘         (una tupla por hoja visible)
   sheets_client.descargar_csv → bytes → leer_csv
                       │
                       ▼  list[Document]   (cacheado; la pregunta no interviene)
pregunta ─→ fila_selector.reducir_tablas ─→ doc_selector.select_relevant_docs
                  (parsear → seleccionar → renderizar)          │
                                                                ▼
                                        pdf_utils.combine_documents → system prompt
```

## Cambios de archivos

| Archivo | Acción | Descripción |
| --- | --- | --- |
| `ingesta.py` | Crear | Despacho por extensión, límite de 5 MB, `IngestaError` |
| `tabla_utils.py` | Crear | Frontera tipada sobre pandas: `Tabla`, `leer_csv`, `leer_excel`, `renderizar`, `parsear` |
| `fila_selector.py` | Crear | `reducir_tablas`, `seleccionar_filas` |
| `sheets_client.py` | Crear | `descargar_csv`, `SheetsError`, detección de HTML |
| `app.py:123-130` | Modificar | `type=["pdf","csv","xlsx","xls"]`, input de URL y advertencia previa |
| `app.py:142-150` | Modificar | `load_doc_text` → `cargar(nombre, origen) -> list[Document]`; `docs.extend(...)`; `except IngestaError` con `st.sidebar.error` |
| `app.py:362` | Modificar | Una línea: `docs = reducir_tablas(question, docs)` antes de `select_relevant_docs` |
| `Makefile:12` | Modificar | Los 4 módulos en `SRC` — si falta, `lint`, `format-check` y `typecheck` los ignoran |
| `pyproject.toml:41` | Modificar | Los 4 módulos en `py-modules` — si falta, `pip install -e .` no los instala |
| `pyproject.toml:81` | Modificar | Los 4 módulos en `known-first-party` — si falta, falla el lint por orden de imports |
| `pyproject.toml:18` | Modificar | `pandas`, `openpyxl`, `xlrd` como dependencias propias |
| `pyproject.toml:98-100` | Modificar | Override de mypy: `pandas.*`, `openpyxl.*`, `xlrd.*` con `ignore_missing_imports` |
| `requirements.txt` | Modificar | Las mismas tres, con la misma restricción de versión |
| `tests/test_dependencias.py` | Crear o extender | Paridad `requirements.txt` ↔ `pyproject.toml`. **Verificado: no existe en esta rama.** El PR 1 no depende de que se mergee la rama `test/sincronia-de-dependencias`: si el archivo no está, lo crea; si está, lo extiende |
| `tests/fixtures/` | Crear | CSV `;`+`cp1252` acentuado, `.xlsx` de 3 hojas (una oculta, una vacía), `.xls` legado chico |
| `documentos-internos/` | Crear | Corpus de Distribuidora Pampa Sureña (PR 5) |
| `openspec/config.yaml:8` | Modificar | Contrato de idioma a español (PR 1) |

**Los tres puntos de registro son obligatorios y rompen compuertas distintas.**
Cada módulo nuevo entra en `Makefile:12`, `pyproject.toml:41` y
`pyproject.toml:81` en el mismo PR que lo crea.

## Interfaces / Contratos

```python
# ingesta.py — único punto de entrada
type Origen = bytes | Path
LIMITE_BYTES = 5 * 1024 * 1024

class IngestaError(Exception): ...        # espejo de groq_client.GroqError

def extraer_documentos(nombre: str, origen: Origen) -> list[Document]: ...

# tabla_utils.py — único módulo que importa pandas
@dataclass(frozen=True)
class Tabla:
    nombre: str
    columnas: list[str]
    filas: list[list[str]]                # todo str; ningún Any sale de acá

def leer_csv(datos: bytes, nombre: str) -> Tabla: ...
def leer_excel(datos: bytes, nombre: str, legado: bool) -> list[Tabla]: ...
def renderizar(tabla: Tabla, filas: list[list[str]]) -> str: ...
def parsear(texto: str) -> Tabla | None: ...        # inversa de renderizar
def _celda(valor: object) -> str: ...               # la única salida de pandas

# fila_selector.py
def reducir_tablas(pregunta: str, docs: list[Document],
                   max_chars: int = MAX_CONTEXT_CHARS) -> list[Document]: ...
def seleccionar_filas(pregunta: str, tabla: Tabla, max_chars: int) -> list[list[str]]: ...

# sheets_client.py
class SheetsError(IngestaError): ...
def descargar_csv(url: str, timeout: int = 20) -> bytes: ...
```

Formato renderizado (contrato de round-trip con `parsear`):

```
Tabla: lista_precios.xlsx — Precios
Columnas: SKU, Producto, Proveedor, Precio (128 filas)

| SKU | Producto | Proveedor | Precio |
| --- | --- | --- | --- |
| 4018 | Yerba Playadito 1kg | Mate SA | 4350,50 |
```

Sin coincidencias: las dos primeras líneas más
`Sin filas que coincidan con la consulta.`

El nombre de una hoja es `f"{archivo} — {hoja}"`. Efecto útil: `doc_selector`
pondera los términos del título ×3, así que el nombre de la hoja participa del
ranking sin código extra.

## Estrategia de testing

TDD estricto: cada test falla primero. `make test` es la compuerta.

| Capa | Qué se prueba | Cómo |
| --- | --- | --- |
| Unit | `tabla_utils`: encoding, separador, encabezado real, decimal con coma, hoja→documento, hojas ocultas y vacías, escape de `\|`, round-trip `renderizar`↔`parsear` | pytest sobre fixtures reales en `tests/fixtures/` |
| Unit | `ingesta`: despacho por extensión, extensión desconocida → `IngestaError`, PDF delegado sin cambios | Doble de `pdf_utils.extract_text_from_pdf` para probar la delegación |
| Unit | `fila_selector`: filas que matchean, **cero filas ante cero coincidencias**, presupuesto respetado, `Document` no-tabla intacto | Test de propiedad: toda fila renderizada contiene al menos un token de la pregunta |
| Unit | `sheets_client`: reconstrucción canónica de la URL, host fuera de la allowlist rechazado, respuesta HTML → `SheetsError` | `requests.get` stubbeado con el mismo patrón de `tests/test_groq_client.py` |
| Integration | Límite de 5 MB antes de pandas | Bytes generados en runtime, no fixture commiteado |
| Integration | Paridad de dependencias | `tests/test_dependencias.py` |
| E2E | La advertencia de exposición es visible al abrir la sección, sin URL pegada | `tests/e2e/test_smoke.py`; es el único requisito cuya garantía es de orden en la UI |

## Matriz de amenazas

| Frontera | Casos adversarios | Aplicabilidad | Respuesta de diseño | Tests RED planificados |
| --- | --- | --- | --- | --- |
| Rutas tipo documentación | Clasificación por extensión (`.csv`, `.xlsx`, `.xls`, `.pdf`), extensión desconocida, extensión que miente sobre el contenido | **Aplicable** — el despacho clasifica archivos por extensión | Allowlist cerrada de extensiones; extensión desconocida → `IngestaError`, nunca un parser por defecto. La clasificación elige un parser, jamás ejecuta nada. Un archivo mal etiquetado hace fallar al parser y el error sube como `IngestaError` | Uno por clase: extensión permitida, extensión desconocida, contenido que no corresponde a la extensión |
| Selección de repositorio Git | — | N/A: el cambio no automatiza Git | — | — |
| Estado de commit | — | N/A: el cambio no automatiza Git | — | — |
| Estado de push | — | N/A: el cambio no automatiza Git | — | — |
| Comandos de PR | — | N/A: el cambio no automatiza PR | — | — |

Frontera adicional fuera de la matriz: **URL provista por el usuario a un GET
del servidor**. Respuesta: no se hace fetch de la URL cruda; se extraen `{ID}` y
`{GID}` y se reconstruye la URL canónica sobre `https://docs.google.com`, con
timeout, sin seguir redirecciones a otro host y con tope de bytes. Tests RED:
host arbitrario rechazado, esquema `file://` rechazado, respuesta HTML
rechazada.

## Migración / Rollout

Sin migración de datos ni estado persistido. Cadena de 5 PR; cada eslabón
entrega algo funcional y se revierte solo.

| PR | Componentes de este diseño | Entregable verificable |
| --- | --- | --- |
| 1 | `ingesta.py` (despacho + adaptador PDF de D1), `tabla_utils.py` (D2, CSV, encabezado real), deps + 3 puntos de registro ×2 módulos, test de paridad, `config.yaml` a español, uploader con `csv` | Un CSV es-AR responde en la app |
| 2 | `tabla_utils.leer_excel` (D5: hojas visibles, `seek(0)`), `.xlsx` y `.xls`, hoja→`Document` | Un `.xlsx` de 3 hojas cita la hoja correcta |
| 3 | `fila_selector.py` (D3, D4) + 3 puntos de registro, `renderizar`/`parsear`, límite de 5 MB en `ingesta.py` | Una planilla de 100+ filas responde un precio puntual; un artículo inexistente devuelve esquema sin filas |
| 4 | `sheets_client.py` + 3 puntos de registro, advertencia previa al input, detección de HTML | Una Sheets publicada responde; una solo compartida da error claro |
| 5 | Corpus de Distribuidora Pampa Sureña, README, y la traducción a español de `Makefile`, `tests/e2e/test_smoke.py` y los comentarios de `pyproject.toml` | El corpus valida los PR 1-4 con datos reales |

La traducción cosmética se difiere al PR 5 a propósito: meterla en el PR 1
infla el diff del eslabón que carga el riesgo real.

Restricción de despliegue (Streamlit Community Cloud): el techo de RAM es de
690 MB a 2,7 GB. El límite de 5 MB por archivo y la reducción de filas antes
del prompt son las dos defensas; `maxUploadSize` sigue en el default de 200 MB
a propósito (ver D5).

## Preguntas abiertas

- [ ] Ninguna que bloquee la implementación.
