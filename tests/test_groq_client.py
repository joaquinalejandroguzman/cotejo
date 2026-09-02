import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from groq_client import (
    FALLBACK_MODEL,
    MODEL_ENV_VAR,
    GroqError,
    _strip_document_hedge,
    chat,
    resolve_model,
)


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
            raise AssertionError("deberia haber lanzado GroqError")
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
                raise AssertionError("deberia haber lanzado GroqError")
            except GroqError as e:
                assert "modelo-inexistente" in str(e)
                assert "ya no está disponible" in str(e)

    def test_el_modelo_por_defecto_no_es_ninguno_de_los_que_groq_apago(self):
        # Groq da de baja modelos con fecha fija. Cada vez que se apago uno
        # que teniamos configurado, la app quedo caida en produccion. La
        # lista crece: hay que dejar constancia de todos, no solo del ultimo.
        retirados = {
            "meta-llama/llama-4-scout-17b-16e-instruct",  # apagado 17/07/2026
            "llama-3.1-8b-instant",  # apagado 16/08/2026
            "llama-3.3-70b-versatile",  # fuera del plan gratuito 16/08/2026
        }
        assert resolve_model() not in retirados


class TestResolveModel:
    """El modelo tiene que poder cambiarse sin tocar el codigo.

    Bug real, dos veces: el modelo estaba escrito a mano en el codigo, Groq
    lo dio de baja y la unica forma de revivir la app fue editar el archivo,
    commitear y redeployar. Con una variable de entorno alcanza con cambiar
    un secret en el panel de Streamlit Cloud y reiniciar.
    """

    def test_sin_variable_de_entorno_usa_el_modelo_por_defecto(self, monkeypatch):
        monkeypatch.delenv(MODEL_ENV_VAR, raising=False)
        assert resolve_model() == FALLBACK_MODEL

    def test_la_variable_de_entorno_tiene_prioridad(self, monkeypatch):
        monkeypatch.setenv(MODEL_ENV_VAR, "openai/gpt-oss-20b")
        assert resolve_model() == "openai/gpt-oss-20b"

    def test_el_argumento_explicito_le_gana_a_la_variable_de_entorno(self, monkeypatch):
        monkeypatch.setenv(MODEL_ENV_VAR, "openai/gpt-oss-20b")
        assert resolve_model("qwen/qwen3.8-27b") == "qwen/qwen3.8-27b"

    def test_una_variable_vacia_no_pisa_el_modelo_por_defecto(self, monkeypatch):
        # Un secret cargado sin valor no deberia mandar un modelo vacio a la
        # API: es preferible caer al modelo por defecto, que sabemos que anda.
        monkeypatch.setenv(MODEL_ENV_VAR, "   ")
        assert resolve_model() == FALLBACK_MODEL

    def test_se_le_sacan_los_espacios_sobrantes(self, monkeypatch):
        monkeypatch.setenv(MODEL_ENV_VAR, "  openai/gpt-oss-20b  ")
        assert resolve_model() == "openai/gpt-oss-20b"

    def test_chat_sin_modelo_explicito_usa_el_resuelto(self, monkeypatch):
        monkeypatch.setenv(MODEL_ENV_VAR, "modelo-de-prueba")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_resp.raise_for_status.return_value = None
        with patch("groq_client.requests.post", return_value=mock_resp) as post:
            chat([{"role": "user", "content": "hola"}], api_key="fake-key")
        assert post.call_args.kwargs["json"]["model"] == "modelo-de-prueba"


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
                raise AssertionError("deberia haber lanzado GroqError")
            except GroqError as e:
                assert "formato inesperado" in str(e)
