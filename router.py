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


def injection_response(company_name: str = None) -> str:
    rol = f"agente de soporte de {company_name}" if company_name else "agente de soporte virtual"
    return (
        f"No puedo compartir instrucciones internas, secretos ni salirme de mi "
        f"función como {rol}. ¿Te ayudo con alguna duda sobre la documentación "
        "cargada?"
    )


def is_greeting(text: str) -> bool:
    t = _normalize(text)
    for p in _SALUDOS:
        m = re.match(p, t)
        if not m:
            continue
        # No alcanza con que el mensaje EMPIECE con un saludo: hay que
        # revisar que despues del saludo no quede una pregunta real.
        # Un umbral de longitud total es fragil (ej: "hola, como compro?"
        # es corto pero es una pregunta real) - lo que importa es cuanto
        # texto queda una vez que se saca el saludo en si.
        resto = t[m.end():].strip(" ,.!?")
        if resto == "" or len(resto.split()) <= 2:
            return True
        return False
    return False


def is_meta_docs_question(text: str) -> bool:
    t = _normalize(text)
    return any(re.search(p, t) for p in _META_DOCS)


def greeting_response(company_name: str = None) -> str:
    con_empresa = f" con {company_name}" if company_name else ""
    return f"¡Hola! ¿En qué puedo ayudarte hoy{con_empresa}? Preguntame lo que necesites sobre la documentación cargada."


def meta_docs_response(doc_names: list, company_name: str = None) -> str:
    nombres = ", ".join(doc_names)
    de_empresa = f" de {company_name}" if company_name else ""
    return (
        f"Tengo cargada la siguiente documentación: **{nombres}**{de_empresa}. "
        "Preguntame lo que necesites sobre esos temas."
    )


def route(text: str, doc_names: list, company_name: str = None):
    """Devuelve una respuesta directa si el mensaje matchea una regla,
    o None si debe ir al LLM.

    company_name: nombre de la empresa a la que pertenece la documentacion
    cargada (None si es generica / no se pudo determinar). Se usa solo
    para personalizar el copy de las respuestas fijas, no cambia la logica
    de deteccion de intencion.
    """
    if is_injection_attempt(text):
        return injection_response(company_name)
    if is_greeting(text):
        return greeting_response(company_name)
    if is_meta_docs_question(text):
        return meta_docs_response(doc_names, company_name)
    return None
