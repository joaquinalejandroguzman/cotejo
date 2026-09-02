"""Utilidades para extraer texto del PDF de documentacion del agente."""

from pathlib import Path
from typing import IO

from pypdf import PdfReader

# Una fuente de PDF: una ruta en disco o un stream de bytes ya en memoria.
# Los archivos que sube el usuario llegan como bytes y se leen sin tocar el
# disco, asi que ambas formas son entradas legitimas.
type PdfSource = str | Path | IO[bytes]

# Un documento ya extraido: (nombre legible, texto completo). Es la unidad
# que circula entre la extraccion, la seleccion de contexto y el prompt.
type Document = tuple[str, str]


def extract_text_from_pdf(source: PdfSource) -> str:
    """Extrae todo el texto de un PDF y lo devuelve como un solo string."""
    reader = PdfReader(source)
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    return "\n".join(parts).strip()


def truncate_for_context(text: str, max_chars: int) -> str:
    """Recorta el texto si excede un tamano razonable para el contexto del modelo."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...documento truncado...]"


def combine_documents(docs: list[Document]) -> str:
    """Combina varios documentos (nombre, texto) en un solo bloque de contexto,
    separando cada uno con un encabezado para que el modelo distinga la fuente.

    docs: lista de tuplas (nombre_legible, texto_extraido)
    """
    partes = []
    for nombre, texto in docs:
        if not texto:
            continue
        partes.append(f"### Documento: {nombre}\n{texto}")
    return "\n\n".join(partes)
