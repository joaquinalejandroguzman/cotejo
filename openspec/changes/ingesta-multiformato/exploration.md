# Exploración: ingesta multi-formato y corpus interno de PyME

> Fase `sdd-explore` del cambio `ingesta-multiformato`.
> Investigación previa a la propuesta. No define alcance ni compromete implementación.

## Estado actual

- `app.py` sube archivos con `st.file_uploader(type=["pdf"], accept_multiple_files=True)` (líneas 123-130), envuelve los bytes en `io.BytesIO` y llama a `extract_text_from_pdf` a través de `load_doc_text` (líneas 142-150, cacheada con `st.cache_data`). Está atado a PDF en tres lugares distintos: el `type=["pdf"]` del uploader, el nombre del módulo `pdf_utils.py`, y `load_doc_text`, que llama directo a `extract_text_from_pdf` sin ninguna capa de despacho por formato.
- `pdf_utils.py` es el único punto de extracción de texto hoy. Expone `type PdfSource = str | Path | IO[bytes]`, `type Document = tuple[str, str]` (nombre legible, texto extraído), `extract_text_from_pdf(source) -> str`, `truncate_for_context` y `combine_documents(docs: list[Document]) -> str`. Internamente usa `pypdf.PdfReader`.
- `doc_selector.py` hace TF-IDF **a nivel de documento completo** (título más cuerpo) contra `MAX_CONTEXT_CHARS = 14000` para decidir qué `Document`s entran en el prompt. No tiene ningún concepto de fila, columna ni tabla: opera sobre el string ya aplanado de cada documento.
- Dependencias declaradas hoy, iguales en `requirements.txt` y `pyproject.toml`: `streamlit>=1.36`, `pypdf>=4.0`, `requests>=2.31`.
- Verificado en el virtualenv del proyecto: **pandas 3.0.5 ya está instalado, pero de forma transitiva**. `streamlit-1.63.0.dist-info/METADATA` declara `Requires-Dist: pandas<4,>=1.4.0`. No está declarado como dependencia propia. **openpyxl no está instalado.**
- `.streamlit/config.toml` no define `maxUploadSize`, así que rige el default de Streamlit de 200 MB por archivo, muy por encima del techo de RAM de Streamlit Community Cloud (690 MB a 2,7 GB).

## Deuda detectada, fuera del alcance de este cambio

- `pyproject.toml` ya dice `name = "sabia"`, pero `app.py`, `README.md` y `openspec/config.yaml` siguen con el branding de «TiendaNova» y el encuadre de agente de cara al cliente. Quedaron desactualizados frente al pivot a soporte interno.
- `openspec/config.yaml` dice explícitamente que el código, los comentarios, los tests y las specs van en inglés. Eso contradice la convención vigente del proyecto, que es español en toda la superficie técnica.

Ninguna de las dos bloquea este cambio, pero se van a notar en cualquier propuesta que toque texto visible.

## Zonas afectadas

| Archivo | Qué cambia |
| --- | --- |
| `app.py:123-130` | Ampliar el uploader a `["pdf", "csv", "xlsx"]` y decidir cómo se ingresa la URL de Google Sheets, que no es un archivo subido |
| `app.py:142-150` | `load_doc_text` debe despachar por formato, y quizá devolver `list[Document]` en vez de `str` para soportar Excel multi-hoja |
| `pdf_utils.py` | Queda intacto: hace una sola cosa y ya está probado |
| `doc_selector.py` | Sirve tal cual para elegir qué archivo u hoja es relevante; **no resuelve** la selección de filas dentro de una tabla grande |
| `requirements.txt` y `pyproject.toml` | Sumar las dependencias nuevas en **ambos** archivos |
| `tests/test_pdf_utils.py` | Plantilla directa para los tests de extracción tabular |
| `documentos/` | Los 6 PDF de cliente quedan intactos; el corpus interno va en una carpeta nueva |

## El problema central: convertir una tabla en texto que el modelo pueda responder

Enfoques evaluados contra el mismo techo de `MAX_CONTEXT_CHARS = 14000` que ya rige para documentos.

### 1. Volcar el CSV crudo entero

Sin transformación ni dependencias. No escala: una lista de precios de 500 filas son 15.000 a 30.000 caracteres y rompe el presupuesto ella sola. El modelo además tiene que separar columnas mentalmente, y se confunde si el separador real es `;`.

**Esfuerzo:** bajo. **Descartado por tamaño.**

### 2. Tabla markdown completa

