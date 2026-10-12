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
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

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
# La ventana de compatibilidad (D2, 2026-10-12)
# --------------------------------------------------------------------------

# Todo sintético. «Anterior» es otra versión inventada de la misma pieza: ningún
# contenido ni huella sale de un repositorio de CONAF.
ANTERIOR = "server {\n    listen 7000;\n}\n"
MOVIDO = "2026-10-14"
HASTA = "2026-11-13"
DENTRO = "2026-10-20"
ULTIMO_DIA = HASTA
DIA_SIGUIENTE = "2026-11-14"
MUCHO_DESPUES = "2027-03-01"


def texto_anterior(entradas: dict[str, str] | None = None, movido: str = MOVIDO,
                   hasta: str = HASTA) -> str:
    """Un `semilla.lock.anterior` bien formado, con el contrato que escribe
    `sellar.py --escribir`. `entradas` es ruta -> CONTENIDO (se calcula la huella)."""
    entradas = {CONGELADO: ANTERIOR} if entradas is None else entradas
    cuerpo = "".join(f"{huella(c)}  {r}\n" for r, c in entradas.items())
    return ("# semilla.lock.anterior — archivo de prueba, sintético.\n#\n"
            f"# movido: {movido}\n# ventana_hasta: {hasta}\n#\n"
            f"# {len(entradas)} archivos.\n\n{cuerpo}")


