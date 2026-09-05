#!/usr/bin/env python3
"""Corre todos los jueces aplicables sobre un repositorio y resume.

    python jueces/correr.py --repo . --modo advisory --perfil aplicacion

Es lo que invoca el workflow reusable. Existe como script y no como un bucle de
`run:` en el YAML porque el YAML no se puede probar: este archivo sí tiene
tests, y la lógica de "qué juez aplica a qué perfil" y "cuándo sale 1" es
precisamente donde un error deja a la flota sin compuerta sin que nadie lo vea.

DESCUBRIMIENTO DINÁMICO
  Se cargan los `jNN_*.py` del directorio. Añadir un juez es añadir un archivo;
  no hay una lista que mantener en dos sitios y que alguien olvide actualizar.
  Un juez que no declare `comprobar` es un ERROR ruidoso, no un archivo que se
  ignora en silencio.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from comun import Repo, Resultado, Severidad, informar  # noqa: E402

PATRON_JUEZ = re.compile(r"^j(\d{2})_[a-z_]+\.py$")


class JuezInvalido(RuntimeError):
    """Un archivo con nombre de juez que no cumple el contrato de juez.

    Se lanza en vez de saltarlo. Un juez que se ignora en silencio es una regla
    apagada que el RESUMEN.md sigue contando como cubierta.
    """


def descubrir(directorio: Path, perfil: str, solo: list[str]) -> list[tuple[str, object]]:
    modulos: list[tuple[str, object]] = []
    for archivo in sorted(directorio.glob("j*.py")):
        m = PATRON_JUEZ.match(archivo.name)
        if not m:
            continue
        nombre = f"j{m.group(1)}"
        if solo and nombre not in solo:
            continue
        spec = importlib.util.spec_from_file_location(archivo.stem, archivo)
        if spec is None or spec.loader is None:
            raise JuezInvalido(f"{archivo.name}: no se pudo cargar")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        if not hasattr(modulo, "comprobar"):
            raise JuezInvalido(f"{archivo.name}: no define comprobar(repo, resultado)")
        perfiles = getattr(modulo, "PERFILES", ("aplicacion", "encuadre_operativo"))
        if perfil not in perfiles:
            continue
        modulos.append((nombre, modulo))
    return modulos


def resumen_markdown(resultados: list[Resultado], *, modo: str, repo: str) -> str:
    lineas = [
        f"# Verificación COIPO — `{repo}`", "",
        f"Modo: **{modo}**", "",
        "| Juez | Bloquea | Avisa | Supresiones | No evaluado |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in resultados:
        b = len(r.bloqueantes)
        a = len(r.hallazgos) - b
        lineas.append(f"| `{r.juez}` | {b} | {a} | {len(r.supresiones)} | {len(r.no_evaluado)} |")

    detalle = [(r, h) for r in resultados for h in r.hallazgos]
    if detalle:
        lineas += ["", "## Hallazgos", ""]
        for r, h in detalle:
            marca = "🔴" if h.severidad is Severidad.BLOQUEA else "🟡"
            lineas.append(f"- {marca} **{h.regla}** `{h.ubicacion()}` — {h.mensaje}")
            lineas.append(f"  - en producción: {h.manifestacion}")
            if h.arreglo:
                lineas.append(f"  - arreglo: {h.arreglo}")

    supr = [(r.juez, s) for r in resultados for s in r.supresiones]
    if supr:
        lineas += ["", "## Supresiones activas", "",
                   "Cada una exige una fila en `DEUDA.md`. Si este número crece "
                   "respecto de `main`, el verificador se está apagando.", ""]
        lineas += [f"- `{j}` — {s}" for j, s in supr]

    no_ev = [(r.juez, n) for r in resultados for n in r.no_evaluado]
    if no_ev:
        lineas += ["", "## No evaluado", "",
                   "Esto **no** es lo mismo que «sin hallazgos».", ""]
        lineas += [f"- `{j}` — {n}" for j, n in no_ev]

    return "\n".join(lineas) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="corre los jueces COIPO")
    p.add_argument("--repo", default=".")
    p.add_argument("--modo", choices=("advisory", "bloqueante"), default="advisory")
    p.add_argument("--perfil", choices=("aplicacion", "encuadre_operativo"),
                   default="aplicacion")
    p.add_argument("--jueces", default="",
                   help="lista separada por espacios o comas (p. ej. 'j01 j09'); "
                        "vacío = todos los del perfil")
    p.add_argument("--resumen", default=None, help="ruta del RESUMEN.md a escribir")
    p.add_argument("--json", dest="json_salida", default=None)
    args = p.parse_args()

    solo = [x for x in re.split(r"[,\s]+", args.jueces) if x]
    repo = Repo(args.repo)
    en_github = os.environ.get("GITHUB_ACTIONS") == "true"

    modulos = descubrir(AQUI, args.perfil, solo)
    if not modulos:
        print(f"::error::ningún juez aplica al perfil '{args.perfil}'"
              if en_github else
              f"[jueces] ningún juez aplica al perfil '{args.perfil}'")
        # Salir 1: "no corrió ningún juez" nunca puede leerse como "todo bien".
        return 1

    resultados: list[Resultado] = []
    for nombre, modulo in modulos:
        r = Resultado(juez=nombre, descripcion=(modulo.__doc__ or "").strip().splitlines()[0])
        modulo.comprobar(repo, r)
        informar(r, modo=args.modo, en_github=en_github)
        resultados.append(r)

    total_b = sum(len(r.bloqueantes) for r in resultados)
    total_a = sum(len(r.hallazgos) for r in resultados) - total_b
    total_s = sum(len(r.supresiones) for r in resultados)

    if args.resumen:
        Path(args.resumen).write_text(
            resumen_markdown(resultados, modo=args.modo, repo=repo.nombre), encoding="utf-8")
    if args.json_salida:
        Path(args.json_salida).write_text(json.dumps(
            {"repo": repo.nombre, "modo": args.modo, "perfil": args.perfil,
             "bloqueantes": total_b, "avisos": total_a, "supresiones": total_s,
             "resultados": [
                 {"juez": r.juez, "no_evaluado": r.no_evaluado,
                  "supresiones": r.supresiones,
                  "hallazgos": [asdict(h) for h in r.hallazgos]}
                 for r in resultados]},
            ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # Las salidas del job las escribe este script y no un heredoc dentro del
    # YAML: un heredoc anidado en un bloque escalar de YAML depende de la
    # indentación relativa del terminador, se rompe con cualquier reformateo y
    # no se puede probar. Aquí sí hay tests.
    salida_gh = os.environ.get("GITHUB_OUTPUT")
    if salida_gh:
        with open(salida_gh, "a", encoding="utf-8") as fh:
            fh.write(f"bloqueantes={total_b}\n")
            fh.write(f"avisos={total_a}\n")
            fh.write(f"supresiones={total_s}\n")

    print(f"\n{'=' * 78}")
    print(f"{len(modulos)} juez/jueces · {total_b} bloqueante(s) · {total_a} aviso(s) · "
          f"{total_s} supresión(es) · modo {args.modo}")
    print("=" * 78)

    if args.modo == "bloqueante" and total_b:
        return 1
    if args.modo == "advisory" and total_b and en_github:
        # En advisory NO se rompe el build: la flota tiene que poder desplegar
        # sus arreglos urgentes mientras se mide la distancia. Pero el número
        # se publica, para que "advisory" no acabe significando "invisible".
        print(f"::warning::{total_b} hallazgo(s) bloqueante(s) en modo advisory. "
              f"Ver RESUMEN.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
