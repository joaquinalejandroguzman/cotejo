"""Evita que requirements.txt y pyproject.toml se desincronicen.

Streamlit Community Cloud instala las dependencias leyendo un solo archivo, y
su orden de prioridad pone requirements.txt por encima de pyproject.toml. En
produccion manda requirements.txt; pyproject.toml queda ignorado.

Eso abre un agujero silencioso: si se agrega una dependencia a pyproject.toml
y se olvida en requirements.txt, la app corre bien en local, el CI pasa en
verde, y revienta unicamente en produccion. Es la misma clase de problema que
ya tumbo esta app dos veces — configuracion que se desincroniza sin que nadie
se entere hasta que la ve un usuario.

Este modulo compara las dos listas y falla en el CI, que es donde todavia
sale barato.
"""

import re
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
PYPROJECT = RAIZ / "pyproject.toml"
REQUIREMENTS = RAIZ / "requirements.txt"


def normalizar(especificacion: str) -> str:
    """Deja una especificacion de dependencia en forma comparable.

    Segun PEP 503 los nombres de paquete no distinguen mayusculas ni entre
    guiones, guiones bajos y puntos: "types-requests" y "Types_Requests" son
    el mismo paquete. Se normaliza el nombre y se deja el resto del
    especificador tal cual, porque ahi si importa la version exacta.
    """
    limpia = especificacion.split("#")[0].strip()
    if not limpia:
        return ""
    partes = re.split(r"([<>=!~]+)", limpia, maxsplit=1)
    nombre = re.sub(r"[-_.]+", "-", partes[0].strip()).lower()
    resto = "".join(p.strip() for p in partes[1:])
    return nombre + resto


def leer_requirements(lineas: Iterable[str]) -> set[str]:
    """Extrae las dependencias de un requirements.txt.

    Ignora comentarios, lineas vacias y directivas de pip (-e, -r, --flags),
    que no son dependencias sino instrucciones para el instalador.
    """
    encontradas = set()
    for linea in lineas:
        limpia = linea.strip()
        if not limpia or limpia.startswith(("#", "-")):
            continue
        normalizada = normalizar(limpia)
        if normalizada:
            encontradas.add(normalizada)
    return encontradas


def diferencias(declaradas: set[str], desplegadas: set[str]) -> list[str]:
    """Describe cada divergencia entre las dos listas, en lenguaje accionable.

    `declaradas` viene de pyproject.toml y `desplegadas` de requirements.txt.
    Devuelve una lista vacia cuando coinciden.
    """
    problemas = []
    for falta in sorted(declaradas - desplegadas):
        problemas.append(
            f"'{falta}' esta en pyproject.toml pero falta en requirements.txt: "
            "la app va a fallar en produccion aunque el CI pase en verde"
        )
    for sobra in sorted(desplegadas - declaradas):
        problemas.append(
            f"'{sobra}' esta en requirements.txt pero falta en pyproject.toml: "
            "se instala en produccion y no en local ni en el CI"
        )
    return problemas


class TestNormalizar:
    def test_separa_el_nombre_de_la_version(self):
        assert normalizar("streamlit>=1.36") == "streamlit>=1.36"

    def test_ignora_espacios_sobrantes(self):
        assert normalizar("  pypdf >= 4.0  ") == "pypdf>=4.0"

    def test_los_nombres_no_distinguen_mayusculas(self):
        assert normalizar("Requests>=2.31") == normalizar("requests>=2.31")

    def test_guion_y_guion_bajo_son_el_mismo_paquete(self):
        # PEP 503: los separadores son intercambiables en el nombre.
        assert normalizar("types_requests") == normalizar("types-requests")

    def test_saca_los_comentarios_al_final_de_la_linea(self):
        assert normalizar("pypdf>=4.0  # lee los PDF") == "pypdf>=4.0"

    def test_una_linea_vacia_no_es_una_dependencia(self):
        assert normalizar("   ") == ""


