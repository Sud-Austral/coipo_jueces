"""Pruebas de j02 — nombre del repositorio y APP_PORT (Guía 8, puntos 1 y 2).

Fixtures SINTÉTICOS. Este repositorio es público: copiar aquí un compose real de
CONAF publicaría en internet el mapa puerto -> aplicación de las VM del Estado,
que es justo lo que estos jueces existen para evitar.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo, RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j02_identidad as j02  # noqa: E402

COMPOSE_CORRECTO = """\
services:
  backend:
    build:
      context: .
  app:
    build:
      context: .
    ports:
      - "${APP_PORT:-8080}:8000"
"""


class PruebaNombre(unittest.TestCase):
    """Guía 8, punto 1: el nombre del repositorio ES la carpeta del servidor."""

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")

    def _juzga(self, nombre: str):
        repo = RepoSintetico(j02, nombre=nombre)
        self.addCleanup(repo.cierra)
        repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        return repo.juzga()

    def test_minusculas_no_bloquea(self):
        self.assertEqual([], self._juzga("coipo_atraso_personal").bloqueantes)

    def test_mayusculas_bloquea(self):
        r = self._juzga("COIPO_ENTREGA_PLANTA")
        self.assertTrue(
            [h for h in r.bloqueantes if h.regla == "G8-1" and "mayúsculas" in h.mensaje],
            [(h.regla, h.mensaje) for h in r.bloqueantes],
        )

    def test_un_caracter_fuera_de_la_lista_bloquea(self):
        """En minúsculas pero con un punto, o empezando por guion: la otra rama de G8-1."""
        for nombre in ("coipo.prensa", "-coipo_prensa"):
            with self.subTest(nombre=nombre):
                r = self._juzga(nombre)
                self.assertTrue(
                    [
                        h
                        for h in r.bloqueantes
                        if h.regla == "G8-1" and "sale de [a-z0-9_-]" in h.mensaje
                    ],
                    [(h.regla, h.mensaje) for h in r.bloqueantes],
                )

    def test_el_arreglo_trae_el_nombre_ya_en_minusculas(self):
        """Un arreglo que hay que traducir a mano es un arreglo que no se aplica."""
        r = self._juzga("COIPO_USUARIOS")
        arreglos = [h.arreglo for h in r.bloqueantes]
        self.assertTrue(any("coipo_usuarios" in a for a in arreglos), arreglos)

    def test_una_sola_mayuscula_tambien_bloquea(self):
        r = self._juzga("coipo_Prensa")
        self.assertEqual(1, len(r.bloqueantes), [h.mensaje for h in r.bloqueantes])


class PruebaNombreDelRemoto(unittest.TestCase):
    """El nombre que usa el despliegue es el del REMOTO, no el de la carpeta local.

    `deploy.yml` arma `/opt/apps/<app>/` con `github.event.repository.name`. En el
    CI la carpeta del checkout se llama igual, pero un clon local puede llamarse
    como quiera: hasta el 2026-11-22 un clon de `coipo_usuarios` en una carpeta
    `COIPO_USUARIOS` salía BLOQUEADO por G8-1 sin que hubiera nada que arreglar.
    """

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: estas pruebas lo necesitan de verdad")

    def _juzga(self, carpeta: str, url: str):
        repo = RepoSintetico(j02, nombre=carpeta).remoto(url)
        self.addCleanup(repo.cierra)
        repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        return repo.juzga()

    def _g8_1(self, r):
        return [h for h in r.bloqueantes if h.regla == "G8-1"]

    def test_carpeta_en_mayusculas_con_remoto_en_minusculas_no_bloquea(self):
        r = self._juzga("COIPO_USUARIOS", "https://github.com/Org/coipo_usuarios.git")
        self.assertEqual([], self._g8_1(r), [h.mensaje for h in r.bloqueantes])

    def test_carpeta_en_minusculas_con_remoto_en_mayusculas_bloquea(self):
        r = self._juzga("coipo_entrega", "git@github.com:Org/COIPO_ENTREGA.git")
        self.assertTrue(
            [h for h in self._g8_1(r) if "`COIPO_ENTREGA`" in h.mensaje],
            [h.mensaje for h in r.bloqueantes],
        )

    def test_formas_de_url_del_remoto(self):
        """https con y sin `.git` y con barra final, y ssh: todas dan el mismo nombre."""
        for url in (
            "https://github.com/Org/coipo_prensa2",
            "https://github.com/Org/coipo_prensa2/",
            "https://github.com/Org/coipo_prensa2.git",
            "git@github.com:Org/coipo_prensa2.git",
            "ssh://git@github.com/Org/coipo_prensa2.git",
        ):
            with self.subTest(url=url):
                r = self._juzga("Carpeta_Local", url)
                self.assertEqual([], self._g8_1(r), [h.mensaje for h in r.bloqueantes])


class PruebaPuerto(CasoConRepo):
    """Guía 8, punto 2: lo que SÍ se puede comprobar desde un repositorio."""

    MODULO = j02

    def test_app_port_por_variable_no_bloquea(self):
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        self.assertSinBloqueos()

    def test_puerto_cableado_bloquea(self):
        self.repo.escribe(
            "docker-compose.yml",
            COMPOSE_CORRECTO.replace('"${APP_PORT:-8080}:8000"', '"8113:8000"'),
        )
        self.assertRegla("G8-2", "BLOQUEA", "cablea el puerto 8113")

    def test_otra_variable_bloquea(self):
        """El bootstrap y el smoke test usan APP_PORT; publicar por otra no sirve."""
        self.repo.escribe(
            "docker-compose.yml",
            COMPOSE_CORRECTO.replace("${APP_PORT:-8080}", "${PUERTO_WEB:-8080}"),
        )
        self.assertRegla("G8-2", "BLOQUEA", "no es `APP_PORT`")

    def test_la_unicidad_se_declara_no_evaluada(self):
        """La honestidad del juez es la prueba.

        La unicidad de APP_PORT es una propiedad de la VM. Un juez que la callara
        dejaría creer que el gate la comprueba, y nadie volvería a mirar
        `ss -tlnp` antes de asignar un puerto.
        """
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        r = self.repo.juzga()
        self.assertTrue(any("unicidad de APP_PORT" in n for n in r.no_evaluado), r.no_evaluado)

    def test_env_example_con_8080_no_es_hallazgo(self):
        """El caso que tumbó la primera versión de esta regla.

        `coipo_prensa2` y `coipo_dendroenergia` declaran `APP_PORT=8080` en su
        `.env.example` mientras sus puertos reales son 8101 y 8103, que viven en
        el `.env` del servidor. Un `.env.example` es un EJEMPLO: exigirle el
        valor de producción es pedirle al repositorio que lo publique.
        """
        self.repo.escribe("docker-compose.yml", COMPOSE_CORRECTO)
        self.repo.escribe(".env.example", "APP_PORT=8080\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_sin_compose_no_inventa_hallazgos(self):
        self.repo.escribe("README.md", "# nada que desplegar\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)
        self.assertTrue(r.no_evaluado)

    def test_la_linea_de_la_semilla_pasa(self):
        """La forma que siembra la fábrica: IP de escucha y guarda `:?` con mensaje."""
        self.repo.escribe(
            "docker-compose.yml",
            COMPOSE_CORRECTO.replace('"${APP_PORT:-8080}:8000"', LINEA_DE_LA_SEMILLA),
        )
        self.assertSinRegla("G8-2")

    def test_otra_variable_bloquea_aunque_su_mensaje_diga_app_port(self):
        """El mensaje de la guarda no es la variable: `${PUERTO:?defina APP_PORT}` es PUERTO."""
        self.repo.escribe(
            "docker-compose.yml",
            COMPOSE_CORRECTO.replace(
                '"${APP_PORT:-8080}:8000"', '"127.0.0.1:${PUERTO:?defina APP_PORT}:8000"'
            ),
        )
        h = self.assertRegla("G8-2", "BLOQUEA", "no es `APP_PORT`")
        self.assertIn("${PUERTO:?defina APP_PORT}", h.mensaje)

    def test_otra_variable_con_ip_sigue_bloqueando(self):
        self.repo.escribe(
            "docker-compose.yml",
            COMPOSE_CORRECTO.replace('"${APP_PORT:-8080}:8000"', '"127.0.0.1:${OTRA}:8000"'),
        )
        self.assertRegla("G8-2", "BLOQUEA", "no es `APP_PORT`")

    def test_puerto_cableado_con_protocolo_bloquea(self):
        self.repo.escribe(
            "docker-compose.yml",
            COMPOSE_CORRECTO.replace('"${APP_PORT:-8080}:8000"', '"127.0.0.1:8113:8000/tcp"'),
        )
        self.assertRegla("G8-2", "BLOQUEA", "cablea el puerto 8113")


# La línea que siembra `semilla/ESQUELETO/docker-compose.yml` de la fábrica (sin datos
# de ninguna aplicación: es la guarda genérica de APP_PORT).
LINEA_DE_LA_SEMILLA = '"127.0.0.1:${APP_PORT:?falta APP_PORT en el .env del servidor}:8000"'


class PruebaLadoHost(unittest.TestCase):
    """El lado del host de un `ports:`, leído entero aunque lleve `:` dentro de `${...}`.

    Hasta el 2026-11-21 se partía por el ÚLTIMO `:` y luego por el último `:` del resto:
    la línea de la semilla daba `?falta APP_PORT en el .env del servidor}` —sin `${`, así
    que ni se juzgaba— y `${PUERTO:?defina APP_PORT}` pasaba igual."""

    def test_la_linea_de_la_semilla_se_lee_entera(self):
        self.assertEqual(
            "${APP_PORT:?falta APP_PORT en el .env del servidor}",
            j02._lado_host(LINEA_DE_LA_SEMILLA),
        )

    def test_la_variable_es_el_nombre_y_no_el_mensaje(self):
        self.assertEqual("PUERTO", j02._variable("${PUERTO:?defina APP_PORT}"))
        self.assertEqual("APP_PORT", j02._variable("${APP_PORT:?falta APP_PORT}"))
        self.assertEqual("APP_PORT", j02._variable("${APP_PORT:-8080}"))
        self.assertEqual("APP_PORT", j02._variable("$APP_PORT"))
        self.assertIsNone(j02._variable("8113"))

    def test_un_valor_por_defecto_anidado_no_cambia_la_variable(self):
        """Forma real de la flota, medida en la calibración del 2026-11-21: el primer
        arreglo la ponía en BLOQUEA porque `[^}]*` no cruzaba la llave interior."""
        host = j02._lado_host('"${APP_PORT:-${PUERTO_PUBLICADO:-3000}}:3000"')
        self.assertEqual("${APP_PORT:-${PUERTO_PUBLICADO:-3000}}", host)
        self.assertEqual("APP_PORT", j02._variable(host))

    def test_formas_conocidas(self):
        casos = {
            '"${APP_PORT:-8080}:8000"': "${APP_PORT:-8080}",
            "127.0.0.1:8113:8000": "8113",
            "8113:8000/tcp": "8113",
            "8000": None,
            "${APP_PORT}:8000": "${APP_PORT}",
        }
        for valor, esperado in casos.items():
            with self.subTest(valor=valor):
                self.assertEqual(esperado, j02._lado_host(valor))


if __name__ == "__main__":
    unittest.main(verbosity=2)
