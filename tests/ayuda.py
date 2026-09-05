"""Arnés compartido de las pruebas.

FIXTURES SINTÉTICOS, SIEMPRE. `coipo_jueces` es un repositorio PÚBLICO: copiar
aquí un archivo de un repo privado de CONAF publicaría código interno en
internet, que es justo el tipo de fuga por conveniencia que estos jueces existen
para evitar. Todo lo que se escribe con este arnés está inventado a mano.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "jueces") not in sys.path:
    sys.path.insert(0, str(RAIZ / "jueces"))

from comun import Repo, Resultado  # noqa: E402


def hay_git() -> bool:
    return shutil.which("git") is not None


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, encoding="utf-8", errors="replace")


class RepoSintetico:
    """Un repositorio git de verdad, en un directorio temporal.

    Se usa git de verdad y no un doble porque varias reglas que se prueban SON
    "qué devuelve `git ls-files`". Un doble que devolviera una lista de rutas
    probaría el filtro, no el comportamiento, y el fallo que más importa —un
    `.env` trackeado pese al `.gitignore`— solo existe dentro de git.
    """

    def __init__(self, modulo, nombre: str | None = None) -> None:
        self.modulo = modulo
        base = Path(tempfile.mkdtemp(prefix="coipo_jueces_"))
        # `nombre` existe para j02: el nombre del DIRECTORIO es lo que ese juez
        # examina, porque es lo que el workflow usa para armar /opt/apps/<app>/.
        self.dir = base / nombre if nombre else base
        self.dir.mkdir(exist_ok=True)
        _git(self.dir, "init", "-q")
        _git(self.dir, "config", "user.email", "prueba@ejemplo.invalid")
        _git(self.dir, "config", "user.name", "prueba")

    def escribe(self, ruta: str, contenido: str, *, versionar: bool = True) -> "RepoSintetico":
        p = self.dir / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")
        if versionar:
            _git(self.dir, "add", "-f", ruta)
        return self

    def juzga(self) -> Resultado:
        r = Resultado(juez="prueba", descripcion="prueba")
        self.modulo.comprobar(Repo(self.dir), r)
        return r

    def cierra(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class CasoConRepo(unittest.TestCase):
    """Base para las pruebas que necesitan un repositorio sintético.

    `MODULO` lo fija cada subclase con el juez bajo prueba.
    """

    MODULO = None

    def setUp(self) -> None:
        if not hay_git():
            # Falla con instrucciones; nunca hace skip. Un test permanentemente
            # saltado tiene el mismo color que uno que pasa, y esa confusión es
            # la razón de que los tests de inmutabilidad de la flota lleven
            # meses sin ejecutarse.
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")
        assert self.MODULO is not None, "la subclase debe fijar MODULO"
        self.repo = RepoSintetico(self.MODULO)
        self.addCleanup(self.repo.cierra)

    # -- aserciones con nombre, para que el fallo se lea solo --------------

    def assertBloquea(self, fragmento: str, resultado=None) -> None:
        r = resultado or self.repo.juzga()
        mensajes = [h.mensaje for h in r.bloqueantes]
        self.assertTrue(
            any(fragmento in m for m in mensajes),
            f"no se bloqueó por «{fragmento}». Bloqueantes: {mensajes}",
        )

    def assertSinBloqueos(self, resultado=None) -> None:
        r = resultado or self.repo.juzga()
        self.assertEqual(
            [], r.bloqueantes,
            "no debería bloquear: " + "; ".join(
                f"{h.ubicacion()} {h.mensaje}" for h in r.bloqueantes),
        )

    def assertAvisa(self, fragmento: str, resultado=None) -> None:
        r = resultado or self.repo.juzga()
        avisos = [h.mensaje for h in r.hallazgos if h not in r.bloqueantes]
        self.assertTrue(
            any(fragmento in m for m in avisos),
            f"no avisó por «{fragmento}». Avisos: {avisos}",
        )
