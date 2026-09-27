"""Pruebas de j15 — un job de pago en el `needs:` de un job que corre gratis.

FIXTURES SINTÉTICOS. Ningún workflow de aquí abajo es copia de uno real: este
repositorio es PÚBLICO y `tests/ayuda.py:1-7` dice por qué copiar un archivo de
un repositorio privado de CONAF sería justo la fuga por conveniencia que estos
jueces existen para evitar. Las etiquetas `conaf-ci` y `conaf-prod` sí se usan
porque ya están escritas en este repositorio público
(`.github/workflows/probar-runner.yml:16`) y porque el juez NO las tiene
cableadas: lo que hace facturable a un runner es ser de GitHub.

LA CALIBRACIÓN REAL NO PUEDE VIVIR AQUÍ, y conviene saberlo al leer estas
pruebas. El 2026-09-27 se corrió este juez sobre el estado de la flota ANTERIOR
al arreglo del 2026-09-26 (con `git show <sha anterior>:<workflow>`) y encendió
en ocho repositorios; sobre el estado de hoy, en cero de treinta y dos. Esa
medición está en el docstring de `jueces/j15_cuota.py`, no en un fixture, porque
el fixture tendría que ser el YAML privado.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ayuda import CasoConRepo, RepoSintetico  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j15_cuota as j15  # noqa: E402

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

# EL CASO DEL 2026-09-26, en sintético: el despliegue corre en el runner propio
# y por tanto es gratis, y su única compuerta corre en un runner de GitHub. Sin
# cuota, la compuerta no arranca y el despliegue gratis no llega a ejecutarse.
INCIDENTE = """\
name: Deploy
on:
  push:
    branches: [main]
jobs:
  compuerta:
    runs-on: ubuntu-latest
    steps:
      - run: echo comprobando
  desplegar:
    needs: compuerta
    runs-on: [self-hosted, conaf-prod]
    steps:
      - run: echo desplegando
