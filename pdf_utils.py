"""Utilidades para extraer texto del PDF de documentacion del agente."""
from pypdf import PdfReader


def extract_text_from_pdf(path: str) -> str:
    """Extrae todo el texto de un PDF y lo devuelve como un solo string."""
    reader = PdfReader(path)
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


def combine_documents(docs: list) -> str:
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
