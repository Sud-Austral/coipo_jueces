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
        self.repo.escribe(
            "src/estilos.css", ".campo:focus { outline: 0; }\n.campo { transition: border .2s; }\n"
        )
        self.assertBloquea("quita el contorno del foco")
        # El código es UI-9 desde el 2026-10-25: «un componente sin `:focus-visible`
        # no es navegable con teclado» es el texto de UI-9 en ESTANDAR_UI.md. UI-10
        # es «el anillo de foco es un token y cumple 3:1», que este juez no mide.
        reglas = {h.regla for h in self.repo.juzga().bloqueantes}
        self.assertIn("UI-9", reglas)
        self.assertNotIn("UI-10", reglas)

    def test_outline_cero_comentado_no_bloquea(self):
        """Un `outline: none` dentro de `/* */` no quita nada (auditoría del
        2026-10-25): `comprobar_foco` era la única de las tres reglas que leía los
        comentarios."""
        self.repo.escribe(
            "src/estilos.css",
            "/* antes: .campo:focus { outline: none; } */\n.campo { transition: border .2s; }\n",
        )
        r = self.repo.juzga()
        self.assertFalse(
            [h for h in r.hallazgos if h.regla == "UI-9"], [h.mensaje for h in r.hallazgos]
        )

    def test_la_supresion_en_un_comentario_css_sigue_valiendo(self):
        """Quitar los comentarios para juzgar no puede borrar el marcador, que en
        CSS sólo cabe dentro de `/* */`."""
        self.repo.escribe(
            "src/estilos.css",
            "/* coipo-jueces:ignorar(UI-9) widget de terceros con foco propio */\n"
            ".campo:focus { outline: 0; }\n",
        )
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-9"])
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_focus_visible_comentado_no_es_sustituto(self):
        """La otra dirección: un `:focus-visible` comentado no reemplaza nada."""
        self.repo.escribe(
            "src/estilos.css",
            "/* .campo:focus-visible { outline: 2px solid; } */\n.campo:focus { outline: 0; }\n",
        )
        self.assertBloquea("quita el contorno del foco")

    def test_outline_cero_con_focus_visible_en_el_mismo_archivo_no_bloquea(self):
        """Conservador a propósito: un `outline:0` acompañado de un
        `:focus-visible` en el mismo archivo es la forma CORRECTA de reemplazar
        el anillo por defecto, y marcarlo sería el falso positivo que enseña a
        suprimir al juez."""
        self.repo.escribe("src/estilos.css", CSS_SANO + ".x:focus { outline: 0; }\n")
        r = self.repo.juzga()
        self.assertFalse(
            [h for h in r.hallazgos if h.regla == "UI-9"],
            f"no debía avisar de foco: {[h.mensaje for h in r.hallazgos]}",
        )

    def test_outline_offset_no_se_confunde_con_outline_cero(self):
        """`outline-offset: 0` es legítimo y frecuente. Confundirlo con
        `outline: 0` marcaría CSS correcto."""
        self.repo.escribe(
            "src/estilos.css", ".x { outline-offset: 0; }\n.x { transition: all .2s; }\n"
        )
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-9"])


