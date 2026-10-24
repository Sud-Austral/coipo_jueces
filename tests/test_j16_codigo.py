"""Pruebas de j16 — código mantenible: tamaño, TypeScript y capas.

Fixtures SINTÉTICOS: este repositorio es público.

LA PRUEBA QUE MÁS IMPORTA es la de la asimetría: lo sembrado ANTES de la vigencia
sólo avisa. «Las soluciones que ya generamos no serán retrocompatibles y está
bien» (FILOSOFIA.md de la fábrica, §3): un juez que tumbara el despliegue de las
apps viejas por nacer antes de la regla la volvería a suprimir en una semana.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j16_codigo as j16  # noqa: E402

NUEVA = "version: 2026-10-24\nfabrica: 2026-10-24\ngerencia: 1_banner_SECOM\nadopta: semilla, interfaz\n"
VIEJA = "version: 2026-10-20\nfabrica: 2026-10-20\ngerencia: 1_banner_SECOM\nadopta: semilla, interfaz\n"
SIN_FECHA = "version: 2026-09-08\ngerencia: 1_banner_SECOM\nadopta: interfaz\n"

TSCONFIG = '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n'
DOMINIO_PURO = "export type Predio = { id: string }\nexport const area = (p: Predio) => p.id.length\n"


def lineas(n: int) -> str:
    return "".join(f"const x{i} = {i}\n" for i in range(n))


class Base(CasoConRepo):
    MODULO = j16

    def frontend_sano(self) -> None:
        (self.repo
         .escribe("frontend/package.json", "{}\n")
         .escribe("frontend/tsconfig.json", TSCONFIG)
         .escribe("frontend/src/dominio/predio.ts", DOMINIO_PURO)
         .escribe("frontend/src/interfaz/App.tsx", "export default function App() { return null }\n"))


class PruebaAlcance(Base):
    def test_sin_semilla_es_no_aplica(self):
        self.repo.escribe("app.py", lineas(5000))
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.hallazgos)

    def test_sembrado_sano_sale_ok(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        r = self.repo.juzga()
        self.assertEqual("OK", r.veredicto, [h.mensaje for h in r.hallazgos])
        self.assertTrue(any("COD-1" in c for c in r.comprobado))
        self.assertTrue(any("COD-3" in c for c in r.comprobado))


class PruebaTamano(Base):
    def test_sobre_mil_bloquea_en_lo_nuevo(self):
        self.repo.escribe(".semilla", NUEVA).escribe("backend/app/grande.py", lineas(1001))
        self.assertBloquea("1001 líneas")

    def test_sobre_mil_solo_avisa_en_lo_viejo(self):
        """La asimetría: lo sembrado antes de la vigencia no se detiene."""
        self.repo.escribe(".semilla", VIEJA).escribe("backend/app/grande.py", lineas(1500))
        self.assertSinBloqueos()
        self.assertAvisa("1500 líneas")

    def test_sin_fecha_de_siembra_solo_avisa(self):
        """Como coipo_prensa2: adopta un estándar sin haberse sembrado."""
        self.repo.escribe(".semilla", SIN_FECHA).escribe("frontend/src/estilos.css", lineas(1985))
        self.assertSinBloqueos()
        self.assertAvisa("1985 líneas")

    def test_entre_ochocientos_y_mil_avisa_siempre(self):
        self.repo.escribe(".semilla", NUEVA).escribe("backend/app/mediano.py", lineas(900))
        self.assertSinBloqueos()
        self.assertAvisa("900 líneas")

    def test_ochocientas_exactas_no_es_hallazgo(self):
        self.repo.escribe(".semilla", NUEVA).escribe("backend/app/justo.py", lineas(800))
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_datos_y_generado_no_cuentan(self):
        (self.repo.escribe(".semilla", NUEVA)
         .escribe("frontend/package-lock.json", lineas(5000))
         .escribe("frontend/public/capas/chile.geojson", lineas(5000))
         .escribe("frontend/dist/assets/index.js", lineas(5000))
         .escribe("frontend/public/lib/maplibre.min.js", lineas(5000)))
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_no_versionado_no_cuenta(self):
        self.repo.escribe(".semilla", NUEVA).escribe("borrador.py", lineas(5000), versionar=False)
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_supresion_en_cabecera_se_cuenta(self):
        cuerpo = "-- coipo-jueces:ignorar(COD-1) migracion historica sellada, no se reescribe\n" + lineas(1200)
        self.repo.escribe(".semilla", NUEVA).escribe("db/0001.sql", cuerpo)
        r = self.repo.juzga()
        self.assertSinBloqueos(r)
        self.assertEqual(1, len(r.supresiones))

    def test_supresion_sin_motivo_no_suprime(self):
        cuerpo = "# coipo-jueces:ignorar(COD-1) corto\n" + lineas(1200)
        self.repo.escribe(".semilla", NUEVA).escribe("backend/app/x.py", cuerpo)
        self.assertBloquea("1201 líneas")


class PruebaTypeScript(Base):
    def test_js_en_src_bloquea_en_lo_nuevo(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/interfaz/Vista.jsx", "export default () => null\n")
        self.assertBloquea("JavaScript en `frontend/src/`")

    def test_js_en_src_avisa_en_lo_viejo(self):
        self.repo.escribe(".semilla", VIEJA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/main.js", "console.log(1)\n")
        self.assertSinBloqueos()
        self.assertAvisa("JavaScript en `frontend/src/`")

    def test_config_de_vite_fuera_de_src_no_cuenta(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/vite.config.js", "export default {}\n")
        self.repo.escribe("frontend/scripts/verify-banner.mjs", "console.log(1)\n")
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_sin_strict_bloquea(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/tsconfig.json", '{ "compilerOptions": { "strict": false } }\n')
        self.assertBloquea('"strict": true')

    def test_strict_en_tsconfig_app_vale(self):
        """La plantilla de Vite pone `strict` en tsconfig.app.json y no en tsconfig.json."""
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/tsconfig.json", '{ "files": [], "references": [] }\n')
        self.repo.escribe("frontend/tsconfig.app.json", TSCONFIG)
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_backend_solo_no_es_hallazgo_de_frontend(self):
        self.repo.escribe(".semilla", NUEVA).escribe("backend/app/main.py", "x = 1\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(any("no hay frontend" in c for c in r.comprobado))


class PruebaCapas(Base):
    def test_dominio_que_importa_react_bloquea(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/dominio/vista.ts", "import { useState } from 'react'\nexport const a = useState\n")
        self.assertBloquea("importa `react`")

    def test_dominio_que_importa_un_adaptador_bloquea(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/dominio/b.ts", "import { pedir } from '../adaptadores/http'\nexport const b = pedir\n")
        self.assertBloquea("importa `../adaptadores/http`")

    def test_dominio_que_importa_un_caso_de_uso_o_una_hoja_bloquea(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/dominio/e.ts",
                          "import { x } from '../aplicacion/casos.ts'\nimport './e.css'\nexport const e = x\n")
        r = self.repo.juzga()
        self.assertBloquea("importa `../aplicacion/casos.ts`", r)
        self.assertBloquea("importa `./e.css`", r)

    def test_dominio_que_hace_fetch_bloquea_con_su_linea(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/dominio/c.ts", "export const a = 1\nexport const c = () => fetch('/api')\n")
        r = self.repo.juzga()
        self.assertBloquea("usa `fetch", r)
        self.assertEqual(2, r.bloqueantes[0].linea)

    def test_un_comentario_que_nombra_fetch_no_es_hallazgo(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/dominio/d.ts",
                          "// el dominio no hace fetch(): recibe los datos\n/* ni window.x */\nexport const d = 1\n")
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_un_adaptador_si_puede_usar_fetch_y_react(self):
        self.repo.escribe(".semilla", NUEVA)
        self.frontend_sano()
        self.repo.escribe("frontend/src/adaptadores/http.ts", "export const pedir = () => fetch('/api')\n")
        self.repo.escribe("frontend/src/interfaz/Uso.tsx", "import { useState } from 'react'\nexport const u = useState\n")
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_sin_dominio_bloquea_en_lo_nuevo(self):
        (self.repo.escribe(".semilla", NUEVA)
         .escribe("frontend/package.json", "{}\n")
         .escribe("frontend/tsconfig.json", TSCONFIG)
         .escribe("frontend/src/App.tsx", "export default 1\n"))
        self.assertBloquea("no tiene `src/dominio/`")

    def test_dominio_del_backend_que_importa_sqlalchemy_bloquea(self):
        self.repo.escribe(".semilla", NUEVA).escribe(
            "backend/app/dominio/modelo/x.py", "from __future__ import annotations\nfrom sqlalchemy import text\n")
        r = self.repo.juzga()
        self.assertBloquea("importa `sqlalchemy`", r)
        self.assertEqual(2, r.bloqueantes[0].linea)

    def test_dominio_del_backend_que_se_importa_a_si_mismo_es_sano(self):
        self.repo.escribe(".semilla", NUEVA).escribe(
            "backend/app/dominio/politicas/p.py", "from app.dominio.errores import DatoInvalido\nimport calendar\n")
        self.assertEqual([], self.repo.juzga().hallazgos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
