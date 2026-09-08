"""`adopta: interfaz` apaga j12 y enciende j13 — en la MISMA ejecución.

POR QUÉ HACE FALTA UNA PRUEBA CRUZADA, y no basta con las unitarias de cada juez.

La clave `adopta:` existe para un caso concreto y de una sola pieza: un
repositorio que **no se sembró** pero **sí quiere el estándar de interfaz**.
`coipo_prensa2` es ése — ocho de sus archivos coinciden en ruta con
`semilla.lock` sin venir de ahí, así que el marcador antiguo le habría encendido
ocho `SEM-1` bloqueantes sobre su propio `backend/Dockerfile` y su propio
`frontend/nginx.conf`.

Las pruebas unitarias de `j12` y de `j13` comprueban cada mitad por separado, y
las dos podrían pasar mientras el comportamiento conjunto es el equivocado: basta
que las dos capas se llamen distinto en cada juez, o que una lea el marcador de
otra forma. Lo que hay que fijar es el resultado de correr el gate ENTERO una vez
sobre el mismo repositorio: un juez callado y el otro hablando.

Se invoca `correr.py` como subproceso a propósito, igual que `test_tres_estados`:
es lo que hace el CI, y comprobarlo importando módulos dejaría fuera el
descubrimiento de jueces y el resumen.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j12_semilla as j12  # noqa: E402

# Un CSS con los defectos que j13 sabe ver, para que «no hay hallazgos» no pueda
# confundirse con «el juez no miró».
CSS_MALO = (
    ":root { --v: #064928; }\n"
    "[data-theme='oscuro'] { --f: #1a1f1c; }\n"
    ".t { color: var(--v); transition: all .2s; }\n"
    ".t:focus { outline: 0; }\n"
)


class PruebaAdoptaCruzado(unittest.TestCase):

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: esta prueba lo necesita de verdad")
        self.repo = RepoSintetico(j12)
        self.addCleanup(self.repo.cierra)
        # Una aplicación mínima que NO se sembró: su nginx.conf es suyo, aunque
        # se llame igual que la pieza congelada.
        self.repo.escribe("frontend/nginx.conf", "server {\n    listen 8000;\n}\n")
        self.repo.escribe("src/estilos.css", CSS_MALO)

    def _correr(self) -> dict:
        salida = Path(self.repo.dir) / "gate.json"
        proc = subprocess.run(
            [sys.executable, str(RAIZ / "jueces" / "correr.py"),
             "--repo", str(self.repo.dir), "--modo", "advisory",
             "--perfil", "aplicacion", "--json", str(salida)],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        if not salida.exists():
            self.fail("correr.py no escribio el JSON.\n"
                      f"stdout:\n{proc.stdout[-2000:]}\n"
                      f"stderr:\n{proc.stderr[-2000:]}")
        return json.loads(salida.read_text(encoding="utf-8"))

    def _veredicto(self, datos: dict, juez: str) -> str:
        for r in datos.get("resultados", []):
            if r.get("juez", "").startswith(juez):
                return r.get("veredicto", "")
        self.fail(f"{juez} no aparece en el resumen: "
                  f"{[r.get('juez') for r in datos.get('resultados', [])]}")

    def test_adopta_interfaz_calla_a_j12_y_enciende_a_j13(self):
        """El caso completo, que es la razón de existir de la clave."""
        self.repo.escribe(".semilla",
                          "version: 2026-09-07\ngerencia: 1_banner_SECOM\n"
                          "adopta: interfaz\n")
        datos = self._correr()
        self.assertEqual("NO_APLICA", self._veredicto(datos, "j12"),
                         "j12 no debe juzgar piezas de una app que no se sembro")
        self.assertEqual("HALLAZGOS", self._veredicto(datos, "j13"),
                         "j13 SI debe juzgar: el repositorio declara la interfaz")

    def test_sin_adopta_los_dos_actuan(self):
        """La otra dirección, que es lo que hace que la prueba de arriba valga.

        Sin esto, un `NO_APLICA` de j12 podría estar tapando que el juez no mira
        nada nunca. Con el marcador y sin la clave se adopta todo, así que los
        dos jueces tienen que actuar sobre el mismo repositorio.
        """
        self.repo.escribe(".semilla",
                          "version: 2026-09-07\ngerencia: 1_banner_SECOM\n")
        datos = self._correr()
        self.assertIn(self._veredicto(datos, "j12"), ("OK", "HALLAZGOS"),
                      "sin la clave, j12 tiene que mirar")
        self.assertEqual("HALLAZGOS", self._veredicto(datos, "j13"))

    def test_sin_marcador_ninguno_de_los_dos_juzga(self):
        """Y el estado de partida de casi toda la flota: catorce de los quince
        repositorios del disco no llevan marcador y salen NO_APLICA en ambos."""
        datos = self._correr()
        self.assertEqual("NO_APLICA", self._veredicto(datos, "j12"))
        self.assertEqual("NO_APLICA", self._veredicto(datos, "j13"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
