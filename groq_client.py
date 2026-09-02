"""Cliente minimo para hablar con la API de Groq (compatible con OpenAI)."""

import os
import re

import requests

# Un mensaje del formato de chat completions: {"role": ..., "content": ...}.
type ChatMessage = dict[str, str]

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Variable de entorno que permite cambiar el modelo sin tocar el codigo.
# En Streamlit Community Cloud se carga como secret; en local, exportandola.
MODEL_ENV_VAR = "GROQ_MODEL"

# Modelo que se usa si nadie configura MODEL_ENV_VAR.
#
# Groq da de baja modelos con fecha fija y este proyecto ya se cayo dos veces
# por eso: meta-llama/llama-4-scout-17b-16e-instruct se apago el 17/07/2026, y
# llama-3.3-70b-versatile salio del plan gratuito el 16/08/2026. Por eso el
# modelo ahora se resuelve por entorno: cuando Groq de de baja el proximo,
# alcanza con cambiar un secret y reiniciar, sin editar codigo ni redeployar.
#
# Verificado el 01/09/2026 contra la API: responde correctamente sobre la
# documentacion del proyecto en ~0.9s. Antes de cambiarlo, mirar las fechas
# de baja en https://console.groq.com/docs/deprecations
FALLBACK_MODEL = "openai/gpt-oss-120b"


def resolve_model(override: str | None = None) -> str:
    """Decide que modelo usar, en orden de prioridad.

    1. El argumento explicito, si se pasa uno.
    2. La variable de entorno MODEL_ENV_VAR.
    3. FALLBACK_MODEL.

    Un valor vacio o solo espacios se ignora: un secret cargado sin valor no
    tiene que mandar un modelo vacio a la API, es preferible caer al que
    sabemos que funciona.
    """
    for candidato in (override, os.environ.get(MODEL_ENV_VAR)):
        if candidato and candidato.strip():
            return candidato.strip()
    return FALLBACK_MODEL


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
    model: str | None = None,
    api_key: str | None = None,
    timeout: int = 60,
) -> str:
    """Envia una conversacion al endpoint de chat completions de Groq
    y devuelve la respuesta del modelo.

    messages: lista de dicts {"role": "system"|"user"|"assistant", "content": str}
    model: si no se pasa, lo resuelve resolve_model() (entorno o por defecto).
    """
    model = resolve_model(model)
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
                "Seguramente fue dado de baja: mirá los modelos vigentes en "
                "https://console.groq.com/docs/models y cargá uno nuevo en la "
                f"variable {MODEL_ENV_VAR} (como secret en Streamlit Cloud, o "
                "como variable de entorno en local). No hace falta tocar el código."
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
