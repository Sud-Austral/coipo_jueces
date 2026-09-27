"""Pruebas de j14 — `timeout-minutes` en un job que llama a un reusable.

TODOS LOS FIXTURES SON SINTETICOS y estan inventados a mano, como exige
`tests/ayuda.py:1-7`. Aqui ademas no habia alternativa: medido el 2026-09-27
sobre los 32 repositorios de `D:/GitHub` con `.github/workflows/`, **no hay ni
un solo caso vivo** de `timeout-minutes` dentro de un job con `uses:`. La
deteccion positiva de esta regla solo existe en este archivo, y por eso el
control positivo de mas abajo no es decorativo: es la unica prueba de que el
juez sabe encontrar lo que dice que encuentra.

Las dos direcciones, siempre (README.md:66-70):
  - `PruebaControlPositivo`  -> el caso que TIENE que dar hallazgo;
  - `PruebaControlNegativo`  -> los tres sitios donde `timeout-minutes` es
                                legitimo y el juez tiene que callarse.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ayuda import CasoConRepo, RepoSintetico  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jueces"))
import j14_timeout as j14  # noqa: E402

RUTA = ".github/workflows/ci.yml"

# EL CASO QUE HAY QUE ENCONTRAR. Es como se escribe el defecto de verdad: quien
# lo comete viene de escribir `timeout-minutes` en todos sus demas jobs y lo
# repite aqui por costumbre.
DEFECTUOSO = """\
name: CI
on: [push]
jobs:
  jueces:
    uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2
    timeout-minutes: 10
    with:
      modo: advisory
"""

# EL MISMO ARCHIVO SIN EL DEFECTO. Si esto diera hallazgo, el juez estaria
# denunciando el `uses:` y no la clave.
CORRECTO = """\
name: CI
on: [push]
jobs:
  jueces:
    uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2
    with:
      modo: advisory
"""


def _avisos_wf1(r) -> list:
    return [h for h in r.hallazgos if h.regla == "WF-1"]


class PruebaControlPositivo(CasoConRepo):
    MODULO = j14

    def test_timeout_en_un_job_con_uses_avisa(self):
        """EL CONTROL POSITIVO. Un juez que no encuentra nada y no se ha probado
        contra un caso que DEBE encontrar no vale nada."""
        self.repo.escribe(RUTA, DEFECTUOSO)
        self.assertAvisa("no es una clave valida en ese tipo de job")

    def test_el_hallazgo_senala_la_linea_de_la_clave(self):
        """La linea es lo que hace que el arreglo cueste diez segundos.

        `timeout-minutes` esta en la sexta linea de DEFECTUOSO, 1-based, como
        exige `Hallazgo.linea`.
        """
        self.repo.escribe(RUTA, DEFECTUOSO)
        h = _avisos_wf1(self.repo.juzga())[0]
        self.assertEqual(6, h.linea)
        self.assertEqual(RUTA, h.archivo)

    def test_nunca_bloquea(self):
        """`WF-1` vive en «Reglas sin fuente escrita»: ningun documento de la
        flota la dice todavia, asi que no puede detener un despliegue."""
        self.repo.escribe(RUTA, DEFECTUOSO)
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertTrue(_avisos_wf1(r))

    def test_valor_que_no_es_un_numero_avisa_igual(self):
        """`timeout-minutes: ${{ inputs.t }}` no se convierte a numero.

        Lo invalido es la CLAVE, no el valor. Y el aviso llega sin pasar por
        `int()`: convertir texto de YAML a numero es lo que tumbo al juez entero
        con un `command: --5` del compose el 2026-09-08 (comun.py:284-288).
        """
        self.repo.escribe(RUTA, DEFECTUOSO.replace(
            "timeout-minutes: 10", "timeout-minutes: ${{ inputs.minutos }}"))
        self.assertAvisa("no es una clave valida en ese tipo de job")

    def test_con_crlf_tambien(self):
        """293 archivos con CRLF en coipo_prensa2, 219 en COIPO_USUARIOS
        (j12_semilla.py:45-52). Un juez que falla por el fin de linea se suprime
        en una semana; uno que lo IGNORA en silencio es peor."""
        self.repo.escribe(RUTA, DEFECTUOSO.replace("\n", "\r\n"))
        self.assertAvisa("no es una clave valida en ese tipo de job")

    def test_sangria_de_cuatro(self):
        """El troceado mide sangrias, no columnas fijas."""
        self.repo.escribe(RUTA, """\
name: CI
on: [push]
jobs:
    jueces:
        uses: ./.github/workflows/verificar.yml
        timeout-minutes: 10
