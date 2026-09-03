"""Pruebas del ranking BM25.

BM25 no reemplaza al TF-IDF: convive con el para poder medir la diferencia.
Expone la misma interfaz que `doc_selector`, asi que la evaluacion puede
correr el mismo set de preguntas contra los dos y comparar numeros en vez de
cambiar por corazonada.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bm25 import K1, B, rank_documents, select_relevant_docs

DOCS = [
    ("Politica de licencias", "Las vacaciones se comunican con sesenta dias de anticipacion. " * 3),
    ("Lista de precios", "Yerba Rosamonte precio bulto proveedor Rosamonte. " * 3),
    ("Procedimiento de facturas", "La factura A genera credito fiscal computable. " * 3),
]


class TestParametros:
    """Los parametros estandar de BM25, explicitos y no magicos."""

    def test_k1_esta_en_el_rango_habitual(self):
        assert 1.2 <= K1 <= 2.0

    def test_b_esta_en_el_rango_habitual(self):
        assert 0.0 <= B <= 1.0


class TestRanking:
    def test_devuelve_todos_los_documentos_puntuados(self):
        resultado = rank_documents("vacaciones", DOCS)
        assert len(resultado) == len(DOCS)
        assert all(len(item) == 3 for item in resultado)

    def test_el_documento_del_tema_queda_primero(self):
        primero = rank_documents("cuantos dias de vacaciones me avisan", DOCS)[0]
        assert primero[0] == "Politica de licencias"

    def test_otra_pregunta_trae_otro_documento(self):
        primero = rank_documents("cuanto sale la yerba", DOCS)[0]
        assert primero[0] == "Lista de precios"

    def test_los_terminos_del_titulo_pesan(self):
        # "facturas" solo aparece en el titulo del tercer documento.
        primero = rank_documents("facturas", DOCS)[0]
        assert primero[0] == "Procedimiento de facturas"

    def test_una_pregunta_sin_coincidencias_no_rompe(self):
        resultado = rank_documents("elefantes rosados en bicicleta", DOCS)
        assert len(resultado) == len(DOCS)
        assert all(score == 0.0 for _, _, score in resultado)

    def test_los_empates_conservan_el_orden_original(self):
        resultado = rank_documents("xyzabc", DOCS)
        assert [nombre for nombre, _, _ in resultado] == [nombre for nombre, _ in DOCS]

    def test_una_lista_vacia_devuelve_vacio(self):
        assert rank_documents("lo que sea", []) == []


class TestSaturacionDeFrecuencia:
    """Lo que distingue a BM25 de TF-IDF y justifica el cambio."""

    def test_repetir_un_termino_no_multiplica_el_puntaje(self):
        # En TF-IDF puro, un termino cien veces vale mucho mas que una vez.
        # BM25 satura: el aporte marginal cae rapido.
        una_vez = [("doc", "yerba contenido de relleno para dar largo al documento")]
        cien_veces = [("doc", "yerba " * 100 + "contenido de relleno para dar largo al documento")]
        score_una = rank_documents("yerba", una_vez)[0][2]
        score_cien = rank_documents("yerba", cien_veces)[0][2]
        assert score_cien < score_una * 4, "el puntaje deberia saturar, no crecer linealmente"

    def test_penaliza_los_documentos_largos(self):
        # A misma cantidad de coincidencias, el documento corto es mas
        # relevante: la coincidencia representa una porcion mayor del texto.
        docs = [
            ("corto", "yerba mate"),
            ("largo", "yerba mate " + "palabras de relleno sin relacion alguna " * 50),
        ]
        assert rank_documents("yerba", docs)[0][0] == "corto"


class TestSeleccion:
    def test_si_todo_entra_no_descarta_nada(self):
        assert len(select_relevant_docs("vacaciones", DOCS, max_chars=100_000)) == len(DOCS)

    def test_respeta_el_presupuesto(self):
        seleccion = select_relevant_docs("vacaciones", DOCS, max_chars=200)
        assert sum(len(texto) for _, texto in seleccion) <= 200 or len(seleccion) == 1

    def test_el_mas_relevante_entra_siempre(self):
        # Aunque haya que recortarlo: devolver vacio dejaria al agente sin fuente.
        seleccion = select_relevant_docs("vacaciones anticipacion", DOCS, max_chars=50)
        assert len(seleccion) >= 1
        assert seleccion[0][0] == "Politica de licencias"

    def test_una_lista_vacia_devuelve_vacio(self):
        assert select_relevant_docs("lo que sea", [], max_chars=1000) == []