Separación explícita de columnas, y los modelos interpretan markdown muy bien. Mismo problema de tamaño que la anterior, con más overhead por fila por los separadores.

**Esfuerzo:** bajo. **Descartado por tamaño.**

### 3. Solo resumen de esquema, sin datos

Columnas, cantidad de filas y tipos. Siempre entra en el presupuesto, pero no permite responder «¿cuánto sale el producto X?», que es justamente el caso de uso central. Sirve para «¿qué columnas tiene la planilla?» y poco más.

**Esfuerzo:** bajo. **Descartado por inútil para el caso real.**

### 4. Resumen de esquema más selección de filas relevantes

Matching léxico fila por fila contra los términos de la pregunta, formateando el subconjunto final como tabla markdown compacta.

Escala a cualquier tamaño de planilla y reutiliza el mismo patrón conceptual que ya usa `doc_selector.py`, extendido de grano de documento a grano de fila. Responde bien preguntas puntuales porque solo viajan las filas que mencionan el producto o tema consultado.

Quedan decisiones abiertas: qué texto de cada fila indexar para el matching, y qué hacer si ningún término matchea. Para ese último caso conviene extender la regla que ya existe en `select_relevant_docs`, donde si nada matchea se devuelven los primeros en orden original.

**Esfuerzo:** medio-alto. **Recomendada.**

### 5. Pre-agregación numérica con pandas

Calcular el promedio real antes de mandar al modelo. Requeriría detectar la intención de «pregunta agregada» con otro router, y no generaliza a preguntas libres.

**Fuera de esta ronda.** Posible trabajo futuro.

## Google Sheets sin API paga

**Archivo → Compartir → Publicar en la web** genera un link público accesible sin login ni credenciales, en formato CSV además de HTML. La URL para una hoja concreta tiene la forma `https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}`. Se actualiza cuando cambia la hoja, con un delay corto.

- **Costo cero.** No requiere proyecto de Google Cloud, API key ni OAuth. Coherente con la restricción de que todo sea gratuito.
- **Sin dependencias nuevas.** Se resuelve con `requests.get(url).text`, que ya está en `requirements.txt`, más el mismo parser de CSV que se use para archivos subidos.
- La alternativa de «compartir con cualquiera que tenga el link», sin publicar explícitamente, usa el mismo endpoint `/export`, pero no hay confirmación sólida de que el comportamiento ante un pedido anónimo sea idéntico bajo todas las políticas de Google Workspace. Publicar en la web es el camino documentado y estable.

**Riesgo de negocio, no solo técnico.** Publicar en la web vuelve la hoja accesible para cualquiera con el link, sin login. Para una demo es aceptable, pero es un riesgo real si una PyME publica sin darse cuenta una planilla con sueldos o costos. Merece una advertencia explícita en la interfaz, sobre todo en un producto que existe justamente para manejar información interna.

## Dependencias y peso

| Dependencia | Estado | Impacto |
| --- | --- | --- |
| `pandas` | Ya presente vía streamlit (`pandas<4,>=1.4.0`) | Ninguno nuevo, pero conviene declararlo explícito |
| `openpyxl` | **No instalado.** Necesario para `pandas.read_excel` con `.xlsx` | Python puro, sin binarios nativos, unos pocos MB |
| CSV | Ninguna dependencia nueva | — |
| Google Sheets | Ninguna dependencia nueva | — |

`pandas` conviene declararlo explícito aunque ya esté disponible: depender en silencio del pin de streamlit es frágil, porque si streamlit alguna vez lo vuelve opcional la app se rompe sin aviso.

**La única dependencia nueva real es `openpyxl`.** Bajo riesgo contra los límites del plan gratuito.

## Corpus interno de PyME ficticia

Los 6 PDF actuales son de cara al cliente y quedan fuera de alcance. Propuesta de corpus interno, pensada para forzar tanto el multi-formato como el problema real de filas.

| Documento | Formato | Por qué |
| --- | --- | --- |
| Manual de carga de facturas | PDF | Proceso paso a paso, el caso clásico de consulta interna |
| Lista de precios | Excel `.xlsx`, 50-100+ filas | Fuerza el problema de selección de filas |
| Política de licencias y vacaciones | PDF o CSV | Días por antigüedad, cómo pedirlas, feriados |
| Planilla de stock | CSV separado por `;`, con acentos | Reproduce la exportación real de Excel en configuración regional argentina |
| Directorio interno por área | Google Sheets publicada | Demuestra el caso de dato que vive fuera del repo y se actualiza solo |
| Onboarding de empleados nuevos | PDF | Opcional |

