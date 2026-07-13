"""Cliente minimo para hablar con un servidor Ollama local via su API REST."""
import requests


class OllamaError(Exception):
    pass


def chat(messages: list, model: str = "llama3.2", host: str = "http://localhost:11434", timeout: int = 240) -> str:
    """Envia una conversacion al endpoint /api/chat de Ollama y devuelve la respuesta del modelo.

    messages: lista de dicts {"role": "system"|"user"|"assistant", "content": str}
    """
    url = f"{host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            # Temperatura baja: priorizamos respuestas ceñidas al documento
            # por sobre respuestas "creativas". La bajamos de 0.2 a 0.3
            # porque en 0.2 el modelo se refugiaba de mas en el mensaje
            # fijo de "no tengo esa informacion" incluso cuando el
            # documento si la tenia.
            "temperature": 0.3,
            # Ollama usa por defecto una ventana de contexto chica (2048
            # tokens), que no alcanza para los 5 documentos base combinados
            # (~36.000 caracteres, ~10.000 tokens). Sin esto, Ollama
            # recortaria el contexto en silencio y el modelo "perderia" los
            # ultimos documentos sin ningun error visible.
            "num_ctx": 16384,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout as exc:
        # Con 6 documentos combinados el contexto ronda los 12.000 tokens;
        # en una maquina sin GPU dedicada, procesarlo puede tardar mas de
        # lo que tardaba con un solo documento chico. Sin este catch, un
        # timeout tiraba un traceback feo en vez de un mensaje claro.
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
    return data.get("message", {}).get("content", "").strip()