"""

# El mismo grafo con la compuerta ya migrada: es el arreglo, y no puede avisar.
ARREGLADO = INCIDENTE.replace("runs-on: ubuntu-latest", "runs-on: conaf-ci")

# Los DOS de pago: la cuota los mata a los dos y no hay nada gratis que rescatar.
# Es la primera de las dos puertas contra el falso positivo.
TODO_DE_PAGO = INCIDENTE.replace("runs-on: [self-hosted, conaf-prod]",
                                 "runs-on: ubuntu-22.04")

COMPOSE = "services:\n  app:\n    build:\n      context: .\n"


class PruebaIncidente(CasoConRepo):
    """El control positivo y su negativo, que es el arreglo real."""

    MODULO = j15

    def test_despliegue_gratis_con_compuerta_de_pago_avisa(self):
        """CONTROL POSITIVO. La forma exacta del 2026-09-26."""
        self.repo.escribe(".github/workflows/deploy.yml", INCIDENTE)
        r = self.repo.juzga()
        self.assertAvisa("en un runner DE PAGO", r)
        self.assertSinBloqueos(r)
        h = r.hallazgos[0]
        self.assertEqual("CUOTA-1", h.regla)
        self.assertEqual(".github/workflows/deploy.yml", h.archivo)
        # Ancla la línea del `needs:`, que es donde se lee la relación.
        self.assertEqual(11, h.linea)
        self.assertIn("The job was not started", h.manifestacion)

    def test_la_compuerta_en_el_runner_propio_no_avisa(self):
        """CONTROL NEGATIVO. Es literalmente el arreglo que hizo la flota."""
        self.repo.escribe(".github/workflows/deploy.yml", ARREGLADO)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertEqual("OK", r.veredicto)

    def test_si_los_dos_son_de_pago_no_hay_nada_gratis_que_rescatar(self):
        """La puerta que el encargo pide explícitamente.

        Un `needs:` hacia un job alojado NO es un defecto si el job que depende
        también es alojado: sin cuota se caen los dos, y mover uno no salva nada.
        Marcarlo sería una regla aplicada fuera de su dominio, que es lo que
        `j06_config.py:81-94` llama «el falso positivo que enseña a suprimir».
        """
        self.repo.escribe(".github/workflows/deploy.yml", TODO_DE_PAGO)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_sin_needs_no_hay_arrastre(self):
        """Dos jobs, uno gratis y uno de pago, sin relación: no es este defecto."""
        self.repo.escribe(".github/workflows/deploy.yml",
                          INCIDENTE.replace("    needs: compuerta\n", ""))
        self.assertEqual([], self.repo.juzga().hallazgos)

    def test_el_hallazgo_nombra_el_coste_de_windows(self):
        """Los runners Windows facturan al doble; eso va en el mensaje."""
        self.repo.escribe(".github/workflows/deploy.yml",
                          INCIDENTE.replace("ubuntu-latest", "windows-latest"))
        r = self.repo.juzga()
        self.assertTrue(any("windows de GitHub facturan el DOBLE" in h.manifestacion
                            for h in r.hallazgos),
                        [h.manifestacion for h in r.hallazgos])

    def test_el_hallazgo_nombra_el_coste_de_macos(self):
        self.repo.escribe(".github/workflows/deploy.yml",
                          INCIDENTE.replace("ubuntu-latest", "macos-14"))
        r = self.repo.juzga()
        self.assertTrue(any("macos de GitHub facturan DIEZ VECES" in h.manifestacion
                            for h in r.hallazgos),
                        [h.manifestacion for h in r.hallazgos])

    def test_un_solo_aviso_por_job_aunque_cuelgue_de_seis(self):
        """Medido el 2026-09-27: el estado previo de `coipo_prensa2` daba DOCE.

        Sus dos despliegues cuelgan de seis jobs cada uno. Con un hallazgo por
        arista salían doce avisos idénticos anclados en dos líneas. El arreglo es
        uno —mover esos jobs de runner— y el aviso tiene que ser uno.
        """
        wf = ["name: CI", "on: [push]", "jobs:"]
        for i in range(6):
            wf += [f"  g{i}:", "    runs-on: ubuntu-latest",
                   "    steps:", "      - run: echo x"]
        wf += ["  desplegar:", "    needs: [g0, g1, g2, g3, g4, g5]",
               "    runs-on: conaf-prod", "    steps:", "      - run: echo y"]
        self.repo.escribe(".github/workflows/ci.yml", "\n".join(wf) + "\n")
        r = self.repo.juzga()
        self.assertEqual(1, len(r.hallazgos), [h.mensaje for h in r.hallazgos])
        self.assertIn("6 job(s) en un runner DE PAGO", r.hallazgos[0].mensaje)

    def test_el_compose_entra_en_el_mensaje_como_evidencia(self):
        """El criterio de j01/j08 reutilizado: con compose, lo que para es producción."""
        self.repo.escribe("docker-compose.yml", COMPOSE)
        self.repo.escribe(".github/workflows/deploy.yml", INCIDENTE)
        r = self.repo.juzga()
        self.assertIn("lo despliega el pipeline de la flota",
                      r.hallazgos[0].manifestacion)

    def test_se_puede_suprimir_con_motivo_en_la_linea_anterior(self):
        """En YAML el sitio natural del marcador es la línea de encima."""
        self.repo.escribe(
            ".github/workflows/deploy.yml",
            INCIDENTE.replace(
                "    needs: compuerta\n",
                "    # coipo-jueces:ignorar(CUOTA-1) la compuerta necesita docker de GitHub\n"
                "    needs: compuerta\n"))
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        # Se CUENTA y se publica: `comun.py:87-91`, «un verificador cuyas
        # supresiones nadie mira está desactivado de hecho a los tres meses».
        self.assertEqual(1, len(r.supresiones))
        self.assertIn("la compuerta necesita docker de GitHub", r.supresiones[0])
        self.assertIn(".github/workflows/deploy.yml:12", r.supresiones[0])

    def test_un_marcador_de_otra_regla_no_suprime(self):
        """El marcador nombra la regla. `suprimido()` compara el código exacto."""
        self.repo.escribe(
            ".github/workflows/deploy.yml",
            INCIDENTE.replace(
                "    needs: compuerta\n",
                "    # coipo-jueces:ignorar(CI-1) esto es otra regla distinta\n"
                "    needs: compuerta\n"))
        r = self.repo.juzga()
        self.assertTrue(r.hallazgos, "un marcador de otra regla no puede suprimir")
        self.assertEqual([], r.supresiones)

    def test_un_marcador_sin_motivo_suficiente_no_suprime(self):
        """`comun.py:571-586`: el motivo exige 12 caracteres o no suprime nada."""
        self.repo.escribe(
            ".github/workflows/deploy.yml",
            INCIDENTE.replace(
                "    needs: compuerta\n",
                "    # coipo-jueces:ignorar(CUOTA-1) porque si\n"
                "    needs: compuerta\n"))
        r = self.repo.juzga()
        self.assertTrue(r.hallazgos, "un motivo de menos de 12 caracteres no suprime")
        self.assertEqual([], r.supresiones)


class PruebaCadenaDeReusables(CasoConRepo):
    """El corazón del juez: el runner lo decide un `uses:`, no un `runs-on:`.

    `coipo_jueces/.github/workflows/verificar.yml` acepta `runner:` desde
    `v2.0.9` con `default: ubuntu-latest`. Así que un job que pasa
    `runner: conaf-ci` es GRATIS y uno que no pasa nada es DE PAGO por el valor
    por defecto — y ésa es exactamente la diferencia entre el estado anterior y
    el posterior al arreglo del 2026-09-26.
    """

    MODULO = j15

    LLAMA_AL_REUSABLE = """\
