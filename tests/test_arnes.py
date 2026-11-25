"""El arnés de las pruebas limpia lo que crea.

EL DEFECTO, medido el 2026-11-24. `RepoSintetico.cierra()` era
`shutil.rmtree(self.dir, ignore_errors=True)`. git escribe sus objetos sueltos como sólo
lectura, en Windows `rmtree` no los borra, e `ignore_errors=True` callaba el fallo: cada
prueba dejaba su repositorio en `%TEMP%` con el `.git` dentro. Había 22.651 directorios
`coipo_jueces_*`, el más antiguo del 2026-11-20, y cada corrida de la suite añadía unos 400.

No rompía ninguna prueba, y por eso nadie lo vio: el informe de optimización del 2026-11-21
anotó diecinueve fallos inestables de `git init` con el disco temporal casi lleno, sin
relacionarlos con esto (la relación es una hipótesis: no la comprobé).

Un arnés que ensucia la máquina donde corre es un defecto del arnés aunque la suite salga
verde. Estas pruebas hacen que deje de ser invisible.
"""

from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import RepoSintetico, borrar_arbol, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j01_despliegue as j01  # noqa: E402


class PruebaLimpieza(unittest.TestCase):
    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")

    def test_cierra_borra_el_repositorio_con_su_git(self):
        """El caso real: un archivo versionado deja objetos de sólo lectura en `.git`."""
        repo = RepoSintetico(j01)
        repo.escribe("README.md", "# x\n")
        objetos = [p for p in (repo.dir / ".git" / "objects").rglob("*") if p.is_file()]
        self.assertTrue(objetos, "el fixture no creó ningún objeto de git: no prueba nada")
        repo.cierra()
        self.assertFalse(repo.base.exists(), f"quedó en el disco: {repo.base}")

    def test_con_nombre_se_borra_tambien_la_base(self):
        """`nombre` crea una subcarpeta: hasta el 2026-11-25 la base de `mkdtemp` se quedaba."""
        repo = RepoSintetico(j01, nombre="mi_app")
        self.assertEqual("mi_app", repo.dir.name)
        self.assertNotEqual(repo.base, repo.dir)
        repo.cierra()
        self.assertFalse(repo.base.exists(), f"quedó en el disco: {repo.base}")

    def test_cierra_dos_veces_no_falla(self):
        repo = RepoSintetico(j01)
        repo.cierra()
        repo.cierra()


class PruebaBorrarArbol(unittest.TestCase):
    def test_borra_un_archivo_de_solo_lectura(self):
        """Lo que `ignore_errors=True` callaba, sin depender de git."""
        base = Path(tempfile.mkdtemp(prefix="coipo_jueces_arnes_"))
        archivo = base / "sub" / "objeto"
        archivo.parent.mkdir()
        archivo.write_text("x", encoding="utf-8")
        archivo.chmod(stat.S_IREAD)
        borrar_arbol(base)
        self.assertFalse(base.exists(), f"quedó en el disco: {base}")

    def test_lo_que_no_existe_no_es_un_error(self):
        borrar_arbol(Path(tempfile.gettempdir()) / "coipo_jueces_arnes_no_existe_nunca")


if __name__ == "__main__":
    unittest.main(verbosity=2)
