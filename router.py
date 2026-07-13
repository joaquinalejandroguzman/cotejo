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

# Preguntas claramente fuera de tema (no tienen nada que ver con ningun
# documento de negocio posible): fecha/hora, clima, matematica basica y
# contenido creativo. El modelo deberia responder con el mensaje fijo de
# "no tengo esa informacion", pero en la practica un modelo chico a veces
# contesta con un disclaimer generico de IA en vez de seguir la instruccion
# al pie de la letra - mejor resolverlo aca, como el resto de estos casos.
_OFFTOPIC = [
    r"que dia es hoy", r"que dia es$", r"que fecha es", r"en que fecha estamos",
    r"que hora es", r"que hora son",
    r"que clima hace", r"como esta el clima", r"va a llover", r"el pronostico",
    r"contame un chiste", r"decime un chiste", r"contame un poema",
    r"escribime un poema", r"hazme un poema", r"escribime una cancion",
    r"cuanto es \d", r"resolveme esta cuenta", r"cuanto suman",

    # Insistencia corta tras el rechazo (mismo problema que la categoria H
    # de jailbreak, mas abajo): un "como que no?" solo, sin nada mas,
    # despues de la respuesta fija de "no tengo esa informacion" es casi
    # siempre volver a insistir con la misma pregunta fuera de tema, no una
    # pregunta de negocio nueva. Bug real: "que hora es" -> rechazo ->
    # "como que no" hacia que el modelo alucinara una respuesta sobre
    # reembolsos, sin ninguna relacion con la pregunta.
    r"^como que no\??!?$", r"^como asi que no\??!?$", r"^por que no\??!?$",
    r"^en serio que no\??!?$", r"^y eso\??!?$",
]