name: Deploy
on: [push]
jobs:
  verificar:
    uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2
    with:
      modo: advisory
      perfil: aplicacion
{runner}  desplegar:
    needs: verificar
    uses: Sud-Austral/infra-docker-base/.github/workflows/deploy.yml@main
    with:
      app_name: x
"""

    def test_sin_runner_en_el_with_la_compuerta_es_de_pago(self):
        """CONTROL POSITIVO por cadena, sin un solo `runs-on:` en el archivo."""
        self.repo.escribe(".github/workflows/deploy.yml",
                          self.LLAMA_AL_REUSABLE.format(runner=""))
        r = self.repo.juzga()
        self.assertAvisa("en un runner DE PAGO", r)
        self.assertIn("valor por defecto de `runner`", r.hallazgos[0].mensaje)

    def test_con_runner_conaf_ci_no_avisa(self):
        """CONTROL NEGATIVO por cadena: es la línea que cerró el incidente."""
        self.repo.escribe(".github/workflows/deploy.yml",
                          self.LLAMA_AL_REUSABLE.format(runner="      runner: conaf-ci\n"))
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertEqual("OK", r.veredicto)

    def test_reusable_local_con_su_propio_runs_on(self):
        """Un `uses: ./.github/workflows/x.yml` SÍ se puede leer, y se lee."""
        self.repo.escribe(".github/workflows/ci.yml", """\
name: CI
on:
  workflow_call:
jobs:
  probar:
    runs-on: ubuntu-latest
    steps:
      - run: echo x
""")
        self.repo.escribe(".github/workflows/deploy.yml", """\
name: Deploy
on: [push]
jobs:
  suite:
    uses: ./.github/workflows/ci.yml
  desplegar:
    needs: suite
    runs-on: conaf-prod
    steps:
      - run: echo y
""")
        r = self.repo.juzga()
        self.assertAvisa("en un runner DE PAGO", r)

    def test_reusable_local_parametrizado_por_input(self):
        """`runs-on: ${{ inputs.runner }}` con `default:`, que es la forma real.

        Sin resolver el input, este caso sería «no pude mirarlo» y el juez no
        vería el defecto central de la flota, que es exactamente no pasarle el
        parámetro al reusable.
        """
        reusable = """\
name: Verificar
on:
  workflow_call:
    inputs:
      runner:
        type: string
        default: ubuntu-latest
jobs:
  verificar:
    runs-on: ${{ inputs.runner }}
    steps:
      - run: echo x
"""
        llamante = """\
name: Deploy
on: [push]
jobs:
  compuerta:
    uses: ./.github/workflows/verificar.yml
{con}  desplegar:
    needs: compuerta
    runs-on: conaf-prod
    steps:
      - run: echo y
"""
        self.repo.escribe(".github/workflows/verificar.yml", reusable)
        self.repo.escribe(".github/workflows/deploy.yml", llamante.format(con=""))
        self.assertAvisa("en un runner DE PAGO")

        otro = RepoSintetico(j15)
        try:
            otro.escribe(".github/workflows/verificar.yml", reusable)
            otro.escribe(".github/workflows/deploy.yml",
                         llamante.format(con="    with:\n      runner: conaf-ci\n"))
            r = otro.juzga()
            self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        finally:
            otro.cierra()


class PruebaReglaDeOro(CasoConRepo):
    """Lo que no se puede resolver es SIN_EVALUAR, y NUNCA silencio.

    `comun.py:82-86`: «un juez que no pudo mirar no es un juez que miró y no
    encontró nada, y confundirlos es cómo un control se apaga sin que nadie se
    entere».
    """

    MODULO = j15

    def test_reusable_de_otro_repositorio_desconocido_no_se_calla(self):
        self.repo.escribe(".github/workflows/deploy.yml", """\
