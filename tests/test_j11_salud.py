"""Pruebas de j11 — `/health` (Guía 8, puntos 9 y 11).

Fixtures SINTÉTICOS: este repositorio es público.

Todo lo que se comprueba aquí sale de una sola línea del despliegue:

    curl -sf http://127.0.0.1:$APP_PORT/health

`curl -sf` falla con cualquier código >= 400 y no sigue redirecciones. Es lo
ÚNICO que verifica que la aplicación quedó viva.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j11_salud as j11  # noqa: E402

COMPOSE = """\
services:
  backend:
    build:
      context: .
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/health"]
  app:
    build:
      context: .
    ports:
      - "${APP_PORT:-8080}:8000"
"""

SALUD_CORRECTO = '''\
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db

router = APIRouter()


@router.get("/health")
def salud(db: Session = Depends(get_db)) -> dict:
    """Sin autenticación, sin redirección, 200 con JSON simple."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "app": "prueba"}
'''


class PruebaSalud(CasoConRepo):
    MODULO = j11

    def setUp(self):
        super().setUp()
        self.repo.escribe("docker-compose.yml", COMPOSE)

    def test_endpoint_correcto_no_bloquea(self):
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO)
        self.assertSinBloqueos()

    def test_sin_endpoint_bloquea(self):
        """Sin `/health` el despliegue falla siempre, o nadie sabe si funcionó."""
        self.repo.escribe("backend/app/main.py",
                          "from fastapi import FastAPI\napp = FastAPI()\n")
        self.assertRegla("G8-9", "BLOQUEA", "no se encontró ningún endpoint `/health`")

    def test_execute_con_string_crudo_bloquea(self):
        """En SQLAlchemy 2.x lanza ArgumentError: el /health falla SIEMPRE.

        La versión anterior de `fastapi-postgresql-conexion.md` traía el ejemplo
        sin `text()`, así que quien copió de ahí lo tiene roto y no lo sabe.
        """
        self.repo.escribe("backend/app/routers/salud.py",
                          SALUD_CORRECTO.replace('text("SELECT 1")', '"SELECT 1"'))
        self.assertRegla("G8-9", "BLOQUEA", "`execute()` con un string crudo")

    def test_healthcheck_que_apunta_a_otra_ruta_avisa_dk5(self):
        """El incidente H9: `coipo_cabania` lleva días `unhealthy` con /health en 200.

        Un contenedor marcado mal para siempre no rompe nada hoy, y por eso
        esconderá un problema real el día que lo haya. AVISA (`DK-5`).

        Hasta el 2026-11-21 se llamaba `..._bloquea` y sólo comprobaba que hubiera
        ALGÚN hallazgo: el código salía como `DOCKER-hc`, sin fila en REGLAS.md, y
        la prueba pasaba igual.
        """
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO)
        self.repo.escribe("docker-compose.yml",
                          COMPOSE.replace("/health", "/api/estado"))
        r = self.repo.juzga()
        self.assertRegla("DK-5", "AVISA", "`/api/estado`", r)
        self.assertSinBloqueos(r)


SALUD_CON = '''\
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from .sesion import sesion_actual, sesion_opcional, usuario_actual, exigir_rol

router = APIRouter()
privado = APIRouter(dependencies=[Depends(sesion_actual)])


{decorador}
def salud({parametros}) -> dict:
    {cuerpo}
    return {{"status": "ok", "app": "prueba"}}
