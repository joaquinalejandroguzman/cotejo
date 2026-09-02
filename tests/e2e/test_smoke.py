"""Smoke test proving the end-to-end harness reaches a live app.

This is deliberately minimal. Its job is to fail loudly if the browser, the
server fixture, or the app shell stops working — not to assert product
behaviour, which belongs in dedicated end-to-end suites.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_app_shell_renders_without_an_api_key(page: Page, streamlit_server: str) -> None:
    """The app must render its shell even with no Groq API key configured."""
    page.goto(streamlit_server)

    # Product copy is Spanish by design; assert against what a user sees.
    expect(page.get_by_role("heading", name="Agente de Soporte Virtual")).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_role("button", name="Nuevo chat")).to_be_visible()


@pytest.mark.e2e
def test_question_input_is_available_with_the_default_corpus(
    page: Page, streamlit_server: str
) -> None:
    """The bundled corpus loads by default, so the chat input must be usable."""
    page.goto(streamlit_server)

    chat_input = page.get_by_placeholder(
        "Escribe tu pregunta sobre políticas, envíos, devoluciones..."
    )
    expect(chat_input).to_be_visible(timeout=30_000)
    expect(chat_input).to_be_editable()