""")
        self.assertAvisa("no es una clave valida en ese tipo de job")

    def test_clave_entrecomillada(self):
        self.repo.escribe(RUTA, DEFECTUOSO.replace(
            "timeout-minutes: 10", '"timeout-minutes": 10'))
        self.assertAvisa("no es una clave valida en ese tipo de job")


class PruebaControlNegativo(CasoConRepo):
    """Los tres sitios donde `timeout-minutes` es legitimo.

    Un aviso falso aqui seria caro aunque sea AVISA: se dispararia sobre la
    practica correcta —`coipo_api` lo lleva en sus tres jobs y `verificar.yml`
    de este repositorio en el suyo— y ensenaria a suprimir al juez, que es el
    modo de fallo que `j06_config.es_desplegable` documenta.
    """

    MODULO = j14

    def test_job_con_uses_y_sin_timeout_no_avisa(self):
        """EL CONTROL NEGATIVO. Si esto fallara, el juez estaria denunciando el
        `uses:` y no la clave prohibida."""
        self.repo.escribe(RUTA, CORRECTO)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertTrue(r.comprobado)

    def test_timeout_en_un_job_normal_no_avisa(self):
        """Es el caso de `verificar.yml:78` de este mismo repositorio, con el
        motivo escrito al lado: sin timeout, un juez con un bucle infinito
        encola todos los despliegues siguientes."""
        self.repo.escribe(RUTA, """\
