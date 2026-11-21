"""Una comprobación se registra DESPUÉS de juzgar, y «no hay nada que mirar» es N/A.

Hasta el 2026-11-21 varios jueces llamaban a `r.comprobo()` sin haber mirado nada:

- `j14` registraba «FAB-9: no hay `frontend/package.json`» y `j16` «COD-2: no hay
  frontend», «COD-3: ningún otro `dominio/`» y «COD-4: no hay casos de uso» como
  comprobaciones REALIZADAS. El contador de comprobaciones —lo que separa OK de
  SIN_EVALUAR— contaba lo que no existía;
- `j11` registraba «endpoint /health» ANTES de parsear el módulo, así que un módulo
  que no compila o sin la función decorada dejaba una comprobación que no se hizo;
- y `j11` tomaba el PRIMER módulo que nombra `/health` (un middleware con la lista de
  rutas públicas, por ejemplo) y, si ahí no estaba la función, no buscaba en los
  demás: la autenticación del `/health` real no se miraba.
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
import j14_construccion as j14  # noqa: E402
import j16_codigo as j16  # noqa: E402

COMPOSE = (
    "services:\n  backend:\n    build:\n      context: .\n  app:\n    build:\n"
    '      context: .\n    ports:\n      - "${APP_PORT:-8080}:8000"\n'
)


class PruebaJ14(CasoConRepo):
    MODULO = j14

    def test_sin_frontend_fab9_no_aplica_y_no_cuenta_como_comprobacion(self):
        self.repo.escribe(".semilla", "version: 2026-09-08\nadopta: semilla\n")
        self.repo.escribe("docs/CONSTRUCCION.md", "# vacío\n")
        r = self.repo.juzga()
        self.assertFalse([c for c in r.comprobado if c.startswith("FAB-9")], r.comprobado)
        self.assertTrue([n for n in r.no_aplica if n.startswith("FAB-9")], r.no_aplica)


class PruebaJ16(CasoConRepo):
    MODULO = j16

    def test_lo_que_no_existe_no_es_una_comprobacion(self):
        self.repo.escribe(".semilla", "version: 2026-09-08\nadopta: semilla\n")
        self.repo.escribe("backend/app/main.py", "app = 1\n")
        r = self.repo.juzga()
        for prefijo in ("COD-2", "COD-3: ningún", "COD-4"):
            with self.subTest(prefijo=prefijo):
                self.assertFalse([c for c in r.comprobado if c.startswith(prefijo)], r.comprobado)
                self.assertTrue([n for n in r.no_aplica if n.startswith(prefijo)], r.no_aplica)
        # COD-5 (2026-11-21) avisa aquí con razón —hay backend y no hay ruff—, y no es lo
        # que esta prueba mira: que COD-1 midió y que nada más dio un falso «comprobado».
        self.assertEqual([], [h for h in r.hallazgos if h.regla != "COD-5"], r.hallazgos)
        self.assertEqual([], r.bloqueantes, "COD-1 sí midió: el juez no bloquea")


class PruebaJ11(CasoConRepo):
    MODULO = j11

    def setUp(self):
        super().setUp()
        self.repo.escribe("docker-compose.yml", COMPOSE)

    def test_un_modulo_que_no_compila_no_deja_la_comprobacion(self):
        self.repo.escribe(
            "backend/app/salud.py", '@router.get("/health")\ndef salud(:\n    return {}\n'
        )
        r = self.repo.juzga()
        self.assertFalse(
            [c for c in r.comprobado if c.startswith("endpoint /health")], r.comprobado
        )
        self.assertTrue(any("no se pudo parsear" in n for n in r.no_evaluado), r.no_evaluado)

    def test_busca_la_funcion_en_todos_los_modulos_que_nombran_health(self):
        """El primero que nombra `/health` es un middleware; la ruta está en otro."""
        self.repo.escribe(
            "backend/app/auth.py",
            (
                'PUBLICAS = ["/health"]\n\n\n@app.middleware("http")\n'
                "async def exigir_sesion(request, call_next):\n    return await call_next(request)\n"
            ),
        )
        self.repo.escribe(
            "backend/app/routers/salud.py",
            (
                "from fastapi import APIRouter, Depends\n\nrouter = APIRouter()\n\n\n"
                '@router.get("/health")\ndef salud(u = Depends(usuario_actual)) -> dict:\n'
                '    return {"status": "ok", "app": "prueba"}\n'
            ),
        )
        r = self.repo.juzga()
        self.assertRegla("G8-9", "BLOQUEA", "autenticación", r)
        self.assertIn("endpoint /health (backend/app/routers/salud.py)", r.comprobado)


if __name__ == "__main__":
    unittest.main(verbosity=2)