name: Deploy
on: [push]
jobs:
  compuerta:
    runs-on: ubuntu-latest
    steps:
      - run: echo x
  desplegar:
    needs: compuerta
    uses: OtraOrg/otro_repo/.github/workflows/lo-que-sea.yml@v1
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertTrue(any("no pudo determinar" in n.lower() or
                            "NO se pudo determinar" in n for n in r.no_evaluado),
                        r.no_evaluado)
        self.assertTrue(any("OtraOrg/otro_repo" in n for n in r.no_evaluado),
                        "el no_evaluado tiene que citar el `uses:` literal")
        # Y aun así el juez COMPROBÓ algo: no puede salir SIN_EVALUAR, que en
        # perfil `aplicacion` y modo bloqueante hace salir 1 (correr.py:270-275).
        self.assertEqual("OK", r.veredicto)

    def test_runner_por_matrix_es_sin_evaluar(self):
        self.repo.escribe(".github/workflows/ci.yml", """\
name: CI
on: [push]
jobs:
  compuerta:
    runs-on: ubuntu-latest
    steps:
      - run: echo x
  construir:
    needs: compuerta
    strategy:
      matrix:
        os: [ubuntu-latest, conaf-ci]
    runs-on: ${{ matrix.os }}
    steps:
      - run: echo y
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(any("matrix.os" in n for n in r.no_evaluado), r.no_evaluado)

    def test_un_needs_a_un_job_que_no_existe_se_reporta(self):
        self.repo.escribe(".github/workflows/ci.yml", """\
name: CI
on: [push]
jobs:
  desplegar:
    needs: fantasma
    runs-on: conaf-prod
    steps:
      - run: echo y
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(any("fantasma" in n for n in r.no_evaluado), r.no_evaluado)

    def test_sin_workflows_es_NO_APLICA_y_no_SIN_EVALUAR(self):
        """El molde de `j12_semilla.py:130-140`: se miró y aquí no corresponde.

        La diferencia importa: `SIN_EVALUAR` frena un perfil `aplicacion` en modo
        bloqueante (correr.py:270-275) y `NO_APLICA` no, y un repositorio sin
        Actions legítimamente no tiene ningún grafo de `needs:`.
        """
        self.repo.escribe("README.md", "# sin CI\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertTrue(any("no ejecuta nada en Actions" in n for n in r.no_aplica),
                        r.no_aplica)

    def test_un_workflow_sin_versionar_es_invisible(self):
        """El límite de `versionados()`, dicho en una prueba.

        El juez mira `git ls-files` y no el disco, igual que el resto de la casa
        (comun.py:177-183). Un workflow que no está en el índice no lo ejecuta
        GitHub, así que no verlo es correcto — pero el veredicto entonces no
        puede ser OK, porque no se comprobó nada.
        """
        self.repo.escribe(".github/workflows/deploy.yml", INCIDENTE, versionar=False)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertEqual("NO_APLICA", r.veredicto)


class PruebaLimitesDelTroceado(unittest.TestCase):
    """El escáner de bloques: lo que tiene que ver y lo que NO tiene que ver.

    Es una duplicación consciente del escáner de
    `tests/test_workflows_yaml.py:23-61` —que vive en `tests/` y no se puede
    importar desde `jueces/`—, así que sus límites se prueban aquí igual que allí.
    """

    def test_un_run_en_bloque_no_aporta_claves(self):
        """La palabra `runs-on` dentro de un `echo` no es un runner."""
        jobs = j15.jobs_del_workflow("""\
jobs:
  x:
    runs-on: conaf-ci
    steps:
      - run: |
          echo "runs-on: ubuntu-latest"
          echo "needs: otro"
""")
        self.assertEqual(["x"], list(jobs))
        self.assertEqual(["conaf-ci"], jobs["x"].runs_on)
        self.assertEqual([], jobs["x"].needs)

    def test_un_comentario_no_aporta_claves(self):
        jobs = j15.jobs_del_workflow("""\
jobs:
  x:
    # runs-on: ubuntu-latest  <- esto es prosa
    runs-on: conaf-ci   # y esto un comentario al final
""")
        self.assertEqual(["conaf-ci"], jobs["x"].runs_on)

    def test_sangria_de_dos_y_de_cuatro(self):
        for sangria in (2, 4):
            with self.subTest(sangria=sangria):
                s, d = " " * sangria, " " * (sangria * 2)
                jobs = j15.jobs_del_workflow(
                    f"jobs:\n{s}x:\n{d}runs-on: ubuntu-latest\n"
                    f"{s}y:\n{d}needs: x\n{d}runs-on: conaf-ci\n")
                self.assertEqual(["ubuntu-latest"], jobs["x"].runs_on)
                self.assertEqual(["x"], jobs["y"].needs)

    def test_las_tres_formas_de_escribir_una_lista(self):
        for texto, esperado in (
            ("jobs:\n  y:\n    needs: x\n", ["x"]),
            ("jobs:\n  y:\n    needs: [x, z]\n", ["x", "z"]),
            ("jobs:\n  y:\n    needs:\n      - x\n      - z\n", ["x", "z"]),
            # Secuencia AL NIVEL de su clave: YAML lo permite y GitHub lo acepta.
            # Sin esta rama el juez leía `needs:` vacío y dejaba pasar la
            # dependencia, que es un falso negativo silencioso.
            ("jobs:\n  y:\n    needs:\n    - x\n    - z\n", ["x", "z"]),
        ):
            with self.subTest(texto=texto):
                self.assertEqual(esperado, j15.jobs_del_workflow(texto)["y"].needs)

    def test_runs_on_como_secuencia_de_bloque(self):
        jobs = j15.jobs_del_workflow(
            "jobs:\n  x:\n    runs-on:\n      - self-hosted\n      - conaf-prod\n")
        self.assertEqual(["self-hosted", "conaf-prod"], jobs["x"].runs_on)

    def test_jobs_vacio_y_archivo_sin_jobs_no_revientan(self):
        for texto in ("jobs:\n", "name: nada\non: [push]\n", "", "   \n#\n"):
            with self.subTest(texto=texto):
                with self.assertRaises(j15.EstructuraIlegible):
                    j15.jobs_del_workflow(texto)

    def test_un_archivo_truncado_no_revienta(self):
        """Se corta el fixture en cada carácter. Ninguno puede lanzar otra cosa."""
        for corte in range(len(INCIDENTE) + 1):
            trozo = INCIDENTE[:corte]
            try:
                j15.jobs_del_workflow(trozo)
            except j15.EstructuraIlegible:
                pass
            except Exception as e:  # noqa: BLE001
                self.fail(f"cortado en {corte} lanzó {type(e).__name__}: {e}")

    def test_la_tabulacion_en_la_indentacion_se_declara_ilegible(self):
        """GitHub también rechaza el archivo. Mejor declararse incapaz que adivinar."""
        with self.assertRaises(j15.EstructuraIlegible):
            j15.jobs_del_workflow("jobs:\n  x:\n\truns-on: conaf-ci\n")

    def test_el_with_del_llamante_se_lee(self):
        jobs = j15.jobs_del_workflow("""\
jobs:
  x:
    uses: ./.github/workflows/v.yml
    with:
      modo: advisory
      runner: conaf-ci
""")
        self.assertEqual("conaf-ci", jobs["x"].entrada_with("runner"))
        self.assertIsNone(jobs["x"].entrada_with("no-existe"))

    def test_el_default_de_un_input_se_lee(self):
        texto = """\
name: V
on:
  workflow_call:
    inputs:
      runner:
        description: >-
          Etiqueta del runner. Un escalar en bloque aquí no puede
          confundir al lector del `default:` de abajo.
        type: string
        default: ubuntu-latest
jobs:
  v:
    runs-on: ${{ inputs.runner }}
"""
        self.assertEqual("ubuntu-latest", j15.entrada_por_defecto(texto, "runner"))
        self.assertIsNone(j15.entrada_por_defecto(texto, "modo"))


class PruebaNadaHaceReventar(unittest.TestCase):
    """El único fallo que este juez no se puede permitir es la EXCEPCIÓN.

    `correr.py:282-287`: ante un juez reventado se sale con 1 **en cualquier
    modo**, incluido advisory. O sea que un AVISA falso es inocuo y un
    `AttributeError` sobre un YAML raro de cualquiera de las 24 aplicaciones
    bloquea despliegues. Todo lo que sale de este módulo tiene que ser
    `EstructuraIlegible`, que `comprobar()` convierte en `no_evaluado`.
    """

    HOSTILES = (
        "", "\n", "\r\n",
        # BOM y CRLF: ya resueltos en `comun.texto()` (comun.py:237-240), pero el
        # escáner tiene que aguantarlos igual si llegan por otra vía.
        "\ufeffjobs:\r\n  x:\r\n    runs-on: conaf-ci\r\n",
        "---\njobs:\n  x:\n    runs-on: ubuntu-latest\n",
        # Anclas y alias: `comun.carga_yaml` los rechaza a propósito. Aquí no
        # pueden reventar, aunque el resultado sea incompleto.
        "jobs:\n  x: &a\n    runs-on: ubuntu-latest\n  y:\n    <<: *a\n    needs: x\n",
        "jobs:\n  x:\n    runs-on:\n      group: grande\n      labels: [x]\n",
        "jobs:\n  x:\n    needs: [\n",
        "jobs:\n  x:\n    runs-on: []\n    needs: []\n",
        "jobs:\n  \"x y\":\n    runs-on: ubuntu-latest\n",
        # Un ciclo en el grafo de `needs:`. No se recorre, pero que conste.
        "jobs:\n  a:\n    needs: b\n    runs-on: conaf-ci\n"
        "  b:\n    needs: a\n    runs-on: ubuntu-latest\n",
        "jobs:" + "\n" + " " * 200 + "x:\n" + " " * 400 + "runs-on: ubuntu-latest\n",
        # El caso que ya tumbó un juez de esta casa una vez: un valor que parece
        # número y no lo es (comun.py:284-288, medido el 2026-09-08).
        "jobs:\n  x:\n    runs-on: ubuntu-latest\n    timeout-minutes: --5\n",
    )

    def _hostiles_aleatorias(self, cuantas: int = 1500) -> list[str]:
        """Ruido reproducible con las piezas con las que el escáner trabaja."""
        import random

        alfabeto = "jobs:-runsonneedsuses[]{}|>#\n \t\"'$@./\\\r\ufeffñ"
        rnd = random.Random(15)  # semilla fija: una prueba no puede ser distinta
                                # cada vez que corre, o el rojo no se reproduce
        return ["".join(rnd.choice(alfabeto) for _ in range(rnd.randint(0, 120)))
                for _ in range(cuantas)]

    def test_nada_sale_de_este_modulo_salvo_EstructuraIlegible(self):
        for texto in list(self.HOSTILES) + self._hostiles_aleatorias():
            for nombre, llamada in (
                ("jobs_del_workflow", lambda t: j15.jobs_del_workflow(t)),
                ("entrada_por_defecto", lambda t: j15.entrada_por_defecto(t, "runner")),
                ("clasificar", lambda t: j15.clasificar([t[:40]])),
            ):
                try:
                    llamada(texto)
                except j15.EstructuraIlegible:
                    pass
                except Exception as e:  # noqa: BLE001
                    self.fail(f"{nombre} lanzó {type(e).__name__}: {e} "
                              f"sobre {texto[:80]!r}")

    def test_un_repositorio_con_un_workflow_ilegible_no_revienta_y_no_se_calla(self):
        repo = RepoSintetico(j15)
        try:
            repo.escribe(".github/workflows/roto.yml", "jobs:\n  x:\n\truns-on: x\n")
            r = repo.juzga()
            self.assertEqual([], r.hallazgos)
            self.assertTrue(any("no se pudo analizar la estructura de jobs" in n
                                for n in r.no_evaluado), r.no_evaluado)
            # Ni un solo workflow troceado -> no se llama a comprobo(), y el
            # veredicto es SIN_EVALUAR. Es lo correcto: no se miró nada.
            self.assertEqual("SIN_EVALUAR", r.veredicto)
        finally:
            repo.cierra()

    def test_un_workflow_ilegible_no_impide_mirar_los_demas(self):
        """Un archivo roto no puede apagar la comprobación del repositorio entero."""
        repo = RepoSintetico(j15)
        try:
            repo.escribe(".github/workflows/roto.yml", "jobs:\n  x:\n\truns-on: x\n")
            repo.escribe(".github/workflows/deploy.yml", INCIDENTE)
            r = repo.juzga()
            self.assertTrue(r.hallazgos, "el archivo roto tapó el hallazgo del otro")
            self.assertTrue(r.no_evaluado, "y el roto tiene que seguir constando")
            self.assertEqual("HALLAZGOS", r.veredicto)
        finally:
            repo.cierra()


class PruebaClasificacionDeRunners(unittest.TestCase):
    """Se razona por la lista de GitHub, que es cerrada, no por una lista blanca."""

    def test_las_familias_de_github_son_de_pago(self):
        for etiqueta in ("ubuntu-latest", "ubuntu-22.04", "ubuntu-24.04-arm",
                         "windows-latest", "windows-2022", "macos-14",
                         "macos-13-xlarge", "ubuntu-latest-4-cores", "UBUNTU-LATEST"):
            with self.subTest(etiqueta=etiqueta):
                self.assertEqual(j15.PAGO, j15.clasificar([etiqueta]).clase)

    def test_cualquier_otra_etiqueta_es_propia(self):
        for etiqueta in ("conaf-ci", "conaf-uat", "conaf-prod", "conaf-vm4"):
            with self.subTest(etiqueta=etiqueta):
                self.assertEqual(j15.PROPIO, j15.clasificar([etiqueta]).clase)

    def test_self_hosted_manda_sobre_la_etiqueta_de_al_lado(self):
        """`[self-hosted, ubuntu-latest]` es un runner propio con esa etiqueta."""
        self.assertEqual(j15.PROPIO,
                         j15.clasificar(["self-hosted", "ubuntu-latest"]).clase)

    def test_una_expresion_no_se_adivina(self):
        for etiqueta in ("${{ matrix.os }}", "${{ inputs.runner }}",
                         "${{ vars.RUNNER }}"):
            with self.subTest(etiqueta=etiqueta):
                self.assertEqual(j15.DESCONOCIDO, j15.clasificar([etiqueta]).clase)

    def test_sin_etiquetas_es_desconocido_y_no_gratis(self):
        self.assertEqual(j15.DESCONOCIDO, j15.clasificar([]).clase)


class PruebaContratoDelModulo(unittest.TestCase):
    """Lo que `correr.py` exige, y un defecto que ya costó una sesión entera."""

    def test_el_modulo_carga_como_lo_carga_correr(self):
        """SIN ESTA PRUEBA, UN `@dataclass` TUMBA EL GATE DE LAS 24 APLICACIONES.

        Medido el 2026-09-27. `correr.py:58-62` carga cada juez con
        `spec_from_file_location` + `exec_module` y NO lo registra en
        `sys.modules`. `dataclasses` resuelve las anotaciones —cadenas, por
        `from __future__ import annotations`— con
        `sys.modules.get(cls.__module__).__dict__`, que en ese modo es `None`:

            AttributeError: 'NoneType' object has no attribute '__dict__'

        Y `descubrir()` se llama FUERA de cualquier try (correr.py:150), así que
        eso no es «un juez reventado» sino `correr.py` tumbado sin resumen. La
        primera versión de este juez usaba `@dataclass` y los 32 repositorios de
        la flota salían con traceback y exit 1. El `import` normal de `pytest` o
        de este archivo NO lo detecta: hay que cargarlo igual que `correr.py`.
        """
        import importlib.util

        ruta = RAIZ / "jueces" / "j15_cuota.py"
        spec = importlib.util.spec_from_file_location(ruta.stem, ruta)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)  # sin sys.modules, a propósito
        self.assertTrue(hasattr(modulo, "comprobar"))
        self.assertEqual(("aplicacion", "encuadre_operativo"), modulo.PERFILES)

    def test_la_primera_linea_del_docstring_es_la_descripcion(self):
        """`correr.py:174-175` la imprime en el informe de las 24 aplicaciones."""
        primera = (j15.__doc__ or "").strip().splitlines()[0]
        self.assertTrue(primera.startswith("j15 — "), primera)

    def test_este_juez_no_puede_bloquear(self):
        """`REGLAS.md` lista `CUOTA-1` como regla sin fuente escrita.

        `tests/test_reglas_citadas.py:178-188` ya lo comprueba por AST para todas;
        esto lo dice también aquí, en el archivo del juez, porque el día que
        alguien cambie `r.avisa` por `r.bloquea` va a estar leyendo esto.
        """
        fuente = (RAIZ / "jueces" / "j15_cuota.py").read_text(encoding="utf-8")
        self.assertNotIn("r.bloquea(", fuente)


