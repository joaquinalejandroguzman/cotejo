"""Corre la evaluación del agente sobre el corpus de Distribuidora Pampa Sureña.

Mide dos cosas distintas, y la distinción importa:

**Recuperación.** ¿El sistema trajo el documento que contiene la respuesta?
Es determinista, no cuesta nada, no consume cuota y corre en milisegundos.
Cada pregunta declara qué documento la responde, así que se puede verificar
sin ningún juicio subjetivo. Es también donde se compara TF-IDF contra BM25:
la única forma honesta de decidir entre dos recuperadores es medirlos sobre
el corpus real.

**Respuesta.** ¿Lo que contestó el modelo contiene el hecho correcto? Requiere
llamar a la API, cuesta cuota y es más lento, así que corre solo cuando se
pide con --con-llm. La cuota gratuita de Groq se agota rápido con un corpus
de este tamaño, de ahí la pausa entre consultas.

Uso:
    python evaluacion/ejecutar.py                 # solo recuperación
    python evaluacion/ejecutar.py --con-llm       # además pregunta al modelo
    python evaluacion/ejecutar.py --con-llm --limite 10
"""

import argparse
import json
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import bm25  # noqa: E402
import doc_selector  # noqa: E402
from ingesta import extraer_documentos  # noqa: E402
from pdf_utils import Document, combine_documents  # noqa: E402

PREGUNTAS = Path(__file__).resolve().parent / "preguntas.json"

# Pausa entre consultas al modelo. La cuota gratuita de Groq se mide en tokens
# por minuto, y un corpus de 46.000 caracteres la agota en pocas preguntas.
PAUSA_SEGUNDOS = 25

RECUPERADORES = {"tfidf": doc_selector, "bm25": bm25}


