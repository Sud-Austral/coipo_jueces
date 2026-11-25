"""Sólo biblioteca estándar: ningún import de terceros en `jueces/` ni en `tests/`.

Es el primer punto del «Contrato de un juez» del README: los jueces corren en el CI de
cada aplicación con el `python3` del runner, sin `pip install`. Un `import yaml` que se
colara no rompería el CI de este repositorio: rompería el de las aplicaciones, donde el
diagnóstico es mucho más caro.

CÓMO SE COMPROBABA HASTA EL 2026-11-25. Un bucle dentro de `autotest.yml` importaba cada
`jueces/j*.py` con el `python3` del runner. Su comentario decía «con el intérprete
pelado», y nada lo pelaba: un paquete que la imagen del runner traiga instalado se
importa sin error. Tampoco corría fuera de CI, así que en la máquina de quien edita
—con cientos de paquetes instalados— un import de terceros funcionaba sin que nada lo
dijera. Y era lógica dentro del YAML, que no se puede probar (`correr.py` explica por qué
la suya no vive ahí).

Aquí se lee el código y no se ejecuta: cada módulo importado tiene que ser de la
biblioteca estándar (`sys.stdlib_module_names`) o un archivo de este repositorio. Da el
mismo resultado en cualquier máquina.

LO QUE NO VE, dicho: un import armado en tiempo de ejecución (`importlib.import_module`
con un nombre que no es un literal). Hoy el único uso es `correr.py` cargando los jueces
por ruta, que no nombra ningún módulo.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = ("jueces", "tests")


def modulos_importados(fuente: str) -> list[tuple[int, str]]:
    """(línea, módulo raíz) de cada import ABSOLUTO del fuente, esté donde esté.

    Un import relativo (`from . import x`) nombra un módulo del propio paquete y no cuenta."""
    salida: list[tuple[int, str]] = []
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            salida += [(nodo.lineno, alias.name.split(".")[0]) for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            salida.append((nodo.lineno, nodo.module.split(".")[0]))
    return salida


def de_terceros(fuente: str, propios: set[str]) -> list[tuple[int, str]]:
    """Los imports que no son de la biblioteca estándar ni de este repositorio."""
    return [
        (linea, modulo)
        for linea, modulo in modulos_importados(fuente)
        if modulo not in sys.stdlib_module_names and modulo not in propios
    ]


def archivos() -> list[Path]:
    return sorted(p for carpeta in CARPETAS for p in (RAIZ / carpeta).glob("*.py"))


class PruebaSoloBibliotecaEstandar(unittest.TestCase):
    def test_hay_archivos_que_mirar(self):
        """Cero de cero: si el glob dejara de casar, la prueba de abajo pasaría en vacío."""
        nombres = {p.name for p in archivos()}
        self.assertIn("comun.py", nombres)
        self.assertIn("correr.py", nombres)
        self.assertIn("ayuda.py", nombres)

    def test_ningun_import_de_terceros(self):
        propios = {p.stem for p in archivos()}
        problemas = [
            f"{p.relative_to(RAIZ).as_posix()}:{linea} import {modulo}"
            for p in archivos()
            for linea, modulo in de_terceros(p.read_text(encoding="utf-8"), propios)
        ]
        self.assertEqual(
            [],
            problemas,
            "estos imports no son de la biblioteca estándar: en el CI de una aplicación no "
            "hay `pip install`, así que el juez moriría al importarse",
        )


class PruebaDelDetector(unittest.TestCase):
    """El detector tiene que ver lo que dice ver, sobre fuentes sintéticos."""

    def test_ve_un_import_de_terceros(self):
        self.assertEqual([(1, "yaml")], de_terceros("import yaml\n", set()))

    def test_ve_un_from_import_y_un_submodulo(self):
        fuente = "import os\nfrom requests.adapters import HTTPAdapter\nimport numpy.linalg as la\n"
        self.assertEqual([(2, "requests"), (3, "numpy")], de_terceros(fuente, set()))

    def test_ve_el_import_dentro_de_una_funcion(self):
        """El import perezoso es justo el que un bucle de «importa el módulo» no ejecuta."""
        fuente = "def f():\n    import yaml\n    return yaml\n"
        self.assertEqual([(2, "yaml")], de_terceros(fuente, set()))

    def test_la_biblioteca_estandar_y_lo_propio_no_cuentan(self):
        fuente = "import json\nfrom pathlib import Path\nimport comun\nfrom comun_yaml import x\n"
        self.assertEqual([], de_terceros(fuente, {"comun", "comun_yaml"}))

    def test_un_import_relativo_no_es_de_terceros(self):
        self.assertEqual([], de_terceros("from . import vecino\nfrom .otro import x\n", set()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
