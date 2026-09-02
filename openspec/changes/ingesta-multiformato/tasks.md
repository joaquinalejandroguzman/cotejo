# Tasks: Ingesta multi-formato

Fase `sdd-tasks`. Cubre `proposal.md`, `specs/ingesta/spec.md` y `design.md`.
TDD estricto: toda tarea de implementación va precedida por su tarea RED.
Compuerta de cada fase: `make lint format-check typecheck test` (+ `test-e2e`
donde se indica). CI corre en Python 3.12, 3.13 y 3.14.

## Review Workload Forecast

| Field | Value |
| --- | --- |
| Estimated changed lines | ~900–1300 (PR1 ~300, PR2 ~280, PR3 ~320, PR4 ~250, PR5 ~200) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 |
| Delivery strategy | ask-on-risk |
| Chain strategy | secuencial contra main (confirmado por el usuario el 2026-09-02) |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: secuencial contra main
400-line budget risk: High
```

`Decision needed before apply: No` porque la elección de cadena (cadena de PRs
encadenados) ya se resolvió con el usuario antes de esta fase. Base sugerida:
`sdd/ingesta-multiformato` es la rama tracker; PR1 la target, PR2 targetea la
rama de PR1, PR3 la de PR2, y así — solo el tracker mergea a `main`.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
| --- | --- | --- | --- | --- | --- |
| 1 | CSV punta a punta | PR1 | `pytest tests/test_ingesta.py tests/test_tabla_utils.py tests/test_dependencias.py` | `make run` + subir CSV es-AR de `tests/fixtures/` | Revertir `ingesta.py`, `tabla_utils.py`, deps y `app.py:123-190` — vuelve a solo-PDF |
| 2 | Excel `.xlsx`/`.xls` | PR2 | `pytest tests/test_tabla_utils.py -k excel` | `make run` + subir `.xlsx` de 3 hojas (una oculta, una vacía) | Revertir `leer_excel` y el `type=[...]` del uploader — CSV sigue andando |
| 3 | Selección de filas + límite 5MB | PR3 | `pytest tests/test_fila_selector.py tests/test_ingesta.py -k limite` | `make run` + planilla de 100+ filas, pregunta puntual | Revertir `fila_selector.py` y `app.py:362` — tablas vuelven a ir completas |
| 4 | Google Sheets por URL | PR4 | `pytest tests/test_sheets_client.py` + `make test-e2e -k advertencia` | `make run` + pegar URL de Sheets publicada real | Revertir `sheets_client.py` y el input de URL en `app.py` |
| 5 | Corpus Pampa Sur + README | PR5 | `make test test-e2e` | `make run` + corpus completo de Pampa Sur | Revertir `documentos-internos/` y traducciones — no toca código de producción |

## Fase 1 (PR 1): CSV punta a punta

- [ ] 1.1 Verificar si `tests/test_dependencias.py` ya existe (podría venir mergeado de `test/sincronia-de-dependencias`, PR #6). A la fecha no existe en esta rama.
- [ ] 1.2 RED: crear/extender `tests/test_dependencias.py` — paridad `requirements.txt` ↔ `pyproject.toml`, misma versión para `pandas`/`openpyxl`/`xlrd`. Falla: aún no declaradas.
- [ ] 1.3 GREEN: declarar `pandas`, `openpyxl`, `xlrd` en `pyproject.toml:18` (dependencies) **y** `requirements.txt`, misma restricción de versión en ambos.
- [ ] 1.4 Extender override de mypy en `pyproject.toml:98-100` con `pandas.*`, `openpyxl.*`, `xlrd.*`, `ignore_missing_imports = true` (pandas no trae `py.typed`).
- [ ] 1.5 RED: crear fixtures en `tests/fixtures/` (CSV es-AR `;`+`cp1252` acentuado, CSV vacío, CSV solo-encabezado) + `tests/test_tabla_utils.py`: encoding, separador, encabezado real (cabecera decorativa), CSV vacío/solo-encabezado sin excepción, decimal con coma, escape de `\|`, round-trip `renderizar`↔`parsear`. Falla: módulo no existe.
- [ ] 1.6 GREEN: crear `tabla_utils.py` — `Tabla` (dataclass frozen), `leer_csv`, `renderizar`, `parsear`, `_celda(valor: object) -> str` como única salida de pandas (D2).
- [ ] 1.7 RED: crear `tests/test_ingesta.py` — despacho `.csv`/`.pdf`, extensión desconocida → `IngestaError`, PDF delegado a `extract_text_from_pdf` sin cambios (mock/doble). Falla: módulo no existe.
- [ ] 1.8 GREEN: crear `ingesta.py` — `extraer_documentos(nombre, origen) -> list[Document]`, `IngestaError`, adaptador PDF de D1 (`[(nombre, texto)]`).
- [ ] 1.9 Registrar `ingesta.py` y `tabla_utils.py` en `Makefile:12` (SRC), `pyproject.toml:41` (py-modules) y `pyproject.toml:81` (known-first-party).
- [ ] 1.10 Modificar `app.py:123-130` (`type=["pdf","csv"]`) y `app.py:142-150`/`184-190` (`cargar(nombre, origen)` reemplaza `load_doc_text`; `docs.extend(...)`; `except IngestaError` → `st.sidebar.error`).
- [ ] 1.11 Corregir `openspec/config.yaml:8` — contrato de idioma a español.
- [ ] 1.12 `make lint format-check typecheck test` en verde.

## Fase 2 (PR 2): Excel `.xlsx` y `.xls`, hoja = documento

- [ ] 2.1 Crear fixtures: `.xlsx` de 3 hojas (una oculta, una vacía) y `.xls` legado chico en `tests/fixtures/`.
- [ ] 2.2 RED: `tests/test_tabla_utils.py` — hoja visible→`Document`, hoja oculta descartada, hoja vacía descartada, nombre `f"{archivo} — {hoja}"`. Falla: `leer_excel` no existe.
- [ ] 2.3 RED explícito (trampa `seek(0)`): test que falla si falta `origen.seek(0)` entre la pasada de visibilidad de hojas y la pasada de datos — sin el seek, el resultado es `list[Tabla]` vacío sin ningún error.
- [ ] 2.4 GREEN: extender `tabla_utils.py` con `leer_excel(datos: bytes, nombre: str, legado: bool) -> list[Tabla]` (D5: `openpyxl` `sheet_state=="visible"` / `xlrd` `visibility==0`, con `origen.seek(0)` entre pasadas).
- [ ] 2.5 GREEN: `ingesta.py` despacha `.xlsx`/`.xls` → `leer_excel` → `[Tabla] → renderizar → [(nombre, texto)]`.
- [ ] 2.6 Modificar `app.py:123-130` — `type=["pdf","csv","xlsx","xls"]`.
- [ ] 2.7 `make lint format-check typecheck test` en verde.

## Fase 3 (PR 3): Selección de filas y límite de tamaño

- [ ] 3.1 RED: crear `tests/test_fila_selector.py` — filas que matchean, **cero filas ante cero coincidencias** (D4, sin fallback de "primeras N filas"), presupuesto `max_chars` respetado, `Document` no-tabla (PDF) intacto, test de propiedad (toda fila renderizada contiene ≥1 token de la pregunta). Falla: módulo no existe.
- [ ] 3.2 GREEN: crear `fila_selector.py` — `reducir_tablas(pregunta, docs, max_chars=MAX_CONTEXT_CHARS)`, `seleccionar_filas(pregunta, tabla, max_chars)`; importa `_tokens` y `MAX_CONTEXT_CHARS` de `doc_selector.py` (precedente: `tests/test_doc_selector.py:8-9`).
- [ ] 3.3 RED: test de integración `reducir_tablas` → `select_relevant_docs` — ninguna fila queda cortada a la mitad; falla si se invierte el orden o si `select_relevant_docs` recorta con slice duro antes de reducir.
- [ ] 3.4 GREEN: en `app.py:362`, `docs = reducir_tablas(question, docs)` **antes** de `select_relevant_docs(question, docs)` — el orden es load-bearing.
- [ ] 3.5 RED: `tests/test_ingesta.py` — archivo `.xlsx`/`.csv` >5MB (bytes generados en runtime, no fixture) rechazado con `IngestaError` antes de tocar pandas.
- [ ] 3.6 GREEN: en `ingesta.py`, validar `LIMITE_BYTES = 5 * 1024 * 1024` antes de cualquier llamada a pandas.
- [ ] 3.7 Registrar `fila_selector.py` en `Makefile:12`, `pyproject.toml:41`, `pyproject.toml:81`.
- [ ] 3.8 `make lint format-check typecheck test` en verde.

## Fase 4 (PR 4): Google Sheets por URL y advertencia

- [ ] 4.1 RED: crear `tests/test_sheets_client.py` — reconstrucción canónica de URL (`{ID}`+`{GID}` → `.../export?format=csv&gid=`), host fuera de allowlist rechazado, esquema `file://` rechazado, respuesta HTML → `SheetsError` (`requests.get` stubbeado, patrón de `tests/test_groq_client.py`). Falla: módulo no existe.
- [ ] 4.2 GREEN: crear `sheets_client.py` — `descargar_csv(url, timeout=20) -> bytes`, `SheetsError(IngestaError)`, sin redirecciones cross-host, tope de bytes.
- [ ] 4.3 RED: `tests/e2e/test_smoke.py` — advertencia de exposición visible al abrir la sección, sin URL pegada todavía.
- [ ] 4.4 GREEN: `app.py` — input de URL con advertencia visible **antes** del campo; despacho a `sheets_client.descargar_csv` → `tabla_utils.leer_csv`.
- [ ] 4.5 Registrar `sheets_client.py` en `Makefile:12`, `pyproject.toml:41`, `pyproject.toml:81`.
- [ ] 4.6 `make lint format-check typecheck test test-e2e` en verde.

## Fase 5 (PR 5): Corpus Distribuidora Pampa Sur y README

- [ ] 5.1 Crear `documentos-internos/` con corpus ficticio de Distribuidora Pampa Sur (CSV, Excel, Sheets) que ejercite los PR 1–4 con datos reales.
- [ ] 5.2 Actualizar `README.md` con los formatos nuevos y el corpus de ejemplo.
- [ ] 5.3 Traducir a español: `Makefile`, `tests/e2e/test_smoke.py`, comentarios de `pyproject.toml`.
- [ ] 5.4 `make lint format-check typecheck test test-e2e` en verde (Python 3.12/3.13/3.14).
