"""
Router de intencion simple, basado en reglas (sin LLM).

Modelos muy chicos (ej. llama3.2:1b) no siguen bien instrucciones complejas
de un system prompt largo. Para los casos mas comunes y repetitivos
(saludos, "que documentacion tenes") conviene resolverlos de forma
deterministica en Python, sin depender de que el modelo razone bien.
Solo las preguntas reales sobre el contenido del documento llegan al LLM.
"""
import re

_SALUDOS = [
    r"^hola\b", r"^buenas\b", r"^buen[oa]s? d[ií]as?\b", r"^buenas tardes\b",
    r"^buenas noches\b", r"^hey\b", r"^que tal\b", r"^qu[eé] tal\b",
    r"^como estas\b", r"^c[oó]mo est[aá]s\b", r"^gracias\b", r"^muchas gracias\b",
    r"^chau\b", r"^adios\b", r"^adi[oó]s\b", r"^hasta luego\b", r"^ok gracias\b",
]

_META_DOCS = [
    r"que documentaci[oó]n ten[eé]s",
    r"que documentos ten[eé]s",
    r"que datos (manej|ten[eé]s|tenes)",
    r"que informaci[oó]n ten[eé]s cargada",
    r"como (hago para )?ver.*documentaci[oó]n",
    r"como (hago para )?saber.*documentaci[oó]n",
    r"que documentaci[oó]n.*cargad",
    r"acceso a (la|tu) documentaci[oó]n",
]


def _normalize(text: str) -> str:
    return text.strip().lower()


def is_greeting(text: str) -> bool:
    t = _normalize(text)
    if len(t) > 40:
        # Un saludo real es corto; si el mensaje es largo probablemente
        # incluye una pregunta real ademas del saludo.
        return False
    return any(re.search(p, t) for p in _SALUDOS)


def is_meta_docs_question(text: str) -> bool:
    t = _normalize(text)
    return any(re.search(p, t) for p in _META_DOCS)


def greeting_response() -> str:
    return "¡Hola! ¿En qué puedo ayudarte hoy con TiendaNova? Puedo responder dudas sobre privacidad, devoluciones, envíos, pagos o términos y condiciones."


def meta_docs_response(doc_names: list) -> str:
    nombres = ", ".join(doc_names)
    return (
        f"Tengo cargada la siguiente documentación: **{nombres}**, que cubre "
        "política de privacidad, devoluciones, preguntas frecuentes, envíos "
        "y términos y condiciones de TiendaNova. Preguntame lo que necesites "
        "sobre esos temas."
    )


def route(text: str, doc_names: list):
    """Devuelve una respuesta directa si el mensaje matchea una regla,
    o None si debe ir al LLM."""
    if is_greeting(text):
        return greeting_response()
    if is_meta_docs_question(text):
        return meta_docs_response(doc_names)
    return None