'''


class PruebaSinAutenticacion(CasoConRepo):
    """Guía 8, punto 9: ni autenticación ni redirección en `/health`.

    Hasta el 2026-11-21 sólo se miraban la anotación y el NOMBRE de cada parámetro:
    un `Depends(...)` como valor por defecto, `dependencies=[...]` en el decorador o en
    el `APIRouter`, `sesion_actual` y un `RedirectResponse` pasaban sin hallazgo, y esta
    regla BLOQUEA no tenía ni una prueba."""

    MODULO = j11

    def setUp(self):
        super().setUp()
        self.repo.escribe("docker-compose.yml", COMPOSE)

    def _salud(self, decorador='@router.get("/health")', parametros="", cuerpo="pass"):
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CON.format(
            decorador=decorador, parametros=parametros, cuerpo=cuerpo))
        return self.repo.juzga()

    def test_depends_como_valor_por_defecto_bloquea(self):
        r = self._salud(parametros="u = Depends(usuario_actual)")
        self.assertRegla("G8-9", "BLOQUEA", "autenticación", r)

    def test_depends_solo_de_palabra_clave_bloquea(self):
        r = self._salud(parametros="*, u = Depends(usuario_actual)")
        self.assertRegla("G8-9", "BLOQUEA", "autenticación", r)

    def test_sesion_actual_bloquea(self):
        r = self._salud(parametros="s = Depends(sesion_actual)")
        self.assertRegla("G8-9", "BLOQUEA", "autenticación", r)

    def test_dependencies_en_el_decorador_bloquea(self):
        r = self._salud(decorador='@router.get("/health", '
                                  'dependencies=[Depends(exigir_rol("administrador"))])')
        self.assertRegla("G8-9", "BLOQUEA", "autenticación", r)

    def test_dependencies_en_el_router_bloquea(self):
        r = self._salud(decorador='@privado.get("/health")')
        self.assertRegla("G8-9", "BLOQUEA", "autenticación", r)

    def test_redirect_response_bloquea(self):
        r = self._salud(cuerpo='return RedirectResponse("/login")')
        self.assertRegla("G8-9", "BLOQUEA", "redirige", r)

    def test_anotacion_annotated_sigue_bloqueando(self):
        r = self._salud(parametros="u: 'Annotated[dict, Depends(usuario_actual)]'")
        self.assertRegla("G8-9", "BLOQUEA", "autenticación", r)

    def test_sesion_opcional_no_es_autenticacion(self):
        """`sesion_opcional` devuelve None sin sesión: no corta a nadie."""
        r = self._salud(parametros="s = Depends(sesion_opcional)")
        self.assertSinRegla("G8-9", r)
        self.assertIn("/health sin autenticación", r.comprobado)

    def test_la_base_de_datos_no_es_autenticacion(self):
        r = self._salud(parametros="db = Depends(get_db)")
        self.assertSinRegla("G8-9", r)

    def test_dependencies_de_otro_router_no_cuentan(self):
        """`privado` exige sesión, pero `/health` cuelga de `router`."""
        r = self._salud()
        self.assertSinRegla("G8-9", r)


SALUD_COMO_LA_SEMILLA = '''\
from fastapi import APIRouter, Response

APP_NOMBRE = "coipo_prueba"
router = APIRouter()


def _identidad() -> dict:
    return {"app": APP_NOMBRE, "version": "1", "commit": "abc", "construido_en": "hoy"}


@router.get("/health")
def salud(respuesta: Response) -> dict:
    cuerpo = {"status": "ok", **_identidad()}
    return cuerpo
