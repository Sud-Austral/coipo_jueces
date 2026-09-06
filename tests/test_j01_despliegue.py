"""Pruebas de j01 — sobre de despliegue.

Fixtures sintéticos: ningún compose de aquí abajo es copia de un repositorio de
CONAF. Reproducen la FORMA del defecto, no el archivo.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ayuda import CasoConRepo, RepoSintetico  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jueces"))
import j01_despliegue as j01  # noqa: E402

# El compose que cumple el contrato. Cada prueba lo degrada en un solo punto,
# para que el hallazgo no pueda venir de otra cosa.
COMPOSE_BUENO = """\
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
    mem_limit: 512m
    restart: unless-stopped

  app:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    depends_on:
      - backend
    ports:
      - "${APP_PORT:-8080}:8000"
    mem_limit: 128m
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "true"]
"""

NGINX_BUENO = """\
server {
    listen 8000;
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $destino backend;
    location /api/ {
        proxy_pass http://$destino:8000$request_uri;
    }
}
"""

NGINX_LITERAL = """\
server {
    listen 8000;
    location /api/ {
        proxy_pass http://backend:8000/api/;
    }
}
"""


class PruebaCompose(CasoConRepo):
    MODULO = j01

    def _base(self, compose: str = COMPOSE_BUENO) -> None:
        self.repo.escribe("docker-compose.yml", compose)
        self.repo.escribe(".dockerignore", ".git\n.env\nnode_modules\n")
        self.repo.escribe("frontend/nginx.conf", NGINX_BUENO)

    def test_el_compose_correcto_no_bloquea(self):
        """El caso de referencia. Si esto falla, el resto de las pruebas mienten."""
        self._base()
        self.assertSinBloqueos()

    def test_version_obsoleta_bloquea(self):
        self._base("version: '3.8'\n" + COMPOSE_BUENO)
        self.assertBloquea("`version:`")

    def test_dos_servicios_con_puerto_bloquean(self):
        self._base(COMPOSE_BUENO.replace(
            "    env_file: .env\n",
            '    env_file: .env\n    ports:\n      - "9000:8000"\n'))
        self.assertBloquea("publican puerto")

    def test_ningun_puerto_bloquea(self):
        """Sin puerto no hay smoke test posible: el despliegue no se puede verificar."""
        self._base(COMPOSE_BUENO.replace('    ports:\n      - "${APP_PORT:-8080}:8000"\n', ""))
        self.assertBloquea("ningún servicio publica un puerto")

    def test_base_de_datos_en_el_compose_bloquea(self):
        self._base(COMPOSE_BUENO + """
  db:
    image: postgres:17-alpine
    restart: unless-stopped
    mem_limit: 1g
    healthcheck:
      test: ["CMD", "true"]
""")
        self.assertBloquea("motor de base de datos")

    def test_compose_ausente_no_se_declara_limpio(self):
        """«No pude evaluar» y «evalué y está bien» no son lo mismo."""
        self.repo.escribe("README.md", "# x\n")
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertTrue(r.no_evaluado)

    def test_compose_inparseable_no_se_declara_limpio(self):
        """Un parser que no entiende un archivo no puede dar verde.

        Es la razón de que carga_yaml lance en vez de adivinar: un compose mal
        leído produciría un veredicto por el motivo equivocado.
        """
        self.repo.escribe("docker-compose.yml",
                          "services:\n  backend:\n    command: |\n      algo\n")
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertTrue(any("no se pudo verificar" in n for n in r.no_evaluado))

    def test_avisos_de_robustez(self):
        self._base("""\
services:
  app:
    build:
      context: .
    ports:
      - "8080:8000"
""")
        r = self.repo.juzga()
        for fragmento in ("no tiene healthcheck", "no declara `mem_limit`",
                          "no declara `restart:`"):
            self.assertAvisa(fragmento, r)

    def test_un_servicio_de_imagen_upstream_no_exige_healthcheck(self):
        """El `app` de coipo_n8n es un nginx traductor sin healthcheck, a propósito.

        Exigírselo a una imagen de terceros que no controlas es la clase de
        regla que la gente suprime, y con ella suprime las que sí importan.
        """
        self._base("""\
services:
  app:
    image: nginx:1.27-alpine
    ports:
      - "8125:8000"
    mem_limit: 128m
    restart: unless-stopped
