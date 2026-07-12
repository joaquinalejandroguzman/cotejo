"""
Agente Inteligente TiendaNova - Challenge AlurAgente (Oracle ONE / Alura Latam)

Streamlit app que lee un documento (PDF) de la tienda y responde preguntas
de los clientes usando un modelo local servido por Ollama.

Ejecutar localmente:
    ollama serve                      # (en otra terminal, si no esta corriendo)
    ollama pull llama3.2               # una sola vez
    pip install -r requirements.txt
    streamlit run app.py
"""
import os
import streamlit as st

from pdf_utils import extract_text_from_pdf, truncate_for_context
from ollama_client import chat, OllamaError

DEFAULT_PDF = os.path.join(os.path.dirname(__file__), "documentacion_agente.pdf")

st.set_page_config(page_title="Agente TiendaNova", page_icon="🛍️", layout="centered")

# ---------------------------------------------------------------------------
# Sidebar: configuracion del modelo
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración")
    ollama_host = st.text_input("Host de Ollama", value=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    model_name = st.text_input("Modelo", value=os.environ.get("OLLAMA_MODEL", "llama3.2"))

    st.divider()
    st.subheader("📄 Documento base")
    uploaded = st.file_uploader("Reemplazar documento (PDF)", type=["pdf"])
    st.caption("Por defecto se usa `documentacion_agente.pdf` (TiendaNova).")

    st.divider()
    if st.button("🔄 Reiniciar conversación"):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# Carga del documento (con cache para no re-leer el PDF en cada mensaje)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Leyendo documento...")
def load_doc_text(file_bytes_or_path):
    if isinstance(file_bytes_or_path, (bytes, bytearray)):
        import io
        return extract_text_from_pdf(io.BytesIO(file_bytes_or_path))
    return extract_text_from_pdf(file_bytes_or_path)


if uploaded is not None:
    doc_text = load_doc_text(uploaded.getvalue())
    doc_label = uploaded.name
else:
    doc_text = load_doc_text(DEFAULT_PDF)
    doc_label = "documentacion_agente.pdf"

doc_text = truncate_for_context(doc_text)

SYSTEM_PROMPT = f"""Eres el agente de soporte virtual de TiendaNova, una tienda online.
Tu unica fuente de verdad es el siguiente documento. Respondes SOLO con base en su contenido.
Si la pregunta no puede responderse con el documento, dilo claramente y sugiere contactar a soporte@tiendanova.com.
Responde siempre en español, de forma clara, breve y amable.

--- DOCUMENTO ---
{doc_text}
--- FIN DEL DOCUMENTO ---
"""

# ---------------------------------------------------------------------------
# UI principal
# ---------------------------------------------------------------------------
st.title("🛍️ Agente Inteligente — TiendaNova")
st.caption(f"Challenge AlurAgente · Oracle ONE / Alura Latam · Documento cargado: `{doc_label}`")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Escribe tu pregunta sobre políticas, envíos, devoluciones...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                answer = chat(llm_messages, model=model_name, host=ollama_host)
            except OllamaError as e:
                answer = f"⚠️ {e}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
