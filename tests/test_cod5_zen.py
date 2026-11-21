"""COD-5: el Zen de Python con chequeos en el CI de la aplicación (jueces/comun_zen.py).

Fixtures SINTÉTICOS: este repositorio es público.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j16_codigo as j16  # noqa: E402

SEMILLA = "version: 2026-11-22\nfabrica: 2026-11-22\nadopta: semilla, interfaz\n"
CI_COMPLETO = (
    "jobs:\n  backend:\n    steps:\n      - run: |\n          ruff check .\n"
    "          ruff format --check .\n  frontend:\n    steps:\n      - run: npm run lint\n"
)
OXLINT_ZEN = {
    "rules": {
        "no-empty": "error",
        "eqeqeq": "error",
        "no-nested-ternary": "error",
        "prefer-const": "error",
        "no-var": "error",
        "max-depth": ["error", 4],
        "max-params": ["error", 5],
        "complexity": ["error", 10],
    }
}


class PruebaCod5(CasoConRepo):
    MODULO = j16

    def setUp(self) -> None:
        super().setUp()
        self.repo.escribe(".semilla", SEMILLA)

    def _app_completa(
        self, oxlint: dict | None = None, ci: str = CI_COMPLETO, con_ruff_toml: bool = True
    ) -> None:
        (
            self.repo.escribe("backend/app/main.py", "x = 1\n")
            .escribe(".github/workflows/ci.yml", ci)
            .escribe("frontend/package.json", "{}\n")
            .escribe("frontend/.oxlintrc.json", json.dumps(oxlint or OXLINT_ZEN))
        )
        if con_ruff_toml:
            self.repo.escribe("backend/ruff.toml", "line-length = 100\n")

    def _cod5(self) -> list:
        return [h for h in self.repo.juzga().hallazgos if h.regla == "COD-5"]

    def test_app_con_el_zen_completo_no_avisa(self) -> None:
        self._app_completa()
        self.assertEqual([], self._cod5())

    def test_sin_ruff_en_el_ci_avisa(self) -> None:
        self._app_completa(ci="jobs:\n  frontend:\n    steps:\n      - run: npm run lint\n")
        self.assertRegla("COD-5", "AVISA", "ruff check")

    def test_sin_ruff_toml_avisa(self) -> None:
        self._app_completa(con_ruff_toml=False)
        self.assertRegla("COD-5", "AVISA", "ruff.toml")

    def test_oxlint_mas_blando_avisa_y_nombra_la_regla(self) -> None:
        blando = json.loads(json.dumps(OXLINT_ZEN))
        blando["rules"]["complexity"] = ["error", 20]
        blando["rules"]["no-empty"] = "warn"
        self._app_completa(oxlint=blando)
        h = self.assertRegla("COD-5", "AVISA", "más blandas")
        self.assertIn("complexity", h.mensaje)
        self.assertIn("no-empty", h.mensaje)

    def test_el_prefijo_eslint_cuenta_igual(self) -> None:
        con_prefijo = {"rules": {f"eslint/{k}": v for k, v in OXLINT_ZEN["rules"].items()}}
        self._app_completa(oxlint=con_prefijo)
        self.assertEqual([], self._cod5())

    def test_sin_lint_del_frontend_en_el_ci_avisa(self) -> None:
        self._app_completa(
            ci="jobs:\n  b:\n    steps:\n      - run: ruff check .\n"
            "      - run: ruff format --check .\n"
        )
        self.assertRegla("COD-5", "AVISA", "npm run lint")

    def test_nunca_bloquea(self) -> None:
        self.repo.escribe("backend/app/main.py", "x = 1\n").escribe("frontend/package.json", "{}\n")
        r = self.repo.juzga()
        self.assertFalse([h for h in r.bloqueantes if h.regla == "COD-5"])


if __name__ == "__main__":
    unittest.main()