""")
        r = self.repo.juzga()
        self.assertSinBloqueos(r)
        avisos = [h.mensaje for h in r.hallazgos if h not in r.bloqueantes]
        self.assertFalse([a for a in avisos if "healthcheck" in a], avisos)


class PruebaContextoDeBuild(CasoConRepo):
    MODULO = j01

    def test_context_raiz_sin_dockerignore_bloquea(self):
        """El defecto real de COIPO_ENTREGA_PLANTA, reproducido en sintético."""
        self.repo.escribe("docker-compose.yml", COMPOSE_BUENO)
        self.repo.escribe("frontend/nginx.conf", NGINX_BUENO)
        self.assertBloquea("falta `.dockerignore`")

    def test_dockerignore_que_no_excluye_env_bloquea(self):
        """El defecto real de COIPO_USUARIOS: existe, pero deja pasar el .env."""
        self.repo.escribe("docker-compose.yml", COMPOSE_BUENO)
        self.repo.escribe("frontend/nginx.conf", NGINX_BUENO)
        self.repo.escribe(".dockerignore", ".git\n**/node_modules\nfrontend/dist\n")
        self.assertBloquea("no excluye `.env`")

    def test_sin_builds_no_se_exige_dockerignore(self):
        """Un encuadre operativo que solo usa `image:` no tiene contexto que proteger."""
        self.repo.escribe("docker-compose.yml", """\
services:
  app:
    image: nginx:1.27-alpine
    ports:
      - "8125:8000"
    mem_limit: 128m
    restart: unless-stopped
""")
        self.assertSinBloqueos()


class PruebaNginxInterno(CasoConRepo):
    MODULO = j01

    def _con_nginx(self, contenido: str) -> None:
        self.repo.escribe("docker-compose.yml", COMPOSE_BUENO)
        self.repo.escribe(".dockerignore", ".git\n.env\n")
        self.repo.escribe("frontend/nginx.conf", contenido)

    def test_proxy_pass_literal_sin_resolver_avisa(self):
        """Avisa y no bloquea: `NG-1` no tiene documento que la respalde.

        Ver REGLAS.md, «Reglas sin fuente escrita». El defecto es real y
        verificable, pero una regla que nadie escribio no puede detener el
        despliegue de siete repositorios que la incumplen.
        """
        self._con_nginx(NGINX_LITERAL)
        self.assertAvisa("sin `resolver`")

    def test_con_resolver_no_bloquea(self):
        self._con_nginx(NGINX_BUENO)
        self.assertSinBloqueos()

    def test_proxy_pass_a_ip_no_bloquea(self):
        """El vhost del host proxea a 127.0.0.1:APP_PORT y eso es correcto.

        Marcarlo confundiría el nginx de dentro del contenedor con el de fuera,
        que son dos cosas distintas con dos contratos distintos.
        """
        self._con_nginx("""\
server {
    listen 80;
    location / {
        proxy_pass http://127.0.0.1:8113;
    }
}
""")
        self.assertSinBloqueos()

    def test_se_puede_suprimir_con_motivo(self):
        self._con_nginx(NGINX_LITERAL.replace(
            "        proxy_pass http://backend:8000/api/;",
            "        # coipo-jueces:ignorar(NG-1) upstream fijo por decisión de red\n"
            "        proxy_pass http://backend:8000/api/;"))
        r = self.repo.juzga()
        self.assertSinBloqueos(r)
        self.assertEqual(1, len(r.supresiones))


class PruebaDelPropioJuez(unittest.TestCase):
    def test_el_juez_detecta_lo_que_dice_detectar(self):
        """Se planta la violación y se exige que el verificador la vea.

        Sin esto, vaciar `comprobar_nginx_interno` deja la suite en verde.
        """
        repo = RepoSintetico(j01)
        try:
            repo.escribe("docker-compose.yml", COMPOSE_BUENO)
            repo.escribe(".dockerignore", ".git\n.env\n")
            repo.escribe("frontend/nginx.conf", NGINX_LITERAL)
            self.assertTrue(repo.juzga().hallazgos,
                            "el juez dejó pasar un proxy_pass literal sin resolver")
        finally:
            repo.cierra()


if __name__ == "__main__":
    unittest.main(verbosity=2)
