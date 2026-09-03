"""Genera el corpus de demostracion de Distribuidora Pampa Sur.

El corpus se versiona ya generado, pero este script queda en el repositorio
para que cualquiera pueda auditar de donde sale cada dato y regenerarlo.

Las estructuras y los datos no son inventados. Salen de una investigacion
contra fuentes primarias: la especificacion del SEPA para las columnas de una
lista mayorista, un catalogo mayorista real de abril de 2026 para los precios,
y el texto de la Ley de Contrato de Trabajo y del CCT 130/75 para las
licencias. Los precios de abril se proyectaron a septiembre con el IPC del
INDEC.

Una decision deliberada: los documentos NO estan todos actualizados a la
misma fecha. El reglamento interno esta fechado en 2022 y todavia habla de
"AFIP" y de un preaviso de vacaciones de 45 dias, que era el texto vigente
entonces. En una PyME real los documentos se actualizan de a uno y quedan
desfasados entre si. Esa inconsistencia es intencional: reproduce como es un
corpus de verdad, y ademas genera los casos de evaluacion mas interesantes,
donde la respuesta correcta esta en un documento y una respuesta plausible
pero equivocada esta en otro.

Uso:
    python scripts/generar_corpus.py
"""

import csv
import io
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "corpus" / "pampa-sur"

# Encoding con el que Excel exporta en configuracion regional argentina.
# El corpus se guarda asi a proposito: es lo que llega de un cliente real.
ENCODING = "cp1252"
SEPARADOR = ";"

EMPRESA = "DISTRIBUIDORA PAMPA SUR S.R.L."
CUIT = "30-71455982-6"
DOMICILIO = "Av. Alem 3450 - Bahía Blanca, Provincia de Buenos Aires"


