"""
Router de intencion simple, basado en reglas (sin LLM).

Modelos muy chicos (ej. llama3.2:1b) no siguen bien instrucciones complejas
de un system prompt largo. Para los casos mas comunes y repetitivos
(saludos, "que documentacion tenes") conviene resolverlos de forma
deterministica en Python, sin depender de que el modelo razone bien.
Solo las preguntas reales sobre el contenido del documento llegan al LLM.
"""
import re
import unicodedata

# Patrones sin tildes: el texto se normaliza (tildes removidas) antes de
# matchear, asi "qué" y "que", "documentación" y "documentacion" matchean igual.
_SALUDOS = [
    r"^hola\b", r"^buenas\b", r"^buen[oa]s? dias?\b", r"^buenas tardes\b",
    r"^buenas noches\b", r"^hey\b", r"^que tal\b",
    r"^como estas\b", r"^gracias\b", r"^muchas gracias\b",
    r"^chau\b", r"^adios\b", r"^hasta luego\b", r"^ok gracias\b",
]

_META_DOCS = [
    r"que documentacion tenes",
    r"que documentos tenes",
    r"que datos (manej|tenes)",
    r"que informacion tenes cargada",
    r"como (hago para )?ver.*documentacion",
    r"como (hago para )?saber.*documentacion",
    r"que documentacion.*cargad",
    r"acceso a (la|tu) documentacion",
]

# Intentos de jailbreak / prompt injection: instrucciones que buscan que el
# agente ignore sus reglas, revele su system prompt, o invente contenido
# fuera del documento haciendose pasar por "sin restricciones".
_JAILBREAK = [
    r"ignora tus instrucciones", r"ignora las instrucciones",
    r"olvida tus instrucciones", r"olvida las instrucciones",
    r"sin restricciones", r"sin filtros", r"no tienes reglas",
    r"modo desarrollador", r"developer mode", r"eres libre de",
    r"actua como si no tuvieras", r"finge que no tienes",
    r"system prompt", r"cual es tu prompt", r"revela tu prompt",
    r"dime tu prompt", r"cuentame un secreto", r"dime un secreto",
    r"contame un secreto", r"que secreto",
]


def _normalize(text: str) -> str:
    t = text.strip().lower()
    # Quita tildes/diacriticos (NFKD separa la letra del acento, luego
    # descartamos los caracteres combinantes).
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    # Quita signos de apertura en español y espacios sobrantes, para que
    # los patrones anclados con ^ funcionen igual con o sin "¿"/"¡".
    t = t.lstrip("¿¡ ")
    return t


def is_injection_attempt(text: str) -> bool:
    t = _normalize(text)
    return any(re.search(p, t) for p in _JAILBREAK)


def injection_response() -> str:
    return (
        "No puedo compartir instrucciones internas, secretos ni salirme de mi "
        "función como agente de soporte de TiendaNova. ¿Te ayudo con alguna duda "
        "sobre nuestras políticas de privacidad, devoluciones, envíos o pagos?"
    )


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
    if is_injection_attempt(text):
        return injection_response()
    if is_greeting(text):
        return greeting_response()
    if is_meta_docs_question(text):
        return meta_docs_response(doc_names)
    return None
