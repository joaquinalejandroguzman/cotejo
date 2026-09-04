"""Pruebas del despacho por formato.

Este modulo decide que extractor usar segun el archivo, y normaliza todo a
`Document`. Es la unica pieza que conoce los formatos soportados: ni
`pdf_utils` ni `tabla_utils` saben de la existencia del otro.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingesta import FORMATOS_SOPORTADOS, IngestaError, extraer_documentos

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PDF = Path(__file__).resolve().parent.parent / "corpus" / "pampa-surena" / "politica_licencias.pdf"


class TestDespachoDeCsv:
    def test_devuelve_un_documento(self):
        datos = (FIXTURES / "precios_es_ar.csv").read_bytes()
        docs = extraer_documentos("precios_es_ar.csv", datos)
        assert len(docs) == 1

    def test_el_documento_lleva_el_nombre_del_archivo(self):
        datos = (FIXTURES / "precios_es_ar.csv").read_bytes()
        nombre, _ = extraer_documentos("precios_es_ar.csv", datos)[0]
        assert nombre == "precios_es_ar.csv"

    def test_el_texto_es_la_tabla_renderizada(self):
        datos = (FIXTURES / "precios_es_ar.csv").read_bytes()
        _, texto = extraer_documentos("precios_es_ar.csv", datos)[0]
        assert texto.startswith("Tabla: precios_es_ar.csv")
        assert "| 4018 | Yerba Playadito 1kg | Mate SA | 4350,50 |" in texto


class TestDespachoDePdf:
    def test_devuelve_un_documento_con_el_texto_extraido(self):
        docs = extraer_documentos("politica_licencias.pdf", PDF.read_bytes())
        assert len(docs) == 1
        nombre, texto = docs[0]
        assert nombre == "politica_licencias.pdf"
        assert "PAMPA SUREÑA" in texto

    def test_delega_en_pdf_utils_sin_modificarlo(self):
        # pdf_utils ya esta probado y en produccion: el despacho lo envuelve,
        # no lo reimplementa ni le cambia la firma.
        with patch("ingesta.extract_text_from_pdf", return_value="texto falso") as extraer:
            docs = extraer_documentos("cualquiera.pdf", b"%PDF-fake")
        assert extraer.called
        assert docs == [("cualquiera.pdf", "texto falso")]


class TestFormatoNoSoportado:
    def test_una_extension_desconocida_lanza_ingesta_error(self):
        with pytest.raises(IngestaError):
            extraer_documentos("presentacion.pptx", b"loquesea")

    def test_el_error_nombra_el_archivo_y_los_formatos_validos(self):
        # Quien lo lee es el empleado que acaba de subir el archivo: tiene
        # que saber que subir en su lugar, no que fallo por dentro.
        with pytest.raises(IngestaError) as excinfo:
            extraer_documentos("presentacion.pptx", b"loquesea")
        mensaje = str(excinfo.value)
        assert "presentacion.pptx" in mensaje
        for formato in FORMATOS_SOPORTADOS:
            assert formato in mensaje

    def test_un_archivo_sin_extension_lanza_ingesta_error(self):
        with pytest.raises(IngestaError):
            extraer_documentos("sin_extension", b"loquesea")


class TestExtensionesEnMayusculas:
    """Windows entrega .CSV y .PDF en mayusculas mas seguido de lo que parece."""

    def test_csv_en_mayusculas(self):
        datos = (FIXTURES / "precios_es_ar.csv").read_bytes()
        docs = extraer_documentos("PRECIOS.CSV", datos)
        assert len(docs) == 1

    def test_pdf_en_mayusculas(self):
        with patch("ingesta.extract_text_from_pdf", return_value="texto"):
            docs = extraer_documentos("DOC.PDF", b"%PDF-fake")
        assert len(docs) == 1


class TestArchivosVacios:
    def test_un_csv_vacio_no_lanza_excepcion(self):
        # Un archivo vacio no es un error de formato: es un documento sin
        # contenido, y combine_documents ya sabe descartarlo.
        docs = extraer_documentos("vacio.csv", b"")
        assert len(docs) == 1