def escribir_csv(
    nombre: str, columnas: list[str], filas: list[list[str]], preambulo: list[str]
) -> Path:
    """Escribe un CSV con el formato que exporta Excel en es-AR.

    `preambulo` son las lineas decorativas que toda planilla armada a mano
    tiene arriba de la tabla: nombre de la empresa, vigencia, una fila en
    blanco. El lector tiene que saber descartarlas.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=SEPARADOR, lineterminator="\n")
    for linea in preambulo:
        escritor.writerow([linea])
    escritor.writerow([])
    escritor.writerow(columnas)
    escritor.writerows(filas)

    ruta = DESTINO / nombre
    ruta.write_bytes(buffer.getvalue().encode(ENCODING))
    return ruta


def digito_ean(base12: str) -> str:
    """Calcula el digito verificador de un EAN-13.

    Los EAN del corpus tienen que validar: alguien del rubro que cargue un
    codigo en su sistema y vea que lo rechaza, deja de creer el resto.
    """
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return str((10 - suma % 10) % 10)


def ean(base12: str) -> str:
    return base12 + digito_ean(base12)


# Productos con precios reales del catalogo mayorista de abril de 2026,
# proyectados a septiembre con el IPC del INDEC (+10% compuesto). El precio
# es CON IVA y termina en ,90 — es universal en el rubro.
#
# (codigo, base del EAN, descripcion, marca, rubro, un_x_bulto, precio_con_iva, alicuota, proveedor)
PRODUCTOS = [
    # --- Almacen ---
    (
        "4018",
        "779001500101",
        "ARROZ EL DIQUE x 500 gr.",
        "EL DIQUE",
        "Almacen",
        20,
        "494,90",
        "10.5",
        "Molinos del Sur",
    ),
    (
        "4021",
        "779001500102",
        "ARROZ LARGO FINO CAÑUELAS x 500 gr.",
        "CAÑUELAS",
        "Almacen",
        20,
        "659,90",
        "10.5",
        "Molinos del Sur",
    ),
    (
        "4035",
        "779001500103",
        "ARROZ GALLO ORO x 500 gr.",
        "GALLO",
        "Almacen",
        20,
        "934,90",
        "10.5",
        "Molinos Rio de la Plata",
    ),
    (
        "4102",
        "779001500104",
        "FIDEOS MAROLIO GUISERO x 500 gr.",
        "MAROLIO",
        "Almacen",
        20,
        "747,90",
        "21",
        "Marolio SA",
    ),
    (
        "4103",
        "779001500105",
        "FIDEOS MAROLIO TALLARIN x 500 gr.",
        "MAROLIO",
        "Almacen",
        20,
        "747,90",
        "21",
        "Marolio SA",
    ),
    (
        "4118-4119-4120",
        "779001500106",
        "FIDEOS DON VICENTE MOÑO / CODITO / TIRABUZON x 500 gr.",
        "DON VICENTE",
        "Almacen",
        20,
        "2419,90",
        "21",
        "Molinos Rio de la Plata",
    ),
    (
        "4201",
        "779001500107",
        "HARINA PUREZA 0000 x 1 kg.",
        "PUREZA",
        "Almacen",
        10,
        "1055,90",
        "10.5",
        "Molinos Rio de la Plata",
    ),
    (
        "4202",
        "779001500108",
        "HARINA LEUDANTE BLANCAFLOR x 1 kg.",
        "BLANCAFLOR",
        "Almacen",
        10,
        "1188,90",
        "10.5",
        "Molinos Rio de la Plata",
    ),
    (
        "4310",
        "779001500109",
        "GARBANZOS MAROLIO x 400 gr.",
        "MAROLIO",
        "Almacen",
        24,
        "1099,90",
        "21",
        "Marolio SA",
    ),
    (
        "4311",
        "779001500110",
        "LENTEJAS MAROLIO x 400 gr.",
        "MAROLIO",
        "Almacen",
        24,
        "1099,90",
        "21",
        "Marolio SA",
    ),
    (
        "4312",
        "779001500111",
        "ARVEJAS MAROLIO x 350 gr.",
        "MAROLIO",
        "Almacen",
        24,
        "879,90",
        "21",
        "Marolio SA",
    ),
    (
        "4405",
        "779001500112",
        "ACEITE GIRASOL CAÑUELAS-COCINERO x 900 cc.",
        "COCINERO",
        "Almacen",
        12,
        "3189,90",
        "21",
        "Molinos del Sur",
    ),
    (
        "4406",
        "779001500113",
        "ACEITE MEZCLA NATURA x 900 cc.",
        "NATURA",
        "Almacen",
        12,
        "3849,90",
        "21",
        "AGD",
    ),
    (
        "4501",
        "779001500114",
        "AZUCAR LEDESMA x 1 kg.",
        "LEDESMA",
        "Almacen",
        10,
        "1424,90",
        "21",
        "Ledesma SAAI",
    ),
    (
        "4610",
        "779001500115",
        "PURE DE TOMATE ARCOR x 520 gr.",
        "ARCOR",
        "Almacen",
        12,
        "1034,90",
        "21",
        "Arcor",
    ),
    (
        "4611",
        "779001500116",
        "ARVEJAS AL NATURAL ARCOR x 350 gr.",
        "ARCOR",
        "Almacen",
        24,
        "989,90",
        "21",
        "Arcor",
    ),
    (
        "4620",
        "779001500117",
        "ATUN AL ACEITE GOMES DA COSTA x 170 gr.",
        "GOMES DA COSTA",
        "Almacen",
        24,
        "3079,90",
        "21",
        "Gomes da Costa",
    ),
    (
        "4701",
        "779001500118",
        "MERM. DE DURAZNO ARCOR x 454 gr.",
        "ARCOR",
        "Almacen",
        12,
        "1869,90",
        "21",
        "Arcor",
    ),
    (
        "4702",
        "779001500119",
        "D.LECHE LA SERENISIMA x 400 gr.",
        "LA SERENISIMA",
        "Almacen",
        12,
        "2529,90",
        "21",
        "Mastellone",
    ),
    (
        "4801",
        "779001500120",
        "YERBA ROSAMONTE TRAD-SUAVE x 1 kg.",
        "ROSAMONTE",
        "Almacen",
        10,
        "2859,90",
        "21",
        "Rosamonte",
    ),
    (
        "4802",
        "779001500121",
        "YERBA PLAYADITO x 1 kg.",
        "PLAYADITO",
        "Almacen",
        10,
        "2749,90",
        "21",
        "Coop. Liebig",
    ),
    (
        "4803",
        "779001500122",
        "YERBA TARAGUI x 500 gr.",
        "TARAGUI",
        "Almacen",
        20,
        "1704,90",
        "21",
        "Establecimiento Las Marias",
    ),
    (
        "4810",
        "779001500123",
        "TE GREEN HILLS x 25 saq.",
        "GREEN HILLS",
        "Almacen",
        24,
        "1319,90",
        "21",
        "Molinos Rio de la Plata",
    ),
    (
        "4901",
        "779001500124",
        "CACAO TODDY x 180 gr.",
        "TODDY",
        "Almacen",
        24,
        "1374,90",
        "21",
        "PepsiCo",
    ),
    (
        "4902",
        "779001500125",
        "CACAO NESQUIK x 180 gr.",
        "NESQUIK",
        "Almacen",
        24,
        "1759,90",
        "21",
        "Nestle",
    ),
    (
        "4910",
        "779001500126",
        "CAFE LA VIRGINIA MOLIDO x 500 gr.",
        "LA VIRGINIA",
        "Almacen",
        12,
        "7975,90",
        "21",
        "La Virginia",
    ),
    (
        "5001-5002",
        "779001500127",
        "GALLETITAS LIA SURTIDO / VAINILLA x 400 gr.",
        "LIA",
        "Almacen",
        18,
        "1649,90",
        "21",
        "Arcor",
    ),
    (
        "5010",
        "779001500128",
        "GALLETITAS MAROLIO SANDWICH x 303 gr.",
        "MAROLIO",
        "Almacen",
        24,
        "1109,90",
        "21",
        "Marolio SA",
    ),
    (
        "5020",
        "779001500129",
        "GALLETITAS CRIOLLITAS x 300 gr.",
        "CRIOLLITAS",
        "Almacen",
        24,
        "1594,90",
        "21",
        "Mondelez",
    ),
    (
        "5030",
        "779001500130",
        "BIZCOCHOS DON SATUR x 200 gr.",
        "DON SATUR",
        "Almacen",
        24,
        "1264,90",
        "21",
        "Don Satur",
    ),
    (
        "5101",
        "779001500131",
        "SAL FINA CELUSAL x 500 gr.",
        "CELUSAL",
        "Almacen",
        24,
        "659,90",
        "21",
        "Celusal",
    ),
    (
        "5110",
        "779001500132",
        "VINAGRE DE ALCOHOL MENOYO x 500 cc.",
        "MENOYO",
        "Almacen",
        12,
        "824,90",
        "21",
        "Menoyo",
    ),
    (
        "5120",
        "779001500133",
        "POLENTA PRESTO PRONTA x 500 gr.",
        "PRESTO PRONTA",
        "Almacen",
        20,
        "1154,90",
        "21",
        "Molinos Rio de la Plata",
    ),
    # --- Bebidas ---
    (
        "6010",
        "779001500134",
        "GAS. COCA / SPRITE / FANTA x 354 cc.",
        "COCA COLA",
        "Bebidas",
        24,
        "1374,90",
        "21",
        "Coca Cola Andina",
    ),
    (
        "6011",
        "779001500135",
        "GAS. COCA / SPRITE / FANTA x 1,75 lt",
        "COCA COLA",
        "Bebidas",
        6,
        "3739,90",
        "21",
        "Coca Cola Andina",
    ),
    (
        "6012",
        "779001500136",
        "GAS. COCA Z / SPRITE / FANTA x 2,25 lt ( SOLO AMBA )",
        "COCA COLA",
        "Bebidas",
        6,
        "4399,90",
        "21",
        "Coca Cola Andina",
    ),
    (
        "6020",
        "779001500137",
        "GAS. MANAOS COLA x 2,25 lt",
        "MANAOS",
        "Bebidas",
        6,
        "1869,90",
        "21",
        "Refres Now",
    ),
    (
        "6030",
        "779001500138",
        "AGUA MINERAL GLACIAR x 6,4 lt",
        "GLACIAR",
        "Bebidas",
        2,
        "4289,90",
        "21",
        "Coca Cola Andina",
    ),
    (
        "6031",
        "779001500139",
        "AGUA MINERAL VILLA DEL SUR x 2 lt",
        "VILLA DEL SUR",
        "Bebidas",
        6,
        "1979,90",
        "21",
        "Danone",
    ),
    (
        "6040",
        "779001500140",
        "CERVEZA QUILMES CLASICA x 1 lt retornable",
        "QUILMES",
        "Bebidas",
        12,
        "2529,90",
        "21",
        "CCU",
    ),
    (
        "6041",
        "779001500141",
        "CERVEZA BRAHMA x 473 cc. lata",
        "BRAHMA",
        "Bebidas",
        24,
        "1649,90",
        "21",
        "AB InBev",
    ),
    (
        "6050",
        "779001500142",
        "FERNET 1882 x 750 cc.",
        "1882",
        "Bebidas",
        6,
        "7589,90",
        "21",
        "Porta Hnos",
    ),
    (
        "6051",
        "779001500143",
        "APERITIVO GANCIA x 950 cc.",
        "GANCIA",
        "Bebidas",
        6,
        "6929,90",
        "21",
        "Gancia",
    ),
    (
        "6060",
        "779001500144",
        "JUGO EN POLVO CLIGHT x 8 gr.",
        "CLIGHT",
        "Bebidas",
        20,
        "494,90",
        "21",
        "Mondelez",
    ),
    (
        "6061",
        "779001500145",
        "JUGO BAGGIO MULTIFRUTA x 1 lt",
        "BAGGIO",
        "Bebidas",
        12,
        "1594,90",
        "21",
        "RPB SA",
    ),
    (
        "6070",
        "779001500146",
        "VINO TORO TINTO x 1,25 lt",
        "TORO",
        "Bebidas",
        6,
        "3299,90",
        "21",
        "Peñaflor",
    ),
    # --- Lacteos (cadena de frio) ---
    (
        "7010",
        "779001500147",
        "LECHE LS PET x 1 lt (excepto Comod. Rivadavia y Bariloche)",
        "LA SERENISIMA",
        "Lacteos",
        12,
        "2199,90",
        "21",
        "Mastellone",
    ),
    (
        "7011",
        "779001500148",
        "LECHE EN POLVO NIDO x 400 gr.",
        "NIDO",
        "Lacteos",
        12,
        "6379,90",
        "21",
        "Nestle",
    ),
    (
        "7020",
        "779001500149",
        "YOGHURT LA SERENISIMA BEBIBLE x 190 gr.",
        "LA SERENISIMA",
        "Lacteos",
        24,
        "1209,90",
        "21",
        "Mastellone",
    ),
    (
        "7030",
        "779001500150",
        "QUESO CASANCREM CLASICO x 500 gr.",
        "CASANCREM",
        "Lacteos",
        12,
        "5939,90",
        "21",
        "Mastellone",
    ),
    (
        "7031",
        "779001500151",
        "QUESO CREMOSO x kg.",
        "LA PAULINA",
        "Lacteos",
        1,
        "7899,90",
        "21",
        "Sancor",
    ),
    (
        "7040",
        "779001500152",
        "MANTECA LA SERENISIMA x 200 gr.",
        "LA SERENISIMA",
        "Lacteos",
        24,
        "3629,90",
        "21",
        "Mastellone",
    ),
    # --- Limpieza ---
    (
        "8010",
        "779001500153",
        "LAVANDINA AYUDIN x 2 lt",
        "AYUDIN",
        "Limpieza",
        6,
        "1924,90",
        "21",
        "Clorox",
    ),
    (
        "8011",
        "779001500154",
        "LAVANDINA MAROLIO x 1 lt",
        "MAROLIO",
        "Limpieza",
        12,
        "824,90",
        "21",
        "Marolio SA",
    ),
    (
        "8020",
        "779001500155",
        "DETERGENTE MAGISTRAL x 300 cc.",
        "MAGISTRAL",
        "Limpieza",
        12,
        "2199,90",
        "21",
        "P&G",
    ),
    (
        "8021",
        "779001500156",
        "DETERGENTE ALA x 750 cc.",
        "ALA",
        "Limpieza",
        12,
        "3079,90",
        "21",
        "Unilever",
    ),
    (
        "8030",
        "779001500157",
        "JABON EN POLVO SKIP x 800 gr.",
        "SKIP",
        "Limpieza",
        12,
        "5279,90",
        "21",
        "Unilever",
    ),
    (
        "8031",
        "779001500158",
        "JABON EN POLVO ALA x 400 gr.",
        "ALA",
        "Limpieza",
        20,
        "2419,90",
        "21",
        "Unilever",
    ),
    (
        "8040",
        "779001500159",
        "SUAVIZANTE VIVERE x 900 cc.",
        "VIVERE",
        "Limpieza",
        12,
        "3409,90",
        "21",
        "Unilever",
    ),
    (
        "8050",
        "779001500160",
        "ROLLO DE COCINA SUSSEX 3x50 un.",
        "SUSSEX",
        "Limpieza",
        8,
        "3739,90",
        "21",
        "Papelera del Plata",
    ),
    (
        "8051",
        "779001500161",
        "PAPEL HIGIENICO ELEGANTE x 4 un. 30 mts",
        "ELEGANTE",
        "Limpieza",
        10,
        "2969,90",
        "21",
        "Papelera del Plata",
    ),
    (
        "8060",
        "779001500162",
        "ESPONJA MORTIMER DOBLE USO x 1 un.",
        "MORTIMER",
        "Limpieza",
        24,
        "659,90",
        "21",
        "Mortimer",
    ),
    (
        "8070",
        "779001500163",
        "LIMPIADOR CIF CREMA x 750 cc.",
        "CIF",
        "Limpieza",
        12,
        "3079,90",
        "21",
        "Unilever",
    ),
    # --- Perfumeria ---
    (
        "9010",
        "779001500164",
        "SHAMPOO DOVE x 400 ml.",
        "DOVE",
        "Perfumeria",
        12,
        "5279,90",
        "21",
        "Unilever",
    ),
    (
        "9011",
        "779001500165",
        "SHAMPOO SEDAL x 340 ml.",
        "SEDAL",
        "Perfumeria",
        12,
        "3959,90",
        "21",
        "Unilever",
    ),
    (
        "9020",
        "779001500166",
        "JABON DE TOCADOR LUX x 125 gr.",
        "LUX",
        "Perfumeria",
        24,
        "989,90",
        "21",
        "Unilever",
    ),
    (
        "9030",
        "779001500167",
        "DESODORANTE REXONA AEROSOL x 150 ml.",
        "REXONA",
        "Perfumeria",
        12,
        "4619,90",
        "21",
        "Unilever",
    ),
    (
        "9040",
        "779001500168",
        "PASTA DENTAL COLGATE TRIPLE x 90 gr.",
        "COLGATE",
        "Perfumeria",
        24,
        "2199,90",
        "21",
        "Colgate",
    ),
    (
        "9050-9051",
        "779001500169",
        "PROT. FEMENINA ALWAYS C.ALAS / S/ALAS x 8 un.",
        "ALWAYS",
        "Perfumeria",
        24,
        "2749,90",
        "21",
        "P&G",
    ),
    (
        "9060",
        "779001500170",
        "PAÑALES PAMPERS G x 30 un.",
        "PAMPERS",
        "Perfumeria",
        4,
        "18699,90",
        "21",
        "P&G",
    ),
    # --- Kiosco ---
    (
        "9510",
        "779001500171",
        "ALFAJOR JORGITO x 1 un.",
        "JORGITO",
        "Kiosco",
        60,
        "659,90",
        "21",
        "Jorgito",
    ),
    (
        "9511",
        "779001500172",
        "ALFAJOR GUAYMALLEN x 1 un.",
        "GUAYMALLEN",
        "Kiosco",
        60,
        "494,90",
        "21",
        "Guaymallen",
    ),
    ("9520", "779001500173", "CHUPETIN POP x 1 un.", "POP", "Kiosco", 100, "329,90", "21", "Arcor"),
    (
        "9530",
        "779001500174",
        "CHICLE BELDENT x 10 un.",
        "BELDENT",
        "Kiosco",
        20,
        "989,90",
        "21",
        "Mondelez",
    ),
    (
        "9540",
        "779001500175",
        "PAPAS FRITAS LAYS x 65 gr.",
        "LAYS",
        "Kiosco",
        20,
        "2199,90",
        "21",
        "PepsiCo",
    ),
    (
        "9550",
        "779001500176",
        "TURRON ARCOR x 25 gr.",
        "ARCOR",
        "Kiosco",
        50,
        "384,90",
        "21",
        "Arcor",
    ),
    (
        "9560",
        "779001500177",
        "CHOCOLATE MILKA LECHE x 55 gr.",
        "MILKA",
        "Kiosco",
        24,
        "2419,90",
        "21",
        "Mondelez",
    ),
]


def _sin_iva(precio_con_iva: str, alicuota: str) -> str:
    """Despeja el neto a partir del precio con IVA, en formato argentino."""
    valor = float(precio_con_iva.replace(".", "").replace(",", "."))
    neto = valor / (1 + float(alicuota) / 100)
    return f"{neto:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


# Bonificacion por volumen segun el rubro. En la practica no es uniforme:
# almacen y limpieza bonifican mas que bebidas, donde el margen es fino.
BONIFICACIONES = {
    "Almacen": ("0,00", "3,00", "5,00"),
    "Bebidas": ("0,00", "2,00", "3,50"),
    "Lacteos": ("0,00", "2,00", "3,00"),
    "Limpieza": ("0,00", "3,50", "6,00"),
    "Perfumeria": ("0,00", "4,00", "7,00"),
    "Kiosco": ("0,00", "3,00", "5,00"),
}


def generar_lista_precios() -> Path:
    columnas = [
        "codigo",
        "ean",
        "descripcion",
        "marca",
        "rubro",
        "unidad_venta",
        "unidades_por_bulto",
        "precio_lista_sin_iva",
        "alicuota_iva",
        "precio_lista_con_iva",
        "bonif_1",
        "bonif_2",
        "bonif_3",
        "proveedor",
        "vigencia_desde",
        "estado",
    ]
    filas = []
    for codigo, base_ean, desc, marca, rubro, bulto, con_iva, alicuota, proveedor in PRODUCTOS:
        b1, b2, b3 = BONIFICACIONES[rubro]
        filas.append(
            [
                codigo,
                ean(base_ean),
                desc,
                marca,
                rubro,
                "BULTO" if bulto > 1 else "KG",
                str(bulto),
                _sin_iva(con_iva, alicuota),
                alicuota.replace(".", ","),
                con_iva,
                b1,
                b2,
                b3,
                proveedor,
                "01/09/2026",
                "ACTIVO",
            ]
        )

    preambulo = [
        EMPRESA,
        "LISTA DE PRECIOS N° 48 - Vigencia 01/09/2026 al 15/09/2026",
        "Precios expresados en pesos. Precio unitario valido comprando por bulto cerrado.",
        "Bonif_1: 1 a 4 bultos | Bonif_2: 5 a 19 bultos | Bonif_3: 20 bultos o mas.",
        "Las bonificaciones se aplican en cascada, no se suman.",
        "Los precios no incluyen percepciones de IVA (RG 2408) ni de Ingresos Brutos.",
    ]
    return escribir_csv("lista_precios.csv", columnas, filas, preambulo)


# (codigo, deposito, ubicacion, stock_bultos, comprometido_un, stock_minimo, punto_repos, lote, vencimiento)
STOCK = [
    ("4018", "DEP01", "A-01-1", 145, 120, 800, 1400, "L2608A", "12/2027"),
    ("4021", "DEP01", "A-01-2", 88, 0, 600, 1000, "L2607B", "10/2027"),
    ("4035", "DEP01", "A-01-3", 34, 200, 600, 1000, "L2605C", "08/2027"),
    ("4102", "DEP01", "A-02-1", 210, 400, 1000, 1800, "L2608D", "06/2028"),
    ("4103", "DEP01", "A-02-1", 185, 0, 1000, 1800, "L2608D", "06/2028"),
    ("4118-4119-4120", "DEP01", "A-02-2", 62, 120, 400, 700, "L2606E", "04/2028"),
    ("4201", "DEP01", "A-03-1", 96, 50, 400, 700, "L2607F", "03/2027"),
    ("4202", "DEP01", "A-03-1", 41, 0, 300, 550, "L2607G", "03/2027"),
    ("4310", "DEP01", "A-04-2", 128, 0, 500, 900, "L2604H", "11/2027"),
    ("4311", "DEP01", "A-04-2", 117, 96, 500, 900, "L2604H", "11/2027"),
    ("4312", "DEP01", "A-04-3", 74, 0, 400, 700, "L2605J", "09/2027"),
    ("4405", "DEP01", "B-01-1", 156, 240, 700, 1200, "L2608K", "02/2028"),
    ("4406", "DEP01", "B-01-2", 48, 0, 300, 550, "L2607L", "01/2028"),
    ("4501", "DEP01", "B-02-1", 203, 100, 800, 1400, "L2608M", "12/2028"),
    ("4610", "DEP01", "B-03-1", 91, 0, 400, 700, "L2606N", "07/2027"),
    ("4611", "DEP01", "B-03-2", 143, 144, 600, 1000, "L2606P", "07/2027"),
    ("4620", "DEP01", "B-04-1", 27, 48, 300, 550, "L2603Q", "05/2027"),
    ("4701", "DEP01", "C-01-1", 66, 0, 300, 550, "L2605R", "10/2027"),
    ("4702", "DEP01", "C-01-2", 82, 60, 350, 600, "L2607S", "03/2027"),
    ("4801", "DEP01", "C-02-1", 174, 200, 700, 1200, "L2608T", "08/2028"),
    ("4802", "DEP01", "C-02-2", 8, 80, 700, 1200, "L2607U", "07/2028"),
    ("4803", "DEP01", "C-02-3", 121, 0, 500, 900, "L2608V", "09/2028"),
    ("4810", "DEP01", "C-03-1", 95, 0, 400, 700, "L2606W", "06/2028"),
    ("4901", "DEP01", "C-04-1", 112, 120, 500, 900, "L2607X", "04/2028"),
    ("4902", "DEP01", "C-04-2", 58, 0, 300, 550, "L2606Y", "02/2028"),
    ("4910", "DEP01", "C-05-1", 39, 24, 200, 380, "L2605Z", "12/2027"),
    ("5001-5002", "DEP01", "D-01-1", 167, 180, 700, 1200, "L2608AA", "05/2027"),
    ("5010", "DEP01", "D-01-2", 194, 0, 800, 1400, "L2608AB", "04/2027"),
    ("5020", "DEP01", "D-01-3", 76, 96, 400, 700, "L2607AC", "03/2027"),
    ("5030", "DEP01", "D-02-1", 103, 0, 450, 800, "L2608AD", "01/2027"),
    ("5101", "DEP01", "D-03-1", 218, 0, 900, 1500, "L2604AE", "12/2029"),
    ("5110", "DEP01", "D-03-2", 87, 36, 350, 600, "L2606AF", "11/2028"),
    ("5120", "DEP01", "D-04-1", 64, 0, 300, 550, "L2607AG", "10/2027"),
    ("6010", "DEP02", "E-01-1", 312, 480, 1200, 2000, "L2608BA", "03/2027"),
    ("6011", "DEP02", "E-01-2", 148, 60, 500, 900, "L2608BB", "02/2027"),
    ("6012", "DEP02", "E-01-3", 96, 36, 400, 700, "L2608BC", "02/2027"),
    ("6020", "DEP02", "E-02-1", 204, 0, 700, 1200, "L2607BD", "01/2027"),
    ("6030", "DEP02", "E-03-1", 71, 20, 250, 450, "L2608BE", "09/2027"),
    ("6031", "DEP02", "E-03-2", 133, 0, 500, 900, "L2608BF", "08/2027"),
    ("6040", "DEP02", "F-01-1", 89, 144, 400, 700, "L2608BG", "12/2026"),
    ("6041", "DEP02", "F-01-2", 156, 0, 600, 1000, "L2608BH", "01/2027"),
    ("6050", "DEP02", "F-02-1", 43, 18, 150, 280, "L2606BJ", "06/2029"),
    ("6051", "DEP02", "F-02-2", 31, 0, 120, 220, "L2605BK", "04/2029"),
    ("6060", "DEP02", "F-03-1", 187, 0, 700, 1200, "L2607BL", "07/2027"),
    ("6061", "DEP02", "F-03-2", 112, 84, 450, 800, "L2608BM", "05/2027"),
    ("6070", "DEP02", "F-04-1", 67, 0, 250, 450, "L2604BN", "11/2028"),
    ("7010", "FRIO", "G-01-1", 94, 180, 400, 700, "L2609CA", "18/09/2026"),
    ("7011", "DEP01", "C-05-2", 52, 0, 200, 380, "L2607CB", "08/2027"),
    ("7020", "FRIO", "G-01-2", 118, 96, 500, 900, "L2609CC", "22/09/2026"),
    ("7030", "FRIO", "G-02-1", 46, 24, 180, 330, "L2609CD", "05/10/2026"),
    ("7031", "FRIO", "G-02-2", 0, 0, 80, 150, "L2609CE", "28/09/2026"),
    ("7040", "FRIO", "G-03-1", 73, 0, 300, 550, "L2609CF", "12/11/2026"),
    ("8010", "DEP01", "H-01-1", 138, 72, 500, 900, "L2607DA", "07/2028"),
    ("8011", "DEP01", "H-01-2", 176, 0, 700, 1200, "L2608DB", "08/2028"),
    ("8020", "DEP01", "H-02-1", 91, 120, 400, 700, "L2608DC", "05/2029"),
    ("8021", "DEP01", "H-02-2", 68, 0, 300, 550, "L2607DD", "04/2029"),
    ("8030", "DEP01", "H-03-1", 54, 48, 250, 450, "L2606DE", "09/2028"),
    ("8031", "DEP01", "H-03-2", 129, 0, 500, 900, "L2608DF", "10/2028"),
    ("8040", "DEP01", "H-04-1", 83, 36, 350, 600, "L2607DG", "06/2028"),
    ("8050", "DEP01", "J-01-1", 112, 0, 400, 700, "L2608DH", "SIN VTO"),
    ("8051", "DEP01", "J-01-2", 197, 200, 800, 1400, "L2608DJ", "SIN VTO"),
    ("8060", "DEP01", "J-02-1", 241, 0, 900, 1500, "L2605DK", "SIN VTO"),
    ("8070", "DEP01", "H-05-1", 77, 0, 300, 550, "L2607DL", "03/2029"),
    ("9010", "DEP01", "K-01-1", 64, 48, 250, 450, "L2607EA", "11/2028"),
    ("9011", "DEP01", "K-01-2", 98, 0, 400, 700, "L2608EB", "12/2028"),
    ("9020", "DEP01", "K-02-1", 183, 96, 700, 1200, "L2606EC", "02/2029"),
    ("9030", "DEP01", "K-03-1", 71, 0, 300, 550, "L2608ED", "08/2028"),
    ("9040", "DEP01", "K-04-1", 126, 120, 500, 900, "L2607EE", "05/2028"),
    ("9050-9051", "DEP01", "K-05-1", 89, 0, 350, 600, "L2608EF", "01/2029"),
    ("9060", "DEP01", "K-06-1", 23, 8, 80, 150, "L2608EG", "06/2029"),
    ("9510", "DEP01", "L-01-1", 34, 300, 1500, 2600, "L2609FA", "10/12/2026"),
    ("9511", "DEP01", "L-01-2", 47, 0, 1500, 2600, "L2609FB", "28/11/2026"),
    ("9520", "DEP01", "L-02-1", 61, 0, 2000, 3400, "L2607FC", "07/2027"),
    ("9530", "DEP01", "L-02-2", 88, 200, 800, 1400, "L2608FD", "04/2027"),
    ("9540", "DEP01", "L-03-1", 52, 120, 400, 700, "L2609FE", "15/11/2026"),
    ("9550", "DEP01", "L-04-1", 143, 0, 1500, 2600, "L2606FF", "03/2027"),
    ("9560", "DEP01", "L-05-1", 66, 96, 300, 550, "L2608FG", "02/2027"),
    # Depositos logicos: no son lugares fisicos, pero toda distribuidora los tiene.
    ("6040", "AVER", "AVERIAS", 3, 0, 0, 0, "L2608BG", "12/2026"),
    ("8010", "AVER", "AVERIAS", 2, 0, 0, 0, "L2607DA", "07/2028"),
    ("4802", "TRAN", "EN TRANSITO", 60, 0, 0, 0, "L2609U", "07/2028"),
    ("7031", "TRAN", "EN TRANSITO", 40, 0, 0, 0, "L2609CE", "15/10/2026"),
    ("9060", "DEV", "DEVOLUCIONES", 4, 0, 0, 0, "L2608EG", "06/2029"),
]


DEPOSITOS = {
    "DEP01": "Deposito Central",
    "DEP02": "Deposito Bebidas",
    "FRIO": "Camara de frio",
    "AVER": "Averias",
    "TRAN": "En transito",
    "DEV": "Devoluciones",
}


def generar_stock() -> Path:
    por_codigo = {p[0]: p for p in PRODUCTOS}
    columnas = [
        "codigo",
        "descripcion",
        "rubro",
        "deposito",
        "deposito_nombre",
        "ubicacion",
        "unidad",
        "unid_x_bulto",
        "stock_bultos",
        "stock_total_un",
        "comprometido",
        "disponible",
        "stock_minimo",
        "punto_reposicion",
        "lote",
        "vencimiento",
        "ultimo_inventario",
    ]
    filas = []
    for codigo, deposito, ubicacion, bultos, comprometido, minimo, reposicion, lote, vto in STOCK:
        _, _, desc, _, rubro, un_x_bulto, _, _, _ = por_codigo[codigo]
        total = bultos * un_x_bulto
        filas.append(
            [
                codigo,
                desc,
                rubro,
                deposito,
                DEPOSITOS[deposito],
                ubicacion,
                "BULTO" if un_x_bulto > 1 else "KG",
                str(un_x_bulto),
                str(bultos),
                str(total),
                str(comprometido),
                str(total - comprometido),
                str(minimo),
                str(reposicion),
                lote,
                vto,
                "29/08/2026",
            ]
        )

    preambulo = [
        EMPRESA,
        "CONTROL DE STOCK POR DEPOSITO - Corte al 02/09/2026, 18:00 hs",
        "Disponible = Stock total - Comprometido. Comprometido son pedidos cargados sin despachar.",
        "Stock minimo es el piso que no se debe perforar. Punto de reposicion es el nivel que dispara la compra.",
        "AVER, TRAN y DEV son depositos logicos, no ubicaciones fisicas.",
    ]
    return escribir_csv("stock_depositos.csv", columnas, filas, preambulo)


def escribir_pdf(nombre: str, titulo: str, bloques: list[tuple[str, str]]) -> Path:
    """Genera un PDF con la estructura de un documento interno de PyME.

    `bloques` son pares (estilo, texto), donde estilo es "h1", "h2", "p" o
    "nota".
    """
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    base = getSampleStyleSheet()
    estilos = {
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=14, spaceAfter=10),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11, spaceBefore=12, spaceAfter=6
        ),
        "p": ParagraphStyle(
            "p", parent=base["BodyText"], fontSize=9.5, leading=14, alignment=TA_JUSTIFY
        ),
        "nota": ParagraphStyle(
            "nota", parent=base["BodyText"], fontSize=8.5, leading=12, textColor="#555555"
        ),
    }

    ruta = DESTINO / nombre
    doc = SimpleDocTemplate(
        str(ruta),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=titulo,
        author=EMPRESA,
    )
    flujo = []
    for estilo, texto in bloques:
        flujo.append(Paragraph(texto, estilos[estilo]))
        if estilo == "p":
            flujo.append(Spacer(1, 4))
    doc.build(flujo)
    return ruta


def generar_politica_licencias() -> Path:
    """Documento ACTUALIZADO: refleja la Ley 27.802 vigente desde marzo de 2026."""
    return escribir_pdf(
        "politica_licencias.pdf",
        "Politica de licencias y vacaciones",
        [
            ("h1", f"{EMPRESA}<br/>POLÍTICA DE LICENCIAS Y VACACIONES"),
            (
                "nota",
                f"Documento POL-RRHH-002 &nbsp;|&nbsp; Revisión 4 &nbsp;|&nbsp; Vigencia desde el 01/09/2026 "
                f"&nbsp;|&nbsp; Reemplaza a la Revisión 3 del 12/04/2024 &nbsp;|&nbsp; Responsable: Administración de Personal<br/>"
                f"{DOMICILIO} &nbsp;|&nbsp; CUIT {CUIT}",
            ),
            ("h2", "1. Alcance"),
            (
                "p",
                "Esta política alcanza a todo el personal en relación de dependencia de la Empresa, encuadrado en el "
                "Convenio Colectivo de Trabajo 130/75 de Empleados de Comercio. Se complementa con la Ley de Contrato "
                "de Trabajo 20.744 y con las modificaciones introducidas por la Ley 27.802 de Modernización Laboral, "
                "vigente desde el 6 de marzo de 2026.",
            ),
            ("h2", "2. Licencia anual ordinaria (vacaciones)"),
            (
                "p",
                "<b>2.1 Cantidad de días.</b> La cantidad de días de licencia surge de la antigüedad computada "
                "<b>al 31 de diciembre del año al que corresponden</b> las vacaciones, conforme el artículo 150 de la "
                "Ley de Contrato de Trabajo:",
            ),
            (
                "p",
                "&bull; Antigüedad hasta 5 años: <b>14 días corridos</b><br/>"
                "&bull; Más de 5 y hasta 10 años: <b>21 días corridos</b><br/>"
                "&bull; Más de 10 y hasta 20 años: <b>28 días corridos</b><br/>"
                "&bull; Más de 20 años: <b>35 días corridos</b>",
            ),
            (
                "p",
                "El cómputo al 31 de diciembre implica que quien cumpla el aniversario que da derecho a un tramo mayor "
                "antes de esa fecha accede al tramo mayor, aunque al momento de tomarse la licencia todavía no lo "
                "hubiera cumplido.",
            ),
            (
                "p",
                "<b>2.2 Requisito de tiempo mínimo trabajado.</b> Para acceder a la licencia completa, el trabajador debe "
                "haber prestado servicios durante la mitad, como mínimo, de los días hábiles del año calendario "
                "(artículo 151 LCT). Quien no alcance ese mínimo goza de <b>un día de descanso por cada veinte días de "
                "trabajo efectivo</b> (artículo 153 LCT).",
            ),
            (
                "p",
                "<b>2.3 Época de otorgamiento y preaviso.</b> La licencia se otorga entre el 1° de octubre y el 30 de "
                "abril del año siguiente. La Empresa comunica por escrito la fecha de inicio con una anticipación no "
                "menor a <b>sesenta (60) días corridos</b>, conforme el artículo 74 del CCT 130/75.",
            ),
            (
                "nota",
                "Aclaración sobre el plazo de preaviso: el artículo 154 de la LCT, con la redacción dada por la Ley "
                "27.802, fija un preaviso mínimo de treinta (30) días. El CCT 130/75 establece sesenta (60) días. "
                "Por aplicación del principio de la norma más favorable al trabajador, <b>para el personal de comercio "
                "rige el plazo de sesenta (60) días del convenio</b>, que es el que aplica esta Empresa.",
            ),
            (
                "p",
                "<b>2.4 Fraccionamiento.</b> A partir de la Ley 27.802 y <b>por acuerdo escrito entre las partes</b>, el "
                "período puede dividirse en tramos no inferiores a <b>siete (7) días corridos</b> cada uno. El "
                "fraccionamiento no es una facultad unilateral: requiere conformidad de la Empresa y del trabajador. "
                "Al menos una vez cada tres períodos la licencia debe otorgarse en temporada de verano.",
            ),
            (
                "p",
                "<b>2.5 Pago.</b> El haber correspondiente a la licencia se abona <b>al inicio</b> de la misma "
                "(artículo 155 LCT). Para el personal mensualizado se calcula dividiendo el sueldo por veinticinco y "
                "multiplicando por la cantidad de días de licencia.",
            ),
            (
                "p",
                "<b>2.6 Enfermedad durante la licencia.</b> Si el trabajador se enferma durante el goce de las "
                "vacaciones y lo acredita con certificado médico, los días afectados se reprograman.",
            ),
            (
                "p",
                "<b>2.7 Vacaciones no gozadas.</b> Al extinguirse el contrato de trabajo por cualquier causa, el "
                "trabajador percibe una indemnización proporcional por las vacaciones no gozadas (artículo 156 LCT).",
            ),
            (
                "p",
                "<b>2.8 Restricción operativa.</b> Por razones de temporada, entre el 1° y el 20 de diciembre no se "
                "otorgan vacaciones al personal de Depósito y Reparto, salvo autorización expresa de la Gerencia.",
            ),
            ("h2", "3. Licencias especiales"),
            (
                "p",
                "Se aplican los plazos del CCT 130/75, que mejoran los del artículo 158 de la LCT:",
            ),
            (
                "p",
                "&bull; <b>Matrimonio:</b> 12 días corridos, más 1 día para trámites prematrimoniales (art. 77 CCT).<br/>"
                "&bull; <b>Casamiento de hijo:</b> 1 día (art. 77 CCT).<br/>"
                "&bull; <b>Nacimiento de hijo:</b> 2 días hábiles (art. 81 CCT).<br/>"
                "&bull; <b>Fallecimiento de padre, madre, hijo, cónyuge o hermano:</b> 4 días corridos. Si el sepelio "
                "es a más de 500 km, se agregan 2 días (art. 79 CCT).<br/>"
                "&bull; <b>Fallecimiento de abuelos, suegros, cuñados o hijos del cónyuge:</b> 2 días (art. 80 CCT).<br/>"
                "&bull; <b>Donación de sangre:</b> jornada completa (art. 82 CCT).<br/>"
                "&bull; <b>Mudanza:</b> 2 días corridos (art. 83 CCT).<br/>"
                "&bull; <b>Exámenes, estudiante secundario:</b> 10 días por año, acumulables a la licencia anual (art. 85 CCT).<br/>"
                "&bull; <b>Exámenes, estudiante universitario o terciario:</b> 20 días por año, hasta 4 días por examen (art. 86 CCT).<br/>"
                "&bull; <b>Enfermedad de cónyuge, padres o hijos:</b> hasta 30 días por año, sin goce de haberes (art. 78 CCT).<br/>"
                "&bull; <b>Hora para compras:</b> 1 hora mensual con goce de haberes (art. 90 CCT).",
            ),
            (
                "p",
                "En los casos de nacimiento de hijo y de fallecimiento de familiar debe computarse necesariamente un "
                "día hábil, cuando la licencia coincida con domingo, feriado o día no laborable (artículo 160 LCT).",
            ),
            ("h2", "4. Licencia por enfermedad inculpable"),
            (
                "p",
                "<b>4.1 Plazos con goce de haberes</b> (artículo 208 LCT), según antigüedad y cargas de familia:",
            ),
            (
                "p",
                "&bull; Antigüedad menor a 5 años: <b>3 meses</b> sin cargas de familia, <b>6 meses</b> con cargas.<br/>"
                "&bull; Antigüedad mayor a 5 años: <b>6 meses</b> sin cargas de familia, <b>12 meses</b> con cargas.",
            ),
            (
                "p",
                "<b>4.2 Aviso.</b> El trabajador debe dar aviso <b>en el transcurso de la primera jornada</b> de "
                "inasistencia, indicando el lugar donde se encuentra. La Ley 27.802 estableció que la falta de aviso "
                "oportuno hace perder el derecho a la remuneración del período, salvo que se acredite de modo "
                "inequívoco tanto la enfermedad como la imposibilidad de comunicarla.",
            ),
            (
                "p",
                "<b>4.3 Certificado médico.</b> Debe consignar diagnóstico, tratamiento indicado y cantidad de días de "
                "reposo. Se admite el certificado con <b>firma digital</b> emitido por plataformas autorizadas conforme "
                "la Ley 27.553. Ante discrepancia insalvable con el control médico de la Empresa, se recurre a junta "
                "médica en institución oficial.",
            ),
            (
                "p",
                "<b>4.4 Reserva del puesto.</b> Agotados los plazos con goce de haberes, se conserva el puesto durante "
                "un año más sin percepción de remuneración (artículo 211 LCT).",
            ),
            ("h2", "5. Día del Empleado de Comercio"),
            (
                "p",
                "El 26 de septiembre es el Día del Empleado de Comercio conforme la Ley 26.541, asimilado a feriado "
                "nacional a todos los efectos para el personal comprendido en el CCT 130/75.",
            ),
            ("h2", "6. Trámites"),
            (
                "p",
                "Las solicitudes de licencia se presentan en Administración de Personal por escrito o al correo "
                "personal@pampasur.com.ar, con la documentación respaldatoria correspondiente. Las licencias "
                "especiales requieren la presentación del comprobante dentro de las 48 horas de reintegrado el "
                "trabajador.",
            ),
        ],
    )


def generar_procedimiento_facturas() -> Path:
    """Documento ACTUALIZADO: refleja ARCA y la eliminacion de la Factura M."""
    return escribir_pdf(
        "procedimiento_facturas.pdf",
        "Carga de facturas de compra",
        [
            ("h1", f"{EMPRESA}<br/>PROCEDIMIENTO DE CARGA DE FACTURAS DE COMPRA"),
            (
                "nota",
                f"Documento PROC-ADM-004 &nbsp;|&nbsp; Revisión 3 &nbsp;|&nbsp; Vigencia desde el 01/03/2026 "
                f"&nbsp;|&nbsp; Responsable: Administración &nbsp;|&nbsp; CUIT {CUIT}",
            ),
            ("h2", "1. Objeto"),
            (
                "p",
                "Establecer el circuito de recepción, validación, carga y archivo de las facturas de compra recibidas "
                "de proveedores, de modo que la información llegue completa y en término a la liquidación mensual de "
                "IVA y al Libro IVA Digital.",
            ),
            ("h2", "2. Condición fiscal de la Empresa"),
            (
                "p",
                f"{EMPRESA} es <b>Responsable Inscripta</b> en el Impuesto al Valor Agregado, CUIT <b>{CUIT}</b>, con "
                "sede en la Provincia de Buenos Aires e inscripta en Convenio Multilateral por operar en más de una "
                "jurisdicción.",
            ),
            ("h2", "3. Recepción"),
            (
                "p",
                "Las facturas ingresan por el correo compras@pampasur.com.ar o se entregan en mano en Administración. "
                "<b>No se recibe una factura sin el remito conformado correspondiente.</b> El remito es el documento "
                "que respalda el traslado y la entrega de la mercadería; no documenta la venta ni genera IVA. La "
                "factura debe consignar el número del remito o los remitos que ampara.",
            ),
            ("h2", "4. Validación previa a la carga"),
            ("p", "Antes de cargar el comprobante, verificar:"),
            (
                "p",
                "<b>a) Datos del receptor.</b> Que la razón social y el CUIT sean los de la Empresa.",
            ),
            (
                "p",
                "<b>b) Clase de comprobante.</b> Siendo la Empresa Responsable Inscripta, corresponde:",
            ),
            (
                "p",
                "&bull; Proveedor <b>Responsable Inscripto</b> &rarr; debe emitir <b>Factura A</b>, con el IVA "
                "discriminado.<br/>"
                "&bull; Proveedor <b>Monotributista</b> &rarr; emite <b>Factura C</b>, sin IVA discriminado.<br/>"
                "&bull; Proveedor <b>Exento</b> &rarr; emite <b>Factura C</b>.",
            ),
            (
                "nota",
                "Nota sobre el sentido inverso: cuando la Empresa le vende a un cliente monotributista, "
                "<b>corresponde emitir Factura A, no Factura B</b> (RG 1415, artículo 15 inciso a). Esa factura "
                "debe incluir la leyenda: «El crédito fiscal discriminado en el presente comprobante, sólo podrá ser "
                "computado a efectos del Régimen de Sostenimiento e Inclusión Fiscal para Pequeños Contribuyentes de "
                "la Ley N° 27.618».",
            ),
            (
                "p",
                "<b>c) CAE.</b> Que figure al pie el Código de Autorización Electrónico, de catorce dígitos, con su "
                "fecha de vencimiento. Esa fecha es el plazo que tenía el emisor para utilizar la autorización; "
                "<b>no significa que la factura caduque</b> ni que deje de ser válida para su cómputo.",
            ),
            (
                "p",
                "<b>d) Constatación.</b> Verificar el comprobante en ARCA, servicio «Constatación de Comprobantes». Si "
                "el comprobante no valida, <b>no se carga</b> y se devuelve al proveedor solicitando su reemplazo.",
            ),
            ("h2", "5. Imputación"),
            (
                "p",
                "La carga se realiza en el módulo Compras del sistema de gestión, consignando: fecha de emisión, tipo y "
                "número de comprobante con el formato 0000-00000000, CUIT del proveedor, neto gravado discriminado por "
                "alícuota, IVA por alícuota, percepciones, conceptos no gravados y total.",
            ),
            (
                "p",
                "La Empresa opera con dos alícuotas: <b>21%</b> como régimen general y <b>10,5%</b> para determinados "
                "alimentos básicos, entre ellos harina de trigo y arroz. Verificar la alícuota consignada por el "
                "proveedor y no asumirla.",
            ),
            ("h2", "6. Percepciones y retenciones"),
            (
                "p",
                "<b>6.1 Percepciones.</b> Las percepciones que el proveedor incluye en la factura <b>aumentan el total "
                "a pagar</b> y constituyen un <b>crédito</b> a favor de la Empresa, computable a cuenta del impuesto "
                "del período en que se sufrieron. Se cargan en cuentas contables separadas y <b>nunca se incorporan al "
                "costo de la mercadería</b>. Las más frecuentes son la percepción de IVA de la RG 2408, del 3% sobre el "
                "neto gravado, o del 1,5% cuando la operación está gravada al 10,5%, y la percepción de Ingresos "
                "Brutos, cuya alícuota surge del padrón provincial vigente.",
            ),
            (
                "p",
                "<b>6.2 Retenciones.</b> Las retenciones las practica la Empresa <b>al momento del pago</b>, "
                "<b>disminuyen el neto a pagar</b> al proveedor y constituyen una <b>deuda con el fisco</b> que debe "
                "depositarse mediante SICORE. La más habitual es la retención de Ganancias de la RG 830, del 2% para "
                "proveedores inscriptos en operaciones de compra de bienes de cambio.",
            ),
            ("p", "Ejemplo de composición del pie de una factura de compra:"),
            (
                "p",
                "<font face='Courier'>Subtotal neto gravado 21% &nbsp;&nbsp;&nbsp;&nbsp;1.284.500,00<br/>"
                "IVA 21% &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;269.745,00<br/>"
                "Percepción IVA RG 2408 (3%) &nbsp;&nbsp;&nbsp;&nbsp;38.535,00<br/>"
                "Percepción IIBB PBA (2,50%) &nbsp;&nbsp;&nbsp;&nbsp;32.112,50<br/>"
                "TOTAL &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.624.892,50</font>",
            ),
            ("h2", "7. Comprobantes con leyenda especial"),
            (
                "p",
                "Si se recibe una <b>Factura A con la leyenda «OPERACIÓN SUJETA A RETENCIÓN»</b>, debe avisarse a "
                "Tesorería <b>antes de efectuar el pago</b>: corresponde retener el cien por ciento del IVA facturado y "
                "el seis por ciento en concepto de Ganancias.",
            ),
            (
                "p",
                "Si la factura lleva la leyenda <b>«PAGO EN CBU INFORMADA»</b>, el pago debe realizarse exclusivamente "
                "por transferencia a la CBU declarada por el proveedor ante ARCA.",
            ),
            (
                "nota",
                "Estas dos variantes reemplazaron a la antigua Factura clase «M», que fue eliminada por la "
                "RG 5762/2025 con vigencia desde el 1° de diciembre de 2025. Si un proveedor ofrece emitir una "
                "Factura M, el comprobante es inválido.",
            ),
            ("h2", "8. Crédito fiscal según el proveedor"),
            (
                "p",
                "Solo las facturas A de proveedores Responsables Inscriptos generan <b>crédito fiscal computable</b>. "
                "Las facturas C de monotributistas y exentos <b>no generan crédito fiscal</b>: el importe total de la "
                "factura constituye costo. Esta diferencia debe considerarse al comparar presupuestos de proveedores "
                "con distinta condición fiscal, porque un precio aparentemente menor de un monotributista puede "
                "resultar más caro una vez computado el crédito que se pierde.",
            ),
            ("h2", "9. Cierre mensual"),
            (
                "p",
                "La carga de las facturas del mes debe estar cerrada el <b>día 10 del mes siguiente</b>, para que "
                "Contaduría genere el <b>Libro IVA Digital</b> conforme la RG 4597 y presente la declaración jurada de "
                "IVA en término. El Libro IVA Digital es obligatorio para Responsables Inscriptos y sujetos exentos, y "
                "reemplazó a los libros de IVA Compras y Ventas en papel.",
            ),
            ("h2", "10. Archivo"),
            (
                "p",
                "Las facturas se archivan por proveedor y por mes de imputación. Los remitos se conservan por un plazo "
                "no menor a <b>dos años</b> desde su emisión. Los comprobantes anulados se inutilizan con la leyenda "
                "«ANULADO» y se archivan igualmente, sin descartarse.",
            ),
        ],
    )


def generar_reglamento_interno() -> Path:
    """Documento DELIBERADAMENTE DESACTUALIZADO.

    Fechado en 2022 y nunca revisado. Dice "AFIP" en vez de "ARCA" y consigna
    el preaviso de vacaciones de 45 dias que regia antes de la Ley 27.802.

    No es un descuido: es como son los documentos de una PyME real, donde la
    lista de precios se actualiza cada quince dias y el reglamento interno
    queda igual durante anios. Ademas genera el caso de evaluacion mas
    interesante del corpus: la pregunta "con cuanta anticipacion me avisan las
    vacaciones" tiene una respuesta correcta en la politica de licencias
    (60 dias, art. 74 CCT 130/75) y una respuesta plausible pero
    desactualizada en este documento (45 dias). Un sistema que recupera el
    fragmento equivocado responde mal.
    """
    return escribir_pdf(
        "reglamento_interno.pdf",
        "Reglamento interno de trabajo",
        [
            ("h1", f"{EMPRESA}<br/>REGLAMENTO INTERNO DE TRABAJO"),
            (
                "nota",
                f"Documento RI-001 &nbsp;|&nbsp; Revisión 1 &nbsp;|&nbsp; Aprobado el 15/03/2022 "
                f"&nbsp;|&nbsp; Responsable: Gerencia<br/>{DOMICILIO} &nbsp;|&nbsp; CUIT {CUIT}",
            ),
            ("h2", "1. Objeto y alcance"),
            (
                "p",
                "El presente reglamento establece las normas de convivencia y organización del trabajo aplicables a "
                "todo el personal de la Empresa, cualquiera sea su categoría o sector. Se dicta en ejercicio de las "
                "facultades de organización y dirección previstas en los artículos 64 a 68 de la Ley de Contrato de "
                "Trabajo, y no puede alterar derechos reconocidos por dicha ley ni por el Convenio Colectivo de "
                "Trabajo 130/75.",
            ),
            ("h2", "2. Ingreso y legajo"),
            (
                "p",
                "Previo al inicio de tareas, la Empresa tramita el <b>alta temprana ante la AFIP</b> y entrega al "
                "trabajador copia de la constancia. El legajo personal se integra con: contrato de trabajo o nota de "
                "ingreso, fotocopia de DNI, constancia de CUIL, declaración de domicilio, declaración de cargas de "
                "familia, formulario de elección de obra social, constancia de recepción de este reglamento y "
                "constancia de entrega de elementos de protección personal.",
            ),
            (
                "p",
                "El período de prueba es de tres meses, conforme el artículo 92 bis de la Ley de Contrato de Trabajo.",
            ),
            ("h2", "3. Jornada de trabajo y horarios"),
            (
                "p",
                "La jornada de trabajo es de <b>ocho (8) horas diarias y cuarenta y ocho (48) semanales</b>, conforme "
                "la Ley 11.544 y el CCT 130/75. Los horarios habituales por sector son:",
            ),
            (
                "p",
                "&bull; <b>Administración:</b> lunes a viernes de 08:00 a 17:00, con una hora de almuerzo.<br/>"
                "&bull; <b>Depósito:</b> lunes a viernes de 07:00 a 16:00, sábados de 07:00 a 13:00.<br/>"
                "&bull; <b>Reparto:</b> lunes a viernes de 06:30 a 15:30, sábados de 07:00 a 13:00.",
            ),
            (
                "p",
                "El descanso semanal se extiende desde las <b>13:00 del sábado hasta las 24:00 del domingo</b>, "
                "conforme el artículo 204 de la Ley de Contrato de Trabajo.",
            ),
            (
                "p",
                "Las horas trabajadas en exceso de la jornada se abonan con un recargo del <b>50%</b> en días comunes y "
                "del <b>100%</b> los sábados después de las 13:00, domingos y feriados.",
            ),
            ("h2", "4. Control de asistencia y puntualidad"),
            (
                "p",
                "Todo el personal registra su ingreso y su egreso en el reloj biométrico ubicado en el acceso de "
                "personal. <b>No se admite que un tercero registre la asistencia de otro trabajador</b>; hacerlo "
                "constituye falta grave.",
            ),
            (
                "p",
                "Se admite una tolerancia de <b>diez (10) minutos</b>, hasta <b>tres (3) veces por mes</b>. Las "
                "llegadas tarde que excedan ese límite se descuentan del haber y afectan el adicional por asistencia y "
                "puntualidad previsto en el artículo 40 del CCT 130/75, equivalente al 8,33% sobre el básico más "
                "antigüedad.",
            ),
            (
                "p",
                "Las inasistencias deben comunicarse al supervisor directo dentro de la primera hora del horario de "
                "trabajo. El certificado médico se presenta en Administración de Personal dentro de las 48 horas.",
            ),
            ("h2", "5. Licencias"),
            (
                "p",
                "El régimen de licencias se rige por la Ley de Contrato de Trabajo y por el CCT 130/75. La cantidad de "
                "días de licencia anual ordinaria surge de la antigüedad computada al 31 de diciembre del año al que "
                "corresponden: catorce días hasta cinco años de antigüedad, veintiuno de cinco a diez, veintiocho de "
                "diez a veinte y treinta y cinco por encima de veinte años.",
            ),
            (
                "p",
                "La Empresa comunicará por escrito la fecha de inicio de las vacaciones con una anticipación no menor a "
                "<b>cuarenta y cinco (45) días corridos</b>, conforme el artículo 154 de la Ley de Contrato de Trabajo.",
            ),
            (
                "p",
                "El detalle de las licencias especiales y del régimen de enfermedad inculpable se encuentra en la "
                "Política de Licencias y Vacaciones vigente.",
            ),
            ("h2", "6. Remuneraciones"),
            (
                "p",
                "Las remuneraciones se liquidan por mes vencido y se abonan mediante acreditación en cuenta sueldo "
                "dentro de los <b>cuatro (4) días hábiles</b> posteriores al vencimiento del mes trabajado. El recibo "
                "de haberes se pone a disposición en formato digital.",
            ),
            (
                "p",
                "El sueldo anual complementario se abona en dos cuotas, con vencimiento el 30 de junio y el 18 de "
                "diciembre de cada año.",
            ),
            ("h2", "7. Uso de bienes de la Empresa"),
            (
                "p",
                "Los vehículos, teléfonos celulares, herramientas y equipos informáticos entregados al personal son de "
                "propiedad de la Empresa y deben destinarse exclusivamente al cumplimiento de las tareas. El personal "
                "de Reparto es responsable de la limpieza y del control diario de niveles del vehículo asignado, y debe "
                "informar de inmediato cualquier desperfecto o siniestro.",
            ),
            ("h2", "8. Higiene y seguridad"),
            (
                "p",
                "La Empresa provee sin cargo los elementos de protección personal necesarios para cada puesto, conforme "
                "la Ley 19.587 y sus normas reglamentarias. <b>Su uso es obligatorio</b> y su omisión constituye falta "
                "pasible de sanción.",
            ),
            (
                "p",
                "El personal de Depósito debe utilizar calzado de seguridad y faja lumbar para el movimiento manual de "
                "cargas. No está permitido operar el autoelevador sin la habilitación correspondiente.",
            ),
            (
                "p",
                "Todo accidente de trabajo, por leve que sea, debe informarse al supervisor <b>en el momento</b> para "
                "su denuncia ante la Aseguradora de Riesgos del Trabajo. El teléfono de emergencias de la ART se "
                "encuentra publicado en la cartelera de personal y en la cabina de cada vehículo.",
            ),
            ("h2", "9. Uniforme y presentación"),
            (
                "p",
                "El uso del uniforme provisto es obligatorio durante toda la jornada. La Empresa entrega <b>dos equipos "
                "por año</b>, conforme el artículo 67 del CCT 130/75.",
            ),
            ("h2", "10. Confidencialidad"),
            (
                "p",
                "La información sobre precios de compra, márgenes, condiciones comerciales, listas de clientes y datos "
                "de proveedores es confidencial. Su divulgación a terceros constituye falta grave.",
            ),
            ("h2", "11. Régimen disciplinario"),
            (
                "p",
                "Las sanciones son, en orden de gravedad: <b>llamado de atención verbal</b>, <b>apercibimiento "
                "escrito</b> y <b>suspensión</b> sin goce de haberes.",
            ),
            (
                "p",
                "Las suspensiones disciplinarias no podrán exceder de <b>treinta (30) días en un año</b>, contados a "
                "partir de la primera suspensión, y deben notificarse por escrito, con expresión de causa y plazo "
                "determinado, conforme los artículos 218 a 220 de la Ley de Contrato de Trabajo.",
            ),
            (
                "p",
                "El trabajador que no acepte la sanción cuenta con <b>treinta (30) días corridos</b> para impugnarla. "
                "Vencido ese plazo sin cuestionamiento, la sanción se considera consentida (artículo 67 LCT).",
            ),
            ("h2", "12. Vigencia"),
            (
                "p",
                "El presente reglamento entra en vigencia el 15 de marzo de 2022 y permanece publicado en la cartelera "
                "de personal. Toda modificación será comunicada por escrito con una anticipación no menor a treinta "
                "días.",
            ),
        ],
    )


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    generados = [
        generar_lista_precios(),
        generar_stock(),
        generar_politica_licencias(),
        generar_procedimiento_facturas(),
        generar_reglamento_interno(),
    ]
    for ruta in generados:
        print(f"{ruta.stat().st_size:>8,} bytes  {ruta.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