class PruebaVentana(unittest.TestCase):
    """Una pieza del lock ANTERIOR está desfasada, no editada.

    Mover `v2` pone en `SEM-1` a toda aplicación sembrada con la semilla anterior
    por un archivo que ella no tocó (`VERSIONADO.md`, `v2.0.11`). La ventana lo
    distingue: AVISA con fecha hasta `ventana_hasta`, BLOQUEA después. Y la regla
    que más importa de esta clase es la contraria: **ninguna combinación de
    ventana, fecha o archivo roto produce un hallazgo sobre una pieza que coincide
    con el lock vigente**, ni oculta el bloqueo de una pieza realmente editada.
    """

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")
        self.repo = RepoSintetico(j12)
        self.addCleanup(self.repo.cierra)
        self.lock = Path(self.repo.dir) / "semilla.lock.prueba"
        self.lock.write_text(f"{huella(CONTENIDO)}  {CONGELADO}\n", encoding="utf-8")
        # `_ruta_anterior()` sale de `LOCK`, así que parchear `LOCK` mueve ambos.
        self.anterior = Path(str(self.lock) + ".anterior")
        self._real, j12.LOCK = j12.LOCK, self.lock
        self.addCleanup(lambda: setattr(j12, "LOCK", self._real))

    # -- ayudas ---------------------------------------------------------------

    def sembrado(self, contenido: str) -> None:
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe(CONGELADO, contenido)

    def juzga_el(self, fecha: str):
        """Juzga fingiendo que hoy es `fecha`, parcheando `_hoy`, no el reloj."""
        with mock.patch.object(j12, "_hoy",
                               return_value=datetime.date.fromisoformat(fecha)):
            return self.repo.juzga()

    def hallazgo(self, r):
        self.assertEqual(1, len(r.hallazgos), [h.mensaje for h in r.hallazgos])
        return r.hallazgos[0]

    # -- dentro de la ventana: avisa ------------------------------------------

    def test_dentro_de_la_ventana_avisa_y_no_bloquea(self):
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        self.sembrado(ANTERIOR)
        r = self.juzga_el(DENTRO)
        self.assertEqual([], r.bloqueantes)
        h = self.hallazgo(r)
        self.assertEqual("SEM-1", h.regla)
        self.assertEqual(CONGELADO, h.archivo)
        self.assertIn("pieza CONGELADA de una versión ANTERIOR de la semilla", h.mensaje)
        self.assertNotIn(
            "es una pieza CONGELADA de la semilla y está editada", h.mensaje,
            "no puede acusar de editar lo que la aplicación no tocó")

    def test_el_aviso_trae_las_fechas_y_el_arreglo(self):
        """Un aviso con fecha límite que no la dice no es un aviso con fecha."""
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        self.sembrado(ANTERIOR)
        h = self.hallazgo(self.juzga_el(DENTRO))
        self.assertIn(MOVIDO, h.mensaje)
        self.assertIn(HASTA, h.mensaje)
        self.assertIn("2026-11-14", h.mensaje, "y el día en que empieza a bloquear")
        self.assertIn("sembrar.py", h.arreglo)
        self.assertIn("--actualizar", h.arreglo)
        self.assertTrue(h.manifestacion.strip(), "un hallazgo sin manifestación no existe")
        self.assertIn("versión anterior de la semilla", h.manifestacion)

    def test_el_ultimo_dia_de_la_ventana_todavia_avisa(self):
        """`ventana_hasta` es INCLUSIVE: un plazo que vence a medianoche del día
        anterior al que dice es un plazo mal escrito."""
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        self.sembrado(ANTERIOR)
        r = self.juzga_el(ULTIMO_DIA)
        self.assertEqual([], r.bloqueantes)
        self.assertEqual(1, len(r.hallazgos))

    def test_antes_de_la_fecha_de_movido_tambien_avisa(self):
        """Un reloj adelantado o atrasado no convierte el aviso en bloqueo."""
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        self.sembrado(ANTERIOR)
        r = self.juzga_el("2026-10-01")
        self.assertEqual([], r.bloqueantes)
        self.assertEqual(1, len(r.hallazgos))

    # -- fuera de la ventana: bloquea -----------------------------------------

    def test_fuera_de_la_ventana_bloquea_como_desfasada(self):
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        self.sembrado(ANTERIOR)
        for fecha in (DIA_SIGUIENTE, MUCHO_DESPUES):
            with self.subTest(hoy=fecha):
                r = self.juzga_el(fecha)
                h = self.hallazgo(r)
                self.assertEqual([h], r.bloqueantes)
                self.assertIn(f"la ventana de compatibilidad venció el {HASTA}", h.mensaje)
                self.assertIn("desfasada", h.mensaje)
                self.assertIn("No está editada", h.mensaje)
                self.assertIn(MOVIDO, h.mensaje)
                self.assertIn("--actualizar", h.arreglo)
                self.assertTrue(h.manifestacion.strip())

    # -- ni vigente ni anterior: editada, como siempre ------------------------

    def test_ni_vigente_ni_anterior_bloquea_como_editada(self):
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        self.sembrado(CONTENIDO + "# un cambio inocente de una app con prisa\n")
        for fecha in (DENTRO, ULTIMO_DIA, DIA_SIGUIENTE):
            with self.subTest(hoy=fecha):
                r = self.juzga_el(fecha)
                self.assertBloqueaEditada(r)

    def test_editar_la_version_anterior_tampoco_la_salva(self):
        """Partir de la pieza anterior y retocarla es una edición. La ventana
        reconoce un contenido que FUE el vigente, byte a byte, nada más."""
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        self.sembrado(ANTERIOR + "# y ademas lo toque\n")
        self.assertBloqueaEditada(self.juzga_el(DENTRO))

    def assertBloqueaEditada(self, r):
        h = self.hallazgo(r)
        self.assertEqual([h], r.bloqueantes)
        self.assertIn("es una pieza CONGELADA de la semilla y está editada", h.mensaje)
        self.assertNotIn("ANTERIOR", h.mensaje)

    # -- sin archivo anterior: el comportamiento de siempre -------------------

    def test_sin_archivo_anterior_se_comporta_como_antes(self):
        self.assertFalse(self.anterior.exists())
        self.assertIsNone(j12._anterior())
        self.sembrado(ANTERIOR)         # sería «desfasada» si hubiera ventana
        r = self.juzga_el(DENTRO)
        self.assertBloqueaEditada(r)
        self.assertEqual([], r.no_evaluado, "su ausencia no se anota: es el caso normal")

    # -- archivo anterior ilegible: no oculta el bloqueo, y se anota ----------

    def test_anterior_ilegible_no_oculta_el_bloqueo_y_se_anota(self):
        sin_entradas = texto_anterior({})
        casos = {
            "falta ventana_hasta": texto_anterior().replace(
                f"# ventana_hasta: {HASTA}\n", ""),
            "falta movido": texto_anterior().replace(f"# movido: {MOVIDO}\n", ""),
            "fecha imposible": texto_anterior(hasta="2026-13-45"),
            "ventana anterior a movido": texto_anterior(movido=HASTA, hasta=MOVIDO),
            "sin entradas": sin_entradas,
            "vacio": "",
            "basura": "esto no es un lock\n",
        }
        for nombre, texto in casos.items():
            with self.subTest(caso=nombre):
                self.anterior.write_text(texto, encoding="utf-8")
                self.repo.escribe(".semilla", "version: 2026-09-05\n")
                self.repo.escribe(CONGELADO, ANTERIOR)
                r = self.juzga_el(DENTRO)        # DENTRO de lo que sería la ventana
                self.assertBloqueaEditada(r)
                notas = [n for n in r.no_evaluado if ".anterior" in n]
                self.assertEqual(1, len(notas), r.no_evaluado)
                self.assertIn("no se pudo leer", notas[0])
                self.assertIn("EDITADA", notas[0], "dice qué consecuencia tiene")

    def test_anterior_con_bytes_que_no_son_utf8(self):
        self.anterior.write_bytes(b"\xff\xfe\x00\x80 no es texto\n")
        self.sembrado(ANTERIOR)
        r = self.juzga_el(DENTRO)
        self.assertBloqueaEditada(r)
        self.assertEqual(1, len([n for n in r.no_evaluado if ".anterior" in n]))

    def test_anterior_que_es_un_directorio(self):
        """Existe pero no se puede leer: otra forma de «ilegible», por OSError."""
        self.anterior.mkdir()
        self.sembrado(ANTERIOR)
        r = self.juzga_el(DENTRO)
        self.assertBloqueaEditada(r)
        self.assertEqual(1, len([n for n in r.no_evaluado if ".anterior" in n]))

    def test_anterior_ilegible_no_aparece_si_no_se_juzga_nada(self):
        """La nota sólo sale donde el archivo se habría usado: un repositorio sin
        `.semilla` sigue siendo NO_APLICA y no se llena de ruido."""
        self.anterior.write_text("basura\n", encoding="utf-8")
        self.repo.escribe(CONGELADO, "server { listen 9999; }\n")
        r = self.juzga_el(DENTRO)
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.no_evaluado)

    def test_el_fin_de_linea_del_anterior_no_importa(self):
        """Se escribe en Windows y se lee en un runner Linux, o al revés."""
        texto = texto_anterior().replace("\n", "\r\n")
        self.anterior.write_bytes(texto.encode("utf-8"))
        self.sembrado(ANTERIOR)
        r = self.juzga_el(DENTRO)
        self.assertEqual([], r.bloqueantes)
        self.assertEqual(1, len(r.hallazgos))
        self.assertEqual([], r.no_evaluado)

    def test_se_lee_lo_que_dice_el_contrato(self):
        self.anterior.write_text(texto_anterior(), encoding="utf-8")
        hashes, movido, hasta = j12._anterior()
        self.assertEqual({CONGELADO: huella(ANTERIOR)}, hashes)
        self.assertEqual(datetime.date(2026, 10, 14), movido)
        self.assertEqual(datetime.date(2026, 11, 13), hasta)

    # -- la supresión sigue mandando ------------------------------------------

    def test_la_supresion_tiene_precedencia_sobre_la_ventana(self):
        """Quien se suprime a sí mismo paga lo mismo en cualquier fecha: la pieza
        retocada coincide con el lock anterior (que contenía la marca), y aun así
        sale como supresión contada, no como aviso ni como bloqueo."""
        con_marca = ("# coipo-jueces:ignorar(SEM-1) cabecera exigida por seguridad\n"
                     + ANTERIOR)
        self.anterior.write_text(texto_anterior({CONGELADO: con_marca}),
                                 encoding="utf-8")
        self.sembrado(con_marca)
        for fecha in (DENTRO, ULTIMO_DIA, DIA_SIGUIENTE):
            with self.subTest(hoy=fecha):
                r = self.juzga_el(fecha)
                self.assertEqual([], r.hallazgos)
                self.assertEqual(1, len(r.supresiones), r.supresiones)

    # -- la regla que más importa: lo vigente nunca acusa ---------------------

    def test_un_hash_igual_al_vigente_nunca_produce_hallazgo(self):
        """Ni con ventana, ni sin ella, ni vencida, ni con el archivo roto, ni con
        un anterior que (degenerado) trae el mismo hash que el vigente."""
        anteriores = {
            "ausente": None,
            "distinto": texto_anterior(),
            "igual al vigente": texto_anterior({CONGELADO: CONTENIDO}),
            "ilegible": "basura\n",
        }
        for nombre, texto in anteriores.items():
            for fecha in ("2026-10-01", DENTRO, ULTIMO_DIA, DIA_SIGUIENTE,
                          MUCHO_DESPUES):
                with self.subTest(anterior=nombre, hoy=fecha):
                    if texto is None:
                        self.anterior.unlink(missing_ok=True)
                    else:
                        self.anterior.write_text(texto, encoding="utf-8")
                    self.sembrado(CONTENIDO)
                    r = self.juzga_el(fecha)
                    self.assertEqual([], r.hallazgos,
                                     [h.mensaje for h in r.hallazgos])
                    self.assertEqual([], r.supresiones)
                    self.assertEqual("OK", r.veredicto)

    # -- la ventana se aplica pieza por pieza ---------------------------------

    def test_cada_pieza_se_juzga_por_su_cuenta(self):
        """Una vigente, una atrasada y una editada en la MISMA aplicación: nada
        se contagia de una a otra."""
        vigentes = {"frontend/nginx.conf": CONTENIDO,
                    "backend/Dockerfile": "FROM ejemplo:2\n",
                    "backend/requirements-base.txt": "ejemplo>=2\n"}
        self.lock.write_text("".join(f"{huella(c)}  {r}\n"
                                     for r, c in vigentes.items()), encoding="utf-8")
        self.anterior.write_text(texto_anterior({
            "frontend/nginx.conf": ANTERIOR,
            "backend/Dockerfile": "FROM ejemplo:1\n",
            "backend/requirements-base.txt": "ejemplo>=1\n"}), encoding="utf-8")
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe("frontend/nginx.conf", CONTENIDO)                # vigente
        self.repo.escribe("backend/Dockerfile", "FROM ejemplo:1\n")        # atrasada
        self.repo.escribe("backend/requirements-base.txt", "ejemplo>=9\n") # editada
        r = self.juzga_el(DENTRO)
        por_archivo = {h.archivo: h for h in r.hallazgos}
        self.assertEqual({"backend/Dockerfile", "backend/requirements-base.txt"},
                         set(por_archivo))
        self.assertEqual([por_archivo["backend/requirements-base.txt"]], r.bloqueantes)
        self.assertIn("ANTERIOR", por_archivo["backend/Dockerfile"].mensaje)

    # -- «hoy» no tiene interruptor externo -----------------------------------

    def test_hoy_es_la_fecha_del_reloj_y_ninguna_variable_la_mueve(self):
        """Fijado como contrato: una variable de entorno que moviera «hoy» sería
        una prórroga de la ventana que nada cuenta, que es lo que la supresión
        paga. Si algún día se añade, esta prueba se reescribe A PROPÓSITO."""
        antes = datetime.date.today()
        with mock.patch.dict(os.environ, {"JUECES_HOY": "2020-01-01"}):
            hoy = j12._hoy()
        self.assertIn(hoy, {antes, datetime.date.today()})


if __name__ == "__main__":
    unittest.main(verbosity=2)