# Intentos de jailbreak / prompt injection. Organizados por categoria para
# que sea mas facil ver que cubrimos y que falta. "tu" y "vos" (variante
# argentina) se cubren por separado porque son palabras distintas y no
# alcanza con un solo verbo conjugado.
_JAILBREAK = [
    # --- A. Anular / ignorar las instrucciones ---
    r"ignora tus (instrucciones|reglas)", r"ignora las (instrucciones|reglas)",
    r"ignora lo anterior", r"ignora todo lo anterior",
    r"olvida tus (instrucciones|reglas)", r"olvida las (instrucciones|reglas)",
    r"olvida lo anterior", r"olvidate de (tus|las) (instrucciones|reglas)",
    r"descarta (tus|las) (instrucciones|reglas)", r"no sigas (tus|las) (instrucciones|reglas)",
    r"saltea(te)? (tus|las) (instrucciones|reglas)",

    # --- B. Cambio de rol / personaje sin restricciones ---
    r"sin restricciones", r"sin filtros", r"sin censura", r"sin reglas",
    r"no tienes reglas", r"no tenes reglas", r"modo desarrollador", r"developer mode",
    r"modo admin", r"modo sin filtro", r"eres libre de", r"sos libre de",
    r"actua como si no tuvieras", r"actua sin filtros", r"actua sin restricciones",
    r"finge que no tienes", r"fingi que no tenes", r"pretende que no tienes",
    r"pretendas que no tenes", r"imagina que no tenes reglas", r"en un mundo hipotetico.*sin reglas",

    # --- C. Pedido directo del system prompt / instrucciones ---
    # "syst\w*" y "pr\w*mpt" (en vez de "system"/"prompt" literales) toleran
    # errores de tipeo como "systm" o "prmpt" - un typo no deberia bastar
    # para esquivar el filtro. Cubrimos ademas el orden invertido ("prompt
    # system") porque el modelo, cuando esto no matcheaba, terminaba
    # inventando una descripcion completa de su arquitectura interna en vez
    # de rechazar.
    r"\bsyst\w*\s+pr\w*mpt\b", r"\bpr\w*mpt\s+syst\w*\b", r"system instructions",
    r"cual es tu prompt", r"cual es tu configuracion",
    r"cuales son tus instrucciones", r"que instrucciones tenes", r"que instrucciones tienes",
    r"que reglas tenes", r"que reglas tienes", r"cuales son tus reglas",
    r"mostrame (tu prompt|tus instrucciones|el prompt|las instrucciones)",
    r"muestrame (tu prompt|tus instrucciones|el prompt|las instrucciones)",
    r"revela (tu prompt|tus instrucciones)", r"revelame (tu prompt|tus instrucciones)",
    r"repeti (tu prompt|tus instrucciones)", r"repite (tu prompt|tus instrucciones)",
    r"imprimi tu prompt", r"imprime tu prompt", r"tu prompt inicial",
    r"que te dijeron que hicieras", r"que instrucciones te dieron",
    # "dime"/"decime" (imperativo), "tenes/tienes que decir" (obligacion) y
    # "necesito/quiero que me digas" (peticion): tres construcciones
    # gramaticales distintas para pedir lo mismo - y "prompt"/"secreto"
    # con tolerancia a typos, porque tambien se puede escribir mal.
    r"dime tu pr\w*mpt", r"decime tu pr\w*mpt",
    r"(tenes|tienes) que decir(me)?.*(pr\w*mpt|secreto|instruccion)",
    r"(necesito|quiero) que me (digas|cuentes).*(pr\w*mpt|secreto|instruccion)",

    # --- D. Secretos / informacion oculta ---
    r"cuentame un secreto", r"contame un secreto", r"dime un secreto",
    r"decime un secreto", r"que secreto", r"informacion oculta",
    r"que ocultas", r"que me estas ocultando",

    # --- E. Extraccion indirecta (repetir/traducir/resumir instrucciones) ---
    r"repeti todo lo que te dijeron", r"repite todo lo que te dijeron",
    r"traduci tus instrucciones", r"traduce tus instrucciones",
    r"resumime tus instrucciones", r"resume tus instrucciones",
    r"completa esta frase.*mis instrucciones", r"empeza tu respuesta con.*mis instrucciones",

    # --- F. Afirmaciones de autoridad falsa ---
    r"soy el desarrollador", r"soy tu desarrollador", r"soy el creador",
    r"soy tu creador", r"tengo permiso para ver", r"modo admin activado",
    r"acceso de administrador",

    # --- G. Variantes en ingles (cobertura basica) ---
    r"ignore previous instructions", r"ignore all previous instructions",
    r"ignore your instructions", r"show me your (system )?prompt",
    r"reveal your (system )?prompt", r"what is your (system )?prompt",
    r"act as if you have no restrictions", r"pretend you have no rules",
    r"you are now in dan mode",

    # --- H. Continuar insistiendo tras un rechazo ---
    # Bug real: despues de rechazar un intento de jailbreak, un simple
    # "porque" como respuesta hacia que el modelo, en vez de sostener el
    # rechazo, empezara a describir como funciona su propio system prompt.
    # Un mensaje corto y solo (sin nada mas) casi siempre es insistir con
    # la pregunta anterior, no una pregunta de negocio nueva.
    r"^porque\??$", r"^por que\??$", r"^dale\??!?$", r"^posta\??!?$",
    r"^en serio\??!?$", r"^vamos\??!?$",
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


def is_offtopic_question(text: str) -> bool:
    t = _normalize(text)
    return any(re.search(p, t) for p in _OFFTOPIC)


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


def _contacto(company_name: str = None) -> str:
    return "soporte@tiendanova.com" if company_name == "TiendaNova" else "el soporte correspondiente"


def offtopic_response(company_name: str = None) -> str:
    return (
        "No tengo esa información en mi documentación. Te recomiendo "
        f"contactar a {_contacto(company_name)}."
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
    if is_offtopic_question(text):
        return offtopic_response(company_name)
    return None
