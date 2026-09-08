"""Regresión de la revisión adversaria del 2026-09-08.

Cada prueba fija un defecto que se REPRODUJO con un comando antes de arreglarlo.
El nombre de cada una dice el síntoma; el docstring, por qué importaba.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo, RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import comun  # noqa: E402
import j06_config as j06  # noqa: E402
import j11_salud as j11  # noqa: E402
import j12_semilla as j12  # noqa: E402
import j13_interfaz as j13  # noqa: E402
from comun import Resultado, YamlNoSoportado, carga_yaml  # noqa: E402


class PruebaComun(unittest.TestCase):

    def test_7_un_escalar_como_menos_menos_cinco_no_revienta(self):
        """`command: --5` en un compose tumbaba a j01 entero con ValueError:
        `"--5".lstrip("-").isdigit()` es True y `int("--5")` no existe."""
        self.assertEqual("--5", carga_yaml("a: --5\n")["a"])
        self.assertEqual(-5, carga_yaml("a: -5\n")["a"])

    def test_8_una_ancla_en_posicion_de_valor_se_rechaza_y_no_se_interpreta_mal(self):
        """El docstring prometía `YamlNoSoportado` y el parser sólo lo lanzaba si la
        LÍNEA empezaba por `&`. En YAML real la ancla va en el valor
        (`x-comun: &comun`) y el alias en `<<: *comun`: pasaban como cadenas y
        los hijos se colgaban de la raíz, en silencio."""
        for texto in ("x-comun: &comun\n  restart: always\n",
                      "services:\n  app:\n    <<: *comun\n",
                      "ports:\n  - *puerto\n"):
            with self.assertRaises(YamlNoSoportado, msg=texto):
                carga_yaml(texto)
        # y un `*` que NO es alias sigue siendo un valor legítimo
        self.assertEqual("*", carga_yaml('a: "*"\n')["a"])

    def test_9_un_juez_con_hallazgos_nunca_es_sin_evaluar(self):
        """j11, j06 y j08 anotan la AUSENCIA de /health, .env.example o .gitignore
        antes de comprobo(): el informe decía «no comprobó nada» y a la vez
        emitía ::error:: y exit 1. Dos estados a la vez."""
        r = Resultado("jx", "prueba")
        r.bloquea("X-1", "", "falta algo", "se cae", arreglo="ponlo")
        self.assertEqual("HALLAZGOS", r.veredicto)
        self.assertFalse(r.comprobado, "la prueba sólo vale si no hubo comprobo()")

    def test_11_un_bom_no_produce_bloqueantes_falsos(self):
        """`\\ufeffDATABASE_HOST=` no casaba con `^\\s*CLAVE=` y j06 decía que
        faltaban las cinco variables. utf-8-sig lee igual sin BOM."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.txt"
            p.write_bytes("\ufeffhola\n".encode("utf-8"))
            self.assertEqual("hola\n", comun.Repo(d).texto("x.txt"))


class PruebaJ06ConBom(CasoConRepo):
    MODULO = j06

    def test_11_env_example_con_bom_no_es_un_bloqueante(self):
        self.repo.escribe("docker-compose.yml",
                          "services:\n  app:\n    image: x\n    ports:\n"
                          '      - "${APP_PORT:-8080}:8000"\n')
        self.repo.escribe(".env.example",
                          "\ufeffDATABASE_HOST=x\nDATABASE_PORT=5432\nDATABASE_USER=x\n"
                          "DATABASE_PASSWORD=<generar>\nDATABASE_NAME=x\nAPP_PORT=8080\n")
        r = self.repo.juzga()
        faltan = [h for h in r.hallazgos if "DATABASE_" in h.mensaje and "falta" in h.mensaje.lower()]
        self.assertFalse(faltan, [h.mensaje for h in r.hallazgos])


class PruebaJ11SinBackend(CasoConRepo):
    MODULO = j11

    def test_26_software_de_terceros_sin_python_es_no_aplica(self):
        """coipo_n8n: compose, nginx y docs, ni una línea de Python. Exigirle un
        endpoint propio ponía rojo al repositorio que AGENTS.md declara excepción
        legítima y referencia de calibración."""
        self.repo.escribe("docker-compose.yml",
                          "services:\n  n8n:\n    image: n8nio/n8n\n    healthcheck:\n"
                          '      test: ["CMD", "wget", "-q", "-O-", "http://127.0.0.1:5678/healthz"]\n')
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertFalse(r.hallazgos)


SEMILLA_UI = "version: 2026-09-08\nadopta: interfaz\n"


