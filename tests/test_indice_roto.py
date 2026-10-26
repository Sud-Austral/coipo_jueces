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
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))

import j05_cors  # noqa: E402
import j06_config  # noqa: E402
import j08_rsync  # noqa: E402
import j09_secretos  # noqa: E402
import j11_salud  # noqa: E402
import j13_interfaz  # noqa: E402
import j14_construccion  # noqa: E402
import j16_codigo  # noqa: E402
from comun import Repo, Resultado  # noqa: E402

LEEN_EL_INDICE = (j05_cors, j06_config, j08_rsync, j09_secretos, j11_salud,
                  j13_interfaz, j14_construccion, j16_codigo)

# Un CSS con los tres defectos de j13 y un archivo de 1200 líneas: si un juez
# llegara a mirar, tendría con qué dar HALLAZGOS. Que salga SIN_EVALUAR prueba
# que no miró, no que no hubiera nada.
CSS_MALO = ":root { --v: #064928; }\n.t { color: var(--v); transition: all .2s; }\n.t:focus { outline: 0; }\n"


class PruebaIndiceRoto(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="coipo_jueces_roto_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / ".git").write_text("gitdir: ./no-existe-este-directorio\n", encoding="utf-8")
        (self.dir / ".semilla").write_text("version: 2026-10-25\nfabrica: 2026-10-25\n", encoding="utf-8")
        (self.dir / "docker-compose.yml").write_text("services:\n  app:\n    build: .\n", encoding="utf-8")
        (self.dir / "src").mkdir()
        (self.dir / "src" / "estilos.css").write_text(CSS_MALO, encoding="utf-8")
        (self.dir / "src" / "grande.py").write_text("x = 1\n" * 1200, encoding="utf-8")

    def test_el_repo_dice_por_que_fallo(self):
        repo = Repo(self.dir)
        self.assertEqual([], repo.versionados())
        self.assertIsNotNone(repo.indice_roto(), "un fallo de git no puede leerse como «vacío»")

    def test_ningun_juez_que_lee_el_indice_sale_ok_ni_no_aplica(self):
        for modulo in LEEN_EL_INDICE:
            with self.subTest(juez=modulo.__name__):
                r = Resultado(juez=modulo.__name__, descripcion="prueba")
                modulo.comprobar(Repo(self.dir), r)
                self.assertEqual("SIN_EVALUAR", r.veredicto,
                                 f"{modulo.__name__}: {r.comprobado} {r.no_aplica} "
                                 f"{[h.mensaje for h in r.hallazgos]}")
                self.assertTrue(any("git ls-files" in n for n in r.no_evaluado), r.no_evaluado)


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
