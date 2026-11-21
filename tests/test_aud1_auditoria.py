"""AUD-1: la auditoría está siempre, con el último ingreso de cada persona.

Fixtures SINTÉTICOS: este repositorio es público.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import comun_auditoria as aud  # noqa: E402
import j12_semilla as j12  # noqa: E402

NUEVA = "version: 2026-11-22\nfabrica: 2026-11-22\nadopta: semilla, interfaz\n"
VIEJA = "version: 2026-10-24\nfabrica: 2026-10-24\nadopta: semilla, interfaz\n"
MAIN_CABLEADO = "from app.composicion.acceso import montar_acceso\nmontar_acceso(app, c)\n"


class PruebaAud1(CasoConRepo):
    MODULO = j12

    def setUp(self) -> None:
        super().setUp()
        # Un lock sintético con UNA pieza presente: sólo interesa AUD-1.
        self.lock = Path(self.repo.dir) / "semilla.lock.prueba"
        self.lock.write_text(f"{'0' * 64}  frontend/nginx.conf\n", encoding="utf-8")
        self._real, j12.LOCK = j12.LOCK, self.lock
        self.addCleanup(lambda: setattr(j12, "LOCK", self._real))
        self.repo.escribe("frontend/nginx.conf", "server {}\n")

    def _app_cableada(self, marcador: str = NUEVA, sin: str = "") -> None:
        self.repo.escribe(".semilla", marcador)
        piezas = {
            **{ruta: "x = 1\n" for ruta in aud.SELLADAS},
            aud.COMPOSICION: "def montar_acceso(app, c): ...\n",
            aud.MAIN: MAIN_CABLEADO,
            aud.RUTA_ACTIVIDAD: '@router.get("/ultimos-ingresos")\n',
            "frontend/package.json": "{}\n",
            aud.VISTA_ACTIVIDAD: "export default 1\n",
            aud.VISTA_INGRESOS: "export default 1\n",
        }
        for ruta, texto in piezas.items():
            if ruta != sin:
                self.repo.escribe(ruta, texto)

    def _aud1(self):
        return [h for h in self.repo.juzga().hallazgos if h.regla == "AUD-1"]

    def test_app_recien_sembrada_completa_no_tiene_hallazgos(self) -> None:
        self._app_cableada()
        self.assertEqual([], self._aud1())

    def test_sin_montar_el_acceso_bloquea_en_lo_sembrado_desde_la_vigencia(self) -> None:
        self._app_cableada()
        self.repo.escribe(aud.MAIN, "app = 1\n")
        self.assertRegla("AUD-1", "BLOQUEA", "montar_acceso")

    def test_sin_la_vista_de_ultimos_ingresos_bloquea(self) -> None:
        self._app_cableada(sin=aud.VISTA_INGRESOS)
        self.assertRegla("AUD-1", "BLOQUEA", "último ingreso")

    def test_sin_una_pieza_sellada_bloquea(self) -> None:
        self._app_cableada(sin=aud.SELLADAS[0])
        self.assertRegla("AUD-1", "BLOQUEA", "pieza sellada")

    def test_lo_sembrado_antes_solo_avisa(self) -> None:
        """Mira hacia adelante: las apps de antes reciben el aviso y su PR, no un rojo."""
        self._app_cableada(marcador=VIEJA)
        self.repo.escribe(aud.MAIN, "app = 1\n")
        r = self.repo.juzga()
        self.assertRegla("AUD-1", "AVISA", "montar_acceso", r)
        self.assertFalse([h for h in r.bloqueantes if h.regla == "AUD-1"])

    def test_sin_backend_no_corresponde(self) -> None:
        self.repo.escribe(".semilla", NUEVA)
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "AUD-1"])
        self.assertTrue([n for n in r.no_aplica if n.startswith("AUD-1")], r.no_aplica)


if __name__ == "__main__":
    unittest.main()
