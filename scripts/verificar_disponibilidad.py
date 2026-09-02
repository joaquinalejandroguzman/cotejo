"""Verifica que el modelo que usa la app siga vigente en Groq.

Groq da de baja modelos con fecha fija. Esta app ya se cayo dos veces por eso,
y las dos veces el aviso llego por el peor canal posible: alguien intentando
usarla y encontrandose con un error.

Este script corre solo, todos los dias, desde GitHub Actions. Cuando algo
anda mal termina con codigo distinto de cero, el workflow falla y GitHub
manda un mail. El objetivo es enterarse antes que el cliente.

Ejecucion local:
    GROQ_API_KEY=... python scripts/verificar_disponibilidad.py
"""

import os
import sys
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groq_client import MODEL_ENV_VAR, resolve_model

MODELS_URL = "https://api.groq.com/openai/v1/models"
CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT = 30


def diagnosticar(modelo: str, catalogo: list[dict[str, Any]]) -> list[str]:
    """Compara el modelo configurado contra el catalogo que devuelve Groq.

    Devuelve una lista de problemas en lenguaje llano, vacia si esta todo
    bien. Se separa de la parte que hace red para poder probarla sin llamar
    a la API.
    """
    registro = next((m for m in catalogo if m.get("id") == modelo), None)

    if registro is None:
        vigentes = sorted(
            m["id"] for m in catalogo if m.get("id") and "whisper" not in m.get("id", "")
        )
        return [
            f"El modelo '{modelo}' ya no figura en el catálogo de Groq para esta "
            f"cuenta. La app está caída o lo va a estar. Modelos disponibles "
            f"ahora mismo: {', '.join(vigentes)}. Cargá uno de esos en la "
            f"variable {MODEL_ENV_VAR}."
        ]

    problemas = []

    if not registro.get("active", True):
        problemas.append(
            f"El modelo '{modelo}' sigue en el catálogo pero está marcado como "
            "inactivo. Groq lo va a apagar: conviene migrar ahora, no cuando falle."
        )

    # El caso llama-3.3-70b-versatile: el modelo no desaparecio, se movio a un
    # plan pago. Un precio nulo o no numerico significa que dejo de ser
    # utilizable con la cuenta gratuita.
    pricing = registro.get("pricing")
    if pricing is None:
        problemas.append(
            f"El modelo '{modelo}' dejó de exponer precios, lo que suele indicar "
            "que pasó a un plan pago. Verificar en https://console.groq.com/docs/models"
        )

    return problemas


def obtener_catalogo(api_key: str) -> list[dict[str, Any]]:
    """Trae el catálogo de modelos visibles para esta cuenta."""
    resp = requests.get(MODELS_URL, headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
    resp.raise_for_status()
    return list(resp.json()["data"])


def probar_respuesta(modelo: str, api_key: str) -> str | None:
    """Le pide una respuesta minima al modelo. Devuelve el problema, o None.

    Estar en el catálogo no garantiza que responda. Esta es la única
    comprobación que prueba de punta a punta lo mismo que hace la app.
    """
    try:
        resp = requests.post(
            CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": modelo,
                "messages": [{"role": "user", "content": "Respondé solo: OK"}],
                "max_tokens": 10,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"El modelo '{modelo}' figura en el catálogo pero no respondió: {exc}"

    try:
        resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return f"El modelo '{modelo}' respondió con un formato inesperado: {str(resp.json())[:200]}"
    return None


def main() -> int:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("::error::Falta GROQ_API_KEY. Cargala como secret del repositorio.")
        return 1

    modelo = resolve_model()
    print(f"Modelo configurado: {modelo}")

    try:
        catalogo = obtener_catalogo(api_key)
    except requests.RequestException as exc:
        print(f"::error::No se pudo consultar el catálogo de modelos de Groq: {exc}")
        return 1

    print(f"Modelos visibles para la cuenta: {len(catalogo)}")

    problemas = diagnosticar(modelo, catalogo)
    if not problemas:
        fallo = probar_respuesta(modelo, api_key)
        if fallo:
            problemas.append(fallo)

    if problemas:
        for p in problemas:
            print(f"::error::{p}")
        return 1

    print(f"OK: '{modelo}' está vigente y responde.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
