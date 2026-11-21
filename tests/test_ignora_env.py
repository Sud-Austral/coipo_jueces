"""`ignora_env()` de `comun.py`: ¿este `.gitignore` o `.dockerignore` deja fuera el `.env`?

Hasta el 2026-11-21 lo respondían tres listas distintas: `j01` aceptaba `.env.*` —que
NO deja fuera `.env`—, `j08` no aceptaba `**/.env` ni `/.env*` y bloqueaba un
`.gitignore` correcto, y `j09` avisaba de `.env` «sin anclar» mientras `j08` lo daba
por bueno. Ahora es una sola función, y estas pruebas fijan su lectura.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j01_despliegue as j01  # noqa: E402
import j08_rsync as j08  # noqa: E402
from comun import ignora_env  # noqa: E402


class PruebaIgnoraEnv(unittest.TestCase):
    def test_las_formas_que_dejan_fuera_el_env_de_la_raiz(self):
        for patron in (
            ".env",
            "/.env",
            "**/.env",
            ".env*",
            "/.env*",
            "**/.env*",
            "*.env",
            "/*.env",
            "**/*.env",
            "  .env  ",
        ):
            with self.subTest(patron=patron):
                self.assertTrue(ignora_env([patron]))

    def test_las_que_no(self):
        casos = {
            "`.env.*` exige un punto despues de env": [".env.*"],
            "una barra final sólo casa directorios": [".env/"],
            "un comentario no ignora nada": ["# .env"],
            "otra ruta": ["data/", "backend/.env"],
            "vacio": [],
        }
        for motivo, lineas in casos.items():
            with self.subTest(motivo=motivo):
                self.assertFalse(ignora_env(lineas))

    def test_una_negacion_posterior_lo_vuelve_a_incluir(self):
        """En los dos formatos manda la última línea que casa."""
        self.assertFalse(ignora_env([".env", "!.env"]))
        self.assertFalse(ignora_env(["/.env*", "!/.env"]))
        self.assertTrue(ignora_env(["!.env", ".env"]))


class PruebaJ08(CasoConRepo):
    MODULO = j08

    def test_doble_asterisco_ignora_el_env(self):
        self.repo.escribe(".gitignore", "**/.env\n/data/\n")
        self.assertSinRegla("G8-8")

    def test_env_con_asterisco_anclado_ignora_el_env(self):
        self.repo.escribe(".gitignore", "/.env*\n")
        self.assertSinRegla("G8-8")

    def test_env_punto_asterisco_no_ignora_el_env(self):
        self.repo.escribe(".gitignore", ".env.*\n")
        self.assertRegla("G8-8", "BLOQUEA", "`.env` no está ignorado")


class PruebaJ01(CasoConRepo):
    MODULO = j01

    COMPOSE = (
        "services:\n  app:\n    build:\n      context: .\n    ports:\n"
        '      - "${APP_PORT:-8080}:8000"\n    restart: unless-stopped\n'
    )

    def test_env_punto_asterisco_no_excluye_el_env_del_contexto(self):
        self.repo.escribe("docker-compose.yml", self.COMPOSE)
        self.repo.escribe(".dockerignore", ".git\n.env.*\n")
        self.assertRegla("DK-4", "BLOQUEA", "no excluye `.env`")

    def test_doble_asterisco_excluye_el_env_del_contexto(self):
        self.repo.escribe("docker-compose.yml", self.COMPOSE)
        self.repo.escribe(".dockerignore", ".git\n**/.env\n")
        self.assertSinRegla("DK-4")


if __name__ == "__main__":
    unittest.main(verbosity=2)
