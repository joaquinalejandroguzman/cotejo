"""Fixtures that boot a real Streamlit server for end-to-end tests.

End-to-end tests drive an actual browser against an actual server process, so
they are slow and are excluded from the default test run. Run them with
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
    """Reserve an ephemeral port so parallel runs never collide."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_serving(url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    """Poll until the server answers, failing fast if the process dies."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Streamlit exited with code {process.returncode} before serving {url}"
            )
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit did not serve {url} within {timeout}s")


@pytest.fixture(scope="session")
def streamlit_server() -> Iterator[str]:
    """Start the app on a free port and yield its base URL.

    No API key is configured on purpose: the shell of the app must render
    without one, which is exactly what the smoke test asserts.
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
