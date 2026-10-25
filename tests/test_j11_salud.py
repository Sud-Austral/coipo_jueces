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
    return {"status": "ok"}
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
        self.assertBloquea("no se encontró ningún endpoint `/health`")

    def test_execute_con_string_crudo_bloquea(self):
        """En SQLAlchemy 2.x lanza ArgumentError: el /health falla SIEMPRE.

        La versión anterior de `fastapi-postgresql-conexion.md` traía el ejemplo
        sin `text()`, así que quien copió de ahí lo tiene roto y no lo sabe.
        """
        self.repo.escribe("backend/app/routers/salud.py",
                          SALUD_CORRECTO.replace('text("SELECT 1")', '"SELECT 1"'))
        self.assertBloquea("`execute()` con un string crudo")

    def test_healthcheck_que_apunta_a_otra_ruta_bloquea(self):
        """El incidente H9: `coipo_cabania` lleva días `unhealthy` con /health en 200.

        Un contenedor marcado mal para siempre no rompe nada hoy, y por eso
        esconderá un problema real el día que lo haya.
        """
        self.repo.escribe("backend/app/routers/salud.py", SALUD_CORRECTO)
        self.repo.escribe("docker-compose.yml",
                          COMPOSE.replace("/health", "/api/estado"))
        r = self.repo.juzga()
        self.assertTrue(r.hallazgos, "el healthcheck apunta a otra ruta y nadie avisa")


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
        self.assertBloquea("no se encontró ningún endpoint `/health`")

    def test_el_vhost_del_host_no_cuenta(self):
        """El nginx del HOST está delante; el smoke test va directo al contenedor."""
        self.repo.escribe("ops/nginx-host/prueba.conaf.cl.conf", NGINX_SALUD)
        self.assertBloquea("no se encontró ningún endpoint `/health`")

    def test_location_con_autenticacion_bloquea(self):
        self.repo.escribe("frontend/nginx.conf", NGINX_SALUD.replace(
            "        access_log off;\n", "        auth_basic \"restringido\";\n"))
        self.assertBloquea("autenticación")

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
            '    db.execute(text("SELECT 1"))\n    return {"status": "ok"}\n',
            '    try:\n'
            '        db.execute(text("SELECT 1"))\n'
            '    except Exception:\n'
            '        return {"status": "error", "db": "error"}\n'
            '    return {"status": "ok"}\n'))
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes, [h.mensaje for h in r.bloqueantes])
        self.assertAvisa("ninguna sonda automatizada lee el estado degradado", r)

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