class TestLeerRequirements:
    def test_lee_las_dependencias(self):
        assert leer_requirements(["streamlit>=1.36", "pypdf>=4.0"]) == {
            "streamlit>=1.36",
            "pypdf>=4.0",
        }

    def test_ignora_comentarios_y_lineas_vacias(self):
        lineas = ["# un comentario", "", "   ", "streamlit>=1.36"]
        assert leer_requirements(lineas) == {"streamlit>=1.36"}

    def test_ignora_las_directivas_de_pip(self):
        # "-e .[dev]" y "-r otro.txt" son instrucciones, no dependencias.
        lineas = ["-e .[dev]", "-r requirements.txt", "--no-cache-dir", "pypdf>=4.0"]
        assert leer_requirements(lineas) == {"pypdf>=4.0"}


class TestDiferencias:
    def test_listas_identicas_no_reportan_nada(self):
        deps = {"streamlit>=1.36", "pypdf>=4.0"}
        assert diferencias(deps, deps) == []

    def test_detecta_una_dependencia_que_falta_en_requirements(self):
        # El caso que motiva este modulo: se suma pandas para leer CSV en
        # pyproject.toml y se olvida en requirements.txt.
        problemas = diferencias({"streamlit>=1.36", "pandas>=2.0"}, {"streamlit>=1.36"})
        assert len(problemas) == 1
        assert "pandas>=2.0" in problemas[0]
        assert "falta en requirements.txt" in problemas[0]

    def test_detecta_una_dependencia_que_sobra_en_requirements(self):
        problemas = diferencias({"streamlit>=1.36"}, {"streamlit>=1.36", "vieja>=1.0"})
        assert len(problemas) == 1
        assert "vieja>=1.0" in problemas[0]
        assert "falta en pyproject.toml" in problemas[0]

    def test_detecta_una_version_distinta(self):
        # Mismo paquete, distinto minimo: en produccion podria instalarse una
        # version que el CI nunca probo.
        problemas = diferencias({"streamlit>=1.36"}, {"streamlit>=1.30"})
        assert len(problemas) == 2

    def test_reporta_todas_las_divergencias_juntas(self):
        problemas = diferencias({"a>=1", "b>=1"}, {"c>=1"})
        assert len(problemas) == 3


class TestLosArchivosRealesEstanSincronizados:
    """La comprobacion que corre contra los archivos del repositorio."""

    def test_requirements_txt_coincide_con_pyproject_toml(self):
        with PYPROJECT.open("rb") as f:
            declaradas = leer_requirements(tomllib.load(f)["project"]["dependencies"])
        desplegadas = leer_requirements(REQUIREMENTS.read_text().splitlines())

        problemas = diferencias(declaradas, desplegadas)
        assert not problemas, (
            "requirements.txt y pyproject.toml divergieron.\n\n"
            + "\n".join(f"  - {p}" for p in problemas)
            + "\n\nStreamlit Community Cloud instala desde requirements.txt, "
            "asi que esta diferencia rompe la app en produccion sin que el "
            "CI se entere."
        )

    def test_requirements_txt_no_esta_vacio(self):
        # Un archivo vacio pasaria la comparacion solo si pyproject tampoco
        # declara nada, lo cual seria otro error distinto.
        assert leer_requirements(REQUIREMENTS.read_text().splitlines())

    def test_pandas_esta_declarada_explicitamente(self):
        """pandas no puede quedar como dependencia heredada de streamlit.

        streamlit declara `pandas<4,>=1.4.0`, asi que pandas ya se instala
        aunque este proyecto no lo pida. Apoyarse en eso es fragil: el dia
        que streamlit lo vuelva opcional o cambie el rango, la lectura de
        datos tabulares se rompe sin que nada avise. Si lo usamos, lo
        declaramos.
        """
        with PYPROJECT.open("rb") as f:
            declaradas = leer_requirements(tomllib.load(f)["project"]["dependencies"])
        nombres = {d.split(">")[0].split("<")[0].split("=")[0] for d in declaradas}
        assert "pandas" in nombres, (
            "pandas se usa para leer CSV pero no esta declarada en "
            "pyproject.toml. Hoy se instala solo porque streamlit la arrastra."
        )