Preguntas que ese corpus debería poder responder:

- ¿Cómo cargo una factura de compra?
- ¿Cuánto sale el producto X? ¿Qué proveedor tiene el producto Y?
- ¿Cuántos días de licencia me quedan si entré en marzo de 2023?
- ¿Cuánto stock queda del producto Z en el depósito central?
- ¿A quién le pregunto sobre un problema con un proveedor?
- ¿Qué feriados tenemos este semestre?

Conviene no reusar el nombre «TiendaNova» para la empresa ficticia interna, para no mezclar el branding del corpus de cliente con el nuevo.

## Casos borde

- **Archivo vacío**, sin filas o de 0 bytes. El extractor debe devolver texto vacío y dejar que `combine_documents` lo descarte, igual que ya hace con PDF vacíos.
- **Excel con múltiples hojas.** Decidir si cada hoja es un `Document` separado, lo que da mejor cita de fuente y es coherente con la filosofía actual de documentos separados por tema. Las hojas ocultas o vacías deberían filtrarse.
- **Encoding de CSV en Argentina.** Separador `;` en vez de `,` por la configuración regional de Excel, y encoding `cp1252` o `latin-1` en vez de UTF-8, o UTF-8 con BOM si se guardó desde una versión moderna. Nada de esto está cubierto hoy. Hace falta detección con fallback y sniffing de separador, en vez de asumir `,` fijo.
- **Decimal con coma.** No rompe la extracción de texto, pero importaría para cualquier agregación numérica futura.
- **Archivos `.xls` viejos**, formato binario anterior a 2007. `openpyxl` no los lee. No es un caso raro en una PyME con plantillas viejas.
- **Cabeceras decorativas** antes de la tabla real: título de la empresa, fecha del reporte, fila en blanco. Común en planillas armadas a mano, y rompe la detección automática de encabezados de pandas.
- **Archivos grandes.** Streamlit permite hasta 200 MB por archivo por defecto, muy por encima de lo tolerable con pandas cargando una planilla grande en el plan gratuito. Hace falta un límite explícito.
- **Google Sheets mal configurada.** Si la hoja está compartida pero no publicada, el fetch anónimo puede devolver una página de login en HTML en vez de CSV. Hay que detectar ese caso para no tratarlo como datos válidos.

## Recomendación

**Arquitectura de extracción.** No tocar `pdf_utils.py`. Agregar un módulo de despacho que decida el formato por extensión o por `UploadedFile.type` y delegue en `pdf_utils.py`, sin cambios, y en módulos nuevos para CSV y Excel. Mantener `Document = tuple[str, str]` como contrato de salida estable, que ya consumen `doc_selector.py` y `combine_documents`.

**Decisión abierta para `sdd-design`:** si un extractor tabular debe devolver `list[Document]` para soportar Excel multi-hoja mientras `extract_text_from_pdf` sigue devolviendo `str`, o si conviene unificar todas las firmas.

**Tablas a texto.** Enfoque 4, resumen de esquema más selección de filas relevantes, formateando el subconjunto como tabla markdown compacta. Para archivos chicos que entran completos, extender la regla que ya existe en `select_relevant_docs` al nivel de fila, sin construir un selector nuevo para el caso simple.

**Google Sheets.** URL de publicación en formato CSV, sin dependencias nuevas, con advertencia explícita sobre la exposición pública.

**Dependencias.** Sumar `openpyxl` y declarar `pandas` explícito, en `requirements.txt` y en `pyproject.toml`.

**Corpus interno.** Carpeta nueva, separada de `documentos/`, con la mezcla de formatos descrita y una empresa ficticia distinta de TiendaNova.

## Riesgos

- Publicar una Google Sheets deja los datos accesibles sin login. En un producto que maneja información interna, la advertencia no es opcional.
- El límite de 200 MB por archivo de Streamlit supera con holgura lo que la RAM del plan gratuito tolera con pandas. Hace falta un guardrail de tamaño antes de implementar.
- La firma de retorno de los extractores queda sin resolver a propósito: es una decisión de diseño, no de exploración.
- `README.md` y `openspec/config.yaml` siguen desalineados con el pivot.

## Listo para propuesta

Sí. Hay evidencia suficiente sobre el acoplamiento actual a PDF, un enfoque verificado para tablas grandes, una vía gratuita confirmada para Google Sheets y un inventario acotado de dependencias nuevas. Las decisiones abiertas corresponden a las fases de propuesta y diseño, y no bloquean el arranque.
