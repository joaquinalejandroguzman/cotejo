import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ollama_client import _strip_document_hedge


class TestStripDocumentHedge:
    def test_segun_el_documento(self):
        resultado = _strip_document_hedge(
            "Según el documento, un reembolso puede tomar entre 5 y 10 días hábiles."
        )
        assert resultado == "Un reembolso puede tomar entre 5 y 10 días hábiles."

    def test_de_acuerdo_al_documento(self):
        # Bug real: "al" es la contraccion de "a el" y no matcheaba antes.
        resultado = _strip_document_hedge("De acuerdo al documento, hacemos envíos a Argentina.")
        assert resultado == "Hacemos envíos a Argentina."

    def test_de_acuerdo_con_el_documento(self):
        resultado = _strip_document_hedge("De acuerdo con el documento, la garantía es de fábrica.")
        assert resultado == "La garantía es de fábrica."

    def test_segun_la_documentacion(self):
        resultado = _strip_document_hedge("Según la documentación, hacemos envíos a Argentina.")
        assert resultado == "Hacemos envíos a Argentina."

    def test_basandome_en_el_documento(self):
        resultado = _strip_document_hedge("Basándome en el documento, sí hacemos envíos.")
        assert resultado == "Sí hacemos envíos."

    def test_en_base_al_documento(self):
        resultado = _strip_document_hedge("En base al documento, el plazo es de 30 días.")
        assert resultado == "El plazo es de 30 días."

    def test_respuesta_sin_muletilla_no_se_modifica(self):
        resultado = _strip_document_hedge("Sí, hacemos envíos a Argentina.")
        assert resultado == "Sí, hacemos envíos a Argentina."
