# Especificación: Ingesta multi-formato (`ingesta`)

## Propósito

Cotejo hoy solo lee PDF. Esta especificación cubre la ingesta de datos tabulares (CSV, Excel `.xlsx`/`.xls`) y de una Google Sheets publicada, más la selección de filas relevantes para no exceder el presupuesto de contexto. No modifica `pdf_utils.py` ni el contrato `Document = tuple[str, str]` que ya consumen `doc_selector.py` y `combine_documents`. Es una especificación nueva: no existe `openspec/specs/ingesta/` previo.

## Mapeo a la cadena de entrega (5 PR)

| PR | Capacidad cubierta |
| --- | --- |
| 1 | `ingesta-tabular` — CSV |
| 2 | `ingesta-tabular` — Excel `.xlsx` y `.xls` |
| 3 | `seleccion-de-filas` |
| 4 | `ingesta-sheets` |
| 5 | Corpus de Distribuidora Pampa Sur y README — valida los requisitos previos con datos reales, no agrega comportamiento nuevo |

## Capability: ingesta-tabular

### Requirement: Despacho por formato sin modificar `pdf_utils.py`

El sistema MUST despachar la extracción de texto según la extensión o el tipo del archivo subido, delegando en `pdf_utils.py` sin cambios para PDF y en extractores tabulares nuevos para CSV y Excel. El sistema MUST devolver `Document` (o una lista de `Document`) respetando el contrato `tuple[str, str]` existente.

#### Scenario: Un CSV subido se convierte en Document
- GIVEN un archivo `.csv` válido subido por el usuario
- WHEN se despacha la extracción
- THEN el sistema produce un `Document` con nombre legible y texto extraído, sin invocar `pdf_utils.py`

#### Scenario: Un PDF subido sigue funcionando sin cambios
- GIVEN un archivo `.pdf` válido
- WHEN se despacha la extracción
- THEN el sistema delega en `extract_text_from_pdf` sin alterar su comportamiento actual

### Requirement: Declaración explícita de dependencias tabulares

El sistema MUST declarar `pandas`, `openpyxl` y `xlrd` como dependencias propias en `requirements.txt` y en `pyproject.toml`, con versiones consistentes entre ambos archivos.

#### Scenario: Paridad de dependencias
- GIVEN `requirements.txt` y `pyproject.toml` tras el cambio
- WHEN se ejecuta el test de paridad de dependencias
- THEN ambos archivos declaran las mismas dependencias tabulares con la misma restricción de versión

### Requirement: Detección de separador y encoding en CSV

El sistema MUST detectar el separador (`,` o `;`) y el encoding (UTF‑8, UTF‑8 con BOM, `cp1252`/`latin-1`) de un CSV en vez de asumir `,` y UTF‑8 por defecto. El sistema MUST intentar UTF‑8 primero y aplicar fallback a `cp1252`/`latin-1` si falla la decodificación.

#### Scenario: CSV argentino con `;` y `cp1252`
- GIVEN un `.csv` exportado por Excel en configuración regional argentina, separado por `;` y codificado en `cp1252`, con texto acentuado
- WHEN se extrae su contenido
- THEN el texto resultante conserva los acentos sin caracteres corruptos y las columnas quedan separadas correctamente

#### Scenario: CSV vacío o solo con encabezado
- GIVEN un `.csv` de 0 bytes o que solo contiene la fila de encabezado
- WHEN se extrae su contenido
- THEN el sistema devuelve un `Document` con texto vacío o solo el esquema, sin lanzar una excepción

### Requirement: Detección de la fila de encabezado real

El sistema MUST descartar filas decorativas anteriores al encabezado real de una tabla (título de empresa, fecha del reporte, filas en blanco) y usar como encabezado la primera fila con nombres de columna consistentes.

#### Scenario: Cabecera decorativa antes de la tabla
- GIVEN una planilla con el nombre de la empresa y la fecha en las primeras dos filas, y la tabla real a partir de la fila 4
- WHEN se extrae su contenido
- THEN el `Document` resultante usa la fila 4 como encabezado y descarta las filas decorativas

### Requirement: Cada hoja de Excel es un documento separado

El sistema MUST tratar cada hoja de un archivo `.xlsx` o `.xls` como un `Document` independiente, citable por separado. El sistema MUST excluir hojas ocultas y hojas sin filas de datos.

#### Scenario: Excel con varias hojas de datos
- GIVEN un `.xlsx` con tres hojas visibles con datos
- WHEN se extrae su contenido
- THEN el sistema produce tres `Document` distintos, uno por hoja, cada uno con el nombre de la hoja como parte de su nombre legible

#### Scenario: Hojas ocultas o vacías se descartan
- GIVEN un `.xlsx` con una hoja oculta y una hoja visible sin filas de datos
- WHEN se extrae su contenido
- THEN ninguna de las dos genera un `Document`

