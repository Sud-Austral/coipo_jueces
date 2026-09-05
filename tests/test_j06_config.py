"""Pruebas de j06 — superficie de configuración.

Fixtures sintéticos. Ningún `.env.example` de aquí abajo es copia de uno real.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ayuda import CasoConRepo, RepoSintetico  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jueces"))
import j06_config as j06  # noqa: E402

ENV_BUENO = """\
APP_ENV=production
APP_PORT=8104
DATABASE_HOST=<IP_INTERNA_BD>
DATABASE_PORT=5432
DATABASE_USER=<usuario>
DATABASE_PASSWORD=<generar: openssl rand -hex 32>
DATABASE_NAME=<nombre_bd>
SESSION_SECRET=<generar: openssl rand -hex 32>
SESSION_HTTPS_ONLY=true
"""

# La señal de que un repositorio lo despliega el pipeline de la flota. Sin
# esto, `comprobar_ejemplo` no aplica: no es una aplicación.
COMPOSE_MINIMO = """\
services:
  app:
    build:
      context: .
    ports:
      - "${APP_PORT:-8080}:8000"
"""

DOCKERFILE = "FROM python:3.13-slim\nWORKDIR /app\n"
CI = """\
name: CI
on: [push]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@0000000000000000000000000000000000000000
        with:
          python-version: "3.13"
