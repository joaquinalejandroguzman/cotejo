"""Pruebas del diagnostico que corre el monitor diario.

La parte que hace red no se prueba aca: se prueba la logica que decide si un
modelo esta sano, alimentandola con catalogos armados a mano que reproducen
los casos reales que ya rompieron esta app.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verificar_disponibilidad import diagnosticar

VIGENTE = {
    "id": "openai/gpt-oss-120b",
    "active": True,
    "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
}
OTRO = {
    "id": "openai/gpt-oss-20b",
    "active": True,
    "pricing": {"prompt": "0.0000001", "completion": "0.0000005"},
}


class TestModeloSano:
    def test_un_modelo_vigente_no_reporta_problemas(self):
        assert diagnosticar("openai/gpt-oss-120b", [VIGENTE, OTRO]) == []


class TestModeloQueDesaparecio:
    """El caso de julio de 2026: Groq apago el modelo y la app quedo caida."""

    def test_reporta_que_el_modelo_ya_no_esta(self):
        problemas = diagnosticar("meta-llama/llama-4-scout-17b-16e-instruct", [VIGENTE])
        assert len(problemas) == 1
        assert "ya no figura" in problemas[0]

    def test_sugiere_los_modelos_que_si_estan(self):
        # Sin alternativas concretas, el aviso obliga a ir a buscarlas.
        problemas = diagnosticar("modelo-fantasma", [VIGENTE, OTRO])
        assert "openai/gpt-oss-120b" in problemas[0]
        assert "openai/gpt-oss-20b" in problemas[0]

    def test_no_sugiere_modelos_de_audio(self):
        # Whisper transcribe audio: sugerirlo como reemplazo de un modelo de
        # texto seria mandar a quien lee el aviso a romper la app de nuevo.
        whisper = {"id": "whisper-large-v3", "active": True, "pricing": {}}
        problemas = diagnosticar("modelo-fantasma", [VIGENTE, whisper])
        assert "whisper" not in problemas[0]

    def test_un_catalogo_vacio_tambien_es_un_problema(self):
        assert diagnosticar("openai/gpt-oss-120b", []) != []


class TestModeloEnCaminoDeSerApagado:
    """El aviso temprano: todavia figura, pero Groq ya lo marco."""

    def test_un_modelo_inactivo_se_reporta_aunque_siga_listado(self):
        apagandose = {**VIGENTE, "active": False}
        problemas = diagnosticar("openai/gpt-oss-120b", [apagandose])
        assert len(problemas) == 1
        assert "inactivo" in problemas[0]

    def test_el_aviso_dice_que_conviene_migrar_antes(self):
        apagandose = {**VIGENTE, "active": False}
        assert "migrar" in diagnosticar("openai/gpt-oss-120b", [apagandose])[0]


class TestModeloQueSalioDelPlanGratuito:
    """El caso de agosto de 2026: el modelo no desaparecio, se volvio pago."""

    def test_un_modelo_sin_precios_se_reporta(self):
        sin_precio = {**VIGENTE, "pricing": None}
        problemas = diagnosticar("openai/gpt-oss-120b", [sin_precio])
        assert len(problemas) == 1
        assert "plan pago" in problemas[0]

    def test_se_acumulan_los_problemas_de_un_mismo_modelo(self):
        # Inactivo y sin precios a la vez: se informan los dos, no el primero.
        roto = {**VIGENTE, "active": False, "pricing": None}
        assert len(diagnosticar("openai/gpt-oss-120b", [roto])) == 2


class TestMensajesAccionables:
    def test_todos_los_avisos_nombran_el_modelo_afectado(self):
        casos = [
            ("desaparecido", [VIGENTE]),
            ("openai/gpt-oss-120b", [{**VIGENTE, "active": False}]),
            ("openai/gpt-oss-120b", [{**VIGENTE, "pricing": None}]),
        ]
        for modelo, catalogo in casos:
            for problema in diagnosticar(modelo, catalogo):
                assert modelo in problema

    def test_el_modelo_ausente_indica_donde_cargar_el_reemplazo(self):
        # Quien recibe el mail a las 3 de la mañana no deberia tener que
        # acordarse de como se llamaba la variable.
        assert "GROQ_MODEL" in diagnosticar("desaparecido", [VIGENTE])[0]