### Requirement: Soporte de Excel legado `.xls`

El sistema MUST leer archivos `.xls` (formato binario anterior a 2007) sin requerir que el usuario los reexporte a `.xlsx`.

#### Scenario: Archivo `.xls` viejo
- GIVEN un archivo `.xls` generado por una versión de Excel anterior a 2007
- WHEN se extrae su contenido
- THEN el sistema produce el o los `Document` correspondientes sin error ni pedido de reexportación

### Requirement: Preservación de decimales con coma

El sistema MUST preservar el formato numérico tal como aparece en el archivo original (por ejemplo, `1234,50` con coma decimal) sin convertirlo ni corromperlo, dado que la agregación numérica queda fuera de alcance de este cambio.

#### Scenario: Precio con coma decimal
- GIVEN una celda con el valor `1234,50` en una columna de precio
- WHEN se extrae la fila como texto
- THEN el texto final conserva `1234,50` sin alterar el separador decimal ni interpretarlo como separador de miles

## Capability: seleccion-de-filas

### Requirement: Reducción de tablas grandes al presupuesto de contexto

Cuando una tabla extraída no entra completa en `MAX_CONTEXT_CHARS`, el sistema MUST reducirla a un esquema (nombres de columna, cantidad de filas) más las filas cuyo texto coincide léxicamente con los términos de la pregunta, formateadas como tabla compacta.

#### Scenario: Pregunta puntual sobre una tabla grande
- GIVEN una lista de precios de más de 100 filas y la pregunta «¿cuánto sale el producto X?»
- WHEN se seleccionan las filas relevantes
- THEN el texto final incluye el esquema de la tabla y solo las filas que mencionan el producto X, dentro del presupuesto de `MAX_CONTEXT_CHARS`

### Requirement: Ninguna fila coincide con la pregunta

Cuando ninguna fila de una tabla coincide léxicamente con los términos de la pregunta, el sistema MUST devolver únicamente el esquema de la tabla, sin ninguna fila de datos. El sistema MUST NOT aplicar la regla de `select_relevant_docs` de devolver las primeras filas en orden original ante la ausencia de coincidencias: mandar filas con forma de respuesta (SKU, producto, precio) empuja al modelo a contestar con el precio de otro artículo.

#### Scenario: Artículo inexistente en la planilla
- GIVEN una lista de precios y la pregunta «¿cuánto sale el artículo 4021?», donde el artículo 4021 no existe en la planilla
- WHEN se seleccionan las filas relevantes
- THEN el texto final incluye el esquema de la tabla (columnas, cantidad de filas) y cero filas de datos
- AND el modelo dispone de información suficiente para responder que no encuentra el artículo, sin datos de otro artículo con forma de respuesta válida

### Requirement: Límite de tamaño de archivo

El sistema MUST rechazar, antes de cargarlo en memoria con pandas, cualquier archivo tabular que supere los 5 MB, con un mensaje de error claro para el usuario.

#### Scenario: Archivo que supera el límite
- GIVEN un archivo `.xlsx` o `.csv` de más de 5 MB
- WHEN el usuario intenta subirlo
- THEN el sistema rechaza el archivo antes de procesarlo y muestra un mensaje indicando el límite de 5 MB

## Capability: ingesta-sheets

### Requirement: Ingesta de Google Sheets publicada por URL

El sistema MUST aceptar una URL de una Google Sheets publicada en la web (formato `.../export?format=csv&gid=...`) y convertir su contenido en uno o más `Document`, sin requerir credenciales.

#### Scenario: Sheets publicada válida
- GIVEN la URL de una Google Sheets publicada correctamente
- WHEN el usuario la ingresa y confirma
- THEN el sistema descarga el CSV y produce un `Document` con su contenido

### Requirement: Advertencia de exposición visible

El sistema MUST mostrar una advertencia visible, antes del campo donde se pega la URL, indicando que publicar una hoja la vuelve accesible a cualquiera con el link, sin login, y que no conviene publicar sueldos, costos ni datos personales.

#### Scenario: La advertencia aparece antes de cualquier intento de carga
- GIVEN la pantalla de ingesta de Google Sheets
- WHEN el usuario abre esa sección de la interfaz, incluso sin haber pegado ninguna URL todavía
- THEN la advertencia sobre exposición pública ya es visible

### Requirement: Detección de hoja no publicada

El sistema MUST validar que la respuesta de la URL ingresada sea contenido CSV y no una página HTML de login. Si la respuesta es HTML, el sistema MUST mostrar un error claro y MUST NOT tratar ese contenido como datos válidos.

#### Scenario: Hoja compartida pero no publicada
- GIVEN una URL de una hoja que está compartida pero no publicada en la web
- WHEN el usuario la ingresa
- THEN el fetch devuelve HTML en vez de CSV, el sistema lo detecta y muestra un error claro en vez de generar un `Document` con datos falsos
