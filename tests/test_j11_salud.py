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
    """El caso `coipo_cabania`, y es un hallazgo verdadero.

    Su repositorio no tiene backend ni compose —sólo un workflow de Pages— y aun
    así hay algo sirviendo en vm2:8114 bajo `reserva-bienestar.conaf.cl`, marcado
    `unhealthy` desde hace días. Lo que corre en producción no tiene código
    correspondiente en el repositorio, y el veredicto tiene que decir las dos
    cosas a la vez: falta `/health`, Y no se pudo evaluar el healthcheck.
    """

    MODULO = j11

    def test_sin_compose_ni_endpoint(self):
        self.repo.escribe("README.md", "# nada que desplegar\n")
        r = self.repo.juzga()
        self.assertEqual("SIN_EVALUAR", r.veredicto,
                         "cero comprobaciones no puede leerse como conforme")
        self.assertTrue(r.bloqueantes, "falta /health y eso sí es un hallazgo")
        self.assertTrue(r.no_evaluado, r.no_evaluado)


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
