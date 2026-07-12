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

from pdf_utils import extract_text_from_pdf, truncate_for_context, combine_documents
from ollama_client import chat, OllamaError

DEFAULT_PDF = os.path.join(os.path.dirname(__file__), "documentacion_agente.pdf")

st.set_page_config(page_title="Agente TiendaNova", page_icon="🛍️", layout="centered")

# ---------------------------------------------------------------------------
# Sidebar: cara visible del producto (no infraestructura)
# ---------------------------------------------------------------------------
EJEMPLOS = [
    "¿Cuánto tiempo tengo para devolver un producto?",
    "¿Hacen envíos a Colombia?",
    "¿Qué pasa si el pedido llega dañado?",
]

with st.sidebar:
    st.markdown("### 🛍️ TiendaNova")
    st.caption("Asistente virtual · Challenge AlurAgente")
    st.write(
        "Preguntame sobre políticas de privacidad, devoluciones, envíos, "
        "pagos o términos y condiciones."
    )

    st.divider()
    with st.expander("💬 Preguntas de ejemplo"):
        for ejemplo in EJEMPLOS:
            if st.button(ejemplo, use_container_width=True):
                st.session_state["pending_question"] = ejemplo

    st.divider()
    if st.button("🔄 Reiniciar conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("**📄 Documentación**")
    incluir_base = st.checkbox(
        "Incluir documento base (TiendaNova)", value=True,
        help="Desmarcá esto si querés reemplazarlo por completo con tus propios documentos."
    )
    extras = st.file_uploader(
        "Sumar documentos (PDF)", type=["pdf"], accept_multiple_files=True,
        help="Podés subir uno o varios PDFs. Se combinan con el documento base (o lo reemplazan si lo desmarcás arriba)."
    )

    st.divider()
    with st.expander("⚙️ Configuración avanzada"):
        ollama_host = st.text_input(
            "Host de Ollama", value=os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        )
        model_name = st.text_input(
            "Modelo", value=os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
        )

    st.divider()
    st.caption("Desarrollado por **Joaquín A. Guzmán**")
    st.caption("Challenge AlurAgente · Oracle ONE / Alura Latam · 2026")

# ---------------------------------------------------------------------------
# Carga del documento (con cache para no re-leer el PDF en cada mensaje)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Leyendo documento...")
def load_doc_text(file_bytes_or_path):
    import io
    return extract_text_from_pdf(io.BytesIO(file_bytes_or_path) if isinstance(file_bytes_or_path, (bytes, bytearray)) else file_bytes_or_path)


docs = []
if incluir_base:
    docs.append(("documentacion_agente.pdf (base)", load_doc_text(DEFAULT_PDF)))

nombres_extra = []
for f in (extras or []):
    docs.append((f.name, load_doc_text(f.getvalue())))
    nombres_extra.append(f.name)

if not docs:
    # Ni base ni extras: usar el base igual para que la app nunca quede vacia
    docs.append(("documentacion_agente.pdf (base)", load_doc_text(DEFAULT_PDF)))

doc_text = truncate_for_context(combine_documents(docs), max_chars=16000)
doc_label = " + ".join([nombre for nombre, _ in docs])

SYSTEM_PROMPT = f"""Eres el agente de soporte virtual de TiendaNova, una tienda online.
Tu unica fuente de verdad es el documento de mas abajo. Reglas estrictas:

0. Si el mensaje es un saludo o cortesia social (hola, buenas, gracias, chau, como estas,
   etc.) y NO contiene una pregunta real, responde de forma breve, cálida y natural
   (ej: "¡Hola! ¿En qué puedo ayudarte hoy con TiendaNova?"), invitando a preguntar sobre
   políticas, envíos, pagos o devoluciones. No apliques la regla 2 a estos mensajes, y no
   agregues frases robóticas como "no hay mucho más que decir".
0.5. Si te preguntan que documentacion tenes cargada, que datos manejas, o como pueden
   ver el documento, responde SOLO listando estos temas reales (no inventes sitios web,
   indices, ni procedimientos que no existen): {", ".join(nombre for nombre, _ in docs)}.
   Ejemplo: "Tengo cargada la documentación de TiendaNova, que cubre: política de
   privacidad, devoluciones, FAQ, envíos y términos y condiciones. Preguntame lo que
   necesites sobre esos temas."
1. Para preguntas reales, responde SOLO con informacion que este explicitamente en el documento.
2. Si la pregunta NO tiene relacion con el contenido del documento (ejemplos: la fecha
   de hoy, el clima, temas generales, matematica, opiniones personales, cualquier cosa
   fuera de politicas/envios/pagos/devoluciones de TiendaNova), responde exactamente:
   "Esa pregunta esta fuera de mi alcance. Solo puedo ayudarte con dudas sobre las
   politicas y servicios de TiendaNova." No inventes una respuesta ni des excusas falsas.
3. Si la pregunta es sobre TiendaNova pero el documento no cubre ese detalle especifico,
   dilo claramente y sugiere contactar a soporte@tiendanova.com. No inventes datos.
4. Nunca inventes politicas de privacidad, plazos o excusas que no esten en el documento.
5. Responde siempre en español, de forma clara, breve, cordial y natural — nunca cortante
   ni robótica.

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

if not question and "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

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
