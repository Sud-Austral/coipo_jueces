"""Pruebas de una aplicación sembrada desde una MAQUETA validada (`maqueta:` en `.semilla`).

Fixtures SINTÉTICOS: este repositorio es público.

Tres comportamientos, decididos por Luis Monsalve el 2026-11-12 (identidad/ESTANDAR_UI.md
§1-bis de coipo_master_produccion): la cara de la maqueta manda, así que

  - j13 sale NO_APLICA y NO cuenta supresión (sin `maqueta:`, no adoptar `interfaz` sí
    se cuenta: esa puerta se sigue pagando);
  - j16 no mide la referencia `maqueta/` ni la cara copiada `frontend/src/maqueta/`;
  - j12 avisa (MAQ-1) si la cara copiada no coincide con su sha256 de PROCEDENCIA.md.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j12_semilla as j12  # noqa: E402
import j13_interfaz as j13  # noqa: E402
import j16_codigo as j16  # noqa: E402

CSS = ":root { --primary: #007111; }\n.btn { background: var(--primary); }\n"
CON_MAQUETA = ("version: 2026-11-12\nfabrica: 2026-11-12\n"
               "maqueta: https://ejemplo.invalid/maqueta@0123abcd\nadopta: semilla\n")
SIN_MAQUETA = "version: 2026-11-12\nfabrica: 2026-11-12\nadopta: semilla\n"


def _procedencia(css: str = CSS) -> str:
    sha = hashlib.sha256(css.encode("utf-8")).hexdigest()
    return f"# Procedencia\n\n| Archivo | sha256 |\n|---|---|\n| `css/styles.css` | `{sha}` |\n"


class PruebaJ13(CasoConRepo):
    MODULO = j13

    def test_con_maqueta_no_aplica_y_no_es_supresion(self):
        self.repo.escribe(".semilla", CON_MAQUETA)
        self.repo.escribe("frontend/src/maqueta/css/styles.css", CSS + ".x:focus { outline: 0; }\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.supresiones)

    def test_sin_maqueta_no_adoptar_interfaz_sigue_siendo_supresion(self):
        """La puerta de siempre no se abrió: sólo la maqueta declarada la evita."""
        self.repo.escribe(".semilla", SIN_MAQUETA)
        self.repo.escribe("frontend/src/estilos.css", CSS)
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual(1, len(r.supresiones))


class PruebaJ16(CasoConRepo):
    MODULO = j16

    def _grande(self, ruta: str) -> None:
        self.repo.escribe(ruta, "".join(f"var v{i} = {i};\n" for i in range(1200)))

    def test_con_maqueta_no_mide_su_referencia(self):
        self.repo.escribe(".semilla", CON_MAQUETA)
        self._grande("maqueta/js/app.js")
        self.assertSinBloqueos()
        self.assertFalse([h for h in self.repo.juzga().hallazgos if h.regla == "COD-1"])

    def test_sin_maqueta_la_misma_ruta_si_se_mide(self):
        self.repo.escribe(".semilla", SIN_MAQUETA)
        self._grande("maqueta/js/app.js")
        self.assertBloquea("pasa el techo de 1000")

    def test_con_maqueta_el_codigo_propio_si_se_mide(self):
        self.repo.escribe(".semilla", CON_MAQUETA)
        self._grande("frontend/src/vistas/Gigante.ts")
        self.assertBloquea("pasa el techo de 1000")


class PruebaAjeno(CasoConRepo):
    """`ajeno:` saca una carpeta de COD-1/COD-2, y CADA una se cuenta como supresión."""

    MODULO = j16

    def _grande(self, ruta: str) -> None:
        self.repo.escribe(ruta, "".join(f"var v{i} = {i};\n" for i in range(1200)))

    def test_ajeno_no_se_mide_y_se_publica(self):
        self.repo.escribe(".semilla", SIN_MAQUETA + "ajeno: vendor_visor/, frontend/src/libs\n")
        self._grande("vendor_visor/visor.js")
        self.repo.escribe("frontend/package.json", "{}\n")
        self.repo.escribe("frontend/src/libs/grafico.js", "var a = 1;\n")
        r = self.repo.juzga()
        sobre_ajeno = [h for h in r.hallazgos
                       if "vendor_visor" in f"{h.archivo} {h.mensaje}" or "libs/" in f"{h.archivo} {h.mensaje}"]
        self.assertEqual([], [h.mensaje for h in sobre_ajeno])
        self.assertEqual(2, len([s for s in r.supresiones if "ajeno:" in s]))

    def test_sin_ajeno_la_misma_carpeta_se_mide(self):
        self.repo.escribe(".semilla", SIN_MAQUETA)
        self._grande("vendor_visor/visor.js")
        self.assertBloquea("pasa el techo de 1000")

    def test_ajeno_no_tapa_lo_de_al_lado(self):
        self.repo.escribe(".semilla", SIN_MAQUETA + "ajeno: vendor_visor/\n")
        self._grande("vendor_visor_propio/app.ts")
        self.assertBloquea("pasa el techo de 1000")


class PruebaMaq1(CasoConRepo):
    MODULO = j12

    def setUp(self):
        super().setUp()
        # Un lock sintético vacío de piezas presentes: sólo interesa MAQ-1.
        self.lock = Path(self.repo.dir) / "semilla.lock.prueba"
        self.lock.write_text(f"{'0' * 64}  frontend/nginx.conf\n", encoding="utf-8")
        self._real, j12.LOCK = j12.LOCK, self.lock
        self.addCleanup(lambda: setattr(j12, "LOCK", self._real))
        self.repo.escribe(".semilla", CON_MAQUETA)
        self.repo.escribe("frontend/nginx.conf", "server {}\n")

    def _maq1(self):
        return [h for h in self.repo.juzga().hallazgos if h.regla == "MAQ-1"]

    def test_intacta_no_avisa(self):
        self.repo.escribe("maqueta/PROCEDENCIA.md", _procedencia())
        self.repo.escribe("frontend/src/maqueta/css/styles.css", CSS)
        self.assertEqual([], self._maq1())

    def test_con_crlf_no_es_una_edicion(self):
        """git cambia los finales de línea al hacer checkout: eso no es editar la cara."""
        self.repo.escribe("maqueta/PROCEDENCIA.md", _procedencia())
        self.repo.escribe("frontend/src/maqueta/css/styles.css", CSS.replace("\n", "\r\n"))
        self.assertEqual([], self._maq1())

    def test_editada_avisa(self):
        self.repo.escribe("maqueta/PROCEDENCIA.md", _procedencia())
        self.repo.escribe("frontend/src/maqueta/css/styles.css", CSS.replace("#007111", "#064928"))
        self.assertAvisa("alguien editó la cara que aprobó el cliente")

    def test_borrada_avisa(self):
        self.repo.escribe("maqueta/PROCEDENCIA.md", _procedencia())
        self.assertAvisa("falta un archivo de la cara validada")

    def test_sin_procedencia_avisa(self):
        self.repo.escribe("frontend/src/maqueta/css/styles.css", CSS)
        self.assertAvisa("falta su procedencia")

    def test_maq1_nunca_bloquea(self):
        """AGENTS.md §5: la regla es nueva y no está calibrada sobre ninguna app real."""
        self.repo.escribe("maqueta/PROCEDENCIA.md", _procedencia())
        self.repo.escribe("frontend/src/maqueta/css/styles.css", "/* otra */\n")
        self.assertFalse([h for h in self.repo.juzga().bloqueantes if h.regla == "MAQ-1"])
