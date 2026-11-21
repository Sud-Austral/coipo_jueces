"""SEM-2: `backend/paquetes-sistema.txt`, la lista apt que lee el Dockerfile sellado.

Fixtures SINTÉTICOS: este repositorio es público. El caso real que la originó es
`coipo_informe_sapif` (rasterio -> libexpat1, 2026-11-19).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j12_semilla as j12  # noqa: E402

MARCADOR = "version: 2026-11-20\nfabrica: 2026-11-20\nadopta: semilla\n"
CABECERA = "# Paquetes de sistema (apt).\n#\n#     libexpat1  # ejemplo comentado\n"


class PruebaSem2(CasoConRepo):
    MODULO = j12

    def setUp(self):
        super().setUp()
        self.lock = Path(self.repo.dir) / "semilla.lock.prueba"
        self.lock.write_text(f"{'0' * 64}  frontend/nginx.conf\n", encoding="utf-8")
        self._real, j12.LOCK = j12.LOCK, self.lock
        self.addCleanup(lambda: setattr(j12, "LOCK", self._real))
        self.repo.escribe(".semilla", MARCADOR)
        self.repo.escribe("frontend/nginx.conf", "server {}\n")

    def _sem2(self):
        return [h for h in self.repo.juzga().hallazgos if h.regla == "SEM-2"]

    def test_sin_lista_no_avisa(self):
        self.assertEqual([], self._sem2())

    def test_solo_comentarios_no_avisa(self):
        self.repo.escribe(j12.PAQUETES, CABECERA)
        self.assertEqual([], self._sem2())

    def test_con_motivo_no_avisa(self):
        self.repo.escribe(
            j12.PAQUETES, CABECERA + "libexpat1  # rasterio 1.5.2 la carga al importar\r\n"
        )
        self.assertEqual([], self._sem2())

    def test_sin_motivo_avisa(self):
        self.repo.escribe(j12.PAQUETES, CABECERA + "libexpat1\n")
        self.assertAvisa("sin motivo")

    def test_compilador_avisa(self):
        self.repo.escribe(j12.PAQUETES, CABECERA + "gcc libpq-dev  # para compilar psycopg2 2026\n")
        avisos = self._sem2()
        self.assertEqual(2, len(avisos))
        self.assertTrue(all("compilar" in h.mensaje for h in avisos))