'''


class PruebaIdentidadEnSalud(CasoConRepo):
    """SEM-4: el cuerpo de `/health` lleva `app`.

    Es lo único que delata una colisión de `APP_PORT`: si otra aplicación ocupa el
    puerto, el `curl -sf` del despliegue recibe SU `/health`, responde 200, y el
    despliegue se declara exitoso sobre el contenedor equivocado
    (`semilla/ESQUELETO/CLAUDE.md` §4 de la fábrica)."""

    MODULO = j11

    def setUp(self):
        super().setUp()
        self.repo.escribe("docker-compose.yml", COMPOSE)

    def test_sin_app_avisa(self):
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO.replace(
            '{"status": "ok", "app": "prueba"}', '{"status": "ok"}'))
        r = self.repo.juzga()
        self.assertRegla("SEM-4", "AVISA", "`app`", r)
        self.assertSinBloqueos(r)

    def test_con_app_no_avisa(self):
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO)
        self.assertSinRegla("SEM-4")

    def test_la_forma_de_la_semilla_no_avisa(self):
        """La semilla arma el cuerpo con `**_identidad()`: `app` vive en otra función."""
        self.repo.escribe("backend/app/routers/salud.py", SALUD_COMO_LA_SEMILLA)
        self.assertSinRegla("SEM-4")

    def test_un_modelo_con_campo_app_no_avisa(self):
        self.repo.escribe("backend/app/routers/salud.py", (
            "from fastapi import APIRouter\nfrom pydantic import BaseModel\n\n"
            "router = APIRouter()\n\n\nclass Salud(BaseModel):\n    status: str\n    app: str\n\n\n"
            '@router.get("/health")\ndef salud() -> Salud:\n'
            '    return Salud(status="ok", app="coipo_prueba")\n'))
        self.assertSinRegla("SEM-4")

    def test_se_puede_suprimir_con_motivo(self):
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO.replace(
            '{"status": "ok", "app": "prueba"}', '{"status": "ok"}').replace(
            "def salud(", "# coipo-jueces:ignorar(SEM-4) el balanceador ya distingue la app\ndef salud("))
        r = self.repo.juzga()
        self.assertSinRegla("SEM-4", r)
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_el_nginx_sin_app_avisa(self):
        self.repo.escribe("docker-compose.yml", COMPOSE_SOLO_APP)
        self.repo.escribe("frontend/nginx.conf", NGINX_SALUD.replace(
            '\'{"status":"ok","app":"prueba"}\'', "'ok'"))
        self.assertRegla("SEM-4", "AVISA", "`app`")

    def test_el_nginx_con_app_no_avisa(self):
        self.repo.escribe("docker-compose.yml", COMPOSE_SOLO_APP)
        self.repo.escribe("frontend/nginx.conf", NGINX_SALUD)
        self.assertSinRegla("SEM-4")


class PruebaRepositorioVacio(CasoConRepo):
    """El caso `coipo_cabania`: sin compose y sin `/health`. Nunca OK.

    Su repositorio no tiene backend ni compose —sólo un workflow de Pages— y aun
    así hay algo sirviendo en vm2:8114 bajo `reserva-bienestar.conaf.cl`. Lo que
    corre en producción no tiene código correspondiente en el repositorio.

    HASTA EL 2026-10-25 esta prueba exigía un BLOQUEA «no se encontró /health».
    La auditoría de ese día lo cambió a `no_evaluado`, como ya hacían `j01` y
    `j06`: sin compose el pipeline de la flota no despliega este repositorio, así
    que no hay smoke test que vaya a pedir `/health`, y exigirlo es juzgar una
    aplicación que el repositorio no declara ser. El rojo no se pierde donde
    importa: con el perfil `aplicacion` en modo bloqueante, un juez SIN_EVALUAR
    hace salir 1 al gate («el repositorio no es lo que declara»).
    """

    MODULO = j11

    def test_sin_compose_ni_endpoint(self):
        self.repo.escribe("README.md", "# nada que desplegar\n")
        r = self.repo.juzga()
        self.assertEqual("SIN_EVALUAR", r.veredicto, [h.mensaje for h in r.hallazgos])
        self.assertTrue(any("compose" in n for n in r.no_evaluado), r.no_evaluado)


NGINX_SALUD = """\
server {
    listen 8080;
    # el smoke test pide /health al contenedor `app`
    location = /health {
        access_log off;
        default_type application/json;
        return 200 '{"status":"ok","app":"prueba"}';
    }
    location / {
        try_files $uri /index.html;
    }
}
"""

COMPOSE_SOLO_APP = """\
services:
  app:
    build:
      context: .
    ports:
      - "${APP_PORT:-8080}:8080"
"""


class PruebaSaludEnNginx(CasoConRepo):
    """`/health` servido por el nginx INTERNO (auditoría del 2026-10-25).

    `coipo_prevension_ministerial`, `coipo_tv` y `coipo_boton_rojo` responden
    `/health` con un `location = /health { return 200 ...; }` en su
    `frontend/nginx.conf`: el contenedor `app` es el que publica `APP_PORT` y es
    al que llega el `curl -sf` del smoke test. El juez sólo buscaba en Python y
    los BLOQUEABA por «no se encontró ningún endpoint `/health`».
    """

    MODULO = j11

    def setUp(self):
        super().setUp()
        self.repo.escribe("docker-compose.yml", COMPOSE_SOLO_APP)

    def test_location_en_el_nginx_interno_cuenta(self):
        self.repo.escribe("frontend/nginx.conf", NGINX_SALUD)
        r = self.repo.juzga()
        self.assertSinBloqueos(r)
        self.assertTrue(any("nginx" in c for c in r.comprobado), r.comprobado)

    def test_location_comentada_no_cuenta(self):
        self.repo.escribe("frontend/nginx.conf", NGINX_SALUD.replace(
            "    location = /health {", "    # location = /health {"))
        self.assertRegla("G8-9", "BLOQUEA", "no se encontró ningún endpoint `/health`")

    def test_el_vhost_del_host_no_cuenta(self):
        """El nginx del HOST está delante; el smoke test va directo al contenedor."""
        self.repo.escribe("ops/nginx-host/prueba.conaf.cl.conf", NGINX_SALUD)
        self.assertRegla("G8-9", "BLOQUEA", "no se encontró ningún endpoint `/health`")

    def test_location_que_no_devuelve_2xx_bloquea(self):
        """`curl -sf` falla con cualquier código >= 400 y no sigue redirecciones."""
        for codigo in ("302 /login", "503"):
            with self.subTest(codigo=codigo):
                self.repo.escribe("frontend/nginx.conf", NGINX_SALUD.replace(
                    "return 200 '{\"status\":\"ok\",\"app\":\"prueba\"}';",
                    f"return {codigo};"))
                self.assertRegla("G8-9", "BLOQUEA", f"devuelve {codigo.split()[0]}")

    def test_location_con_autenticacion_bloquea(self):
        self.repo.escribe("frontend/nginx.conf", NGINX_SALUD.replace(
            "        access_log off;\n", "        auth_basic \"restringido\";\n"))
        self.assertRegla("G8-9", "BLOQUEA", "autenticación")

    def test_el_hallazgo_de_repositorio_se_puede_suprimir_en_el_compose(self):
        self.repo.escribe("docker-compose.yml",
                          "# coipo-jueces:ignorar(G8-9) colector sin http: lo vigila /health/detalle\n"
                          + COMPOSE_SOLO_APP)
        r = self.repo.juzga()
        self.assertSinBloqueos(r)
        self.assertEqual(1, len(r.supresiones), r.supresiones)


class PruebaTercerosConComposeYaml(CasoConRepo):
    """La excepción de software de terceros leía sólo `docker-compose.yml`."""

    MODULO = j11

    def test_compose_yaml_de_imagenes_ajenas_es_no_aplica(self):
        self.repo.escribe("compose.yaml",
                          "services:\n  n8n:\n    image: n8nio/n8n\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto, [h.mensaje for h in r.hallazgos])


class PruebaFalloDeDatos(CasoConRepo):
    """Guía 8, punto 11 — y por qué esta regla AVISA en vez de bloquear."""

    MODULO = j11

    def setUp(self):
        super().setUp()
        self.repo.escribe("docker-compose.yml", COMPOSE)

    def test_except_que_devuelve_200_avisa_pero_no_bloquea(self):
        """Tres implementaciones independientes eligieron 200, y las tres lo escribieron.

        El hueco real es que el smoke test sólo mira el código HTTP, y ese smoke
        test vive en `infra-docker-base`, que por contrato no se edita por app.
        Ninguna aplicación puede cerrarlo sola: bloquear su despliegue por algo
        que no está en su mano es la forma más rápida de enseñar a suprimir al
        juez.
        """
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO.replace(
            '    db.execute(text("SELECT 1"))\n    return {"status": "ok", "app": "prueba"}\n',
            '    try:\n'
            '        db.execute(text("SELECT 1"))\n'
            '    except Exception:\n'
            '        return {"status": "error", "db": "error"}\n'
            '    return {"status": "ok", "app": "prueba"}\n'))
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes, [h.mensaje for h in r.bloqueantes])
        self.assertRegla("G8-11", "AVISA", "ninguna sonda automatizada lee el estado degradado", r)

    def test_el_arreglo_nombra_la_via_de_plataforma(self):
        """Un arreglo que sólo ofrece caminos imposibles no es un arreglo.

        Las tres vías del repositorio existen, pero la que cierra el hueco de
        verdad es que el smoke test lea el cuerpo. Si el hallazgo no lo dice,
        quien lo lea concluye que el juez no entiende su aplicación.
        """
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO.replace(
            '    db.execute(text("SELECT 1"))\n',
            '    try:\n'
            '        db.execute(text("SELECT 1"))\n'
            '    except Exception:\n'
            '        return {"status": "error"}\n'))
        arreglos = [h.arreglo for h in self.repo.juzga().hallazgos]
        self.assertTrue(any("PLATAFORMA" in a for a in arreglos), arreglos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
