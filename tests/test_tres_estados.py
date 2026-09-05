"""Cero comprobaciones no es un aprobado.

EL INCIDENTE QUE FUNDA ESTAS PRUEBAS es de esta misma organización y costó
meses. En `COIPO_PDF_EXCEL` un comprobante de AFP se clasificó como AFC: no
generó NINGUNA comparación contra su portada, y como la pantalla contaba totales
*fallidos*, cero de cero daba «todos los totales cuadran» mientras la columna
`impo_afp` salía en 0 para los 3.610 trabajadores. El verificador vacío pasaba.

Su corrección fue pasar de un booleano a TRES estados, donde «no hay con qué
comprobarlo» es distinto de «está bien». Estas pruebas fijan esa corrección aquí,
porque un juez que devuelve PASS/FAIL tiene el mismo bug por construcción:
aprueba todos los repositorios sobre los que no supo qué comprobar.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j01_despliegue as j01  # noqa: E402
from comun import Resultado  # noqa: E402


class PruebaVeredicto(unittest.TestCase):
    def test_sin_comprobaciones_es_sin_evaluar_no_ok(self):
        """El caso exacto del incidente: cero de cero NO es conforme."""
        r = Resultado(juez="jX", descripcion="prueba")
        self.assertEqual("SIN_EVALUAR", r.veredicto)

    def test_comprobo_y_limpio_es_ok(self):
        r = Resultado(juez="jX", descripcion="prueba")
        r.comprobo("algo")
        self.assertEqual("OK", r.veredicto)

    def test_comprobo_y_encontro_es_hallazgos(self):
        r = Resultado(juez="jX", descripcion="prueba")
        r.comprobo("algo")
        r.avisa("G8-0", "x", "m", "manifestacion")
        self.assertEqual("HALLAZGOS", r.veredicto)

    def test_un_juez_que_no_pudo_mirar_no_reporta_ok(self):
        """j01 sobre un repositorio sin compose: no puede evaluar nada."""
        if not hay_git():
            self.fail("falta `git` en el PATH: esta prueba lo necesita de verdad")
        repo = RepoSintetico(j01)
        try:
            repo.escribe("README.md", "# no soy una app\n")
            r = repo.juzga()
            self.assertEqual([], r.hallazgos)
            self.assertEqual("SIN_EVALUAR", r.veredicto,
                             "cero hallazgos sin comprobar nada se leería como conforme")
            self.assertTrue(r.no_evaluado)
        finally:
            repo.cierra()


class PruebaCodigoDeSalida(unittest.TestCase):
    """El comportamiento de extremo a extremo, corriendo `correr.py` de verdad.

    Se invoca como subproceso a propósito: lo que se está probando ES el código
    de salida, y comprobarlo llamando a `main()` no verificaría lo que el CI
    realmente observa.
    """

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")
        self.repo = RepoSintetico(j01)
        self.addCleanup(self.repo.cierra)
        self.repo.escribe("README.md", "# no soy una aplicacion de la flota\n")

    def _correr(self, perfil: str) -> int:
        return subprocess.run(
            [sys.executable, str(RAIZ / "jueces" / "correr.py"),
             "--repo", str(self.repo.dir), "--modo", "bloqueante", "--perfil", perfil],
            capture_output=True, encoding="utf-8", errors="replace",
        ).returncode

    def test_perfil_aplicacion_con_jueces_sin_evaluar_falla(self):
        """El perfil es una declaración, y obliga.

        Declararse `aplicacion` afirma que hay compose y `.env.example`. Si los
        jueces que verifican eso no encuentran nada que mirar, o el repositorio
        no es lo que declara o la detección está rota. Las dos son un fallo.
        """
        self.assertEqual(1, self._correr("aplicacion"))

    def test_perfil_encuadre_operativo_lo_permite(self):
        """Software de terceros SÍ puede no tener Dockerfile ni tests.

        Si esta regla no distinguiera por perfil, `coipo_n8n` —el mejor
        docker-compose de la flota— fallaría el gate por no tener lo que
        deliberadamente no tiene.
        """
        self.assertEqual(0, self._correr("encuadre_operativo"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
