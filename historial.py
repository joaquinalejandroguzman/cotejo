"""Prepara el historial de la conversacion para mandarselo al modelo.

El historial cumple dos roles a la vez. Es lo que se dibuja en pantalla, y es
lo que viaja al modelo en cada turno. Los dos necesitan cosas distintas, y
confundirlos tiene dos consecuencias concretas:

**Los errores contaminan el contexto.** Un fallo de cuota se guardaba en el
historial como si fuera una respuesta del asistente. En el turno siguiente el
modelo lo recibia como algo que el mismo habia dicho, y respondia condicionado
por un mensaje que nunca fue una respuesta. Un problema transitorio terminaba
arrastrandose por toda la conversacion.

**La metadata de la interfaz no le sirve al modelo.** Las fuentes consultadas
se guardan junto al mensaje para poder dibujarlas debajo de cada respuesta,
pero mandarselas al modelo solo gasta tokens.

Este modulo existe separado de `app.py` porque `app.py` no tiene tests
unitarios: es un script de Streamlit que ejecuta al importarse. La logica que
puede romper el contexto de una conversacion no puede vivir ahi.
"""

# Cuantos mensajes del historial se le mandan al modelo. El chat completo
# viaja en cada request, asi que una conversacion larga se comia la cuota de
# tokens por minuto del plan gratuito y terminaba en 429 o 413. Con 6 mensajes
# (3 idas y vueltas) alcanza para sostener el contexto de la charla.
MAX_HISTORY_MESSAGES = 6

# Lo unico que entiende la API de chat completions. Todo lo demas que guarde
# la interfaz junto a un mensaje es asunto suyo.
type MensajeGuardado = dict[str, object]
type MensajeParaModelo = dict[str, str]


def mensajes_para_el_modelo(
    mensajes: list[MensajeGuardado], maximo: int = MAX_HISTORY_MESSAGES
) -> list[MensajeParaModelo]:
    """Devuelve los ultimos mensajes reales, sin errores ni metadata.

    El recorte se aplica DESPUES de descartar los errores. Al reves, un tramo
    de fallos consecutivos podria dejar al modelo sin ningun mensaje real
    aunque hubiera conversacion disponible mas atras.
    """
    reales = [
        {"role": str(m["role"]), "content": str(m["content"])}
        for m in mensajes
        if not m.get("error")
    ]
    return reales[-maximo:] if maximo else reales
