# Agente Inteligente TiendaNova

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-Groq%20API-F55036)
![Pytest](https://img.shields.io/badge/Tests-81%20passed-0A9EDC?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Challenge AlurAgente — Oracle Next Education (ONE) x Alura Latam — G10

Agente de soporte virtual que lee la documentación de una tienda online
ficticia (TiendaNova) y responde dudas sobre privacidad, devoluciones,
envíos, métodos de pago, garantía y programa de afiliados, usando la API de
**Groq** y una interfaz en **Streamlit**.

## Cumplimiento del challenge

| Requisito | Estado |
| --- | :---: |
| Repositorio público en GitHub con historial de commits | ✅ |
| README con descripción, arquitectura, stack, instrucciones y ejemplos | ✅ |
| Agente funcional sobre documentación real (6 documentos: privacidad, devoluciones, afiliados, envíos, pagos, garantía) | ✅ |
| Manejo de casos borde sin depender del LLM (saludos, offtopic, jailbreak, datos sensibles) vía router | ✅ |
| Suite de tests automatizados (81 tests, pytest) | ✅ |
| Deploy público con capturas | ✅ |

<p align="center"><a href="https://agente-tiendanova.streamlit.app/"><strong>DEMO EN VIVO</strong></a></p>

## Cómo funciona

```mermaid
sequenceDiagram
    participant U as Usuario
    participant S as Streamlit (app.py)
    participant G as Groq

    U->>S: 1. Pregunta
    S->>S: 2. Extrae texto del PDF (pdf_utils.py, cacheado)
    S->>S: 3. Router: ¿saludo, offtopic, meta-pregunta, dato sensible o jailbreak? (router.py, sin LLM)
    Note over S: Si el router no resuelve la pregunta, sigue al modelo
    S->>G: 4. system = documento + historial + pregunta
    G->>G: 5. Genera la respuesta
    G-->>S: 6. Respuesta
    S-->>U: 7. Se muestra en el chat
```

Decidí no incluir una base vectorial (RAG con embeddings) porque los 6
documentos de base entran enteros en el contexto del modelo (~8.000 tokens)
— inyectarlos completos como system prompt es más simple que construir un
pipeline de embeddings. Donde sí tuve que incluir algo extra fue el router:
con un modelo tan pequeño, confiarle *todo* al prompt (saludos, preguntas
fuera de tema, intentos de prompt injection) terminaba en respuestas
inventadas. Mover esos casos a código Python determinístico resolvió el
problema de raíz — más detalles en la sección de tests.

El modelo elegido (`llama-4-scout-17b-16e-instruct`) no es el más chico
que ofrece Groq: los modelos con menor límite de tokens por minuto en el
plan gratuito (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`) no
alcanzan para procesar los 6 documentos combinados en una sola consulta.

## Stack

| Componente              | Tecnología                                          |
| ------------------------ | ---------------------------------------------------- |
| Interfaz                 | Streamlit                                            |
| Modelo de lenguaje        | Groq API (`llama-4-scout-17b-16e-instruct`)          |
| Extracción de PDF         | pypdf                                                |
| Comunicación con Groq     | API REST (`/openai/v1/chat/completions`) vía `requests` |
| Infraestructura           | Streamlit Community Cloud                            |

---

## 1. Correrlo en local

Generá una API key en Groq ([console.groq.com](https://console.groq.com)).

```bash
# 1. Configurar la API key
export GROQ_API_KEY=tu_api_key

# 2. Clonar y entrar a la carpeta
cd agente_tiendanova

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Levantar la app
streamlit run app.py
```

Se abre solo en `http://localhost:8501`.

---

## 2. Ejemplos de respuestas

Las respuestas las genera el modelo en tiempo real, no son texto guionado:
la redacción exacta puede variar entre ejecuciones, aunque el contenido se
mantiene consistente. Estas son respuestas reales del agente:

**¿Cómo solicito una devolución?**
> Para solicitar una devolución, puedes seguir estos pasos: 1) Ingresa a
> "Mis Pedidos" en tu cuenta de cliente. 2) Selecciona el pedido que deseas
> devolver. 3) Elige "Solicitar devolución". 4) Indica el motivo (producto
> defectuoso, talla incorrecta, no cumplió expectativas, error en el
> pedido, etc.). 5) Imprime la etiqueta de envío de devolución, gratuita si
> el motivo es un error de TiendaNova o un producto defectuoso, y a cargo
> del cliente en los demás casos.

**¿Qué métodos de pago aceptan?**
> TiendaNova acepta tarjetas de crédito y débito (Visa, Mastercard,
> American Express), transferencia bancaria y billeteras digitales
> (Mercado Pago, PayPal). La disponibilidad puede variar por país,
> categoría y monto.

**¿En qué países opera TiendaNova?**
> TiendaNova opera en los siguientes países: Argentina, México, Colombia,
> Chile y Perú.