class PruebaJ13Revision(CasoConRepo):
    MODULO = j13

    def setUp(self):
        super().setUp()
        self.repo.escribe(".semilla", SEMILLA_UI)

    def test_10_un_comentario_que_nombra_la_consulta_no_es_el_bloque(self):
        """La regex buscaba la PALABRA y la primera aparición estaba en un
        comentario de cabecera: el juez tomaba el siguiente `{...}` cualquiera
        como «el bloque». Ocurrió escribiendo el propio comentario del bloque."""
        self.repo.escribe("src/a.css",
                          "/* Este archivo tiene un bloque prefers-reduced-motion abajo */\n"
                          ".x { color: #111; transition: all .2s; }\n"
                          "@media (prefers-reduced-motion: reduce) {\n"
                          "  *, *::before, *::after { transition-duration: .01ms !important; }\n}\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-15"],
                         [h.mensaje for h in r.hallazgos])

    def test_10_un_comentario_no_hace_pasar_un_bloque_selectivo(self):
        """Y al revés: el comentario no puede tapar un bloque que sí es selectivo."""
        self.repo.escribe("src/a.css",
                          "/* prefers-reduced-motion */\n"
                          ".a { transition: all .2s; }\n.b { transition: color .2s; }\n"
                          "@media (prefers-reduced-motion: reduce) {\n  .a { transition: none; }\n}\n")
        self.assertBloquea("es selectivo")

    def test_12_un_token_redefinido_en_la_segunda_regla_del_media_no_es_huerfano(self):
        """`BLOQUE_OSCURO` cortaba en la PRIMERA `}`: dentro del @media sólo veía
        la primera regla y los tokens de la segunda salían como huérfanos."""
        self.repo.escribe("src/a.css",
                          ":root { --texto: #111; --borde: #ccc; }\n"
                          "@media (prefers-color-scheme: dark) {\n"
                          "  :root { --texto: #eee; }\n  .card { --borde: #444; }\n}\n"
                          ".a { color: var(--texto); border: 1px solid var(--borde); }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-3"],
                         [h.mensaje for h in r.hallazgos])


class PruebaAdoptaVacio(CasoConRepo):
    MODULO = j12

    def test_15_adopta_vacio_no_apaga_el_juez_en_silencio(self):
        """`adopta:` sin capas salía NO_APLICA con exit 0, como si fuera legítimo.
        No declara nada: es un error de escritura, y se dice."""
        self.repo.escribe(".semilla", "version: 2026-09-08\nadopta:\n")
        self.repo.escribe("frontend/nginx.conf", "server {}\n")
        r = self.repo.juzga()
        self.assertEqual("SIN_EVALUAR", r.veredicto)
        self.assertTrue(any("VACIA" in n for n in r.no_evaluado), r.no_evaluado)
        self.assertFalse(r.supresiones, "vacío no es una supresión: no declara nada")


class PruebaCorrer(unittest.TestCase):
    """correr.py como subproceso, sobre una copia de jueces/ con un juez extra."""

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH")
        self.tmp = Path(tempfile.mkdtemp())
        self.jueces = self.tmp / "jueces"
        shutil.copytree(RAIZ / "jueces", self.jueces,
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.repo = RepoSintetico(j12)
        self.addCleanup(self.repo.cierra)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo.escribe("README.md", "# x\n")

    def _correr(self, *extra):
        return subprocess.run(
            [sys.executable, str(self.jueces / "correr.py"), "--repo", str(self.repo.dir),
             "--modo", "advisory", "--perfil", "encuadre_operativo", *extra],
            capture_output=True, encoding="utf-8", errors="replace")

    def test_14_un_juez_mal_nombrado_no_se_salta_en_silencio(self):
        (self.jueces / "j7_uno.py").write_text(
            '"""x"""\nPERFILES = ("encuadre_operativo",)\n'
            "def comprobar(repo, r):\n    r.comprobo('x')\n", encoding="utf-8")
        p = self._correr()
        self.assertEqual(1, p.returncode, p.stdout + p.stderr)
        self.assertIn("no sigue el patron", p.stdout + p.stderr)

    def test_un_juez_que_revienta_sale_1_y_lo_dice(self):
        (self.jueces / "j98_roto.py").write_text(
            '"""roto"""\nPERFILES = ("encuadre_operativo",)\n'
            "def comprobar(repo, r):\n    raise RuntimeError('kaput')\n", encoding="utf-8")
        p = self._correr()
        self.assertEqual(1, p.returncode)
        self.assertIn("REVENTO", p.stdout + p.stderr)
        self.assertIn("kaput", p.stdout + p.stderr)

    def test_21_las_salidas_del_job_llevan_centinela(self):
        salida = self.tmp / "out.txt"
        env = dict(os.environ, GITHUB_OUTPUT=str(salida))
        subprocess.run(
            [sys.executable, str(self.jueces / "correr.py"), "--repo", str(self.repo.dir),
             "--modo", "advisory", "--perfil", "encuadre_operativo", "--jueces", "j99"],
            capture_output=True, env=env)
        texto = salida.read_text(encoding="utf-8")
        self.assertIn("estado=no_corrio", texto)
        self.assertIn("bloqueantes=-1", texto)
        self.assertNotIn("estado=corrio", texto, "con --jueces j99 no llega a correr")


if __name__ == "__main__":
    unittest.main(verbosity=2)
