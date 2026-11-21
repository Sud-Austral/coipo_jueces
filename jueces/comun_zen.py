"""COD-5 — el Zen de Python, con chequeos, en el CI de la aplicación (desde el 2026-11-21).

No ejecuta ruff ni oxlint: los jueces son de biblioteca estándar y no instalan nada. Mira que
la aplicación TENGA la configuración, que su CI la CORRA y que las reglas no sean más blandas
que las de la semilla. Lo que ruff y oxlint encuentran lo dice el CI de la propia aplicación.

Fuente: `docs/ESTANDAR_CODIGO.md` §COD-5 de coipo_master_produccion. Decisión de Luis
Monsalve del 2026-11-21: el Zen de Python en todo el código de la fábrica, «principios con
chequeos». AVISA: regla nueva, que mira hacia adelante y todavía no se calibró sobre la flota
(FILOSOFIA.md §4 de la fábrica).

Este módulo es PURO: devuelve los avisos y `j16_codigo` los emite con el código. Así la
prueba de trazabilidad, que lee `jueces/j*.py`, ve el COD-5; un auxiliar que emitiera por su
cuenta quedaría fuera de ella (pasó el 2026-11-21, y lo impide `test_reglas_citadas`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from comun import Repo

RUFF_CHECK = re.compile(r"\bruff\s+check\b")
RUFF_FORMATO = re.compile(r"\bruff\s+format\s+--check\b")
LINT_FRONTEND = re.compile(r"\bnpm\s+run\s+lint\b|\boxlint\b")

# Las reglas de oxlint del Zen que trae `semilla/ESQUELETO/frontend/.oxlintrc.json`: las que
# tienen que estar en `error`, y las que además tienen un techo (más alto es más blando).
OXLINT_ACTIVAS = ("no-empty", "eqeqeq", "no-nested-ternary", "prefer-const", "no-var")
OXLINT_TECHOS = {"max-depth": 4, "max-params": 5, "complexity": 10}

MANIFESTACION = (
    "el código crece con `except` mudos, funciones de cuarenta ramas y anidamientos que "
    "nadie revisa, porque nada los mide: el Zen se queda en un texto decorativo y lo que "
    "imita el siguiente asistente es lo que ya está escrito"
)
FUENTE = "docs/ESTANDAR_CODIGO.md §COD-5 de coipo_master_produccion"


@dataclass(frozen=True)
class Aviso:
    archivo: str
    mensaje: str
    arreglo: str = ""


@dataclass
class Zen:
    """Lo que COD-5 encontró: avisos, qué se miró y, si no había nada, por qué."""

    avisos: list[Aviso] = field(default_factory=list)
    comprobado: list[str] = field(default_factory=list)
    nada_que_mirar: str = ""


def mirar_zen(repo: Repo) -> Zen:
    versionados = repo.versionados()
    workflows = "\n".join(
        repo.texto(p) or ""
        for p in versionados
        if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))
    )
    hay_backend = any(p.startswith("backend/") and p.endswith(".py") for p in versionados)
    hay_frontend = "frontend/package.json" in versionados
    zen = Zen()
    if not (hay_backend or hay_frontend):
        zen.nada_que_mirar = "COD-5: no hay backend en Python ni frontend que medir"
        return zen
    if hay_backend:
        _backend(zen, versionados, workflows)
    if hay_frontend:
        _frontend(zen, repo, workflows)
    return zen


def _backend(zen: Zen, versionados: list[str], workflows: str) -> None:
    if "backend/ruff.toml" not in versionados:
        zen.avisos.append(
            Aviso(
                "backend/ruff.toml",
                "no hay `backend/ruff.toml`: el backend no declara las reglas del Zen",
                f"`sembrar.py --actualizar` trae el `ruff.toml` sellado de la semilla ({FUENTE})",
            )
        )
    faltan = [
        orden
        for orden, patron in (("ruff check", RUFF_CHECK), ("ruff format --check", RUFF_FORMATO))
        if not patron.search(workflows)
    ]
    if faltan:
        zen.avisos.append(
            Aviso(
                ".github/workflows/",
                f"el CI no corre {' ni '.join(f'`{o}`' for o in faltan)} sobre el backend",
                "el paso «Zen de Python (ruff)» del `ci.yml` de la semilla, en el job del "
                "backend y antes de mypy",
            )
        )
    zen.comprobado.append("COD-5: ruff en el backend (configuración y CI)")


def _frontend(zen: Zen, repo: Repo, workflows: str) -> None:
    ruta = "frontend/.oxlintrc.json"
    texto = repo.texto(ruta)
    if texto is None:
        zen.avisos.append(
            Aviso(
                ruta,
                "no hay `.oxlintrc.json`: el frontend no declara las reglas del Zen",
                f"el `.oxlintrc.json` del ESQUELETO de la semilla ({FUENTE})",
            )
        )
    elif aviso := _reglas_oxlint(ruta, texto):
        zen.avisos.append(aviso)
    if not LINT_FRONTEND.search(workflows):
        zen.avisos.append(
            Aviso(
                ".github/workflows/",
                "el CI no corre `npm run lint` (oxlint) sobre el frontend",
                "el paso `npm run lint` del job del frontend del `ci.yml` de la semilla",
            )
        )
    zen.comprobado.append("COD-5: oxlint en el frontend (reglas y CI)")


def _reglas_oxlint(ruta: str, texto: str) -> Aviso | None:
    try:
        reglas = json.loads(texto).get("rules", {})
    except (ValueError, AttributeError):
        return Aviso(ruta, "no se pudo leer como JSON: las reglas del Zen no se pueden comprobar")
    blandas = [n for n in OXLINT_ACTIVAS if _nivel(_regla(reglas, n)) != "error"]
    for nombre, techo in OXLINT_TECHOS.items():
        valor = _regla(reglas, nombre)
        numero = _numero(valor)
        if _nivel(valor) != "error" or numero is None or numero > techo:
            blandas.append(f"{nombre} ≤ {techo}")
    if not blandas:
        return None
    return Aviso(
        ruta,
        "reglas del Zen ausentes o más blandas que las de la semilla: " + ", ".join(blandas),
        "las de `semilla/ESQUELETO/frontend/.oxlintrc.json`, en `error` y con el mismo techo "
        "o uno más bajo",
    )


def _regla(reglas: dict[str, Any], nombre: str) -> Any:
    """oxlint acepta `no-empty` y `eslint/no-empty` para la misma regla."""
    return reglas.get(nombre, reglas.get(f"eslint/{nombre}"))


def _nivel(valor: Any) -> str:
    nivel = valor[0] if isinstance(valor, list) and valor else valor
    if nivel is None:
        return "off"
    return {2: "error", 1: "warn", 0: "off"}.get(nivel, nivel)


def _numero(valor: Any) -> int | None:
    if not isinstance(valor, list) or len(valor) < 2:
        return None
    opcion = valor[1]
    if isinstance(opcion, dict):
        opcion = opcion.get("max")
    return opcion if isinstance(opcion, int) else None