@dataclass
class Resultado:
    id: str
    categoria: str
    recuperado: bool
    posicion: int | None
    trajo: tuple[str, ...] = ()
    respuesta_correcta: bool | None = None
    respuesta: str = ""


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar hechos sin falsos negativos."""
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def cargar_corpus(directorio: Path) -> list[Document]:
    docs: list[Document] = []
    for archivo in sorted(directorio.iterdir()):
        if archivo.is_file():
            docs.extend(extraer_documentos(archivo.name, archivo.read_bytes()))
    return docs


def evaluar_recuperacion(
    recuperador, pregunta: dict, docs: list[Document]
) -> tuple[bool, int | None, tuple[str, ...]]:
    """¿Se trajo el documento que contiene la respuesta, y en qué posición?

    Devuelve además qué documentos se trajeron, que es lo que permite
    diagnosticar un fallo en vez de solo contarlo.
    """
    seleccion = recuperador.select_relevant_docs(pregunta["pregunta"], docs)
    nombres = tuple(nombre for nombre, _ in seleccion)
    esperado = pregunta["documento"]
    if esperado not in nombres:
        return False, None, nombres
    return True, nombres.index(esperado) + 1, nombres


def evaluar_respuesta(
    pregunta: dict, docs: list[Document], recuperador, api_key: str
) -> tuple[bool, str]:
    """¿La respuesta del modelo contiene los hechos esperados?"""
    from groq_client import GroqError, chat

    seleccion = recuperador.select_relevant_docs(pregunta["pregunta"], docs)
    sistema = (
        "Sos el asistente interno de Distribuidora Pampa Sureña. Respondés únicamente "
        "con la información de la documentación de abajo. Si no está, decís que no "
        "la encontrás. Nunca inventes datos.\n\n" + combine_documents(seleccion)
    )
    try:
        respuesta = chat(
            [
                {"role": "system", "content": sistema},
                {"role": "user", "content": pregunta["pregunta"]},
            ],
            api_key=api_key,
        )
    except GroqError as e:
        return False, f"[error: {e}]"

    normalizada = _normalizar(respuesta)
    if pregunta.get("sin_respuesta"):
        # La respuesta correcta es admitir que no está. Se considera correcta
        # si dice que no lo encuentra y no inventa un precio.
        admite = any(f in normalizada for f in ("no encuentro", "no figura", "no esta", "no tengo"))
        return admite, respuesta
    hechos = [_normalizar(h) for h in pregunta["hechos"]]
    return all(h in normalizada for h in hechos), respuesta


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluación de Cotejo sobre el corpus de demostración"
    )
    parser.add_argument(
        "--con-llm", action="store_true", help="además de recuperar, preguntarle al modelo"
    )
    parser.add_argument(
        "--limite", type=int, default=0, help="evaluar solo las primeras N preguntas"
    )
    parser.add_argument("--recuperador", choices=[*RECUPERADORES, "ambos"], default="ambos")
    args = parser.parse_args()

    datos = json.loads(PREGUNTAS.read_text(encoding="utf-8"))
    preguntas = datos["preguntas"]
    if args.limite:
        preguntas = preguntas[: args.limite]

    docs = cargar_corpus(RAIZ / datos["corpus"])
    total_chars = sum(len(t) for _, t in docs)
    print(f"Corpus: {len(docs)} documentos, {total_chars:,} caracteres")
    print(f"Preguntas: {len(preguntas)}")
    print(f"Presupuesto de contexto: {doc_selector.MAX_CONTEXT_CHARS:,} caracteres\n")
    for nombre, texto in sorted(docs, key=lambda d: -len(d[1])):
        proporcion = len(texto) / doc_selector.MAX_CONTEXT_CHARS
        alerta = "  <-- no entra con ningun otro" if proporcion > 0.9 else ""
        print(f"  {nombre:<30} {len(texto):>7,}  ({proporcion:.0%} del presupuesto){alerta}")
    print()

    elegidos = list(RECUPERADORES) if args.recuperador == "ambos" else [args.recuperador]
    resultados: dict[str, list[Resultado]] = {}

    for nombre in elegidos:
        recuperador = RECUPERADORES[nombre]
        acumulado = []
        for p in preguntas:
            ok, pos, trajo = evaluar_recuperacion(recuperador, p, docs)
            acumulado.append(Resultado(p["id"], p["categoria"], ok, pos, trajo))
        resultados[nombre] = acumulado

    _informe_recuperacion(resultados, preguntas)

    if args.con_llm:
        import os

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("\nFalta GROQ_API_KEY en el entorno.")
            return 1
        mejor = max(resultados, key=lambda n: sum(r.recuperado for r in resultados[n]))
        print(f"\n{'=' * 72}\nRESPUESTA DEL MODELO (recuperador: {mejor})\n{'=' * 72}")
        print(f"Pausa de {PAUSA_SEGUNDOS}s entre consultas para no agotar la cuota gratuita.\n")
        _informe_respuestas(preguntas, docs, RECUPERADORES[mejor], api_key)

    return 0


def _informe_recuperacion(resultados: dict[str, list[Resultado]], preguntas: list[dict]) -> None:
    print("=" * 72)
    print("RECUPERACIÓN — ¿se trajo el documento que contiene la respuesta?")
    print("=" * 72)

    for nombre, rs in resultados.items():
        aciertos = sum(r.recuperado for r in rs)
        primeros = sum(1 for r in rs if r.posicion == 1)
        print(
            f"\n{nombre:>6}   {aciertos}/{len(rs)} recuperados ({aciertos / len(rs):.0%})"
            f"   |   primero en el ranking: {primeros} ({primeros / len(rs):.0%})"
        )

    categorias = sorted({p["categoria"] for p in preguntas})
    print(f"\n{'categoría':<14}" + "".join(f"{n:>10}" for n in resultados))
    for cat in categorias:
        fila = f"{cat:<14}"
        for rs in resultados.values():
            de_cat = [r for r in rs if r.categoria == cat]
            fila += f"{sum(r.recuperado for r in de_cat)}/{len(de_cat):<8}".rjust(10)
        print(fila)

    por_id = {p["id"]: p for p in preguntas}
    for nombre, rs in resultados.items():
        fallos = [r for r in rs if not r.recuperado]
        if not fallos:
            continue
        print(f"\n{nombre} no recuperó el documento correcto en:")
        for r in fallos:
            p = por_id[r.id]
            print(f"   {r.id}  {p['pregunta']}")
            print(f"          esperaba {p['documento']} — trajo {', '.join(r.trajo)}")


def _informe_respuestas(
    preguntas: list[dict], docs: list[Document], recuperador, api_key: str
) -> None:
    correctas = 0
    for i, p in enumerate(preguntas):
        if i:
            time.sleep(PAUSA_SEGUNDOS)
        ok, respuesta = evaluar_respuesta(p, docs, recuperador, api_key)
        correctas += ok
        marca = "OK  " if ok else "FALLA"
        print(f"{marca} {p['id']}  {p['pregunta']}")
        print(f"      {respuesta[:160].replace(chr(10), ' ')}")
        if not ok and p.get("hechos"):
            print(f"      esperaba: {', '.join(p['hechos'])}")
        print()
    print(f"Respuestas correctas: {correctas}/{len(preguntas)} ({correctas / len(preguntas):.0%})")


if __name__ == "__main__":
    raise SystemExit(main())
