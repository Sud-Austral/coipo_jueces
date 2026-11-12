"""Pruebas de FAB-9 (j14): alguien MIRÓ la interfaz antes de desplegar.

Fixtures SINTÉTICOS: este repositorio es público. Negativas primero.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j14_construccion as j14  # noqa: E402

# La vigencia es el 2026-11-13; el 12 —el día de la publicación, cuando se sembraron dos
# aplicaciones antes de que la regla existiera— sólo avisa.
HOY = "version: 2026-11-13\nfabrica: 2026-11-13\nadopta: semilla\n"
AYER = "version: 2026-11-12\nfabrica: 2026-11-12\nadopta: semilla, interfaz\n"

BASE = """# Construcción
metodologia: smb-metodologia-construir-una-aplicacion-coipo-de-prueba
instancia: conaf
objetivos:
- 1 se leyó
consultas:
- 2026-11-12 ver_metodologia corr-1700000000000-0000abcd
registrado: no aplica: prueba sintética
"""
MIRADO = "mirado: 2026-11-12, npm run comparar:maqueta, 0,00 % en ingreso; diff revisado\n"


class PruebaFab9(CasoConRepo):
    MODULO = j14

    def _fab9(self, r=None):
        r = r or self.repo.juzga()
        return [h for h in r.hallazgos if h.regla == "FAB-9"]

    def _app(self, semilla: str, construccion: str, frontend: bool = True) -> None:
        self.repo.escribe(".semilla", semilla)
        self.repo.escribe("docs/CONSTRUCCION.md", construccion)
        if frontend:
            self.repo.escribe("frontend/package.json", "{}\n")

    def test_sin_mirado_bloquea_en_lo_nuevo(self):
        self._app(HOY, BASE)
        self.assertBloquea("no dice qué se MIRÓ")

    def test_mirado_pendiente_bloquea(self):
        self._app(HOY, BASE + "mirado: [PENDIENTE] fecha y comando\n")
        self.assertBloquea("vacío o pendiente")

    def test_mirado_vacio_bloquea(self):
        self._app(HOY, BASE + "mirado: sí\n")
        self.assertBloquea("vacío o pendiente")

    def test_en_lo_anterior_solo_avisa(self):
        self._app(AYER, BASE)
        self.assertAvisa("no dice qué se MIRÓ")
        self.assertFalse([h for h in self.repo.juzga().bloqueantes if h.regla == "FAB-9"])

    def test_sin_frontend_no_se_pide(self):
        self._app(HOY, BASE, frontend=False)
        self.assertEqual([], self._fab9())

    def test_mirado_completo_pasa(self):
        self._app(HOY, BASE + MIRADO)
        self.assertEqual([], self._fab9())

    def test_mirado_en_lista_tambien_cuenta(self):
        self._app(HOY, BASE + "- " + MIRADO)
        self.assertEqual([], self._fab9())