class PruebaElDefectoDelDefectoPorDefecto(unittest.TestCase):
    """La constante del `default:` de `verificar.yml` no puede quedarse atrás.

    `j15.DEFECTO_RUNNER_VERIFICAR` es una afirmación sobre
    `.github/workflows/verificar.yml` escrita a mano, porque cuando una aplicación
    llama a `verificar.yml@v2.0.9` el archivo que manda es el de ESA referencia y
    no el que haya aquí hoy. Una constante así se queda vieja en silencio; esta
    prueba es lo que lo impide, igual que `tests/test_verificar_yaml.py` protege
    el `ref_jueces` por defecto.
    """

    def test_la_constante_coincide_con_el_reusable_de_este_repositorio(self):
        texto = (RAIZ / ".github" / "workflows" / "verificar.yml").read_text(
            encoding="utf-8")
        leido = j15.entrada_por_defecto(texto, "runner")
        self.assertEqual(
            j15.DEFECTO_RUNNER_VERIFICAR, leido,
            "el input `runner` de verificar.yml ya no vale "
            f"{j15.DEFECTO_RUNNER_VERIFICAR!r} sino {leido!r}. Si el nuevo valor es "
            "un runner propio, este juez está dejando pasar el defecto del "
            "2026-09-26 al contrario: hay que mover la constante Y volver a medir "
            "la flota.")

    def test_el_reusable_sigue_recibiendo_el_runner_por_input(self):
        """Si `verificar.yml` dejara de parametrizar el runner, la tabla miente."""
        texto = (RAIZ / ".github" / "workflows" / "verificar.yml").read_text(
            encoding="utf-8")
        self.assertTrue(re.search(r"^\s*runs-on:\s*\$\{\{\s*inputs\.runner\s*\}\}",
                                  texto, re.MULTILINE),
                        "verificar.yml ya no toma el runner de su input `runner`")


