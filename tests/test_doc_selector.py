import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from doc_selector import (
    MAX_CONTEXT_CHARS,
    _stem,
    _tokens,
    rank_documents,
    select_relevant_docs,
)

# Documentos sinteticos con el mismo formato que arma app.py:
# (nombre visible, texto extraido del PDF). Son cortos a proposito para que
# los tests no dependan de los PDFs reales.
DOCS = [
    (
        "Guía de Tiempos y Costos de Envío",
        "Los envíos estándar tardan entre 3 y 7 días hábiles. El envío express "
        "llega en 48 horas. Hacemos envíos a Argentina, México y Chile. "
        "La garantía de entrega aplica al envío express.",
    ),
    (
        "Política de Reembolsos y Devoluciones",
        "Podés pedir la devolución de un producto dentro de los 30 días. "
        "El reembolso se acredita en 10 días hábiles. Para devoluciones por "
        "falla aplica también la garantía del fabricante.",
    ),
    (
        "FAQ de Métodos de Pago",
        "Aceptamos tarjeta de crédito, débito y Mercado Pago. Podés pagar "
        "hasta en 12 cuotas sin interés. Los pagos rechazados se reintentan. "
        "La garantía no cubre cargos duplicados.",
    ),
]


class TestStem:
    def test_saca_el_plural_simple(self):
        assert _stem("pagos") == _stem("pago")

    def test_saca_el_plural_en_es(self):
        assert _stem("devoluciones") == _stem("devolucion")

    def test_devolver_y_devoluciones_comparten_raiz(self):
        # Bug real: sin recortar a la raiz, "¿como hago para devolver un
        # producto?" no traia la Politica de Reembolsos y Devoluciones,
        # porque "devolver" y "devoluciones" no son la misma palabra.
        assert _stem("devolver") == _stem("devoluciones")

    def test_palabras_cortas_quedan_igual(self):
        assert _stem("iva") == "iva"
        assert _stem("cvv") == "cvv"


class TestTokens:
    def test_ignora_palabras_vacias(self):
        assert _tokens("como hago para saber esto") == []

    def test_ignora_tildes_y_mayusculas(self):
        assert _tokens("ENVÍO") == _tokens("envio")

    def test_ignora_palabras_de_menos_de_tres_letras(self):
        assert _tokens("a mi el") == []

    def test_conserva_los_terminos_con_contenido(self):
        assert _tokens("¿cuánto tarda el envío?") == [_stem("tarda"), _stem("envio")]


class TestRankDocuments:
    def test_primero_el_documento_del_tema(self):
        orden = [nombre for nombre, _, _ in rank_documents("¿cuánto tarda el envío?", DOCS)]
        assert orden[0] == "Guía de Tiempos y Costos de Envío"

    def test_pregunta_de_pagos_trae_el_faq_de_pagos(self):
        orden = [nombre for nombre, _, _ in rank_documents("¿puedo pagar en cuotas?", DOCS)]
        assert orden[0] == "FAQ de Métodos de Pago"

    def test_termino_presente_en_todos_los_documentos_igual_discrimina(self):
        # Bug real: con IDF sin suavizar, un termino que aparece en todos los
        # documentos valia exactamente 0, asi que "¿cuanto dura la garantia?"
        # no traia el documento de garantia. "garantía" esta mencionada en
        # los tres documentos de prueba, igual que en los PDFs reales.
        orden = [nombre for nombre, _, _ in rank_documents("¿la garantía cubre la entrega?", DOCS)]
        assert orden[0] == "Guía de Tiempos y Costos de Envío"

    def test_sin_documentos_devuelve_lista_vacia(self):
        assert rank_documents("¿cuánto tarda el envío?", []) == []

    def test_pregunta_sin_coincidencias_conserva_el_orden_original(self):
        # sorted es estable: si nada matchea, todos empatan y el orden de
        # carga se respeta en vez de quedar arbitrario.
        orden = [nombre for nombre, _, _ in rank_documents("xyzzy plugh", DOCS)]
        assert orden == [nombre for nombre, _ in DOCS]


class TestSelectRelevantDocs:
    def test_si_todo_entra_no_descarta_nada(self):
        assert select_relevant_docs("¿cuánto tarda el envío?", DOCS) == DOCS

    def test_respeta_el_presupuesto_de_caracteres(self):
        seleccion = select_relevant_docs("¿cuánto tarda el envío?", DOCS, max_chars=250)
        total = sum(len(texto) for _, texto in seleccion)
        assert total <= 250

    def test_con_presupuesto_ajustado_elige_el_documento_del_tema(self):
        seleccion = select_relevant_docs("¿puedo pagar en cuotas?", DOCS, max_chars=200)
        assert [nombre for nombre, _ in seleccion] == ["FAQ de Métodos de Pago"]

    def test_siempre_devuelve_al_menos_un_documento(self):
        # Aunque el presupuesto sea mas chico que cualquier documento, el
        # agente no puede quedarse sin fuente: se manda el mas relevante
        # recortado.
        seleccion = select_relevant_docs("¿puedo pagar en cuotas?", DOCS, max_chars=50)
        assert len(seleccion) == 1
        assert seleccion[0][0] == "FAQ de Métodos de Pago"
        assert len(seleccion[0][1]) == 50

    def test_sin_documentos_devuelve_lista_vacia(self):
        assert select_relevant_docs("¿cuánto tarda el envío?", []) == []

    def test_recorta_el_contexto_de_los_seis_documentos_base(self):
        # El caso que motivo todo esto: seis documentos de ~5.000 caracteres
        # sumaban ~31.700 y agotaban la cuota de tokens por minuto de Groq.
        docs_grandes = [(f"Documento {i}", f"tema{i} " * 1000) for i in range(6)]
        seleccion = select_relevant_docs("tema3", docs_grandes)
        total = sum(len(texto) for _, texto in seleccion)
        assert total <= MAX_CONTEXT_CHARS
        assert seleccion[0][0] == "Documento 3"

    def test_documento_subido_por_el_usuario_tambien_puntua(self):
        # Los PDFs que sube el usuario no estan en ninguna lista de palabras
        # clave: el puntaje sale del propio texto, asi que tienen que poder
        # ganarle a los documentos base.
        docs = DOCS + [("Mi manual propio", "El tornillo métrico M8 se ajusta a 25 newton metro. " * 40)]
        seleccion = select_relevant_docs("¿a cuánto ajusto el tornillo métrico?", docs, max_chars=600)
        assert seleccion[0][0] == "Mi manual propio"