"""


class PruebaEjemplo(CasoConRepo):
    MODULO = j06

    def _base(self, env: str = ENV_BUENO) -> None:
        self.repo.escribe("docker-compose.yml", COMPOSE_MINIMO)
        self.repo.escribe(".env.example", env)
        self.repo.escribe("backend/Dockerfile", DOCKERFILE)
        self.repo.escribe(".github/workflows/ci.yml", CI)

    def test_configuracion_correcta_no_bloquea(self):
        """El caso de referencia. Si esto falla, el resto de pruebas mienten."""
        self._base()
        self.assertSinBloqueos()

    def test_sin_env_example_bloquea(self):
        self.repo.escribe("docker-compose.yml", COMPOSE_MINIMO)
        self.repo.escribe("backend/Dockerfile", DOCKERFILE)
        self.assertBloquea("no hay `.env.example`")

    def test_falta_una_variable_base_bloquea(self):
        self._base(ENV_BUENO.replace("DATABASE_HOST=<IP_INTERNA_BD>\n", ""))
        self.assertBloquea("faltan variables base")

    def test_app_port_entrecomillado_bloquea(self):
        """El pipeline lo extrae con `cut -d= -f2`: las comillas viajan al valor."""
        self._base(ENV_BUENO.replace("APP_PORT=8104", 'APP_PORT="8104"'))
        self.assertBloquea("comillas o espacios")

    def test_database_url_bloquea(self):
        self._base(ENV_BUENO + "DATABASE_URL=postgresql://a:b@c/d\n")
        self.assertBloquea("`DATABASE_URL` como variable de entorno")


    def test_un_repo_que_no_despliega_no_necesita_env_example(self):
        """`coipo_jueces` y `coipo_master_produccion` no son aplicaciones.

        Sin `docker-compose.yml` no hay despliegue por el pipeline de la flota,
        y por tanto no hay contrato de `.env` que cumplir. Exigirselo era el
        falso positivo que este juez producia sobre su propio repositorio.
        """
        self.repo.escribe("README.md", "# doctrina\n")
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertTrue(any("no lo despliega el pipeline" in n for n in r.no_evaluado))


class PruebaGrafiaDeSesion(CasoConRepo):
    MODULO = j06

    def _con(self, env: str) -> None:
        self.repo.escribe("docker-compose.yml", COMPOSE_MINIMO)
        self.repo.escribe(".env.example", env)
        self.repo.escribe("backend/Dockerfile", DOCKERFILE)
        self.repo.escribe(".github/workflows/ci.yml", CI)

    def test_dos_grafias_conviviendo_bloquea(self):
        """El defecto real de coipo_prensa2, reproducido en sintético."""
        self._con(ENV_BUENO + "SESION_HTTPS_ONLY=false\nSESION_ABSOLUTA_SEGUNDOS=2592000\n")
        self.assertBloquea("conviven las dos grafías")

    def test_una_sola_grafia_no_bloquea(self):
        """Consistente es correcto, aunque no sea la grafía del decreto.

        Un repositorio que usa SESION_ en TODAS partes funciona: la variable se
        lee con el nombre con que se escribe. El agujero aparece cuando conviven
        las dos y alguien escribe la que no toca.
        """
        self._con(ENV_BUENO.replace("SESSION_SECRET", "SESION_SECRET")
                           .replace("SESSION_HTTPS_ONLY", "SESION_HTTPS_ONLY"))
        self.assertSinBloqueos()

    def test_se_puede_suprimir_con_motivo(self):
        self._con(ENV_BUENO
                  + "# coipo-jueces:ignorar(G8-6) convención heredada, migra en el trimestre\n"
                    "SESION_HTTPS_ONLY=false\n")
        r = self.repo.juzga()
        self.assertSinBloqueos(r)
        self.assertEqual(1, len(r.supresiones))


class PruebaVersiones(CasoConRepo):
    MODULO = j06

    def _con(self, dockerfile: str, ci: str) -> None:
        self.repo.escribe("docker-compose.yml", COMPOSE_MINIMO)
        self.repo.escribe(".env.example", ENV_BUENO)
        self.repo.escribe("backend/Dockerfile", dockerfile)
        self.repo.escribe(".github/workflows/ci.yml", ci)

    def test_ci_prueba_una_version_que_no_se_construye(self):
        """El defecto real de coipo_prensa2: construye 3.14, prueba 3.11."""
        self._con("FROM python:3.14-slim\n", CI.replace('"3.13"', '"3.11"'))
        self.assertBloquea("ninguna imagen se construye con esa versión")

    def test_version_coincidente_no_bloquea(self):
        self._con(DOCKERFILE, CI)
        self.assertSinBloqueos()

    def test_version_del_ci_mas_corta_casa_por_componentes(self):
        """`3.1` no puede casar con `3.13` por prefijo de cadena.

        Es un error clásico de comparación de versiones, y aquí produciría un
        verde falso justo en la comprobación que existe para evitar verdes
        falsos.
        """
        self._con("FROM python:3.13-slim\n", CI.replace('"3.13"', '"3.1"'))
        self.assertBloquea("ninguna imagen se construye con esa versión")

    def test_sin_dockerfile_no_se_declara_limpio(self):
        self.repo.escribe(".env.example", ENV_BUENO)
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertTrue(any("no hay Dockerfile" in n for n in r.no_evaluado))

    def test_varias_versiones_del_mismo_lenguaje_avisan(self):
        self.repo.escribe(".env.example", ENV_BUENO)
        self.repo.escribe("backend/Dockerfile", "FROM python:3.13-slim\n")
        self.repo.escribe("correo/Dockerfile", "FROM python:3.11-slim\n")
        self.repo.escribe(".github/workflows/ci.yml", CI)
        self.assertAvisa("varias versiones de python")


class PruebaDelPropioJuez(unittest.TestCase):
    def test_el_juez_detecta_lo_que_dice_detectar(self):
        """Sin esto, vaciar `comprobar_grafia_de_sesion` deja la suite en verde."""
        repo = RepoSintetico(j06)
        try:
            repo.escribe("docker-compose.yml", COMPOSE_MINIMO)
            repo.escribe(".env.example", ENV_BUENO + "SESION_HTTPS_ONLY=false\n")
            repo.escribe("backend/Dockerfile", DOCKERFILE)
            repo.escribe(".github/workflows/ci.yml", CI)
            self.assertTrue(repo.juzga().bloqueantes,
                            "el juez dejó pasar las dos grafías conviviendo")
        finally:
            repo.cierra()


if __name__ == "__main__":
    unittest.main(verbosity=2)