class PruebaDelPropioJuez(unittest.TestCase):
    """Una prueba que nunca falla no prueba nada.

    Sin esto, vaciar `comprobar` —o dejar el `for` sin el `r.avisa`— deja la suite
    en verde: todas las pruebas de arriba que comprueban «no avisa» seguirían
    pasando. Es el mismo cerrojo que `test_j06_config.py:178-190` y
    `test_workflows_yaml.py:84-89`.
    """

    def test_el_juez_enciende_sobre_el_incidente(self):
        repo = RepoSintetico(j15)
        try:
            repo.escribe(".github/workflows/deploy.yml", INCIDENTE)
            r = repo.juzga()
            self.assertTrue(r.hallazgos,
                            "el juez dejó pasar el grafo exacto del 2026-09-26")
            self.assertEqual("HALLAZGOS", r.veredicto)
        finally:
            repo.cierra()

    def test_el_juez_no_enciende_sobre_el_arreglo(self):
        repo = RepoSintetico(j15)
        try:
            repo.escribe(".github/workflows/deploy.yml", ARREGLADO)
            self.assertEqual([], repo.juzga().hallazgos)
        finally:
            repo.cierra()

    def test_ningun_workflow_de_este_repositorio_hace_reventar_al_juez(self):
        """Dogfooding: `autotest.yml` corre el gate sobre este repo en BLOQUEANTE.

        Y los dos workflows propios son justo los que `comun.carga_yaml` rechaza
        (medido el 2026-09-27: línea 32 de autotest.yml y línea 45 de
        verificar.yml). O sea que este juez se estrena sobre los archivos más
        hostiles que hay a mano.
        """
        for ruta in sorted((RAIZ / ".github" / "workflows").glob("*.yml")):
            with self.subTest(workflow=ruta.name):
                jobs = j15.jobs_del_workflow(ruta.read_text(encoding="utf-8"))
                self.assertTrue(jobs, f"{ruta.name}: no se troceó ningún job")


if __name__ == "__main__":
    unittest.main(verbosity=2)
