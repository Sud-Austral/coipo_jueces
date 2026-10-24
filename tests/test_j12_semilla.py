"""Pruebas de j12 — las piezas congeladas de la semilla no se editan.

La prueba que más importa de este archivo es
`test_un_repo_que_no_se_sembro_no_se_juzga`. La primera versión de este juez
comparaba por RUTA, sin exigir declaración, y puso rojos a cuatro repositorios
de la flota por tener su propio `backend/Dockerfile` y su propio
`frontend/nginx.conf`. **Ninguno se sembró jamás con esta semilla.**

Es la misma lección que ya costó una vez aquí al intentar deducir las
capacidades de un repositorio leyendo su código: hay cosas que hay que declarar.
"""

from __future__ import annotations

import datetime
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo, RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j12_semilla as j12  # noqa: E402

CONGELADO = "frontend/nginx.conf"
CONTENIDO = "server {\n    listen 8000;\n}\n"


def huella(texto: str) -> str:
    return hashlib.sha256(texto.replace("\r\n", "\n").encode("utf-8")).hexdigest()


class PruebaSemilla(CasoConRepo):
    MODULO = j12

    def setUp(self):
        super().setUp()
        # Un lock sintético, sin tocar el real. El repositorio es público: no se
        # copia nada de un repositorio privado de CONAF, ni siquiera un hash.
        self.lock = Path(self.repo.dir) / "semilla.lock.prueba"
        self.lock.write_text(f"{huella(CONTENIDO)}  {CONGELADO}\n", encoding="utf-8")
        self._real, j12.LOCK = j12.LOCK, self.lock
        self.addCleanup(lambda: setattr(j12, "LOCK", self._real))

    def _sembrado(self, contenido: str = CONTENIDO):
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe(CONGELADO, contenido)

    def test_intacto_no_bloquea(self):
        self._sembrado()
        self.assertSinBloqueos()

    def test_editado_bloquea(self):
        self._sembrado(CONTENIDO + "# un cambio inocente de una app con prisa\n")
        self.assertBloquea("pieza CONGELADA de la semilla y está editada")

    def test_un_repo_que_no_se_sembro_no_se_juzga(self):
        """El falso positivo que puso rojos a cuatro repositorios de la flota.

        Este repositorio tiene un `frontend/nginx.conf` que NO viene de la
        semilla: se llama igual porque toda aplicación web tiene uno.
        """
        self.repo.escribe(CONGELADO, "server { listen 9999; }\n")   # sin `.semilla`
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertEqual("NO_APLICA", r.veredicto)

    def test_el_fin_de_linea_no_es_una_diferencia(self):
        """293 archivos de `coipo_prensa2` tienen CRLF en el árbol de trabajo.

        Un juez que fallara por eso pondría rojo medio Windows por un motivo que
        no tiene nada que ver con el contenido, y se suprimiría en una semana.
        """
        self._sembrado(CONTENIDO.replace("\n", "\r\n"))
        self.assertSinBloqueos()

    def test_que_falte_una_pieza_no_es_un_hallazgo(self):
        """No toda aplicación sembrada usa todas las piezas."""
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe("README.md", "# sin frontend\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)

    def test_supresion_con_motivo(self):
        self._sembrado("# coipo-jueces:ignorar(SEM-1) cabecera exigida por seguridad\n"
                       + CONTENIDO)
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_sin_lock_no_se_declara_conforme(self):
        """Un juez cuyo catálogo no está no aprueba: se declara incapaz de mirar."""
        self._sembrado()
        self.lock.unlink()
        r = self.repo.juzga()
        self.assertEqual([], r.comprobado)
        self.assertTrue(r.no_evaluado, "tiene que decir que no pudo evaluar")
        self.assertEqual("SIN_EVALUAR", r.veredicto)


class PruebaAdopcion(PruebaSemilla):
    """La clave `adopta:` de `.semilla`, en las dos direcciones.

    Estas pruebas se escribieron porque al implementar `adopta:` NINGUNA de las
    existentes se rompió. Cero pruebas rotas es cero cobertura: se podía
    implementar la clave entera, romperla, y la suite salía verde con sus 137.
    Es el mismo patrón que `comun.py` denuncia —cero hallazgos con cero
    comprobaciones no es conformidad— aplicado a la propia suite.
    """

    def _con_adopta(self, valor, contenido=CONTENIDO):
        self.repo.escribe(".semilla", "version: 2026-09-05\nadopta: " + valor + "\n")
        self.repo.escribe(CONGELADO, contenido)

    def test_sin_clave_adopta_se_juzga_todo(self):
        """La retrocompatibilidad, fijada como contrato y no como accidente.

        Los `.semilla` que `sembrar.py` escribió antes de existir esta clave no
        la llevan. Que la ausencia signifique «adopta todo» es lo que hace que
        ningún veredicto de la flota cambie al desplegar esto.
        """
        self._sembrado(CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_sin_semilla_es_no_aplica_y_dice_por_que(self):
        """Y la razón tiene que NOMBRAR la línea que la produjo.

        Un `no_aplica` autodeclarado que no se puede leer es indistinguible de
        uno honesto. La pieza congelada está EDITADA a propósito: sin la clave
        esto sería un bloqueante.
        """
        self._con_adopta("interfaz", CONTENIDO + "# editado\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.hallazgos)
        self.assertTrue(r.no_aplica, "tiene que decir por qué")
        self.assertIn(".semilla:2", r.no_aplica[0])
        self.assertIn("adopta: interfaz", r.no_aplica[0])

    def test_adopta_sin_semilla_se_cuenta_como_supresion(self):
        """Se paga. Es la única vía por la que un repositorio se apaga un juez a
        sí mismo, y `comun.py` explica por qué esa puerta no puede salir gratis:
        sale con `::warning::` y exige su fila en DEUDA.md."""
        self._con_adopta("interfaz", CONTENIDO + "# editado\n")
        r = self.repo.juzga()
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_adopta_con_semilla_sigue_bloqueando(self):
        """Declararlo explícitamente no relaja nada."""
        self._con_adopta("semilla, interfaz", CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_comentado_no_declara_nada(self):
        """El peor caso posible si el patrón se copiara mal.

        Un `# adopta: interfaz` dentro de un comentario que apagara j12 sería una
        puerta trasera invisible en un diff. La expresión exige que la clave
        empiece la línea tras espacios, y `#` no es espacio en blanco.
        """
        self.repo.escribe(".semilla", "# adopta: interfaz\nversion: 2026-09-05\n")
        self.repo.escribe(CONGELADO, CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_en_mayusculas_y_sin_espacio(self):
        """`adopta:SEMILLA` cuenta igual: nadie debería perder o ganar un juez
        por un espacio o una mayúscula."""
        self.repo.escribe(".semilla", "version: 2026-09-05\nadopta:SEMILLA\n")
        self.repo.escribe(CONGELADO, CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_desconocido_no_apaga_este_juez_en_silencio(self):
        """Un typo —`adopta: semila`— no puede apagar el juez sin decirlo.

        Sale NO_APLICA, que es lo correcto porque la lista no incluye la capa,
        pero la razón cita la línea literal: quien lea el resumen ve el typo.
        """
        self._con_adopta("semila", CONTENIDO + "# editado\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertIn("semila", r.no_aplica[0])
        self.assertEqual(1, len(r.supresiones), "y se cuenta, no sale gratis")


# --------------------------------------------------------------------------
# El historial: atrasada no es editada (decisión del 2026-10-24)
# --------------------------------------------------------------------------

# Todo sintético. Tres versiones inventadas de la misma pieza, de la más vieja a la
# vigente: ningún contenido ni huella sale de un repositorio de CONAF.
V1 = "server {\n    listen 6000;\n}\n"
V2 = "server {\n    listen 7000;\n}\n"
VIGENTE = CONTENIDO
HASTA_V1 = "2026-09-05"
HASTA_V2 = "2026-10-24"
RETIRADA = "db/0000_vieja.sql"
RETIRADA_V1 = "-- una pieza que la semilla partió después\n"


def bloque(hasta: str, entradas: dict[str, str]) -> str:
    """Un bloque del historial; `entradas` es ruta -> CONTENIDO (se calcula la huella)."""
    return f"\n# vigente_hasta: {hasta}\n" + "".join(
        f"{huella(c)}  {r}\n" for r, c in entradas.items())


def texto_historial(*bloques: str, formato: str = "1") -> str:
    """Un `semilla.lock.historial` con el contrato de `sellar.py --escribir`."""
    return ("# semilla.lock.historial — archivo de prueba, sintético.\n#\n"
            f"# formato: {formato}\n# {len(bloques)} bloques.\n" + "".join(bloques))


def historial_de_dos() -> str:
    """V1 publicada hasta HASTA_V1 (con la pieza que después se retiró) y V2 hasta HASTA_V2."""
    return texto_historial(bloque(HASTA_V1, {CONGELADO: V1, RETIRADA: RETIRADA_V1}),
                           bloque(HASTA_V2, {CONGELADO: V2}))


class PruebaHistorial(unittest.TestCase):
    """Una pieza de una semilla anterior está ATRASADA, no editada, y AVISA siempre.

    `FILOSOFIA.md` §3 de la fábrica: «una pieza congelada de una versión anterior no
    es una pieza editada». Y la regla que más importa de esta clase es la contraria:
    **ninguna combinación de historial —ausente, roto o degenerado— produce un
    hallazgo sobre una pieza que coincide con el lock vigente**, ni oculta el
    bloqueo de una pieza realmente editada.
    """

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")
        self.repo = RepoSintetico(j12)
        self.addCleanup(self.repo.cierra)
        self.lock = Path(self.repo.dir) / "semilla.lock.prueba"
        self.lock.write_text(f"{huella(VIGENTE)}  {CONGELADO}\n", encoding="utf-8")
        # `_ruta_historial()` sale de `LOCK`, así que parchear `LOCK` mueve ambos.
        self.historial = Path(str(self.lock) + ".historial")
        self._real, j12.LOCK = j12.LOCK, self.lock
        self.addCleanup(lambda: setattr(j12, "LOCK", self._real))

    # -- ayudas ---------------------------------------------------------------

    def sembrado(self, contenido: str, **otras: str) -> None:
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe(CONGELADO, contenido)
        for ruta, texto in otras.items():
            self.repo.escribe(ruta, texto)

    def con_historial(self, texto: str | None = None) -> None:
        self.historial.write_text(historial_de_dos() if texto is None else texto,
                                  encoding="utf-8")

    def hallazgo(self, r):
        self.assertEqual(1, len(r.hallazgos), [h.mensaje for h in r.hallazgos])
        return r.hallazgos[0]

    def assertAtrasada(self, r, hasta: str, archivo: str = CONGELADO):
        h = self.hallazgo(r)
        self.assertEqual([], r.bloqueantes, "una pieza atrasada no bloquea, nunca")
        self.assertEqual(("SEM-1", archivo), (h.regla, h.archivo))
        self.assertIn("atrasada", h.mensaje)
        self.assertIn(f"publicada hasta el {hasta}", h.mensaje)
        self.assertNotIn("es una pieza CONGELADA de la semilla y está editada", h.mensaje,
                         "no puede acusar de editar lo que la aplicación no tocó")
        self.assertTrue(h.manifestacion.strip(), "un hallazgo sin manifestación no existe")
        return h

    def assertBloqueaEditada(self, r):
        h = self.hallazgo(r)
        self.assertEqual([h], r.bloqueantes)
        self.assertIn("es una pieza CONGELADA de la semilla y está editada", h.mensaje)
        self.assertNotIn("atrasada", h.mensaje)

    # -- vigente: nada --------------------------------------------------------

    def test_la_pieza_vigente_no_produce_hallazgo(self):
        self.con_historial()
        self.sembrado(VIGENTE)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertEqual([], r.no_evaluado, "con historial legible no hay nada que anotar")
        self.assertEqual("OK", r.veredicto)

    # -- atrasada: avisa, con fecha y arreglo, sin plazo ----------------------

    def test_atrasada_una_version_avisa_con_su_fecha_y_el_arreglo(self):
        self.con_historial()
        self.sembrado(V2)
        h = self.assertAtrasada(self.repo.juzga(), HASTA_V2)
        self.assertIn("sembrar.py", h.arreglo)
        self.assertIn("--actualizar", h.arreglo)

    def test_atrasada_dos_versiones_avisa_y_no_bloquea(self):
        """La que D2 bloqueaba: con un solo `.anterior`, una aplicación dos
        resellados atrás se juzgaba como editada. Es la fábrica de su fecha."""
        self.con_historial()
        self.sembrado(V1)
        self.assertAtrasada(self.repo.juzga(), HASTA_V1)

    def test_atrasada_no_tiene_plazo(self):
        """Sin ventana: no hay fecha a partir de la cual el aviso se vuelva bloqueo.
        Se comprueba en el contrato, no con el reloj: el módulo ya no tiene `_hoy`."""
        self.assertFalse(hasattr(j12, "_hoy"), "una fecha de hoy es la puerta a un plazo")
        self.assertFalse(hasattr(j12, "VENTANA_HASTA"))
        self.con_historial()
        self.sembrado(V1)
        h = self.assertAtrasada(self.repo.juzga(), HASTA_V1)
        self.assertNotIn("ventana", h.mensaje + h.arreglo)

    def test_una_huella_en_varios_bloques_lleva_la_fecha_mas_reciente(self):
        """La pieza no cambió entre dos resellados: la semilla la publicó hasta el
        último, y esa es la fecha que dice el aviso."""
        self.con_historial(texto_historial(bloque(HASTA_V1, {CONGELADO: V2}),
                                           bloque(HASTA_V2, {CONGELADO: V2})))
        self.sembrado(V2)
        self.assertAtrasada(self.repo.juzga(), HASTA_V2)

    # -- retirada del lock, pero en el historial ------------------------------

    def test_pieza_retirada_del_lock_sin_editar_avisa_como_atrasada(self):
        """Una pieza que la semilla partió en otras sigue en el historial: tenerla
        tal cual es tener la fábrica de su fecha."""
        self.con_historial()
        self.sembrado(VIGENTE, **{RETIRADA: RETIRADA_V1})
        h = self.assertAtrasada(self.repo.juzga(), HASTA_V1, archivo=RETIRADA)
        self.assertIn("ya no la sella", h.mensaje)
        self.assertIn("no la toca", h.arreglo, "--actualizar no borra lo retirado: se dice")

    def test_pieza_retirada_y_editada_no_se_juzga(self):
        """Ya no es una pieza congelada: las reglas miran hacia adelante."""
        self.con_historial()
        self.sembrado(VIGENTE, **{RETIRADA: RETIRADA_V1 + "-- y es mia\n"})
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertEqual("OK", r.veredicto)

    # -- editada: bloquea, con historial o sin él -----------------------------

    def test_editada_bloquea(self):
        self.con_historial()
        self.sembrado(VIGENTE + "# un cambio inocente de una app con prisa\n")
        self.assertBloqueaEditada(self.repo.juzga())

    def test_editar_una_version_anterior_tampoco_la_salva(self):
        """Partir de la pieza anterior y retocarla es una edición. El historial
        reconoce un contenido que FUE el vigente, byte a byte, nada más."""
        self.con_historial()
        self.sembrado(V2 + "# y ademas lo toque\n")
        self.assertBloqueaEditada(self.repo.juzga())

    # -- historial ausente: el comportamiento de antes, y lo dice -------------

    def test_sin_historial_atrasada_es_editada_y_se_anota(self):
        self.assertFalse(self.historial.exists())
        self.assertIsNone(j12._historial())
        self.sembrado(V2)               # sería «atrasada» si hubiera historial
        r = self.repo.juzga()
        self.assertBloqueaEditada(r)
        notas = [n for n in r.no_evaluado if ".historial" in n]
        self.assertEqual(1, len(notas), r.no_evaluado)
        self.assertIn("no hay", notas[0])
        self.assertIn("EDITADA", notas[0], "dice qué consecuencia tiene")

    def test_el_anterior_de_d2_ya_no_se_lee(self):
        """Un `semilla.lock.anterior` olvidado junto al lock no reabre la ventana."""
        Path(str(self.lock) + ".anterior").write_text(
            "# movido: 2026-10-14\n# ventana_hasta: 2099-01-01\n\n"
            f"{huella(V2)}  {CONGELADO}\n", encoding="utf-8")
        self.sembrado(V2)
        self.assertBloqueaEditada(self.repo.juzga())

    # -- historial ilegible: no oculta el bloqueo, y se anota -----------------

    def test_historial_ilegible_no_oculta_el_bloqueo_y_se_anota(self):
        bueno = historial_de_dos()
        casos = {
            "sin formato": bueno.replace("# formato: 1\n", ""),
            "formato desconocido": historial_de_dos().replace("formato: 1", "formato: 2"),
            "fecha imposible": bueno.replace(HASTA_V2, "2026-13-45"),
            "fecha sin forma": bueno.replace(f"vigente_hasta: {HASTA_V2}",
                                             "vigente_hasta: ayer"),
            "entrada fuera de bloque": texto_historial(
                f"\n{huella(V2)}  {CONGELADO}\n", bloque(HASTA_V2, {CONGELADO: V2})),
            "bloque vacio": texto_historial(f"\n# vigente_hasta: {HASTA_V1}\n",
                                            bloque(HASTA_V2, {CONGELADO: V2})),
            "ultimo bloque vacio": texto_historial(bloque(HASTA_V2, {CONGELADO: V2}),
                                                   f"\n# vigente_hasta: {HASTA_V1}\n"),
            "vacio": "",
            "basura": "esto no es un historial\n",
        }
        for nombre, texto in casos.items():
            with self.subTest(caso=nombre):
                self.con_historial(texto)
                self.sembrado(V2)
                r = self.repo.juzga()
                self.assertBloqueaEditada(r)
                notas = [n for n in r.no_evaluado if ".historial" in n]
                self.assertEqual(1, len(notas), r.no_evaluado)
                self.assertIn("no se pudo leer", notas[0])
                self.assertIn("EDITADA", notas[0], "dice qué consecuencia tiene")

    def test_historial_con_bytes_que_no_son_utf8(self):
        self.historial.write_bytes(b"\xff\xfe\x00\x80 no es texto\n")
        self.sembrado(V2)
        r = self.repo.juzga()
        self.assertBloqueaEditada(r)
        self.assertEqual(1, len([n for n in r.no_evaluado if ".historial" in n]))

    def test_historial_que_es_un_directorio(self):
        """Existe pero no se puede leer: otra forma de «ilegible», por OSError."""
        self.historial.mkdir()
        self.sembrado(V2)
        r = self.repo.juzga()
        self.assertBloqueaEditada(r)
        self.assertEqual(1, len([n for n in r.no_evaluado if ".historial" in n]))

    def test_historial_ilegible_no_aparece_si_no_se_juzga_nada(self):
        """La nota sólo sale donde el archivo se habría usado: un repositorio sin
        `.semilla` sigue siendo NO_APLICA y no se llena de ruido."""
        self.con_historial("basura\n")
        self.repo.escribe(CONGELADO, "server { listen 9999; }\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.no_evaluado)

    def test_el_fin_de_linea_del_historial_no_importa(self):
        """Se escribe en Windows y se lee en un runner Linux, o al revés."""
        self.historial.write_bytes(historial_de_dos().replace("\n", "\r\n").encode("utf-8"))
        self.sembrado(V1)
        r = self.repo.juzga()
        self.assertAtrasada(r, HASTA_V1)
        self.assertEqual([], r.no_evaluado)

    def test_se_lee_lo_que_dice_el_contrato(self):
        self.con_historial()
        d = datetime.date.fromisoformat
        self.assertEqual({CONGELADO: {huella(V1): d(HASTA_V1), huella(V2): d(HASTA_V2)},
                          RETIRADA: {huella(RETIRADA_V1): d(HASTA_V1)}},
                         j12._historial())

    def test_un_historial_sin_bloques_es_legible(self):
        """El de una semilla que todavía no se reselló nunca: no hay versiones
        anteriores, y decirlo no es un archivo roto."""
        self.con_historial(texto_historial())
        self.sembrado(V2)
        r = self.repo.juzga()
        self.assertBloqueaEditada(r)
        self.assertEqual([], r.no_evaluado)

    # -- la supresión sigue mandando ------------------------------------------

    def test_la_supresion_tiene_precedencia_sobre_el_historial(self):
        """Quien se suprime a sí mismo paga lo mismo: la pieza coincide con una
        versión publicada (que contenía la marca) y aun así sale como supresión
        contada, no como aviso."""
        con_marca = ("# coipo-jueces:ignorar(SEM-1) cabecera exigida por seguridad\n" + V2)
        self.con_historial(texto_historial(bloque(HASTA_V2, {CONGELADO: con_marca})))
        self.sembrado(con_marca)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    # -- la regla que más importa: lo vigente nunca acusa ---------------------

    def test_un_hash_igual_al_vigente_nunca_produce_hallazgo(self):
        """Ni sin historial, ni con él, ni roto, ni con un historial que
        (degenerado) trae el mismo hash que el vigente."""
        historiales = {
            "ausente": None,
            "normal": historial_de_dos(),
            "igual al vigente": texto_historial(bloque(HASTA_V2, {CONGELADO: VIGENTE})),
            "ilegible": "basura\n",
        }
        for nombre, texto in historiales.items():
            with self.subTest(historial=nombre):
                if texto is None:
                    self.historial.unlink(missing_ok=True)
                else:
                    self.con_historial(texto)
                self.sembrado(VIGENTE)
                r = self.repo.juzga()
                self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
                self.assertEqual([], r.supresiones)
                self.assertEqual("OK", r.veredicto)

    # -- el historial se aplica pieza por pieza -------------------------------

    def test_cada_pieza_se_juzga_por_su_cuenta(self):
        """Una vigente, dos atrasadas de semillas distintas y una editada en la MISMA
        aplicación: nada se contagia de una a otra."""
        vigentes = {"frontend/nginx.conf": VIGENTE,
                    "backend/Dockerfile": "FROM ejemplo:3\n",
                    "backend/requirements-base.txt": "ejemplo>=3\n",
                    "backend/pyproject.toml": "[tool.ejemplo]\nv = 3\n"}
        self.lock.write_text("".join(f"{huella(c)}  {r}\n"
                                     for r, c in vigentes.items()), encoding="utf-8")
        self.con_historial(texto_historial(
            bloque(HASTA_V1, {"backend/Dockerfile": "FROM ejemplo:1\n",
                              "backend/pyproject.toml": "[tool.ejemplo]\nv = 1\n"}),
            bloque(HASTA_V2, {"backend/Dockerfile": "FROM ejemplo:2\n",
                              "backend/pyproject.toml": "[tool.ejemplo]\nv = 2\n"})))
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe("frontend/nginx.conf", VIGENTE)                   # vigente
        self.repo.escribe("backend/Dockerfile", "FROM ejemplo:2\n")         # atrasada, V2
        self.repo.escribe("backend/pyproject.toml", "[tool.ejemplo]\nv = 1\n")  # atrasada, V1
        self.repo.escribe("backend/requirements-base.txt", "ejemplo>=9\n")  # editada
        r = self.repo.juzga()
        por_archivo = {h.archivo: h for h in r.hallazgos}
        self.assertEqual({"backend/Dockerfile", "backend/pyproject.toml",
                          "backend/requirements-base.txt"}, set(por_archivo))
        self.assertEqual([por_archivo["backend/requirements-base.txt"]], r.bloqueantes)
        self.assertIn(HASTA_V2, por_archivo["backend/Dockerfile"].mensaje)
        self.assertIn(HASTA_V1, por_archivo["backend/pyproject.toml"].mensaje)


if __name__ == "__main__":
    unittest.main(verbosity=2)
