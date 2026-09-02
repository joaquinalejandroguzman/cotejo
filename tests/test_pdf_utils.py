import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf_utils import combine_documents, extract_text_from_pdf, truncate_for_context

PDF_PATH = Path(__file__).resolve().parent.parent / "documentos" / "politica_devoluciones.pdf"


class TestExtractTextFromPdf:
    def test_extrae_texto_no_vacio(self):
        texto = extract_text_from_pdf(str(PDF_PATH))
        assert len(texto) > 0

    def test_contiene_secciones_esperadas(self):
        texto = extract_text_from_pdf(str(PDF_PATH))
        assert "TiendaNova" in texto
        assert "Devoluciones" in texto or "devoluciones" in texto.lower()
        assert "Reembolso" in texto or "reembolso" in texto.lower()

    def test_acepta_un_path(self):
        """Callers pass a Path, not only a string."""
        assert extract_text_from_pdf(PDF_PATH) == extract_text_from_pdf(str(PDF_PATH))

    def test_acepta_un_stream_de_bytes(self):
        """Uploaded files arrive as bytes and are read through BytesIO.

        The app wraps uploaded content in BytesIO rather than writing it to
        disk, so a byte stream is a supported input and must extract exactly
        the same text as reading the same document from a path.
        """
        stream = io.BytesIO(PDF_PATH.read_bytes())
        assert extract_text_from_pdf(stream) == extract_text_from_pdf(str(PDF_PATH))


class TestTruncateForContext:
    def test_texto_corto_no_se_modifica(self):
        texto = "hola mundo"
        assert truncate_for_context(texto, max_chars=100) == texto

    def test_texto_largo_se_trunca(self):
        texto = "a" * 500
        resultado = truncate_for_context(texto, max_chars=100)
        assert len(resultado) < len(texto)
        assert resultado.startswith("a" * 100)

    def test_texto_largo_incluye_marca_de_truncado(self):
        texto = "a" * 500
        resultado = truncate_for_context(texto, max_chars=100)
        assert "truncado" in resultado

    def test_limite_exacto_no_se_trunca(self):
        texto = "a" * 100
        assert truncate_for_context(texto, max_chars=100) == texto


class TestCombineDocuments:
    def test_combina_dos_documentos_con_encabezados(self):
        docs = [("doc1.pdf", "contenido uno"), ("doc2.pdf", "contenido dos")]
        resultado = combine_documents(docs)
        assert "### Documento: doc1.pdf" in resultado
        assert "contenido uno" in resultado
        assert "### Documento: doc2.pdf" in resultado
        assert "contenido dos" in resultado

    def test_documento_vacio_se_omite(self):
        docs = [("doc1.pdf", "contenido"), ("doc2.pdf", "")]
        resultado = combine_documents(docs)
        assert "doc1.pdf" in resultado
        assert "doc2.pdf" not in resultado

    def test_lista_vacia_devuelve_string_vacio(self):
        assert combine_documents([]) == ""
