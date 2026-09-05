"""Pruebas de j02 — nombre del repositorio y APP_PORT (Guía 8, puntos 1 y 2).

Fixtures SINTÉTICOS. Este repositorio es público: copiar aquí un compose real de
CONAF publicaría en internet el mapa puerto -> aplicación de las VM del Estado,
que es justo lo que estos jueces existen para evitar.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo, RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j02_identidad as j02  # noqa: E402

COMPOSE_CORRECTO = """\
services:
  backend:
    build:
      context: .
  app:
    build:
      context: .
    ports:
      - "${APP_PORT:-8080}:8000"
"""


class PruebaNombre(unittest.TestCase):
    """Guía 8, punto 1: el nombre del repositorio ES la carpeta del servidor."""

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")

    def _juzga(self, nombre: str):
        repo = RepoSintetico(j02, nombre=nombre)
        self.addCleanup(repo.cierra)
        repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        return repo.juzga()

    def test_minusculas_no_bloquea(self):
        self.assertEqual([], self._juzga("coipo_atraso_personal").bloqueantes)

    def test_mayusculas_bloquea(self):
        r = self._juzga("COIPO_ENTREGA_PLANTA")
        self.assertTrue(any("mayúsculas" in h.mensaje for h in r.bloqueantes),
                        [h.mensaje for h in r.bloqueantes])

    def test_el_arreglo_trae_el_nombre_ya_en_minusculas(self):
        """Un arreglo que hay que traducir a mano es un arreglo que no se aplica."""
        r = self._juzga("COIPO_USUARIOS")
        arreglos = [h.arreglo for h in r.bloqueantes]
        self.assertTrue(any("coipo_usuarios" in a for a in arreglos), arreglos)

    def test_una_sola_mayuscula_tambien_bloquea(self):
        r = self._juzga("coipo_Prensa")
        self.assertEqual(1, len(r.bloqueantes), [h.mensaje for h in r.bloqueantes])


class PruebaPuerto(CasoConRepo):
    """Guía 8, punto 2: lo que SÍ se puede comprobar desde un repositorio."""

    MODULO = j02

    def test_app_port_por_variable_no_bloquea(self):
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        self.assertSinBloqueos()

    def test_puerto_cableado_bloquea(self):
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO.replace(
            '"${APP_PORT:-8080}:8000"', '"8113:8000"'))
        self.assertBloquea("cablea el puerto 8113")

    def test_otra_variable_bloquea(self):
        """El bootstrap y el smoke test usan APP_PORT; publicar por otra no sirve."""
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO.replace(
            "${APP_PORT:-8080}", "${PUERTO_WEB:-8080}"))
        self.assertBloquea("no es `APP_PORT`")

    def test_la_unicidad_se_declara_no_evaluada(self):
        """La honestidad del juez es la prueba.

        La unicidad de APP_PORT es una propiedad de la VM. Un juez que la callara
        dejaría creer que el gate la comprueba, y nadie volvería a mirar
        `ss -tlnp` antes de asignar un puerto.
        """
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        r = self.repo.juzga()
        self.assertTrue(any("unicidad de APP_PORT" in n for n in r.no_evaluado),
                        r.no_evaluado)

    def test_env_example_con_8080_no_es_hallazgo(self):
        """El caso que tumbó la primera versión de esta regla.

        `coipo_prensa2` y `coipo_dendroenergia` declaran `APP_PORT=8080` en su
        `.env.example` mientras sus puertos reales son 8101 y 8103, que viven en
        el `.env` del servidor. Un `.env.example` es un EJEMPLO: exigirle el
        valor de producción es pedirle al repositorio que lo publique.
        """
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        self.repo.escribe(".env.example", "APP_PORT=8080\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_sin_compose_no_inventa_hallazgos(self):
        self.repo.escribe("README.md", "# nada que desplegar\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(r.no_evaluado)


if __name__ == "__main__":
    unittest.main(verbosity=2)