name: CI
on: [push]
jobs:
  pruebas:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@0000000000000000000000000000000000000000
      - run: python3 -m unittest discover -s tests
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_timeout_dentro_de_un_paso_no_avisa(self):
        self.repo.escribe(RUTA, """\
name: CI
on: [push]
jobs:
  pruebas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@0000000000000000000000000000000000000000
        timeout-minutes: 3
      - run: echo hola
        timeout-minutes: 1
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_secuencia_a_ras_no_convierte_el_uses_de_un_paso_en_clave_del_job(self):
        """EL FALSO POSITIVO QUE MAS CARO SALDRIA.

        En el estilo «a ras», `- uses:` esta a la MISMA sangria que las claves
        del job. Un troceado que no cierre el mapa al ver el guion leeria `uses`
        como clave del job y, como el job normal SI puede llevar
        `timeout-minutes`, dispararia sobre casi todos los repositorios de la
        flota — sobre la practica correcta.
        """
        self.repo.escribe(RUTA, """\
name: CI
on: [push]
jobs:
  pruebas:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
    - uses: actions/checkout@0000000000000000000000000000000000000000
    - run: echo hola
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_un_run_que_habla_de_la_clave_no_es_la_clave(self):
        """Lo de dentro de un escalar de bloque es TEXTO.

        El repositorio de los jueces es publico y documenta esta misma regla: el
        dia que alguien escriba el ejemplo del defecto dentro de un `run:`, el
        juez no puede denunciar su propia documentacion.
        """
        self.repo.escribe(RUTA, """\
name: CI
on: [push]
jobs:
  documentar:
    runs-on: ubuntu-latest
    steps:
      - name: Ejemplo del defecto
        run: |
          echo "jobs:"
          echo "  x:"
          echo "    uses: ./.github/workflows/y.yml"
          echo "    timeout-minutes: 5"
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_un_comentario_no_es_una_clave(self):
        self.repo.escribe(RUTA, """\
name: CI
on: [push]
jobs:
  jueces:
    uses: ./.github/workflows/verificar.yml
    # timeout-minutes: 10  <- esto no vale aqui, y por eso esta comentado
    with:
      modo: advisory
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_un_if_de_bloque_no_esconde_el_defecto_ni_lo_inventa(self):
        """El caso real mas hostil de la flota: `coipo_boton_rojo/ci.yml:381`.

        Su job `desplegar:` lleva `needs:`, un `if: >-` de doce lineas y `uses:`.
        El escalar de bloque no puede ni tapar la clave que viene despues ni
        inventarse una desde su propio texto.
        """
        base = """\
name: CI
on: [push]
jobs:
  desplegar:
    needs: [pruebas]
    if: >-
      always() && (
        github.ref == 'refs/heads/main'
        && needs.pruebas.result == 'success'
      )
    uses: Sud-Austral/infra-docker-base/.github/workflows/deploy.yml@main
    with:
      app_name: ejemplo
"""
        self.repo.escribe(RUTA, base)
        self.assertEqual([], self.repo.juzga().hallazgos)

        self.repo.escribe(RUTA, base.replace(
            "    uses: Sud", "    timeout-minutes: 20\n    uses: Sud"))
        self.assertAvisa("no es una clave valida en ese tipo de job")

    def test_un_timeout_minutes_bajo_with_es_un_input_del_reusable(self):
        """`with:` son los INPUTS del workflow llamado, no claves del job.

        Un reusable puede declarar perfectamente un input llamado
        `timeout-minutes` —es el sitio correcto donde poner ese limite cuando se
        quiere parametrizar— y denunciarlo seria castigar el arreglo que este
        mismo juez recomienda.
        """
        self.repo.escribe(RUTA, """\
name: CI
on: [push]
jobs:
  jueces:
    uses: ./.github/workflows/verificar.yml
    with:
      modo: advisory
      timeout-minutes: 5
""")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_sin_workflows_es_no_aplica_y_no_sin_evaluar(self):
        """`coipo_dendroenergia` antes de tener CI, y cualquier encuadre
        operativo. «Lo mire y aqui no hay nada que comprobar» no es lo mismo que
        «no pude mirarlo»: SIN_EVALUAR frena un perfil `aplicacion` en modo
        bloqueante (correr.py:270-275) y esto no debe frenarlo.
        """
        self.repo.escribe("README.md", "# sin CI\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.no_evaluado)

    def test_un_yml_en_un_subdirectorio_de_workflows_no_es_un_workflow(self):
        """GitHub lee `.github/workflows/*.yml`, no sus subdirectorios.

        Una plantilla guardada ahi debajo no la ejecuta nadie, asi que no puede
        romper ningun despliegue y denunciarla seria ruido.
        """
        self.repo.escribe(".github/workflows/plantillas/base.yml", DEFECTUOSO)
        self.repo.escribe(RUTA, CORRECTO)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])


class PruebaSupresion(CasoConRepo):
    MODULO = j14

    def test_se_puede_suprimir_con_motivo_y_se_cuenta(self):
        """Suprimir no es desaparecer: sale como `::warning::` y exige fila en
        DEUDA.md (comun.py:87-91)."""
        self.repo.escribe(RUTA, DEFECTUOSO.replace(
            "    timeout-minutes: 10",
            "    # coipo-jueces:ignorar(WF-1) reproduccion del defecto para el "
            "informe del 2026-09-27\n    timeout-minutes: 10"))
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertEqual(1, len(r.supresiones))

    def test_un_motivo_corto_no_suprime_nada(self):
        """Si silenciar cuesta lo mismo que arreglar, se arregla
        (comun.py:565)."""
        self.repo.escribe(RUTA, DEFECTUOSO.replace(
            "    timeout-minutes: 10",
            "    # coipo-jueces:ignorar(WF-1) luego\n    timeout-minutes: 10"))
        r = self.repo.juzga()
        self.assertEqual([], r.supresiones)
        self.assertTrue(_avisos_wf1(r))


class PruebaNoSeCalla(CasoConRepo):
    """Cuando no se puede decidir, el veredicto es SIN_EVALUAR y nunca silencio.

    `comun.py:83-86`: «un juez que no pudo mirar no es un juez que miro y no
    encontro nada, y confundirlos es como un control se apaga sin que nadie se
    entere».
    """

    MODULO = j14

    def test_una_tabulacion_en_la_sangria_no_se_calla(self):
        self.repo.escribe(RUTA, "jobs:\n  x:\n\tuses: ./a.yml\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(any("tabulacion" in n for n in r.no_evaluado), r.no_evaluado)

    def test_un_mapa_en_linea_no_se_calla(self):
        """`x: {uses: ./a.yml, timeout-minutes: 5}` es YAML legal y este
        troceado no lo abre. Callarse seria apagar la regla justo en el unico
        caso que no cubre."""
        self.repo.escribe(RUTA, "jobs:\n  x: {uses: ./a.yml, timeout-minutes: 5}\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(any("mapa en" in n for n in r.no_evaluado), r.no_evaluado)

    def test_un_workflow_sin_jobs_no_se_calla(self):
        self.repo.escribe(RUTA, "name: CI\non: [push]\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(any("jobs:" in n for n in r.no_evaluado), r.no_evaluado)

    def test_un_workflow_sin_git_add_es_invisible_y_hay_que_saberlo(self):
        """LIMITE DECLARADO, no defecto.

        Este juez lee `git ls-files` como toda la casa (comun.py:177-183). Un
        workflow que no esta en el indice no lo ejecuta GitHub tampoco, asi que
        no puede romper un despliegue — pero si es el UNICO workflow, el
        veredicto es NO_APLICA, y eso se dice aqui para que nadie lo descubra
        el dia que importe.
        """
        self.repo.escribe("README.md", "# hay algo versionado\n")
        self.repo.escribe(RUTA, DEFECTUOSO, versionar=False)
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertEqual("NO_APLICA", r.veredicto)

    def test_un_indice_vacio_no_es_un_repositorio_sin_workflows(self):
        """`versionados()` devuelve [] tambien cuando falta `git` en el PATH
        (comun.py:211-216). Leerlo como N/A seria declarar «aqui no
        corresponde» desde una averia del entorno, y el N/A solo se declara
        desde evidencia encontrada en el codigo (comun.py:118-122)."""
        r = self.repo.juzga()   # repositorio git recien creado, sin un archivo
        self.assertEqual("SIN_EVALUAR", r.veredicto)
        self.assertTrue(any("git ls-files" in n for n in r.no_evaluado),
                        r.no_evaluado)


class PruebaTroceado(unittest.TestCase):
    """El troceado por bloques de `jobs:`, a solas y contra sus limites.

    Es codigo propio de este juez —`comun.carga_yaml` no sirve aqui: rechaza el
    75 % de los workflows de la flota— y por tanto no lo cubre ninguna prueba
    anterior. Nada de esto puede lanzar: un juez que revienta hace salir 1 en
    cualquier modo (correr.py:282-287).
    """

    def _trocea(self, texto: str):
        return j14._trabajos(texto.splitlines())

    def test_claves_del_job_y_no_de_sus_pasos(self):
        trabajos, problema = self._trocea("""\
jobs:
  a:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@x
        with:
          ref: main
""")
        self.assertIsNone(problema)
        self.assertEqual(["a"], [t.identificador for t in trabajos])
        self.assertEqual({"runs-on", "timeout-minutes", "steps"},
                         set(trabajos[0].claves))

    def test_dos_jobs_no_se_mezclan(self):
        trabajos, problema = self._trocea("""\
jobs:
  a:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo a
  b:
    uses: ./.github/workflows/b.yml
""")
        self.assertIsNone(problema)
        claves = {t.identificador: set(t.claves) for t in trabajos}
        self.assertEqual({"runs-on", "timeout-minutes", "steps"}, claves["a"])
        self.assertEqual({"uses"}, claves["b"])

    def test_jobs_vacio(self):
        _, problema = self._trocea("name: CI\njobs:\n")
        self.assertIsNotNone(problema)

    def test_archivo_truncado_a_media_clave(self):
        trabajos, problema = self._trocea(
            "jobs:\n  a:\n    uses: ./a.yml\n    with:")
        self.assertIsNone(problema)
        self.assertIn("uses", trabajos[0].claves)

    def test_archivo_vacio(self):
        _, problema = self._trocea("")
        self.assertIsNotNone(problema)

    def test_una_jobs_dentro_de_un_run_no_manda(self):
        """Si el troceado cogiera «la primera `jobs:`» en vez de la de menor
        sangria, un `run:` que imprima un workflow de ejemplo convertiria el
        resto del analisis en basura silenciosa."""
        trabajos, problema = self._trocea("""\
name: CI
on: [push]
jobs:
  documentar:
    runs-on: ubuntu-latest
    steps:
      - run: |
          jobs:
            falso:
              uses: ./mentira.yml
  real:
    uses: ./.github/workflows/verificar.yml
""")
        self.assertIsNone(problema)
        self.assertEqual(["documentar", "real"],
                         [t.identificador for t in trabajos])

    def test_el_detector_detecta_el_caso_que_dice_detectar(self):
        """Una prueba que nunca falla no prueba nada
        (tests/test_workflows_yaml.py:84-89)."""
        trabajos, problema = self._trocea("""\
jobs:
  jueces:
    uses: ./.github/workflows/verificar.yml
    timeout-minutes: 10
""")
        self.assertIsNone(problema)
        self.assertEqual({"uses": 3, "timeout-minutes": 4}, trabajos[0].claves)


class PruebaDelPropioJuez(unittest.TestCase):
    """Sin esto, vaciar `comprobar` deja la suite en verde.

    En la flota hay CERO casos vivos de este defecto (medido el 2026-09-27), asi
    que un juez apagado saldria limpio sobre los 32 repositorios y nadie lo
    notaria. Esta es la unica prueba que lo impide.
    """

    def test_el_juez_encuentra_el_defecto_que_existe_para_encontrar(self):
        repo = RepoSintetico(j14)
        try:
            repo.escribe(RUTA, DEFECTUOSO)
            r = repo.juzga()
            self.assertTrue(
                [h for h in r.hallazgos if h.regla == "WF-1"],
                "el juez dejo pasar `timeout-minutes` en un job con `uses:`")
            self.assertTrue(r.comprobado, "no registro ninguna comprobacion")
        finally:
            repo.cierra()

    def test_el_juez_no_encuentra_el_defecto_donde_no_esta(self):
        repo = RepoSintetico(j14)
        try:
            repo.escribe(RUTA, CORRECTO)
            r = repo.juzga()
            self.assertEqual("OK", r.veredicto)
        finally:
            repo.cierra()


if __name__ == "__main__":
    unittest.main(verbosity=2)