class PruebaTemaOscuro(ConSemilla):
    def test_token_de_texto_sin_redefinir_bloquea(self):
        self.repo.escribe(
            "src/estilos.css",
            ":root { --verde: #064928; }\n"
            "[data-theme='oscuro'] { --fondo: #1a1f1c; }\n"
            ".t { color: var(--verde); }\n",
        )
        self.assertBloquea("NO se redefinen en el tema oscuro")

    def test_token_usado_solo_de_fondo_no_bloquea(self):
        """Un color que sólo se usa como fondo puede ser legítimo en los dos
        temas: la superficie del banner institucional es el caso real. Sólo se
        exige redefinir lo que se usa como texto, borde o foco."""
        self.repo.escribe(
            "src/estilos.css",
            ":root { --marca: #064928; }\n"
            "[data-theme='oscuro'] { --fondo: #1a1f1c; }\n"
            ".banner { background: var(--marca); }\n",
        )
        r = self.repo.juzga()
        self.assertFalse(
            [h for h in r.hallazgos if h.regla == "UI-3"],
            "un token usado sólo de fondo no exige redefinición",
        )

    # Sembrado con la regla «sin tema oscuro» ya vigente (j13.VIGENCIA_SIN_TEMA).
    SEMILLA_NUEVA = "version: 2026-11-22\nfabrica: 2026-11-22\nadopta: semilla, interfaz\n"

    def test_sin_tema_oscuro_bloquea_en_lo_sembrado_desde_la_vigencia(self):
        """UI-3: todo token de texto, borde o foco «se redefine en los dos temas».

        Hasta el 2026-11-21 esto salía como «no evaluado» y el juez daba OK —cero de
        cero— en un repositorio que declara adoptar `interfaz`. Ahora es un hallazgo
        con la severidad de UI-3, y nombra los tokens que se quedan claros."""
        self.repo.escribe(".semilla", self.SEMILLA_NUEVA)
        self.repo.escribe(
            "src/estilos.css", ":root { --verde: #064928; }\n.t { color: var(--verde); }\n"
        )
        r = self.repo.juzga()
        h = self.assertRegla("UI-3", "BLOQUEA", "tema oscuro", r)
        self.assertIn("--verde", h.mensaje)
        self.assertEqual(("src/estilos.css", 1), (h.archivo, h.linea))
        self.assertEqual("HALLAZGOS", r.veredicto)

    def test_sin_tema_oscuro_y_sin_tokens_tambien_bloquea(self):
        """Sin tokens no hay nada que redefinir, pero tampoco hay segundo tema."""
        self.repo.escribe(".semilla", self.SEMILLA_NUEVA)
        self.repo.escribe("src/estilos.css", ".t { color: #111; }\n")
        self.assertRegla("UI-3", "BLOQUEA", "tema oscuro")

    def test_sin_tema_oscuro_solo_avisa_en_lo_sembrado_antes(self):
        """Mira hacia adelante (FILOSOFIA.md §4): con BLOQUEA para todos, la calibración
        del 2026-11-21 ponía rojo a un repositorio que estaba verde (sembrado el
        2026-10-14), y eso es una mayor nueva."""
        self.repo.escribe(
            ".semilla", "version: 2026-10-14\nfabrica: 2026-10-14\nadopta: semilla, interfaz\n"
        )
        self.repo.escribe(
            "src/estilos.css", ":root { --verde: #064928; }\n.t { color: var(--verde); }\n"
        )
        r = self.repo.juzga()
        self.assertRegla("UI-3", "AVISA", "antes de la regla", r)
        self.assertEqual([], r.bloqueantes)

    def test_sin_tema_oscuro_sin_fecha_de_siembra_solo_avisa(self):
        """`adopta: interfaz` sin `fabrica:` (un repositorio alineado, no sembrado)."""
        self.repo.escribe(
            "src/estilos.css", ":root { --verde: #064928; }\n.t { color: var(--verde); }\n"
        )
        self.assertRegla("UI-3", "AVISA", "tema oscuro")

    def test_sin_tema_oscuro_se_suprime_con_motivo(self):
        self.repo.escribe(
            "src/estilos.css",
            "/* coipo-jueces:ignorar(UI-3) quiosco de pantalla fija, sin tema */\n"
            ":root { --verde: #064928; }\n.t { color: var(--verde); }\n",
        )
        r = self.repo.juzga()
        self.assertSinRegla("UI-3", r)
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_css_minificado_en_una_linea_tambien_se_mira(self):
        """Regresión. La primera versión del juez exigía que el bloque del tema
        oscuro cerrase en su propia línea, así que sobre un CSS MINIFICADO —que
        es la forma en que el bundle llega al servidor— no encontraba ninguno y
        declaraba «no evaluado» en silencio. Un juez que no mira nada y no lo
        dice es peor que no tenerlo."""
        self.repo.escribe(
            "src/estilos.css",
            ":root{--verde:#064928}[data-theme='oscuro']{--fondo:#1a1f1c}.t{color:var(--verde)}\n",
        )
        self.assertBloquea("NO se redefinen en el tema oscuro")

    def test_data_theme_dark_cuenta_como_tema_oscuro(self):
        """Regresión (2026-11-25). El juez sólo reconocía `[data-theme=oscuro]`, y una
        hoja con `:root[data-theme="dark"]` que redefinía todos sus tokens salía con
        «ninguna hoja declara el tema oscuro»: un falso positivo sobre CSS correcto
        (el visor de `coipo_gestionypresupuesto`)."""
        self.repo.escribe(
            "src/estilos.css",
            ":root { --verde: #064928; }\n"
            ':root[data-theme="dark"] { --verde: #4fb37a; }\n'
            ".t { color: var(--verde); }\n",
        )
        self.assertSinRegla("UI-3")

    def test_data_theme_dark_sin_redefinir_solo_avisa_en_lo_anterior(self):
        """Con `dark` reconocido, la hoja pasa de «sin tema oscuro» —que en lo anterior
        AVISA— a la comprobación por hoja, que BLOQUEA. Para no poner rojo a nadie que
        hoy está verde (docs/VERSIONADO.md), lo que sólo se ve gracias a `dark` avisa
        salvo en lo sembrado desde `VIGENCIA_DARK` (FILOSOFIA.md §4 de la fábrica)."""
        self.repo.escribe(
            "src/estilos.css",
            ":root { --verde: #064928; }\n"
            "[data-theme='dark'] { --fondo: #1a1f1c; }\n"
            ".t { color: var(--verde); }\n",
        )
        self.assertRegla("UI-3", "AVISA", "NO se redefinen en el tema oscuro")
        self.assertSinBloqueos()

    def test_data_theme_dark_sin_redefinir_bloquea_desde_la_vigencia(self):
        self.repo.escribe(
            ".semilla",
            f"version: {j13.VIGENCIA_DARK}\nfabrica: {j13.VIGENCIA_DARK}\n"
            "adopta: semilla, interfaz\n",
        )
        self.repo.escribe(
            "src/estilos.css",
            ":root { --verde: #064928; }\n"
            "[data-theme='dark'] { --fondo: #1a1f1c; }\n"
            ".t { color: var(--verde); }\n",
        )
        self.assertRegla("UI-3", "BLOQUEA", "NO se redefinen en el tema oscuro")

    def test_oscuro_sin_redefinir_sigue_bloqueando_en_lo_anterior(self):
        """La asimetría es SÓLO para lo que `dark` destapa: `oscuro` bloquea como antes."""
        self.repo.escribe(
            "src/estilos.css",
            ":root { --verde: #064928; }\n"
            "[data-theme='oscuro'] { --fondo: #1a1f1c; }\n"
            ".t { color: var(--verde); }\n",
        )
        self.assertRegla("UI-3", "BLOQUEA", "NO se redefinen en el tema oscuro")

    def test_prefers_color_scheme_cuenta_como_tema_oscuro(self):
        """Las dos vías son válidas: el selector explícito para quien eligió, y
        la consulta de medio para quien no."""
        self.repo.escribe(
            "src/estilos.css",
            ":root { --verde: #064928; }\n"
            "@media (prefers-color-scheme: dark) {\n"
            "  :root { --verde: #4fb37a; }\n}\n"
            ".t { color: var(--verde); }\n",
        )
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-3"])


