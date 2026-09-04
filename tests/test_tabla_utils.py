"""Pruebas de la lectura de datos tabulares.

Los fixtures no son sinteticos: reproducen lo que exporta Excel en una PyME
argentina, que es separador `;`, encoding cp1252 y decimales con coma. Ese
es el caso por defecto de este producto, no el caso borde.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tabla_utils import Tabla, _celda, leer_csv, renderizar

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _leer(nombre: str) -> Tabla:
    archivo = FIXTURES / nombre
    return leer_csv(archivo.read_bytes(), archivo.name)


class TestLecturaDeCsvArgentino:
    """El caso que trae un cliente real, no el del tutorial."""

    def test_detecta_el_separador_punto_y_coma(self):
        tabla = _leer("precios_es_ar.csv")
        assert tabla.columnas == ["SKU", "Producto", "Proveedor", "Precio"]

    def test_detecta_el_encoding_cp1252(self):
        # Si se leyera como UTF-8, "Azúcar" vendria roto o reventaria.
        tabla = _leer("precios_es_ar.csv")
        productos = [fila[1] for fila in tabla.filas]
        assert "Azúcar Ledesma 1kg" in productos
        assert "Café La Virginia 500g" in productos

    def test_lee_todas_las_filas(self):
        assert len(_leer("precios_es_ar.csv").filas) == 4

    def test_conserva_los_decimales_con_coma(self):
        # Leyendo como texto, 4350,50 nunca se convierte en 4350.5.
        tabla = _leer("precios_es_ar.csv")
        precios = [fila[3] for fila in tabla.filas]
        assert "4350,50" in precios
        assert "1890,00" in precios

    def test_tambien_lee_el_csv_internacional(self):
        # Coma como separador y UTF-8: no se rompe el caso comun.
        tabla = _leer("precios_utf8.csv")
        assert tabla.columnas == ["SKU", "Producto", "Proveedor", "Precio"]
        assert len(tabla.filas) == 2


class TestCabeceraDecorativa:
    """Una planilla de PyME tiene el nombre de la empresa arriba de la tabla."""

    def test_descarta_el_titulo_y_la_fecha_previos(self):
        tabla = _leer("con_cabecera_decorativa.csv")
        assert tabla.columnas == ["SKU", "Producto", "Precio"]

    def test_no_toma_el_titulo_como_si_fuera_una_fila(self):
        tabla = _leer("con_cabecera_decorativa.csv")
        primeras_celdas = [fila[0] for fila in tabla.filas]
        assert "DISTRIBUIDORA PAMPA SUREÑA" not in primeras_celdas
        assert len(tabla.filas) == 2


class TestArchivosDegenerados:
    """Ninguno de estos puede reventar: llegan de usuarios reales."""

    def test_un_archivo_vacio_no_lanza_excepcion(self):
        tabla = _leer("vacio.csv")
        assert tabla.filas == []

    def test_un_archivo_solo_con_encabezado_no_lanza_excepcion(self):
        tabla = _leer("solo_encabezado.csv")
        assert tabla.columnas == ["SKU", "Producto", "Precio"]
        assert tabla.filas == []


class TestRenderizado:
    """El texto que finalmente ve el modelo."""

    def test_incluye_el_nombre_de_la_tabla(self):
        tabla = _leer("precios_es_ar.csv")
        texto = renderizar(tabla, tabla.filas)
        assert texto.startswith("Tabla: precios_es_ar.csv")

    def test_declara_las_columnas_y_el_total_de_filas(self):
        tabla = _leer("precios_es_ar.csv")
        texto = renderizar(tabla, tabla.filas)
        assert "Columnas: SKU, Producto, Proveedor, Precio (4 filas)" in texto

    def test_el_total_es_el_de_la_tabla_no_el_de_las_filas_mostradas(self):
        # Al reducir una tabla grande, el modelo tiene que saber que esta
        # viendo un subconjunto, no la planilla entera.
        tabla = _leer("precios_es_ar.csv")
        texto = renderizar(tabla, tabla.filas[:1])
        assert "(4 filas)" in texto

    def test_emite_una_tabla_markdown(self):
        tabla = _leer("precios_es_ar.csv")
        texto = renderizar(tabla, tabla.filas)
        assert "| SKU | Producto | Proveedor | Precio |" in texto
        assert "| --- | --- | --- | --- |" in texto
        assert "| 4018 | Yerba Playadito 1kg | Mate SA | 4350,50 |" in texto

    def test_emite_exactamente_las_filas_que_recibe(self):
        tabla = _leer("precios_es_ar.csv")
        texto = renderizar(tabla, tabla.filas[:2])
        assert "4018" in texto
        assert "4021" in texto
        assert "4035" not in texto

    def test_sin_filas_lo_dice_explicitamente(self):
        # Esta frase es la que le permite al agente responder algo util y
        # verdadero: "tengo la lista, no encuentro el articulo".
        tabla = _leer("precios_es_ar.csv")
        texto = renderizar(tabla, [])
        assert "Sin filas que coincidan con la consulta." in texto

    def test_sin_filas_no_emite_ninguna_fila_de_datos(self):
        # La garantia central: nunca datos con forma de respuesta valida
        # cuando no hubo coincidencia.
        tabla = _leer("precios_es_ar.csv")
        texto = renderizar(tabla, [])
        for sku in ("4018", "4021", "4035", "4102"):
            assert sku not in texto

    def test_escapa_el_caracter_de_pipe_en_las_celdas(self):
        # Sin escape, una celda con | rompe la tabla markdown y corre las
        # columnas de lugar.
        tabla = _leer("con_pipes.csv")
        texto = renderizar(tabla, tabla.filas)
        assert r"alto \| ancho" in texto


class TestCelda:
    """La unica salida de pandas: todo cruza como str."""

    def test_convierte_a_texto(self):
        assert _celda("hola") == "hola"
        assert _celda(42) == "42"

    def test_recorta_espacios_sobrantes(self):
        assert _celda("  hola  ") == "hola"

    def test_un_valor_nulo_queda_como_cadena_vacia(self):
        assert _celda(None) == ""
