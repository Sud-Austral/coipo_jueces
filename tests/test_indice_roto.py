"""«Cero de cero»: si `git ls-files` FALLA, ningún juez puede salir OK ni NO_APLICA.

EL DEFECTO, encontrado en la auditoría del 2026-10-25. `Repo.versionados()`
atrapaba el error de git (código 128: `.git` roto, un `gitdir:` que apunta a
ninguna parte, un clon a medias) y devolvía una lista VACÍA. El comentario de
`comun.py` prometía que «el juez lo declara como no evaluado», y no era cierto:
vacío y fallido eran indistinguibles, así que

  - j13 no encontraba hojas de estilo y salía NO_APLICA («no tiene interfaz»);
  - j16 medía cero archivos y salía OK («COD-1: tamaño de 0 archivos»);
  - j11 no encontraba Python y BLOQUEABA por «no hay /health» (un rojo falso);
  - j05 no encontraba CORS y salía NO_APLICA.

Es el incidente de COIPO_PDF_EXCEL en otra forma: cero comprobaciones leídas
como conformidad. Ahora `Repo.indice_roto()` dice POR QUÉ falló y cada juez que
lee el índice lo anota en `no_evaluado` y no dictamina nada (SIN_EVALUAR).

El repositorio roto se fabrica con un `.git` que es un ARCHIVO `gitdir:` hacia un
directorio que no existe: git sale 128 y no sube a buscar un repositorio padre.

LA LISTA SALE DEL CÓDIGO (2026-11-25). Hasta ese día esta prueba llevaba a mano la
lista de jueces que leen el índice, y le faltaba `j12`: lo lee a través de
`comun_auditoria.lo_que_falta()` (AUD-1) sin llamar a `sin_indice()`. `correr.py`
presume de que añadir un juez no exige tocar ninguna lista; ésta era una, y un juez
nuevo que leyera el índice sin la guarda no lo habría visto nadie. Ahora se deduce:
lee el índice todo juez que llama a `.versionados(`, él o un auxiliar que importa.
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import RepoSintetico, borrar_arbol, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
JUECES = RAIZ / "jueces"
sys.path.insert(0, str(JUECES))

import j16_codigo  # noqa: E402
from comun import Repo, Resultado  # noqa: E402

ES_JUEZ = re.compile(r"^j\d{2}_[a-z_]+$")
# `comun.py` DEFINE `versionados()` e `indice_roto()`: importarlo no es leer el índice.
DEFINE_EL_INDICE = "comun"

# Jueces que leen el índice y TODAVÍA no llaman a `sin_indice()`. Es deuda declarada, con
# su motivo. `test_la_deuda_declarada_sigue_siendo_deuda` falla el día que uno de éstos
# ya cumple: la línea se borra entonces, no se queda aquí tapando al siguiente.
PENDIENTES = {
    "j12_semilla": "lee el índice por `comun_auditoria.lo_que_falta()` (AUD-1) sin llamar a "
    "`sin_indice()`: con el índice ilegible AUD-1 sale N/A y el gate pasa de 1 a 0. "
    "Anotado el 2026-11-25; se arregla con el resto de los falsos verdes de `j12`.",
}

# Un CSS con los tres defectos de j13 y un archivo de 1200 líneas: si un juez
# llegara a mirar, tendría con qué dar HALLAZGOS. Que salga SIN_EVALUAR prueba
# que no miró, no que no hubiera nada.
CSS_MALO = ":root { --v: #064928; }\n.t { color: var(--v); transition: all .2s; }\n.t:focus { outline: 0; }\n"


def _importados(fuente: str, locales: set[str]) -> set[str]:
    """Los módulos de `jueces/` que un fuente importa, sin el que define el índice."""
    nombres: set[str] = set()
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            nombres |= {alias.name for alias in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return (nombres & locales) - {DEFINE_EL_INDICE}


def lee_el_indice(nombre: str, fuentes: dict[str, str]) -> bool:
    """¿El módulo `nombre`, o un auxiliar que importa, llama a `.versionados(`?"""
    vistos: set[str] = set()
    pendientes = [nombre]
    while pendientes:
        actual = pendientes.pop()
        if actual in vistos or actual not in fuentes:
            continue
        vistos.add(actual)
        if ".versionados(" in fuentes[actual]:
            return True
        pendientes += sorted(_importados(fuentes[actual], set(fuentes)))
    return False


def jueces_que_leen_el_indice() -> list[str]:
    fuentes = {p.stem: p.read_text(encoding="utf-8") for p in JUECES.glob("*.py")}
    return sorted(n for n in fuentes if ES_JUEZ.match(n) and lee_el_indice(n, fuentes))


class PruebaIndiceRoto(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="coipo_jueces_roto_"))
        self.addCleanup(borrar_arbol, self.dir)
        (self.dir / ".git").write_text("gitdir: ./no-existe-este-directorio\n", encoding="utf-8")
        (self.dir / ".semilla").write_text(
            "version: 2026-10-25\nfabrica: 2026-10-25\n", encoding="utf-8"
        )
        (self.dir / "docker-compose.yml").write_text(
            "services:\n  app:\n    build: .\n", encoding="utf-8"
        )
        (self.dir / "src").mkdir()
        (self.dir / "src" / "estilos.css").write_text(CSS_MALO, encoding="utf-8")
        (self.dir / "src" / "grande.py").write_text("x = 1\n" * 1200, encoding="utf-8")

    def _juzga(self, nombre: str) -> Resultado:
        r = Resultado(juez=nombre, descripcion="prueba")
        importlib.import_module(nombre).comprobar(Repo(self.dir), r)
        return r

    @staticmethod
    def _cumple(r: Resultado) -> bool:
        return r.veredicto == "SIN_EVALUAR" and any("git ls-files" in n for n in r.no_evaluado)

    def test_el_repo_dice_por_que_fallo(self):
        repo = Repo(self.dir)
        self.assertEqual([], repo.versionados())
        self.assertIsNotNone(repo.indice_roto(), "un fallo de git no puede leerse como «vacío»")

    def test_la_lista_sale_del_codigo_y_no_esta_vacia(self):
        """Cero de cero: si el detector dejara de ver lecturas, la prueba de abajo pasaría
        sin juzgar a nadie."""
        leen = jueces_que_leen_el_indice()
        for conocido in ("j05_cors", "j09_secretos", "j13_interfaz", "j16_codigo"):
            self.assertIn(conocido, leen)
        self.assertIn(
            "j12_semilla", leen, "j12 lee el índice por `comun_auditoria`: no se siguió el import"
        )

    def test_ningun_juez_que_lee_el_indice_sale_ok_ni_no_aplica(self):
        for nombre in jueces_que_leen_el_indice():
            if nombre in PENDIENTES:
                continue
            with self.subTest(juez=nombre):
                r = self._juzga(nombre)
                self.assertEqual(
                    "SIN_EVALUAR",
                    r.veredicto,
                    f"{nombre}: {r.comprobado} {r.no_aplica} {[h.mensaje for h in r.hallazgos]}",
                )
                self.assertTrue(any("git ls-files" in n for n in r.no_evaluado), r.no_evaluado)

    def test_la_deuda_declarada_sigue_siendo_deuda(self):
        """Una excepción que nadie revisa se queda para siempre. Ésta caduca sola."""
        leen = jueces_que_leen_el_indice()
        for nombre, motivo in PENDIENTES.items():
            with self.subTest(juez=nombre):
                self.assertIn(
                    nombre, leen, f"{nombre} ya no lee el índice: borra su línea de PENDIENTES"
                )
                self.assertFalse(
                    self._cumple(self._juzga(nombre)),
                    f"{nombre} ya llama a `sin_indice()`: borra su línea de PENDIENTES. "
                    f"Decía: {motivo}",
                )


class PruebaDelDetector(unittest.TestCase):
    """El detector tiene que ver lo que dice ver, sobre fuentes sintéticos."""

    def test_ve_la_lectura_directa(self):
        fuentes = {"j90_x": "def comprobar(repo, r):\n    return repo.versionados()\n"}
        self.assertTrue(lee_el_indice("j90_x", fuentes))

    def test_ve_la_lectura_a_traves_de_un_auxiliar(self):
        """El caso de j12: el juez no nombra el índice; lo lee el módulo que importa."""
        fuentes = {
            "j90_x": "from auxiliar import mirar\n\ndef comprobar(repo, r):\n    mirar(repo)\n",
            "auxiliar": "def mirar(repo):\n    return set(repo.versionados())\n",
        }
        self.assertTrue(lee_el_indice("j90_x", fuentes))

    def test_importar_comun_no_es_leer_el_indice(self):
        fuentes = {
            "j90_x": "from comun import Repo\n\ndef comprobar(repo, r):\n    repo.texto('x')\n",
            "comun": "class Repo:\n    def indice_roto(self):\n        self.versionados()\n",
        }
        self.assertFalse(lee_el_indice("j90_x", fuentes))

    def test_un_import_circular_no_cuelga(self):
        fuentes = {"j90_x": "import auxiliar\n", "auxiliar": "import j90_x\n"}
        self.assertFalse(lee_el_indice("j90_x", fuentes))


class PruebaIndiceVacio(unittest.TestCase):
    """La otra dirección: un repositorio sano y sin archivos NO está roto."""

    def test_vacio_no_es_roto(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: esta prueba lo necesita de verdad")
        repo = RepoSintetico(j16_codigo)
        self.addCleanup(repo.cierra)
        r = Repo(repo.dir)
        self.assertEqual([], r.versionados())
        self.assertIsNone(r.indice_roto())


if __name__ == "__main__":
    unittest.main(verbosity=2)
