import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from groq_client import _strip_document_hedge, chat, GroqError, DEFAULT_MODEL


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


class TestChatSinApiKey:
    def test_chat_sin_api_key_lanza_error_claro(self):
        # Bug potencial: sin GROQ_API_KEY configurada, la app no deberia
        # tirar un traceback feo sino un mensaje claro para el usuario.
        try:
            chat([{"role": "user", "content": "hola"}], api_key=None)
            assert False, "deberia haber lanzado GroqError"
        except GroqError as e:
            assert "API key" in str(e)


class TestChatModeloDadoDeBaja:
    def test_404_explica_que_el_modelo_ya_no_existe(self):
        # Bug real (17/07/2026): Groq apago
        # meta-llama/llama-4-scout-17b-16e-instruct y la app quedo mostrando
        # "Groq respondió con error: 404 Client Error: Not Found", que no
        # decia que el problema era el modelo dado de baja.
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        with patch("groq_client.requests.post", return_value=mock_resp):
            try:
                chat(
                    [{"role": "user", "content": "hola"}],
                    model="modelo-inexistente",
                    api_key="fake-key",
                )
                assert False, "deberia haber lanzado GroqError"
            except GroqError as e:
                assert "modelo-inexistente" in str(e)
                assert "ya no está disponible" in str(e)

    def test_el_modelo_por_defecto_no_es_el_que_groq_apago(self):
        assert DEFAULT_MODEL != "meta-llama/llama-4-scout-17b-16e-instruct"


class TestChatRespuestaMalformada:
    def test_respuesta_sin_choices_lanza_groqerror(self):
        # Bug potencial: si Groq devuelve 200 pero sin "choices" (respuesta
        # filtrada, formato inesperado), antes tiraba un KeyError crudo
        # en vez de un GroqError prolijo como el resto de la funcion.
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": []}
        mock_resp.raise_for_status.return_value = None
        with patch("groq_client.requests.post", return_value=mock_resp):
            try:
                chat([{"role": "user", "content": "hola"}], api_key="fake-key")
                assert False, "deberia haber lanzado GroqError"
            except GroqError as e:
                assert "formato inesperado" in str(e)
