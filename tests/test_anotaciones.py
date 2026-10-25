"""En modo advisory ningún hallazgo sale como `::error::` (auditoría del 2026-10-25).

`_anotacion_github` prometía en su docstring que «en advisory todo baja a
`::warning::`», y el código emitía `::error::` para todo BLOQUEA sin mirar el
modo. En el PR de una aplicación en advisory eso pinta errores rojos en el diff de
un build que pasa: la anotación miente sobre el estado del build, y una salida que
miente se aprende a ignorar.

Se prueba de las dos maneras: llamando a `informar` y corriendo `correr.py` como
lo corre el CI, con `GITHUB_ACTIONS=true`.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j09_secretos  # noqa: E402
from comun import Resultado, informar  # noqa: E402

# 64 hex inventados en el momento: no abren nada.
HEX_FALSO = "9c2f4e1a7b3d6058e1f2a9c4d7b03e6f5a8c1d2e3f4a5b6c7d8e9f0a1b2c3d4e"


def _resultado_con_bloqueo() -> Resultado:
    r = Resultado(juez="j09", descripcion="prueba")
    r.comprobo("algo")
    r.bloquea("G8-4", ".env", "secreto versionado", "se publica", linea=1)
    return r


class PruebaInformar(unittest.TestCase):

    def _salida(self, modo: str) -> str:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            informar(_resultado_con_bloqueo(), modo=modo, en_github=True)
        return buf.getvalue()

    def test_advisory_baja_a_warning(self):
        salida = self._salida("advisory")
        self.assertNotIn("::error", salida)
        self.assertIn("::warning file=.env,line=1::[j09/G8-4]", salida)

    def test_bloqueante_sigue_siendo_error(self):
        self.assertIn("::error file=.env,line=1::[j09/G8-4]", self._salida("bloqueante"))


class PruebaCorrerEnGithub(unittest.TestCase):

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: esta prueba lo necesita de verdad")
        self.repo = RepoSintetico(j09_secretos)
        self.addCleanup(self.repo.cierra)
        self.repo.escribe(".env", f"JWT_SECRET={HEX_FALSO}\n")

    def _correr(self, modo: str) -> subprocess.CompletedProcess:
        entorno = {k: v for k, v in os.environ.items() if k != "GITHUB_OUTPUT"}
        entorno.update(GITHUB_ACTIONS="true", PYTHONUTF8="1")
        return subprocess.run(
            [sys.executable, "-B", str(RAIZ / "jueces" / "correr.py"), "--repo", str(self.repo.dir),
             "--modo", modo, "--perfil", "encuadre_operativo", "--jueces", "j09"],
            capture_output=True, encoding="utf-8", errors="replace", env=entorno)

    def test_advisory_no_emite_error_y_sale_0(self):
        p = self._correr("advisory")
        self.assertEqual(0, p.returncode, p.stdout[-1500:])
        self.assertNotIn("::error", p.stdout)
        self.assertIn("::warning file=.env", p.stdout)

    def test_bloqueante_emite_error_y_sale_1(self):
        p = self._correr("bloqueante")
        self.assertEqual(1, p.returncode)
        self.assertIn("::error file=.env", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
