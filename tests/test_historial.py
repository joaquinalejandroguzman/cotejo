"""Pruebas del armado del historial que viaja al modelo.

El historial cumple dos roles a la vez: es lo que se dibuja en pantalla y es
lo que se le manda al modelo en cada turno. Los dos necesitan cosas
distintas, y confundirlos tiene consecuencias reales.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from historial import mensajes_para_el_modelo


class TestLosErroresNoViajanAlModelo:
    """El bug que motiva este modulo.

    Un fallo de cuota se guardaba como si fuera una respuesta del asistente,
    y en el turno siguiente el modelo lo recibia como algo que el mismo habia
    dicho. Un error transitorio terminaba contaminando toda la conversacion.
    """

    def test_un_mensaje_marcado_como_error_se_excluye(self):
        mensajes = [
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "El asistente no está disponible.", "error": True},
            {"role": "user", "content": "¿cuánto sale la yerba?"},
        ]
        assert mensajes_para_el_modelo(mensajes) == [
            {"role": "user", "content": "hola"},
            {"role": "user", "content": "¿cuánto sale la yerba?"},
        ]

    def test_una_respuesta_normal_si_viaja(self):
        mensajes = [{"role": "assistant", "content": "Sale $2.859,90."}]
        assert mensajes_para_el_modelo(mensajes) == mensajes

    def test_varios_errores_seguidos_se_excluyen_todos(self):
        mensajes = [
            {"role": "assistant", "content": "falla 1", "error": True},
            {"role": "assistant", "content": "falla 2", "error": True},
        ]
        assert mensajes_para_el_modelo(mensajes) == []


class TestLaMetadataDeInterfazNoViajaAlModelo:
    """Las fuentes se dibujan en pantalla, no se le mandan al modelo."""

    def test_las_fuentes_se_descartan(self):
        mensajes = [
            {"role": "assistant", "content": "Sale $2.859,90.", "fuentes": ["Lista de precios"]}
        ]
        assert mensajes_para_el_modelo(mensajes) == [
            {"role": "assistant", "content": "Sale $2.859,90."}
        ]

    def test_solo_sobreviven_role_y_content(self):
        mensajes = [{"role": "user", "content": "hola", "fuentes": [], "cualquier_cosa": 1}]
        assert set(mensajes_para_el_modelo(mensajes)[0]) == {"role", "content"}


class TestRecorte:
    """El chat entero viaja en cada request y agota la cuota por minuto."""

    def test_se_queda_con_los_ultimos_mensajes(self):
        mensajes = [{"role": "user", "content": str(i)} for i in range(10)]
        recortado = mensajes_para_el_modelo(mensajes, maximo=4)
        assert [m["content"] for m in recortado] == ["6", "7", "8", "9"]

    def test_el_recorte_se_aplica_despues_de_sacar_los_errores(self):
        # Si se recortara antes, un tramo de errores podria dejar al modelo
        # sin ningun mensaje real pese a haber conversacion disponible.
        mensajes = [
            {"role": "user", "content": "vieja"},
            {"role": "assistant", "content": "falla", "error": True},
            {"role": "assistant", "content": "falla", "error": True},
            {"role": "user", "content": "nueva"},
        ]
        recortado = mensajes_para_el_modelo(mensajes, maximo=2)
        assert [m["content"] for m in recortado] == ["vieja", "nueva"]

    def test_una_lista_vacia_devuelve_vacio(self):
        assert mensajes_para_el_modelo([]) == []
