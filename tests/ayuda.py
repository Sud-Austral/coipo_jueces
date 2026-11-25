"""Arnés compartido de las pruebas.

FIXTURES SINTÉTICOS, SIEMPRE. `coipo_jueces` es un repositorio PÚBLICO: copiar
aquí un archivo de un repo privado de CONAF publicaría código interno en
internet, que es justo el tipo de fuga por conveniencia que estos jueces existen
para evitar. Todo lo que se escribe con este arnés está inventado a mano.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "jueces") not in sys.path:
    sys.path.insert(0, str(RAIZ / "jueces"))

from comun import Hallazgo, Repo, Resultado, Severidad  # noqa: E402


def hay_git() -> bool:
    return shutil.which("git") is not None


def _git(cwd: Path, *args: str) -> None:
    try:
        subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as e:
        # El `CalledProcessError` crudo no decía qué pasó. El 2026-11-21 diecinueve pruebas
        # fallaron con «git init salió 128» y hubo que adivinar que era el disco temporal.
        raise RuntimeError(
            f"`git {' '.join(args)}` salió {e.returncode} en {cwd}: "
            f"{(e.stderr or '').strip()[:300] or 'sin mensaje'}. Es un fallo del entorno "
            "de la prueba, no del juez: mira el espacio libre del disco temporal."
        ) from e


def _quitar_solo_lectura(funcion, camino, _error) -> None:
    """Manejador de `rmtree`: quita el atributo de sólo lectura y reintenta."""
    os.chmod(camino, stat.S_IWRITE)
    funcion(camino)


def borrar_arbol(ruta: Path) -> None:
    """Borra un directorio temporal DE VERDAD, también en Windows.

    git escribe sus objetos sueltos como sólo lectura. En Windows `shutil.rmtree` no borra
    un archivo de sólo lectura, y con `ignore_errors=True` lo callaba: cada prueba dejaba su
    repositorio en %TEMP% con el `.git` dentro. Medido el 2026-11-24: 22.651 directorios
    `coipo_jueces_*`, el más antiguo del 2026-11-20. Aquí se quita el atributo y se
    reintenta; si aun así no se puede, FALLA: un residuo que nadie ve es el defecto.
    """
    for intento in range(3):
        if not ruta.exists():
            return
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(ruta, onexc=_quitar_solo_lectura)
            else:
                shutil.rmtree(ruta, onerror=_quitar_solo_lectura)
        except OSError:
            # Un antivirus o un `git` que todavía no soltó el archivo: se espera y se repite.
            if intento == 2:
                raise
            time.sleep(0.2)


class RepoSintetico:
    """Un repositorio git de verdad, en un directorio temporal.

    Se usa git de verdad y no un doble porque varias reglas que se prueban SON
    "qué devuelve `git ls-files`". Un doble que devolviera una lista de rutas
    probaría el filtro, no el comportamiento, y el fallo que más importa —un
    `.env` trackeado pese al `.gitignore`— solo existe dentro de git.
    """

    def __init__(self, modulo, nombre: str | None = None) -> None:
        self.modulo = modulo
        # Lo que `mkdtemp` creó y `cierra()` tiene que borrar. Con `nombre`, `self.dir` es
        # una subcarpeta: hasta el 2026-11-25 se borraba sólo ella y la base se quedaba.
        self.base = Path(tempfile.mkdtemp(prefix="coipo_jueces_"))
        # `nombre` existe para j02: el nombre del DIRECTORIO es lo que ese juez
        # examina, porque es lo que el workflow usa para armar /opt/apps/<app>/.
        self.dir = self.base / nombre if nombre else self.base
        self.dir.mkdir(exist_ok=True)
        _git(self.dir, "init", "-q")
        _git(self.dir, "config", "user.email", "prueba@ejemplo.invalid")
        _git(self.dir, "config", "user.name", "prueba")

    def remoto(self, url: str) -> RepoSintetico:
        """Declara el remoto `origin`: de él sale el nombre que juzga j02."""
        _git(self.dir, "remote", "add", "origin", url)
        return self

    def escribe(self, ruta: str, contenido: str, *, versionar: bool = True) -> RepoSintetico:
        p = self.dir / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        # `newline=""` desactiva la traduccion de fin de linea de Python. Sin
        # esto, en Windows un `\n` se escribe como `\r\n` y un `\r\n` como
        # `\r\r\n` -- que git no produce JAMAS. El fixture dejaba de representar
        # lo que hay en un repositorio real justo en las pruebas que van sobre
        # el fin de linea, que son las que lo necesitan.
        p.write_text(contenido, encoding="utf-8", newline="")
        if versionar:
            _git(self.dir, "add", "-f", ruta)
        return self

    def juzga(self) -> Resultado:
        r = Resultado(juez="prueba", descripcion="prueba")
        self.modulo.comprobar(Repo(self.dir), r)
        return r

    def cierra(self) -> None:
        borrar_arbol(self.base)


class AsercionesDeJuez(unittest.TestCase):
    """Aserciones con nombre, para que el fallo se lea solo.

    Necesitan `self.repo` con un `juzga()`. Viven aparte de `CasoConRepo` para que las
    use también quien arma su propio repositorio sintético (`test_j09_secretos.py`).
    """

    repo: RepoSintetico

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
            [],
            r.bloqueantes,
            "no debería bloquear: "
            + "; ".join(f"{h.ubicacion()} {h.mensaje}" for h in r.bloqueantes),
        )

    def assertAvisa(self, fragmento: str, resultado=None) -> None:
        r = resultado or self.repo.juzga()
        avisos = [h.mensaje for h in r.hallazgos if h not in r.bloqueantes]
        self.assertTrue(
            any(fragmento in m for m in avisos),
            f"no avisó por «{fragmento}». Avisos: {avisos}",
        )

    def assertRegla(
        self, codigo: str, severidad: str, fragmento: str = "", resultado=None
    ) -> Hallazgo:
        """Hay un hallazgo con ESE código y ESA severidad (y el fragmento, si se da).

        `assertBloquea`/`assertAvisa` miran sólo el mensaje: un hallazgo con el código
        equivocado —el `DOCKER-hc` que salía en lugar de `DK-5`, o un G8-4 donde tocaba
        G8-8— los pasa igual. Ésta mira lo que el gate cuenta y publica."""
        r = resultado or self.repo.juzga()
        esperada = Severidad(severidad)
        hallados = [
            h
            for h in r.hallazgos
            if h.regla == codigo and h.severidad is esperada and fragmento in h.mensaje
        ]
        self.assertTrue(
            hallados,
            f"no hay {codigo} {esperada.value}"
            + (f" con «{fragmento}»" if fragmento else "")
            + f". Hallazgos: {[(h.regla, h.severidad.value, h.mensaje) for h in r.hallazgos]}",
        )
        return hallados[0]

    def assertSinRegla(self, codigo: str, resultado=None) -> None:
        """Ningún hallazgo con ese código, de ninguna severidad."""
        r = resultado or self.repo.juzga()
        self.assertEqual(
            [],
            [
                f"{h.severidad.value} {h.ubicacion()} {h.mensaje}"
                for h in r.hallazgos
                if h.regla == codigo
            ],
            f"no debería haber {codigo}",
        )


class CasoConRepo(AsercionesDeJuez):
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
