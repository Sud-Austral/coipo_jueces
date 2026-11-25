"""AUD-1: la auditoría está siempre, con el último ingreso de cada persona.

Fixtures SINTÉTICOS: este repositorio es público.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo, RepoSintetico  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import comun_auditoria as aud  # noqa: E402
import j12_semilla as j12  # noqa: E402

NUEVA = "version: 2026-11-22\nfabrica: 2026-11-22\nadopta: semilla, interfaz\n"
# El día anterior a la vigencia: la frontera, por el lado que sólo avisa.
VISPERA = "version: 2026-11-21\nfabrica: 2026-11-21\nadopta: semilla, interfaz\n"
VIEJA = "version: 2026-10-24\nfabrica: 2026-10-24\nadopta: semilla, interfaz\n"
MAIN_CABLEADO = "from app.composicion.acceso import montar_acceso\nmontar_acceso(app, c)\n"
FRONTEND = "frontend/package.json"
# Las cuatro piezas selladas de la auditoría, escritas AQUÍ y no leídas de `aud.SELLADAS`:
# una prueba que saca sus casos de la constante que vigila no ve que la constante encoja
# (medido el 2026-11-25: recorriendo `aud.SELLADAS`, dejarla en una sola pieza pasaba).
CUATRO_SELLADAS = (
    "backend/app/adaptadores/entrada/http/middleware_acceso.py",
    "backend/app/adaptadores/entrada/http/rutas/autenticacion.py",
    "backend/app/adaptadores/salida/postgres/auditor.py",
    "backend/app/adaptadores/salida/postgres/registro_de_accesos.py",
)


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

    def _app_cableada(
        self,
        marcador: str = NUEVA,
        sin: str | tuple[str, ...] = (),
        repo: RepoSintetico | None = None,
    ) -> RepoSintetico:
        """Una aplicación con TODO lo que AUD-1 pide, menos lo que nombre `sin`."""
        repo = repo or self.repo
        fuera = {sin} if isinstance(sin, str) else set(sin)
        repo.escribe(".semilla", marcador)
        piezas = {
            **{ruta: "x = 1\n" for ruta in CUATRO_SELLADAS},
            aud.COMPOSICION: "def montar_acceso(app, c): ...\n",
            aud.MAIN: MAIN_CABLEADO,
            aud.RUTA_ACTIVIDAD: '@router.get("/ultimos-ingresos")\n',
            FRONTEND: "{}\n",
            aud.VISTA_ACTIVIDAD: "export default 1\n",
            aud.VISTA_INGRESOS: "export default 1\n",
        }
        for ruta, texto in piezas.items():
            if ruta not in fuera:
                repo.escribe(ruta, texto)
        return repo

    def _otra_app(self) -> RepoSintetico:
        """Otro repositorio sintético contra el mismo lock: una falta por aplicación."""
        repo = RepoSintetico(j12)
        self.addCleanup(repo.cierra)
        repo.escribe("frontend/nginx.conf", "server {}\n")
        return repo

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
        self._app_cableada(sin=CUATRO_SELLADAS[0])
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

    # -- la vigencia, por sus dos lados ----------------------------------------

    def test_sembrada_la_vispera_de_la_vigencia_solo_avisa(self) -> None:
        """La frontera, que nadie fijaba: sembrada el 2026-11-21 avisa; el 22, bloquea.

        Las pruebas tenían dos fechas alejadas (2026-10-24 y 2026-11-22), así que
        `VIGENCIA_AUDITORIA` podía moverse un día o un mes y la suite seguía en verde
        (mutación del 2026-11-24). Un día antes es lo que con FAB-9 habría puesto a bloquear
        a dos aplicaciones sembradas el día de su publicación (REGLAS.md, fila de FAB-9).
        """
        self._app_cableada(marcador=VISPERA)
        self.repo.escribe(aud.MAIN, "app = 1\n")
        r = self.repo.juzga()
        self.assertRegla("AUD-1", "AVISA", "montar_acceso", r)
        self.assertFalse([h for h in r.bloqueantes if h.regla == "AUD-1"])

    # -- cada cosa que AUD-1 pide, una por una ----------------------------------

    def test_sin_cada_pieza_sellada_bloquea_por_su_archivo(self) -> None:
        """Las cuatro piezas selladas de la auditoría, una por una.

        Sólo se probaba la primera: `SELLADAS` podía quedarse en una pieza y la suite seguía
        en verde (mutación del 2026-11-24). El hallazgo nombra el archivo que falta, y sólo
        ése. Si la semilla añade o renombra una pieza de la auditoría, esta lista se cambia
        a propósito, junto con `SELLADAS` y la fila de REGLAS.md.
        """
        self.assertEqual(set(CUATRO_SELLADAS), set(aud.SELLADAS))
        for ruta in CUATRO_SELLADAS:
            with self.subTest(falta=ruta):
                r = self._app_cableada(sin=ruta, repo=self._otra_app()).juzga()
                self.assertEqual([ruta], [h.archivo for h in r.hallazgos if h.regla == "AUD-1"])
                self.assertRegla("AUD-1", "BLOQUEA", "pieza sellada", r)

    def test_sin_la_composicion_del_acceso_bloquea(self) -> None:
        """`composicion/acceso.py` es donde se arman la sesión, el IAM y el auditor. Nada
        exigía que estuviera: la comprobación se podía quitar entera (mutación del
        2026-11-24)."""
        self._app_cableada(sin=aud.COMPOSICION)
        h = self.assertRegla("AUD-1", "BLOQUEA", "composición")
        self.assertEqual(aud.COMPOSICION, h.archivo)

    def test_sin_la_ruta_de_ultimos_ingresos_bloquea(self) -> None:
        """Sin la ruta `ultimos-ingresos` el administrador no ve el último ingreso de nadie.

        Falta igual si `rutas/actividad.py` está y no la sirve que si no está, y un archivo
        ausente no puede tumbar el juez. Nada lo exigía: la comprobación se podía quitar
        entera (mutación del 2026-11-24).
        """
        with self.subTest(caso="el archivo está y no sirve la ruta"):
            self._app_cableada()
            self.repo.escribe(aud.RUTA_ACTIVIDAD, "router = APIRouter()\n")
            h = self.assertRegla("AUD-1", "BLOQUEA", "últimos ingresos")
            self.assertEqual(aud.RUTA_ACTIVIDAD, h.archivo)
        with self.subTest(caso="el archivo no está"):
            otra = self._app_cableada(sin=aud.RUTA_ACTIVIDAD, repo=self._otra_app())
            h = self.assertRegla("AUD-1", "BLOQUEA", "últimos ingresos", otra.juzga())
            self.assertEqual(aud.RUTA_ACTIVIDAD, h.archivo)

    def test_sin_la_vista_de_actividad_bloquea(self) -> None:
        """`Actividad.tsx` es la pestaña del administrador y `UltimosIngresos.tsx` lo que
        muestra dentro. Sólo se probaba la segunda: la primera podía dejar de exigirse
        (mutación del 2026-11-24)."""
        self._app_cableada(sin=aud.VISTA_ACTIVIDAD)
        r = self.repo.juzga()
        self.assertEqual(
            [aud.VISTA_ACTIVIDAD], [h.archivo for h in r.hallazgos if h.regla == "AUD-1"]
        )
        self.assertRegla("AUD-1", "BLOQUEA", "vista del administrador", r)

    def test_sin_frontend_no_se_exigen_las_vistas(self) -> None:
        """Una aplicación sin `frontend/package.json` no tiene dónde poner las vistas: no se
        le piden, y lo demás de AUD-1 se mira igual. Sin esa condición todo backend sin
        frontend sembrado desde la vigencia saldría bloqueado, y ninguna prueba lo notaba
        (mutación del 2026-11-24)."""
        self._app_cableada(sin=(FRONTEND, aud.VISTA_ACTIVIDAD, aud.VISTA_INGRESOS))
        r = self.repo.juzga()
        self.assertSinRegla("AUD-1", r)
        self.assertTrue([c for c in r.comprobado if c.startswith("AUD-1")], r.comprobado)

    def test_importar_el_acceso_no_es_montarlo(self) -> None:
        """Lo que se busca en `main.py` es la llamada `montar_acceso(`, no la palabra
        «acceso»: importar el módulo sin llamarla deja la aplicación sin registro de
        accesos. Con cualquier mención dándose por buena, la suite seguía en verde (mutación
        del 2026-11-24)."""
        self._app_cableada()
        self.repo.escribe(aud.MAIN, "from app.composicion.acceso import contenedor\napp = 1\n")
        h = self.assertRegla("AUD-1", "BLOQUEA", "montar_acceso")
        self.assertEqual(aud.MAIN, h.archivo)

    # -- lo que registra ---------------------------------------------------------

    def test_registra_su_comprobacion(self) -> None:
        """Con todo en su sitio no hay hallazgos, y la única señal de que AUD-1 corrió es su
        comprobación: sin ella, «cero hallazgos» no se distingue de «no miró» (mutación del
        2026-11-24)."""
        self._app_cableada()
        r = self.repo.juzga()
        self.assertSinRegla("AUD-1", r)
        self.assertTrue([c for c in r.comprobado if c.startswith("AUD-1")], r.comprobado)

    def test_sin_backend_no_registra_comprobacion(self) -> None:
        """Sin `backend/app/` no hay nada que mirar, y lo que no se miró no se cuenta."""
        self.repo.escribe(".semilla", NUEVA)
        self.assertEqual([], [c for c in self.repo.juzga().comprobado if c.startswith("AUD-1")])


class PruebaContraLoPublicado(unittest.TestCase):
    """Lo que AUD-1 da por cierto fuera de su código: su fila de REGLAS.md.

    Que las piezas que exige sigan selladas en el lock real lo comprueba
    `tests/test_datos_semilla.py`, una sola vez."""

    def _fila_de_reglas(self) -> str:
        texto = (RAIZ / "REGLAS.md").read_text(encoding="utf-8")
        filas = [linea for linea in texto.splitlines() if linea.startswith("| `AUD-1`")]
        self.assertEqual(1, len(filas), "REGLAS.md tiene que traer UNA fila para AUD-1")
        return filas[0]

    def test_reglas_md_da_la_misma_vigencia_que_el_codigo(self) -> None:
        """La fecha desde la que AUD-1 bloquea está escrita en `VIGENCIA_AUDITORIA` y en la
        fila de REGLAS.md, y nada las ataba: se podía mover una sin tocar la otra.

        Se busca «desde el <fecha>» y no la fecha a secas: la fila cita también el
        2026-11-21, el día de la decisión, y con la fecha suelta un `VIGENCIA_AUDITORIA`
        adelantado a ese día pasaba (medido el 2026-11-25)."""
        self.assertIn(f"desde el {j12.VIGENCIA_AUDITORIA}", self._fila_de_reglas())

    def test_reglas_md_nombra_cada_pieza_sellada_que_se_exige(self) -> None:
        """La fila lista por su nombre las piezas selladas que AUD-1 exige: si `SELLADAS`
        gana una, el catálogo tiene que decirlo."""
        fila = self._fila_de_reglas()
        for ruta in aud.SELLADAS:
            with self.subTest(pieza=ruta):
                self.assertIn(Path(ruta).name, fila)


if __name__ == "__main__":
    unittest.main()