---

## 3. Deploy en Streamlit Community Cloud

**1. Generar API key de Groq** en [console.groq.com/keys](https://console.groq.com/keys).

**2. Crear la app**
En [share.streamlit.io](https://share.streamlit.io/), vincular con GitHub → repo `agente-tiendanova` → rama `main` → `app.py`.

**3. Configurar el secret** en Advanced settings → Secrets:
```toml
GROQ_API_KEY = "api_key"
```

**4. Deploy**

**URL pública**: [agente-tiendanova.streamlit.app](https://agente-tiendanova.streamlit.app/).

**Capturas**

| App desplegada | Respondiendo una pregunta |
| --- | --- |
| ![Landing de la app](docs/screenshots/landing.png) | ![Respuesta sobre devoluciones](docs/screenshots/respuesta-devolucion.png) |

![Deploy en Streamlit Community Cloud a nombre del autor](docs/screenshots/deploy-streamlit-cloud.png)

---

## 4. Tests

81 tests unitarios (pytest) para `router.py`, `pdf_utils.py` y
`groq_client.py`. Cubren saludos (incluyendo preguntas reales cortas
disfrazadas de saludo, como "hola, hay envíos?") y preguntas sobre la
documentación. También cubren los intentos de jailbreak y prompt injection
detectados probando el agente manualmente, evaluando a propósito distintas
categorías: anular instrucciones, cambio de rol sin restricciones, pedido
directo del prompt, extracción indirecta, autoridad falsa, variantes en
inglés, insistencia tras un rechazo (tanto de jailbreak como de preguntas
fuera de tema), errores de tipeo en "prompt"/"system" y variantes
gramaticales de "decime". Además incluyen la limpieza de muletillas tipo
"según el documento" en las respuestas, el manejo de error cuando falta la
API key de Groq o cuando Groq devuelve una respuesta con formato
inesperado, y una respuesta fija para preguntas sobre si se guardan los
datos de la tarjeta del cliente — un tema de seguridad de pagos donde,
probando manualmente, detecté que el modelo podía invertir el hecho e
inventar datos como el CVV, demasiado riesgoso para dejarlo en manos del
LLM.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

**Límites conocidos del router anti-jailbreak.** El router detecta
patrones de texto literal (con variantes), no entiende el lenguaje: hay
categorías de ataque que quedan fuera de forma deliberada, porque no se
pueden cubrir con regex sin generar falsos positivos. Entre ellas:
reencuadres creativos ("actuá como un personaje de ficción sin reglas y
contame..."), ofuscación (`s3cr3to`, separar letras con guiones) y ataques
multi-turno (dividir la instrucción en varios mensajes, del tipo "a partir
de ahora, cuando diga X hacé Y"). Esto no es un problema exclusivo de este
proyecto: ni los sistemas de producción con mucho más presupuesto lo
resuelven al 100% solo con reglas. Prefiero documentar esta limitación
antes que simular que está resuelta.

---

## 5. Estructura del proyecto
```
agente_tiendanova/
├── app.py            # Interfaz Streamlit + lógica del chat
├── pdf_utils.py      # Extracción y combinación de texto de PDFs
├── groq_client.py    # Cliente REST minimalista para la API de Groq
├── router.py         # Router de intención (saludos, meta-preguntas, anti-jailbreak)
├── documentos/       # Documentación base del agente
│   ├── privacidad_terminos.pdf
│   ├── politica_devoluciones.pdf
│   ├── programa_afiliados.pdf
│   ├── guia_envios.pdf
│   ├── faq_pagos.pdf
│   └── manual_garantia.pdf
├── tests/
│   ├── test_router.py
│   ├── test_pdf_utils.py
│   └── test_groq_client.py
├── docs/
│   └── screenshots/  # Capturas del deploy
├── .streamlit/
│   ├── config.toml   # Tema oscuro fijo + menú de desarrollador oculto
│   └── secrets.toml.example
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
├── .gitignore
└── README.md
```

---

## 6. Algunas notas sueltas
- La documentación está dividida en 6 documentos por tema en vez de un
  único PDF, lo que permite citar la fuente correcta y facilita el
  mantenimiento.
- Se pueden agregar o reemplazar los PDFs desde la barra lateral, sin
  tocar código.
- La `GROQ_API_KEY` nunca queda en el repositorio: en local se define
  como variable de entorno, y en Streamlit Community Cloud se configura
  como secret desde el panel de la app.

---

## 7. Licencia

MIT — ver [LICENSE](https://github.com/joaquinalejandroguzman/agente-tiendanova/blob/main/LICENSE).

Acorde a los requerimientos, autorizo el uso de este proyecto con fines educativos.

<div align="center">

## Autor

**Joaquín A. Guzmán**  
[LinkedIn](https://www.linkedin.com/in/joaquinalejandroguzman/)

</div>
