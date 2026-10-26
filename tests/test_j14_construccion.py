"""Pruebas de j14 — la aplicación se construyó con la fábrica y lo demuestra.

Fixtures SINTÉTICOS: los `correlation_id` y los ids de metodología de aquí
están inventados con la forma real (`corr-<13 dígitos>-<8 hex>`,
`smb-metodologia-<slug>`), no copiados de ninguna instancia.

Cada caso que bloquea se vio ponerse rojo antes de darlo por bueno; el caso
completo es el que prueba que el juez sabe callarse.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j14_construccion as j14  # noqa: E402

SEMILLA_NUEVA = "# sembrada\nfabrica: 2026-10-20\nadopta: semilla, interfaz\n"
SEMILLA_VIEJA = "# sembrada\nadopta: semilla, interfaz\n"

COMPLETO = """# Construcción de esta aplicación con la fábrica

metodologia: smb-metodologia-construir-una-aplicacion-coipo-con-la-fabrica
instancia: conaf
fecha: 2026-10-20

objetivos:
- 1 Consultar la fábrica antes de escribir: se leyó la metodología y el grafo.
- 4 Construir por capas: el collector no lleva n8n; el dato se congela con su origen.

consultas:
- 2026-10-20 listar_metodologias conaf corr-1792511425938-00017df0
- 2026-10-20 ver_metodologia corr-1792511430001-0001a2b3
- 2026-10-20 consultar_grafo.py "calidad aire" 3 secciones

registrado: obj-leccion-monitor-sin-fuente-real-k3x9
"""


class PruebaAusencia(CasoConRepo):
    MODULO = j14

    def test_sin_archivo_y_sembrado_desde_octubre_bloquea(self):
        self.repo.escribe(".semilla", SEMILLA_NUEVA)
        self.repo.escribe("README.md", "# app\n")
        self.assertBloquea("no hay `docs/CONSTRUCCION.md`")

    def test_sin_archivo_y_sembrado_antes_avisa_pero_no_bloquea(self):
        """Poner rojas las 24 aplicaciones anteriores de golpe es un cambio de mayor."""
        self.repo.escribe(".semilla", SEMILLA_VIEJA)
        self.repo.escribe("README.md", "# app\n")
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes, [h.mensaje for h in r.bloqueantes])
        self.assertAvisa("no hay `docs/CONSTRUCCION.md`", r)

    def test_sin_archivo_y_sin_semilla_avisa(self):
        self.repo.escribe("README.md", "# app\n")
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertAvisa("no hay `docs/CONSTRUCCION.md`", r)

    def test_la_razon_nombra_la_fecha_de_la_semilla(self):
        self.repo.escribe(".semilla", SEMILLA_NUEVA)
        r = self.repo.juzga()
        self.assertTrue(any("fabrica: 2026-10-20" in h.manifestacion for h in r.bloqueantes),
                        [h.manifestacion for h in r.bloqueantes])


class PruebaContenido(CasoConRepo):
    MODULO = j14

    def setUp(self):
        super().setUp()
        self.repo.escribe(".semilla", SEMILLA_VIEJA)

    def test_completo_no_tiene_hallazgos_y_comprobo(self):
        self.repo.escribe("docs/CONSTRUCCION.md", COMPLETO)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertTrue(r.comprobado, "un juez que no anota lo que comprobó se lee como «todo bien»")

    def test_plantilla_a_medias_bloquea_aunque_el_repo_sea_viejo(self):
        self.repo.escribe("docs/CONSTRUCCION.md", COMPLETO.replace("conaf", "[PENDIENTE]"))
        self.assertBloquea("marcador(es) `[PENDIENTE]`")

    def test_sin_metodologia_bloquea(self):
        sin = COMPLETO.replace("smb-metodologia-construir-una-aplicacion-coipo-con-la-fabrica", "la de la fábrica")
        self.repo.escribe("docs/CONSTRUCCION.md", sin)
        self.assertBloquea("no cita ninguna metodología de IGNUS")

    def test_sin_correlation_id_bloquea(self):
        sin = COMPLETO.replace("corr-1792511425938-00017df0", "ok").replace("corr-1792511430001-0001a2b3", "ok")
        self.repo.escribe("docs/CONSTRUCCION.md", sin)
        self.assertBloquea("no hay ningún `correlation_id`")

    def test_sin_campos_bloquea_y_los_nombra(self):
        sin = COMPLETO.replace("consultas:", "llamadas:").replace("instancia:", "neo4j:")
        self.repo.escribe("docs/CONSTRUCCION.md", sin)
        r = self.repo.juzga()
        self.assertBloquea("faltan los campos", r)
        mensajes = " ".join(h.mensaje for h in r.bloqueantes)
        self.assertIn("`instancia:`", mensajes)
        self.assertIn("`consultas:`", mensajes)

    def test_sin_registrado_avisa_pero_no_bloquea(self):
        sin = COMPLETO.replace("registrado: obj-leccion-monitor-sin-fuente-real-k3x9\n", "")
        self.repo.escribe("docs/CONSTRUCCION.md", sin)
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes, [h.mensaje for h in r.bloqueantes])
        self.assertAvisa("no dice qué se registró", r)


class PruebaPerfil(unittest.TestCase):
    def test_solo_aplica_a_aplicaciones(self):
        """Los repositorios que ALOJAN las herramientas no se construyen con ellas."""
        self.assertEqual(("aplicacion",), j14.PERFILES)


if __name__ == "__main__":
    unittest.main()
