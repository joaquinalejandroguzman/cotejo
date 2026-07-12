import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf_utils import extract_text_from_pdf, truncate_for_context, combine_documents

PDF_PATH = Path(__file__).resolve().parent.parent / "documentacion_agente.pdf"


class TestExtractTextFromPdf:
    def test_extrae_texto_no_vacio(self):
        texto = extract_text_from_pdf(str(PDF_PATH))
        assert len(texto) > 0

    def test_contiene_secciones_esperadas(self):
        texto = extract_text_from_pdf(str(PDF_PATH))
        assert "TiendaNova" in texto
        assert "Privacidad" in texto
        assert "Devoluciones" in texto or "devoluciones" in texto.lower()


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
