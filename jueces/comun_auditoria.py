"""AUD-1 — la auditoría está siempre, con el último ingreso de cada persona (2026-11-21).

Lo pidieron los superiores de Luis Monsalve: en TODA aplicación de la fábrica la auditoría
está siempre, y la vista del administrador muestra quién entró y hace cuánto fue su último
ingreso. Desde ese día la semilla nace con ello cableado (`patrones/auditoria` y
`patrones/actividad` de coipo_master_produccion, que `sembrar.py` aplica siempre); esta
regla mira que siga ahí. Fuente: `docs/decisiones/2026-11-auditoria-siempre.md` de la
fábrica.

Mira la FORMA —que las piezas estén y que `main.py` monte el acceso—, no que escriban
filas: eso lo prueban los contratos sellados de la propia aplicación
(`tests/contrato/test_auditoria_y_accesos.py`, contra Postgres), que `SEM-1`/`SEM-3` vigilan.

Este módulo es PURO: devuelve lo que falta y `j12_semilla` lo emite con el código, para que
la prueba de trazabilidad lo vea (lee `jueces/j*.py`).
"""

from __future__ import annotations

from dataclasses import dataclass

from comun import Repo

# Las piezas SELLADAS de la auditoría (semilla/CONGELADO). Que no estén editadas lo mira
# SEM-1; que no FALTEN, esta regla: SEM-3 sólo cuenta las pruebas ausentes.
SELLADAS = (
    "backend/app/adaptadores/entrada/http/middleware_acceso.py",
    "backend/app/adaptadores/entrada/http/rutas/autenticacion.py",
    "backend/app/adaptadores/salida/postgres/auditor.py",
    "backend/app/adaptadores/salida/postgres/registro_de_accesos.py",
)
# Lo que el patrón `auditoria` escribe y edita en la aplicación.
COMPOSICION = "backend/app/composicion/acceso.py"
MAIN = "backend/app/main.py"
MONTAJE = "montar_acceso("
# La pestaña Actividad con los últimos ingresos (patrón `actividad`).
RUTA_ACTIVIDAD = "backend/app/adaptadores/entrada/http/rutas/actividad.py"
ULTIMOS_INGRESOS_API = "ultimos-ingresos"
VISTA_INGRESOS = "frontend/src/vistas/UltimosIngresos.tsx"
VISTA_ACTIVIDAD = "frontend/src/vistas/Actividad.tsx"

MANIFESTACION = (
    "nadie puede decir quién entró a la aplicación ni cuándo: ante una pregunta de la "
    "Contraloría o un incidente, no hay registro que mostrar, y el administrador no ve el "
    "último ingreso de nadie"
)
ARREGLO = (
    "`python ../coipo_master_produccion/semilla/sembrar.py --destino . --actualizar` trae lo "
    "sellado; `semilla/patrones/auditoria/aplicar.py` y `semilla/patrones/actividad/aplicar.py` "
    "de la fábrica cablean el resto (docs/decisiones/2026-11-auditoria-siempre.md, §6)"
)


@dataclass(frozen=True)
class Falta:
    archivo: str
    mensaje: str


def lo_que_falta(repo: Repo) -> list[Falta] | None:
    """Lo que falta de la auditoría siempre, o None si no hay backend que mirar."""
    versionados = set(repo.versionados())
    if not any(p.startswith("backend/app/") for p in versionados):
        return None
    faltas = [
        Falta(ruta, "falta una pieza sellada de la auditoría")
        for ruta in SELLADAS
        if ruta not in versionados
    ]
    if COMPOSICION not in versionados:
        faltas.append(Falta(COMPOSICION, "falta la composición del acceso (sesión, IAM, auditor)"))
    if MONTAJE not in (repo.texto(MAIN) or ""):
        faltas.append(
            Falta(
                MAIN,
                "`main.py` no monta el acceso (`montar_acceso(...)`): no se "
                "escribe ni `log_acceso` ni el ingreso en `log_auditoria`",
            )
        )
    if ULTIMOS_INGRESOS_API not in (repo.texto(RUTA_ACTIVIDAD) or ""):
        faltas.append(
            Falta(
                RUTA_ACTIVIDAD,
                "no hay ruta de últimos ingresos (`GET /api/v1/actividad/ultimos-ingresos`)",
            )
        )
    if "frontend/package.json" in versionados:
        for vista in (VISTA_ACTIVIDAD, VISTA_INGRESOS):
            if vista not in versionados:
                faltas.append(
                    Falta(
                        vista,
                        "falta la vista del administrador con la actividad y "
                        "el último ingreso de cada persona",
                    )
                )
    return faltas
