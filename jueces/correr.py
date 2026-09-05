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
        "| Juez | Veredicto | Comprobó | Bloquea | Avisa | Supresiones |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in resultados:
        b = len(r.bloqueantes)
        a = len(r.hallazgos) - b
        icono = {"OK": "🟢 OK", "HALLAZGOS": "🔴 HALLAZGOS",
                 "SIN_EVALUAR": "⚪ SIN EVALUAR",
                 "NO_APLICA": "➖ NO APLICA"}[r.veredicto]
        lineas.append(f"| `{r.juez}` | {icono} | {len(r.comprobado)} | {b} | {a} "
                      f"| {len(r.supresiones)} |")
    if any(r.veredicto == "SIN_EVALUAR" for r in resultados):
        lineas += ["", "> **SIN EVALUAR no es un aprobado.** Ese juez no encontró nada "
                       "que comprobar en este repositorio; cero hallazgos ahí no "
                       "significa que esté conforme."]

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

    n_a = [(r.juez, n) for r in resultados for n in r.no_aplica]
    if n_a:
        lineas += ["", "## No aplica", "",
                   "El `[N/A]` de la Guía 8: se miró y aquí no corresponde. Lo "
                   "declara el juez desde la evidencia, nunca el repositorio.", ""]
        lineas += [f"- `{j}` — {n}" for j, n in n_a]

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

    disponibles = [n for n, _ in descubrir(AQUI, args.perfil, [])]
    # Un --jueces que no casa con nada NO es "el perfil no tiene jueces". Decirlo
    # asi manda a revisar el perfil cuando el error es un id mal escrito
    # (`j11_salud` en vez de `j11`), y eso cuesta media hora de CI.
    desconocidos = [x for x in solo if x not in disponibles]
    if desconocidos:
        aviso = (f"--jueces nombra {', '.join(desconocidos)}, que no existe(n) "
                 f"para el perfil '{args.perfil}'. Se espera el id corto del juez "
                 f"(p. ej. 'j11', no 'j11_salud'). Disponibles: "
                 f"{', '.join(disponibles) or 'ninguno'}")
        print(f"::error::{aviso}" if en_github else f"[jueces] {aviso}")
        return 1

    modulos = descubrir(AQUI, args.perfil, solo)
    if not modulos:
        aviso = (f"ningún juez aplica al perfil '{args.perfil}'. "
                 f"Jueces del perfil: {', '.join(disponibles) or 'ninguno'}")
        print(f"::error::{aviso}" if en_github else f"[jueces] {aviso}")
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
    total_c = sum(len(r.comprobado) for r in resultados)
    sin_evaluar = [r.juez for r in resultados if r.veredicto == "SIN_EVALUAR"]
    todo_na = all(r.veredicto == "NO_APLICA" for r in resultados)

    if args.resumen:
        Path(args.resumen).write_text(
            resumen_markdown(resultados, modo=args.modo, repo=repo.nombre), encoding="utf-8")
    if args.json_salida:
        Path(args.json_salida).write_text(json.dumps(
            {"repo": repo.nombre, "modo": args.modo, "perfil": args.perfil,
             "bloqueantes": total_b, "avisos": total_a, "supresiones": total_s,
             "resultados": [
                 {"juez": r.juez, "veredicto": r.veredicto,
                  "comprobado": r.comprobado, "no_evaluado": r.no_evaluado,
                  "no_aplica": r.no_aplica,
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
    print(f"{len(modulos)} juez/jueces · {total_c} comprobación(es) · {total_b} bloqueante(s) · "
          f"{total_a} aviso(s) · {total_s} supresión(es) · modo {args.modo}")
    if sin_evaluar:
        print(f"SIN EVALUAR: {', '.join(sin_evaluar)} — no comprobaron nada. "
              f"Cero hallazgos ahí NO significa conforme.")
    print("=" * 78)

    if args.modo == "bloqueante" and total_b:
        return 1

    # CERO COMPROBACIONES TAMBIÉN ES UN FALLO.
    #
    # Es la lección de COIPO_PDF_EXCEL, y en esta flota costó meses: un
    # verificador que contaba comparaciones FALLIDAS daba «todos los totales
    # cuadran» cuando el número de comparaciones era cero, y una columna salió
    # en 0 para los 3.610 trabajadores sin que nadie lo notara.
    #
    # El modo de fallo equivalente aquí: los jueces no encuentran nada que
    # comprobar —porque el repositorio tiene otra forma, o porque un cambio
    # rompió la detección— y el gate sale verde habiendo verificado NADA. Un
    # repositorio que no es una aplicación puede tener jueces SIN_EVALUAR y eso
    # es correcto; lo que nunca puede pasar es que NINGUNO haya comprobado algo.
    #
    # LA EXCEPCIÓN, Y ES ESTRECHA A PROPÓSITO: si todos los jueces que corrieron
    # dijeron NO_APLICA, cero comprobaciones es la respuesta honesta y no un
    # fallo de detección. Pasa al correr un solo juez a mano —`--jueces j05`
    # sobre una app de mismo origen, que legítimamente no tiene CORS—. En el CI
    # corren todos, así que basta con que UNO compruebe algo para que esta rama
    # no se active.
    if not total_c and not todo_na:
        aviso = ("ningún juez comprobó nada: un gate que no verifica no aprueba. "
                 "Revisa el perfil, o si el repositorio tiene una forma que los "
                 "jueces no reconocen.")
        print(f"::error::{aviso}" if en_github else f"[jueces] {aviso}")
        return 1

    # El PERFIL es una declaración, y obliga.
    #
    # `perfil: aplicacion` afirma que este repositorio es una app de la flota:
    # tiene compose, tiene `.env.example`, despliega por el pipeline. Si un juez
    # que verifica precisamente eso no encuentra NADA que comprobar, solo hay dos
    # explicaciones y las dos son un fallo: o el repositorio no es lo que declara,
    # o algo rompió la detección del juez. Dejarlo pasar en verde es el caso
    # «cero de cero cuadra» con otro disfraz.
    #
    # Un `encuadre_operativo` (software de terceros) SÍ puede tener jueces sin
    # evaluar —no tiene Dockerfile ni tests— y por eso la regla no le aplica.
    if args.modo == "bloqueante" and args.perfil == "aplicacion" and sin_evaluar:
        aviso = (f"perfil 'aplicacion' pero {', '.join(sin_evaluar)} no encontró nada "
                 f"que comprobar. O el repositorio no es una aplicación de la flota, "
                 f"o la detección del juez está rota. Un gate no aprueba lo que no miró.")
        print(f"::error::{aviso}" if en_github else f"[jueces] {aviso}")
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
