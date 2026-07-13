"""Cliente minimo para hablar con un servidor Ollama local via su API REST."""
import requests


class OllamaError(Exception):
    pass


def chat(messages: list, model: str = "llama3.2", host: str = "http://localhost:11434", timeout: int = 120) -> str:
    """Envia una conversacion al endpoint /api/chat de Ollama y devuelve la respuesta del modelo.

    messages: lista de dicts {"role": "system"|"user"|"assistant", "content": str}
    """
    url = f"{host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        # Temperatura baja: priorizamos respuestas ceñidas al documento por
        # sobre respuestas "creativas", que es justo lo que produce alucinaciones.
        "options": {"temperature": 0.2},
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
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
