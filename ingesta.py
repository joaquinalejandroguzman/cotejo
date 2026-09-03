"""Despacho por formato: decide como extraer texto de cada archivo.

Es la unica pieza que conoce los formatos soportados. `pdf_utils` y
`tabla_utils` no saben de la existencia del otro, y siguen haciendo cada uno
una sola cosa.

El puerto de salida es siempre `list[Document]`, aunque hoy todos los
formatos devuelvan un solo documento. La lista, y no el documento suelto, es
lo que permite que un formato con varias secciones —una planilla con varias
hojas, por ejemplo— entregue una por separado sin cambiarle la firma a nadie
ni obligar a los consumidores a estrechar tipos.
"""

import io
from pathlib import PurePosixPath

from pdf_utils import Document, extract_text_from_pdf
from tabla_utils import leer_csv, renderizar

# Extensiones que la app sabe leer, en el orden en que se le muestran a quien
# sube el archivo.
FORMATOS_SOPORTADOS = ("pdf", "csv")


class IngestaError(Exception):
    """No se pudo leer un archivo. El mensaje esta escrito para el usuario."""


def _extension(nombre: str) -> str:
    return PurePosixPath(nombre).suffix.lstrip(".").lower()


def extraer_documentos(nombre: str, origen: bytes) -> list[Document]:
    """Extrae el contenido de un archivo y lo devuelve como documentos.

    `nombre` es el nombre visible del archivo: da la extension que decide el
    formato, y es el titulo con el que el agente va a citar la fuente.
    """
    extension = _extension(nombre)

    if extension == "pdf":
        return [(nombre, extract_text_from_pdf(io.BytesIO(origen)))]

    if extension == "csv":
        tabla = leer_csv(origen, nombre)
        return [(nombre, renderizar(tabla, tabla.filas))]

    formatos = ", ".join(f".{f}" for f in FORMATOS_SOPORTADOS)
    raise IngestaError(f"No puedo leer «{nombre}». Por ahora manejo estos formatos: {formatos}.")
