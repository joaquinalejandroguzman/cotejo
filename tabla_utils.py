"""Lectura de datos tabulares y su conversion a texto para el modelo.

Este es el unico modulo que importa pandas. La frontera es deliberada: pandas
no trae `py.typed`, asi que todos sus simbolos son `Any`, y mypy en modo
estricto convierte en error devolver una expresion suya desde una funcion
anotada. Ningun valor sale de aca sin pasar por `_celda`, que lo coacciona a
`str`.

Esa misma decision resuelve los decimales con coma: leyendo todo como texto,
"4350,50" nunca se parsea a float ni se re-renderiza como "4350.5". El alcance
de la garantia es honesto — una celda que la planilla ya guardo como numero
binario perdio la coma en origen y no hay nada que preservar.
"""

import csv
import io
from collections import Counter
from dataclasses import dataclass

import pandas as pd

# Encodings a probar, en orden. utf-8-sig primero porque las versiones
# modernas de Excel guardan UTF-8 con BOM; cp1252 despues porque es lo que
# exporta Excel en configuracion regional argentina. latin-1 cierra la lista
# como red de seguridad: es de un byte por caracter, asi que nunca falla.
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252")

# Separadores candidatos. El ';' va primero porque en es-AR es el default de
# Excel, justamente para no chocar con la coma decimal.
_SEPARADORES = ";,\t|"


@dataclass(frozen=True)
class Tabla:
    """Una tabla ya leida, con todo su contenido como texto."""

    nombre: str
    columnas: list[str]
    filas: list[list[str]]


def _celda(valor: object) -> str:
    """Coacciona un valor a texto. Es la unica salida de pandas."""
    if valor is None:
        return ""
    return str(valor).strip()


def _decodificar(datos: bytes) -> str:
    """Decodifica los bytes probando los encodings en orden."""
    for encoding in _ENCODINGS:
        try:
            return datos.decode(encoding)
        except UnicodeDecodeError:
            continue
    # latin-1 mapea cualquier byte a un caracter, asi que no puede fallar.
    # Puede dar mojibake, pero es preferible a perder el archivo entero.
    return datos.decode("latin-1")


def _detectar_separador(texto: str) -> str:
    """Deduce el separador mirando las primeras lineas con contenido."""
    lineas = [linea for linea in texto.splitlines() if linea.strip()]
    if not lineas:
        return ","
    muestra = "\n".join(lineas[:20])
    try:
        return csv.Sniffer().sniff(muestra, delimiters=_SEPARADORES).delimiter
    except csv.Error:
        # Sin pistas suficientes: gana el separador mas frecuente, y la coma
        # como ultimo recurso.
        conteos = {sep: muestra.count(sep) for sep in _SEPARADORES}
        mejor = max(conteos, key=lambda s: conteos[s])
        return mejor if conteos[mejor] else ","


def _fila_de_encabezado(filas: list[list[str]]) -> int:
    """Ubica la fila que realmente encabeza la tabla.

    Las planillas armadas a mano suelen traer el nombre de la empresa, una
    fecha y alguna linea en blanco antes de los encabezados de verdad. Esas
    lineas decorativas ocupan menos columnas que la tabla, asi que el ancho
    mas repetido identifica a la tabla y la primera fila que lo alcanza es
    el encabezado.
    """
    con_contenido = [(i, f) for i, f in enumerate(filas) if any(c.strip() for c in f)]
    if not con_contenido:
        return 0
    anchos = Counter(len(f) for _, f in con_contenido)
    ancho_tabla = anchos.most_common(1)[0][0]
    for i, fila in con_contenido:
        if len(fila) == ancho_tabla:
            return i
    return con_contenido[0][0]


def leer_csv(datos: bytes, nombre: str) -> Tabla:
    """Lee un CSV y devuelve su contenido como texto, sin interpretar tipos."""
    texto = _decodificar(datos)
    if not texto.strip():
        return Tabla(nombre=nombre, columnas=[], filas=[])

    separador = _detectar_separador(texto)
    crudas = list(csv.reader(io.StringIO(texto), delimiter=separador))
    inicio = _fila_de_encabezado(crudas)

    marco = pd.read_csv(
        io.StringIO(texto),
        sep=separador,
        skiprows=inicio,
        header=0,
        dtype=str,
        keep_default_na=False,
        skip_blank_lines=True,
        engine="python",
    )

    columnas = [_celda(c) for c in marco.columns]
    filas = [[_celda(v) for v in registro] for registro in marco.itertuples(index=False)]
    return Tabla(nombre=nombre, columnas=columnas, filas=filas)


def _escapar(celda: str) -> str:
    """Escapa el caracter que separa columnas en el renderizado."""
    return celda.replace("|", r"\|")


def renderizar(tabla: Tabla, filas: list[list[str]]) -> str:
    """Convierte una tabla en el texto que se le manda al modelo.

    El encabezado declara siempre el total de filas de la tabla completa,
    aunque se muestren menos: el modelo tiene que saber que esta viendo un
    subconjunto y no la planilla entera.

    Emite exactamente las filas que recibe. No existe ninguna rama que
    complete el espacio sobrante con filas adicionales — cuando no hubo
    coincidencias, se lo dice en palabras. Mostrar filas irrelevantes con
    forma de respuesta valida es lo que hace que un modelo conteste con el
    precio de otro articulo.
    """
    encabezado = [
        f"Tabla: {tabla.nombre}",
        f"Columnas: {', '.join(tabla.columnas)} ({len(tabla.filas)} filas)",
    ]
    if not filas:
        return "\n".join([*encabezado, "", "Sin filas que coincidan con la consulta."])

    cuerpo = [
        "| " + " | ".join(_escapar(c) for c in tabla.columnas) + " |",
        "| " + " | ".join("---" for _ in tabla.columnas) + " |",
    ]
    cuerpo += ["| " + " | ".join(_escapar(c) for c in fila) + " |" for fila in filas]
    return "\n".join([*encabezado, "", *cuerpo])
