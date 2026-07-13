"""Cliente minimo para hablar con un servidor Ollama local via su API REST."""
import re
import requests


class OllamaError(Exception):
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


def chat(messages: list, model: str = "llama3.2", host: str = "http://localhost:11434", timeout: int = 240) -> str:
    """Envia una conversacion al endpoint /api/chat de Ollama y devuelve la respuesta del modelo.

    messages: lista de dicts {"role": "system"|"user"|"assistant", "content": str}
    """
    url = f"{host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        # Evita recargar el modelo de memoria cada pocos minutos de inactividad.
        "keep_alive": "30m",
        "options": {
            # Bajada de 0.2 a 0.3: en 0.2 el modelo abusaba del mensaje de
            # "no tengo esa informacion" aunque el documento si la tenia.
            "temperature": 0.3,
            # El default de Ollama (2048) no alcanza para los 6 documentos
            # combinados y los recortaba en silencio.
            "num_ctx": 16384,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout as exc:
        # Sin este catch, un timeout tiraba un traceback feo en vez de un
        # mensaje claro.
        raise OllamaError(
            f"Ollama tardó más de {timeout}s en responder. Con los 6 "
            "documentos de base cargados, la primera respuesta puede tardar "
            "bastante en una maquina sin GPU dedicada — probá de nuevo, "
            "usualmente las siguientes preguntas son mas rapidas."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError(
            f"No se pudo conectar a Ollama en {host}. "
            "Asegurate de que el servidor este corriendo (`ollama serve`) "
            f"y que el modelo '{model}' este descargado (`ollama pull {model}`)."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        raise OllamaError(f"Ollama respondio con error: {exc}") from exc

    data = resp.json()
    contenido = data.get("message", {}).get("content", "").strip()
    return _strip_document_hedge(contenido)
