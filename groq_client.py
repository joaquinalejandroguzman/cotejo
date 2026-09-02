"""Cliente minimo para hablar con la API de Groq (compatible con OpenAI)."""

import re

import requests

# Un mensaje del formato de chat completions: {"role": ..., "content": ...}.
type ChatMessage = dict[str, str]

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Groq da de baja modelos con fecha fija y, una vez apagados, el endpoint
# responde 404. El modelo anterior (meta-llama/llama-4-scout-17b-16e-instruct)
# se apago el 17/07/2026 y la app quedo caida hasta que se cambio este valor.
# Antes de tocarlo, verificar la fecha de baja en
# https://console.groq.com/docs/deprecations
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqError(Exception):
    pass


# El modelo no siempre evita la muletilla "segun el documento" solo con
# pedirselo en el prompt. La sacamos del inicio de la respuesta por codigo.
_HEDGE_PREFIX = re.compile(
    r"^(seg[uú]n (el|la|los|las|al) document\w*|de acuerdo (a|al|con) (el |la )?document\w*|"
    r"de acuerdo a la documentaci[oó]n|bas[aá]ndome en (el |la |al )?document\w*|"
    r"en base a(l)? (el |la )?document\w*)[,:]?\s*",
    re.IGNORECASE,
)


def _strip_document_hedge(text: str) -> str:
    nuevo = _HEDGE_PREFIX.sub("", text, count=1)
    if nuevo and nuevo != text:
        nuevo = nuevo[0].upper() + nuevo[1:]
    return nuevo


def chat(
    messages: list[ChatMessage],
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    timeout: int = 60,
) -> str:
    """Envia una conversacion al endpoint de chat completions de Groq
    y devuelve la respuesta del modelo.

    messages: lista de dicts {"role": "system"|"user"|"assistant", "content": str}
    """
    if not api_key:
        raise GroqError(
            "Falta la API key de Groq. Configurala como GROQ_API_KEY en "
            "los secrets de la app (o como variable de entorno en local)."
        )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        # Bajada de 0.2 a 0.3: en 0.2 el modelo abusaba del mensaje de
        # "no tengo esa informacion" aunque el documento si la tenia.
        "temperature": 0.3,
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise GroqError(f"Groq tardó más de {timeout}s en responder. Probá de nuevo.") from exc
    except requests.exceptions.ConnectionError as exc:
        raise GroqError(
            "No se pudo conectar con la API de Groq. Revisá tu conexión a internet."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        if resp.status_code == 401:
            raise GroqError("La API key de Groq es inválida o no está configurada.") from exc
        if resp.status_code == 404:
            # Caso real: Groq apago el modelo que teniamos configurado y el
            # mensaje generico ("404 Client Error") no dejaba ver la causa.
            raise GroqError(
                f"El modelo '{model}' ya no está disponible en Groq (404). "
                "Seguramente fue dado de baja: revisá "
                "https://console.groq.com/docs/deprecations y actualizá "
                "DEFAULT_MODEL en groq_client.py."
            ) from exc
        if resp.status_code == 429:
            raise GroqError(
                "Se alcanzó el límite de uso gratuito de Groq. Probá de nuevo en un momento."
            ) from exc
        if resp.status_code == 413:
            raise GroqError(
                "La conversación quedó demasiado grande para el plan gratuito de Groq. "
                "Iniciá un chat nuevo para liberar contexto."
            ) from exc
        raise GroqError(f"Groq respondió con error: {exc}") from exc

    data = resp.json()
    try:
        contenido = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise GroqError("Groq devolvió una respuesta con un formato inesperado.") from exc
    return _strip_document_hedge(contenido)
