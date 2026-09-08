"""Pruebas de j13 — la interfaz: foco, tema oscuro y movimiento reducido.

Fixtures SINTÉTICOS: este repositorio es público.

El estándar se FIRMÓ el 2026-09-07 y estas tres reglas BLOQUEAN. Hasta entonces
había aquí una prueba, `test_ninguna_regla_de_este_juez_bloquea`, que impedía
subir la severidad sin firmar; se borró al firmar, que era su trámite. Para
revocar: devolver las filas a «Reglas sin fuente escrita» de REGLAS.md y las
llamadas a `r.avisa(`; `PruebaSeveridad` vuelve a impedirlo sola.

LA PRUEBA QUE MÁS IMPORTA es `test_backend_sin_css_es_no_aplica`: un juez de
interfaz que tratara «este repositorio no tiene CSS» como defecto pondría rojos
a todos los backends, colectores y encuadres operativos de la flota. Ese falso
positivo no se discute: se suprime el juez, y a los tres meses el gate está
apagado.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j13_interfaz as j13  # noqa: E402


SEMILLA = """\
version: 2026-09-07
gerencia: 1_banner_SECOM
"""

CSS_SANO = """\
:root {
  --verde: #064928;
  --tinta: #1f2a24;
}
[data-theme='oscuro'] {
  --verde: #4fb37a;
  --tinta: #e8eae9;
}
.boton { color: var(--verde); transition: background .2s; }
.boton:focus-visible { outline: 3px solid var(--verde); }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; }
}
"""


class ConSemilla(CasoConRepo):
    """Repositorio que DECLARA seguir el estándar de interfaz.

    El estándar es para proyectos NUEVOS, así que `j13` sólo juzga a quien lo
    declara con `.semilla` en la raíz — el mismo marcador que exige `j12`. Sin
    él sale NO_APLICA, y eso lo prueba `PruebaAlcance` más abajo.
    """

    MODULO = j13

    def setUp(self) -> None:
        super().setUp()
        self.repo.escribe(".semilla", SEMILLA)


class PruebaFoco(ConSemilla):

    def test_outline_cero_sin_sustituto_bloquea(self):
        self.repo.escribe("src/estilos.css",
                          ".campo:focus { outline: 0; }\n"
                          ".campo { transition: border .2s; }\n")
        self.assertBloquea("quita el contorno del foco")

    def test_outline_cero_con_focus_visible_en_el_mismo_archivo_no_bloquea(self):
        """Conservador a propósito: un `outline:0` acompañado de un
        `:focus-visible` en el mismo archivo es la forma CORRECTA de reemplazar
        el anillo por defecto, y marcarlo sería el falso positivo que enseña a
        suprimir al juez."""
        self.repo.escribe("src/estilos.css", CSS_SANO + ".x:focus { outline: 0; }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-10"],
                         f"no debía avisar de foco: {[h.mensaje for h in r.hallazgos]}")

    def test_outline_offset_no_se_confunde_con_outline_cero(self):
        """`outline-offset: 0` es legítimo y frecuente. Confundirlo con
        `outline: 0` marcaría CSS correcto."""
        self.repo.escribe("src/estilos.css",
                          ".x { outline-offset: 0; }\n.x { transition: all .2s; }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-10"])


class PruebaTemaOscuro(ConSemilla):

    def test_token_de_texto_sin_redefinir_bloquea(self):
        self.repo.escribe("src/estilos.css",
                          ":root { --verde: #064928; }\n"
                          "[data-theme='oscuro'] { --fondo: #1a1f1c; }\n"
                          ".t { color: var(--verde); }\n")
        self.assertBloquea("NO se redefinen en el tema oscuro")

    def test_token_usado_solo_de_fondo_no_bloquea(self):
        """Un color que sólo se usa como fondo puede ser legítimo en los dos
        temas: la superficie del banner institucional es el caso real. Sólo se
        exige redefinir lo que se usa como texto, borde o foco."""
        self.repo.escribe("src/estilos.css",
                          ":root { --marca: #064928; }\n"
                          "[data-theme='oscuro'] { --fondo: #1a1f1c; }\n"
                          ".banner { background: var(--marca); }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-3"],
                         "un token usado sólo de fondo no exige redefinición")

    def test_sin_tema_oscuro_es_no_evaluado_y_no_hallazgo(self):
        """No tener tema oscuro es una carencia del proyecto, no un defecto de
        este archivo: se dice como no evaluado, que es lo honesto, en vez de
        inventar un hallazgo sobre algo que el juez no puede ver."""
        self.repo.escribe("src/estilos.css",
                          ":root { --verde: #064928; }\n.t { color: var(--verde); }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-3"])
        self.assertTrue(any("tema oscuro" in n for n in r.no_evaluado),
                        f"debía declararlo no evaluado: {r.no_evaluado}")

    def test_css_minificado_en_una_linea_tambien_se_mira(self):
        """Regresión. La primera versión del juez exigía que el bloque del tema
        oscuro cerrase en su propia línea, así que sobre un CSS MINIFICADO —que
        es la forma en que el bundle llega al servidor— no encontraba ninguno y
        declaraba «no evaluado» en silencio. Un juez que no mira nada y no lo
        dice es peor que no tenerlo."""
        self.repo.escribe(
            "src/estilos.css",
            ":root{--verde:#064928}[data-theme='oscuro']{--fondo:#1a1f1c}"
            ".t{color:var(--verde)}\n")
        self.assertBloquea("NO se redefinen en el tema oscuro")

    def test_prefers_color_scheme_cuenta_como_tema_oscuro(self):
        """Las dos vías son válidas: el selector explícito para quien eligió, y
        la consulta de medio para quien no."""
        self.repo.escribe("src/estilos.css",
                          ":root { --verde: #064928; }\n"
                          "@media (prefers-color-scheme: dark) {\n"
                          "  :root { --verde: #4fb37a; }\n}\n"
                          ".t { color: var(--verde); }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-3"])


class PruebaMovimientoReducido(ConSemilla):

    def test_sin_bloque_bloquea(self):
        self.repo.escribe("src/estilos.css",
                          ".a { transition: all .2s; }\n.b { animation: x 1s; }\n")
        self.assertBloquea("ninguna hoja tiene un bloque `prefers-reduced-motion`")

    def test_bloque_selectivo_bloquea_con_la_cuenta(self):
        """El caso real de coipo_prensa2: apaga una transición y deja ocho vivas."""
        self.repo.escribe("src/estilos.css",
                          ".a { transition: all .2s; }\n"
                          ".b { transition: color .2s; }\n"
                          ".c { transition: opacity .2s; }\n"
                          "@media (prefers-reduced-motion: reduce) {\n"
                          "  .a { transition: none; }\n}\n")
        self.assertBloquea("es selectivo")

    def test_bloque_universal_no_bloquea(self):
        self.repo.escribe("src/estilos.css", CSS_SANO)
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-15"],
                         f"el selector universal cubre todo: {[h.mensaje for h in r.hallazgos]}")

    def test_sin_movimiento_no_exige_el_bloque(self):
        """Un CSS sin una sola transición no necesita apagar nada."""
        self.repo.escribe("src/estilos.css", ".a { color: #111; }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-15"])


class PruebaAlcance(ConSemilla):

    def test_backend_sin_css_es_no_aplica(self):
        self.repo.escribe("backend/app/main.py", "app = 1\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto,
                         "un repositorio sin interfaz no tiene interfaz que juzgar")

    def test_css_de_dependencias_y_build_no_se_juzga(self):
        """`node_modules/` y `dist/` no son código del proyecto. Si se juzgaran,
        cualquier repositorio con un lockfile versionado saldría rojo por CSS
        que nadie escribió."""
        self.repo.escribe("node_modules/x/a.css", ".x:focus { outline: 0; }\n")
        self.repo.escribe("dist/b.css", ".y:focus { outline: none; }\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)

    def test_un_css_sano_sale_ok_con_comprobaciones(self):
        """Y sale OK, no SIN_EVALUAR: cero hallazgos con cero comprobaciones no
        es conformidad, y este juez tiene que registrar lo que miró."""
        self.repo.escribe("src/estilos.css", CSS_SANO)
        r = self.repo.juzga()
        self.assertEqual("OK", r.veredicto, f"hallazgos: {[h.mensaje for h in r.hallazgos]}")
        self.assertTrue(r.comprobado, "un veredicto OK exige comprobaciones registradas")


class PruebaDeclaracion(CasoConRepo):
    """El alcance se declara, y la declaración pide MÁS obligación, no menos.

    Es la única clase de este archivo que NO hereda de `ConSemilla`: prueba
    justamente lo que pasa sin el marcador.
    """

    MODULO = j13

    def test_sin_declaracion_es_no_aplica_aunque_el_css_este_mal(self):
        """El estándar es para proyectos NUEVOS.

        Una aplicación anterior no lo incumple: no existía cuando se escribió.
        Este CSS tiene los tres defectos a la vez y aun así no se juzga —y ese
        es el comportamiento correcto, no una laxitud—. Sin esto, cada regla
        nueva del estándar encendería 32 frontends heredados a la vez, y lo que
        se aprende de un gate que avisa de lo que nadie va a arreglar es a
        ignorarlo.
        """
        self.repo.escribe("src/estilos.css",
                          ":root { --v: #064928; }\n"
                          "[data-theme='oscuro'] { --f: #1a1f1c; }\n"
                          ".t { color: var(--v); transition: all .2s; }\n"
                          ".t:focus { outline: 0; }\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertFalse(r.hallazgos, f"no debía juzgar nada: {[h.regla for h in r.hallazgos]}")

    def test_la_declaracion_lo_enciende(self):
        """El mismo CSS, con el marcador puesto, sí se juzga.

        Las dos pruebas juntas son lo que hace que este juez tenga alcance: sin
        la segunda, `NO_APLICA` podría estar tapando que el juez no mira nada.
        """
        self.repo.escribe(".semilla", SEMILLA)
        self.repo.escribe("src/estilos.css",
                          ":root { --v: #064928; }\n"
                          "[data-theme='oscuro'] { --f: #1a1f1c; }\n"
                          ".t { color: var(--v); transition: all .2s; }\n"
                          ".t:focus { outline: 0; }\n")
        r = self.repo.juzga()
        self.assertEqual("HALLAZGOS", r.veredicto)
        self.assertTrue(r.hallazgos, "con la declaración puesta, el mismo CSS sí se juzga")
        # Desde la firma del 2026-09-07 las tres BLOQUEAN. Antes, esta línea
        # comprobaba lo contrario.
        self.assertTrue(r.bloqueantes, "y bloquean: el estándar está firmado")


class PruebaAdopcionInterfaz(CasoConRepo):
    """La capa `interfaz` de `adopta:`, y por qué existe.

    El estándar de interfaz y las piezas congeladas son dos declaraciones
    DISTINTAS, y `.semilla` las tenía cableadas al mismo interruptor porque j13
    reutilizó el marcador de j12. Se rompió al intentar declararlo en un
    repositorio real: `coipo_prensa2` puede cumplir el estándar de interfaz y
    NUNCA se sembró, así que el marcador le habría encendido ocho `SEM-1`
    bloqueantes sobre archivos legítimamente suyos.
    """

    MODULO = j13

    CSS_MALO = (":root { --v: #064928; }\n"
                "[data-theme='oscuro'] { --f: #1a1f1c; }\n"
                ".t { color: var(--v); transition: all .2s; }\n")

    def test_adopta_interfaz_enciende_j13(self):
        """El caso que motiva toda la clave: adoptar la interfaz SIN declararse
        sembrado. El mismo CSS que sin marcador no se juzga, aquí sí."""
        self.repo.escribe(".semilla", "version: 2026-09-07\nadopta: interfaz\n")
        self.repo.escribe("src/estilos.css", self.CSS_MALO)
        r = self.repo.juzga()
        self.assertEqual("HALLAZGOS", r.veredicto)
        self.assertTrue(r.bloqueantes, "el estándar está firmado: bloquean")

    def test_adopta_solo_semilla_apaga_j13(self):
        """Y en la otra dirección: quien declara sólo la procedencia no recibe el
        estándar de interfaz. Sin las dos pruebas, un NO_APLICA podría estar
        tapando que el juez no mira nada."""
        self.repo.escribe(".semilla", "version: 2026-09-07\nadopta: semilla\n")
        self.repo.escribe("src/estilos.css", self.CSS_MALO)
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.hallazgos)
        self.assertIn(".semilla:2", r.no_aplica[0])
        self.assertEqual(1, len(r.supresiones), "se cuenta como supresión")

    def test_sin_clave_adopta_se_juzga_igual_que_antes(self):
        """Retrocompatibilidad: los `.semilla` anteriores a esta clave no la
        llevan, y su comportamiento no puede cambiar."""
        self.repo.escribe(".semilla", SEMILLA)
        self.repo.escribe("src/estilos.css", self.CSS_MALO)
        r = self.repo.juzga()
        self.assertEqual("HALLAZGOS", r.veredicto)

    def test_adopta_comentado_no_apaga_este_juez(self):
        """Un `# adopta: semilla` comentado no puede apagar j13 en silencio."""
        self.repo.escribe(".semilla", "# adopta: semilla\nversion: 2026-09-07\n")
        self.repo.escribe("src/estilos.css", self.CSS_MALO)
        r = self.repo.juzga()
        self.assertEqual("HALLAZGOS", r.veredicto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
