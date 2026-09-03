"""Ranking BM25, alternativa medible al TF-IDF de `doc_selector`.

No lo reemplaza: convive con el. La decision de que recuperador usar tiene
que salir de numeros sobre el corpus real, no de que BM25 sea el estandar.
Por eso este modulo expone la misma interfaz que `doc_selector` y la
evaluacion corre el mismo set de preguntas contra los dos.

Que aporta BM25 sobre TF-IDF, y por que la literatura que respalda la
recuperacion lexica sin base vectorial habla de BM25 y no de su antecesor:

1. **Saturacion de frecuencia.** En TF-IDF un termino que aparece cien veces
   suma mucho mas que uno que aparece una vez. BM25 satura ese aporte: la
   diferencia entre una y dos apariciones importa, entre noventa y cien no.

2. **Normalizacion por longitud.** A igual cantidad de coincidencias, un
   documento corto es mas relevante que uno largo, porque la coincidencia
   representa una porcion mayor de su contenido. TF-IDF no lo contempla.

Se reutilizan el tokenizador y el stemmer de `doc_selector` a proposito: si
cada recuperador tokenizara distinto, la comparacion mediria dos cosas a la
vez y no serviria para decidir nada.
"""

import math
from collections import Counter

from doc_selector import _TITLE_WEIGHT, MAX_CONTEXT_CHARS, _tokens
from pdf_utils import Document

# Un documento puntuado: (nombre, texto, score de relevancia).
type ScoredDocument = tuple[str, str, float]

# Parametros estandar de BM25. k1 controla que tan rapido satura la frecuencia
# de un termino; b, cuanto pesa la normalizacion por longitud (0 la desactiva,
# 1 la aplica por completo). Estos son los valores de referencia de la
# literatura y el punto de partida razonable sin datos para calibrarlos.
K1 = 1.5
B = 0.75


def _idf(n_docs: int, frecuencia_documental: int) -> float:
    """IDF de BM25, con el suavizado que evita valores negativos.

    La formula clasica se vuelve negativa cuando un termino aparece en mas de
    la mitad de los documentos. El +1 dentro del logaritmo lo impide: un
    termino omnipresente vale poco, pero nunca resta.
    """
    return math.log(1 + (n_docs - frecuencia_documental + 0.5) / (frecuencia_documental + 0.5))


def rank_documents(question: str, docs: list[Document]) -> list[ScoredDocument]:
    """Ordena los documentos por relevancia BM25 contra la pregunta.

    Los empates conservan el orden original, igual que en `doc_selector`.
    """
    if not docs:
        return []

    cuerpos = [Counter(_tokens(texto)) for _, texto in docs]
    titulos = [set(_tokens(nombre)) for nombre, _ in docs]
    largos = [sum(cuerpo.values()) for cuerpo in cuerpos]
    largo_promedio = sum(largos) / len(largos) if any(largos) else 1.0

    frecuencia_documental: Counter[str] = Counter()
    for cuerpo, titulo in zip(cuerpos, titulos, strict=True):
        for termino in set(cuerpo) | titulo:
            frecuencia_documental[termino] += 1

    terminos = set(_tokens(question))
    puntuados: list[ScoredDocument] = []
    for i, (nombre, texto) in enumerate(docs):
        total = 0.0
        for termino in terminos:
            df = frecuencia_documental.get(termino, 0)
            if not df:
                continue
            idf = _idf(len(docs), df)
            if termino in titulos[i]:
                total += idf * _TITLE_WEIGHT
            frecuencia = cuerpos[i].get(termino, 0)
            if frecuencia:
                normalizacion = 1 - B + B * (largos[i] / largo_promedio)
                total += idf * (frecuencia * (K1 + 1)) / (frecuencia + K1 * normalizacion)
        puntuados.append((nombre, texto, total))

    return sorted(puntuados, key=lambda item: item[2], reverse=True)


def select_relevant_docs(
    question: str, docs: list[Document], max_chars: int = MAX_CONTEXT_CHARS
) -> list[Document]:
    """Devuelve los documentos mas relevantes que entren en el presupuesto.

    Misma politica que `doc_selector.select_relevant_docs`, para que la
    comparacion aisle el ranking y no la estrategia de seleccion.
    """
    if not docs:
        return []

    if sum(len(texto) for _, texto in docs) <= max_chars:
        return list(docs)

    seleccionados: list[Document] = []
    usados = 0
    for nombre, texto, _ in rank_documents(question, docs):
        if not seleccionados:
            # El mas relevante entra siempre, aunque haya que recortarlo:
            # devolver la lista vacia dejaria al agente sin ninguna fuente.
            recortado = texto[:max_chars]
            seleccionados.append((nombre, recortado))
            usados = len(recortado)
            continue
        if usados + len(texto) > max_chars:
            continue
        seleccionados.append((nombre, texto))
        usados += len(texto)
    return seleccionados
