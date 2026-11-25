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

    def test_el_motivo_cuenta_desde_doce_caracteres(self):
        """El umbral, que nadie fijaba: once caracteres no son un motivo y doce sí.

        Sólo se probaban un motivo largo y ninguno, así que el mínimo podía bajar a un
        carácter —`libexpat1  # x`— y la suite seguía en verde (mutación del 2026-11-24). Es
        el mismo mínimo que piden las supresiones (`comun.suprimido`).
        """
        for motivo, falta in (("12345678901", True), ("123456789012", False)):
            with self.subTest(caracteres=len(motivo)):
                self.repo.escribe(j12.PAQUETES, CABECERA + f"libexpat1  # {motivo}\n")
                r = self.repo.juzga()
                if falta:
                    self.assertRegla("SEM-2", "AVISA", "sin motivo", r)
                else:
                    self.assertSinRegla("SEM-2", r)

    def test_cada_compilador_de_la_lista_avisa(self):
        """`gcc`, `g++`, `make`, `build-essential` y cualquier `*-dev`: los cinco de REGLAS.md.

        Sólo se probaban `gcc` y `libpq-dev`: quitar los otros tres de la expresión no
        rompía nada (mutación del 2026-11-24). Y que sea AVISA y no BLOQUEA: la prueba de
        arriba cuenta hallazgos sin mirar la severidad.
        """
        for paquete in ("gcc", "g++", "make", "build-essential", "libpq-dev"):
            with self.subTest(paquete=paquete):
                self.repo.escribe(
                    j12.PAQUETES, CABECERA + f"{paquete}  # lo pide una dependencia nativa\n"
                )
                r = self.repo.juzga()
                self.assertRegla("SEM-2", "AVISA", f"`{paquete}` es para compilar", r)
                self.assertEqual(1, len([h for h in r.hallazgos if h.regla == "SEM-2"]))
