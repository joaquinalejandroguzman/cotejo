"""Fixtures que levantan un servidor Streamlit real para los tests e2e.

Estos tests manejan un navegador de verdad contra un proceso de verdad, asi
que son lentos y quedan fuera de la corrida por defecto. Se corren con
`make test-e2e`.
"""

import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STARTUP_TIMEOUT_SECONDS = 60


def _free_port() -> int:
    """Reserva un puerto efimero para que dos corridas nunca choquen."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_serving(url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    """Espera a que el servidor responda, y falla rapido si el proceso muere."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Streamlit termino con codigo {process.returncode} antes de servir {url}"
            )
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit no llego a servir {url} en {timeout}s")


@pytest.fixture(scope="session")
def streamlit_server() -> Iterator[str]:
    """Levanta la app en un puerto libre y devuelve su URL base.

    No se configura API key a proposito: la app tiene que renderizar su
    estructura sin una, que es justo lo que verifica el test de humo.
    """
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            "--server.address",
            "127.0.0.1",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_until_serving(url, process, STARTUP_TIMEOUT_SECONDS)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