class PruebaMovimientoReducido(ConSemilla):
    def test_sin_bloque_bloquea(self):
        self.repo.escribe(
            "src/estilos.css", ".a { transition: all .2s; }\n.b { animation: x 1s; }\n"
        )
        self.assertBloquea("ninguna hoja tiene un bloque `prefers-reduced-motion`")

    def test_bloque_selectivo_bloquea_con_la_cuenta(self):
        """El caso real de coipo_prensa2: apaga una transición y deja ocho vivas."""
        self.repo.escribe(
            "src/estilos.css",
            ".a { transition: all .2s; }\n"
            ".b { transition: color .2s; }\n"
            ".c { transition: opacity .2s; }\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  .a { transition: none; }\n}\n",
        )
        # «1 de 3», no «1 de 4»: hasta el 2026-10-25 la cuenta incluía la propia
        # declaración del bloque, y esta prueba pasaba con el número equivocado.
        self.assertBloquea("apaga 1 de 3 declaración(es)")

    def test_bloque_enumerado_que_apaga_todo_no_bloquea(self):
        """Apagar N de N enumerando selectores cumple: no es selectivo.

        Salía «N de 2N» y BLOQUEABA, porque las N declaraciones del bloque se
        contaban también como movimiento propio del archivo."""
        self.repo.escribe(
            "src/estilos.css",
            ".a { transition: all .2s; }\n"
            ".b { animation: giro 1s; }\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  .a { transition: none; }\n"
            "  .b { animation: none; }\n}\n",
        )
        r = self.repo.juzga()
        self.assertFalse(
            [h for h in r.hallazgos if h.regla == "UI-15"], [h.mensaje for h in r.hallazgos]
        )

    def test_bloque_universal_no_bloquea(self):
        self.repo.escribe("src/estilos.css", CSS_SANO)
        r = self.repo.juzga()
        self.assertFalse(
            [h for h in r.hallazgos if h.regla == "UI-15"],
            f"el selector universal cubre todo: {[h.mensaje for h in r.hallazgos]}",
        )

    def test_no_preference_anidado_antes_del_universal_no_bloquea(self):
        """Un `no-preference` anidado ANTES del bloque universal no lo tapa.

        Hasta el 2026-11-22 el juez miraba solo el PRIMER `@media prefers-reduced-motion`
        de cada archivo. Un `.x:hover { @media (prefers-reduced-motion: no-preference)
        {...} }` —la forma progresiva, que es correcta— quedaba como «el bloque», y el
        universal de más abajo no se veía: salía «apaga 0 de N». Pasó con el IAM."""
        self.repo.escribe(
            "src/estilos.css",
            ".card { transition: transform .2s; }\n"
            ".card:hover {\n"
            "  @media (prefers-reduced-motion: no-preference) {\n"
            "    transform: translateY(-2px);\n"
            "  }\n"
            "}\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  *, *::before, *::after {\n"
            "    transition-duration: .01ms !important;\n"
            "    animation-duration: .01ms !important;\n"
            "  }\n"
            "}\n",
        )
        r = self.repo.juzga()
        self.assertFalse(
            [h for h in r.hallazgos if h.regla == "UI-15"], [h.mensaje for h in r.hallazgos]
        )

    def test_no_preference_antes_de_un_reduce_parcial_cuenta_el_reduce(self):
        """Con un `reduce` parcial, la cuenta sale del `reduce`, no del `no-preference`."""
        self.repo.escribe(
            "src/estilos.css",
            ".a { transition: all .2s; }\n"
            ".b { transition: color .2s; }\n"
            ".a:hover {\n"
            "  @media (prefers-reduced-motion: no-preference) { transform: scale(1.1); }\n"
            "}\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  .a { transition: none; }\n"
            "}\n",
        )
        self.assertBloquea("apaga 1 de 2 declaración(es)")

    def test_sin_movimiento_no_exige_el_bloque(self):
        """Un CSS sin una sola transición no necesita apagar nada."""
        self.repo.escribe("src/estilos.css", ".a { color: #111; }\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.hallazgos if h.regla == "UI-15"])


class PruebaAlcance(ConSemilla):
    def test_backend_sin_css_es_no_aplica(self):
        self.repo.escribe("backend/app/main.py", "app = 1\n")
        r = self.repo.juzga()
        self.assertEqual(
            "NO_APLICA", r.veredicto, "un repositorio sin interfaz no tiene interfaz que juzgar"
        )

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
        self.repo.escribe(
            "src/estilos.css",
            ":root { --v: #064928; }\n"
            "[data-theme='oscuro'] { --f: #1a1f1c; }\n"
            ".t { color: var(--v); transition: all .2s; }\n"
            ".t:focus { outline: 0; }\n",
        )
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertFalse(r.hallazgos, f"no debía juzgar nada: {[h.regla for h in r.hallazgos]}")

    def test_la_declaracion_lo_enciende(self):
        """El mismo CSS, con el marcador puesto, sí se juzga.

        Las dos pruebas juntas son lo que hace que este juez tenga alcance: sin
        la segunda, `NO_APLICA` podría estar tapando que el juez no mira nada.
        """
        self.repo.escribe(".semilla", SEMILLA)
        self.repo.escribe(
            "src/estilos.css",
            ":root { --v: #064928; }\n"
            "[data-theme='oscuro'] { --f: #1a1f1c; }\n"
            ".t { color: var(--v); transition: all .2s; }\n"
            ".t:focus { outline: 0; }\n",
        )
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

    CSS_MALO = (
        ":root { --v: #064928; }\n"
        "[data-theme='oscuro'] { --f: #1a1f1c; }\n"
        ".t { color: var(--v); transition: all .2s; }\n"
    )

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
