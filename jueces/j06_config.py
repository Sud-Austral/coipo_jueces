#!/usr/bin/env python3
"""j06 — la superficie de configuración: `.env.example`, nombres y versiones.

El `.env` real vive en el servidor, lo teclea una persona y el pipeline lo
EXCLUYE del rsync. Nadie lo revisa nunca. Eso convierte al `.env.example` en el
único contrato de configuración que se puede verificar, y a cada divergencia
silenciosa en un incidente que solo aparece en producción.

CALIBRACIÓN INVERSA (medida el 2026-09-05)
  coipo_prensa2        -> ROJO. Conviven `SESSION_SECRET` y cinco `SESION_*`, y
                          su CI prueba con python 3.11 mientras sus imágenes se
                          construyen con 3.13 y 3.14.
  COIPO_ENTREGA_PLANTA -> ROJO. Su CI usa node 20 y su Dockerfile node 22.
  COIPO_USUARIOS       -> VERDE. Sin variables de sesión y con el python del CI
                          (3.13) igual al de su imagen.
  coipo_n8n            -> VERDE. Sin Dockerfile y sin versiones que contrastar.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, suprimido  # noqa: E402

PERFILES = ("aplicacion", "encuadre_operativo")

# Las seis que el pipeline da por supuestas. `fastapi-postgresql-conexion.md`
# las fija: cinco para la base, más el puerto que lee el smoke test.
BASE = ("DATABASE_HOST", "DATABASE_PORT", "DATABASE_USER",
        "DATABASE_PASSWORD", "DATABASE_NAME", "APP_PORT")

ASIGNACION_ENV = re.compile(r"^\s*(?P<clave>[A-Z][A-Z0-9_]*)\s*=(?P<valor>.*)$")

FROM_IMAGEN = re.compile(
    r"^\s*FROM\s+(?P<lenguaje>python|node):(?P<version>\d+(?:\.\d+)?)", re.MULTILINE)
VERSION_CI = re.compile(
    r"^\s*(?P<lenguaje>python|node)-version:\s*[\"']?(?P<version>\d+(?:\.\d+)?)",
    re.MULTILINE)


def _archivos_env(repo: Repo) -> list[str]:
    return [r for r in repo.versionados()
            if Path(r).name == ".env" or Path(r).name.startswith(".env.")]


COMPOSE = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")


def es_desplegable(repo: Repo) -> bool:
    """¿Lo despliega el pipeline de la flota?

    El compose es la señal: `rsync` + `docker compose up` + `curl /health` es
    todo lo que hace el reusable, así que sin compose no hay despliegue y no hay
    contrato de `.env` que cumplir.

    Sin esta puerta, el juez exigía un `.env.example` a `coipo_jueces` y a
    `coipo_master_produccion`, que no son aplicaciones sino un repositorio de
    verificadores y otro de doctrina. Una regla aplicada fuera de su dominio es
    un falso positivo, y los falsos positivos son lo que enseña a la gente a
    suprimir al juez.
    """
    return any(repo.existe(c) for c in COMPOSE)


def comprobar_ejemplo(repo: Repo, r: Resultado) -> None:
    if not es_desplegable(repo):
        r.no_evaluado.append(
            "sin docker-compose.yml: este repositorio no lo despliega el pipeline "
            "de la flota, así que no se le exige el contrato de .env")
        return

    if not repo.existe(".env.example"):
        r.bloquea("D-06", "", "no hay `.env.example` en la raíz",
                  "el pipeline aborta si falta /opt/apps/<app>/.env y nadie sabe "
                  "qué variables tiene que llevar; el contenedor arranca sin "
                  "alguna, falla el healthcheck y `docker compose up` se cae "
                  "entero con «dependency failed to start», que no dice la causa",
                  arreglo="crear .env.example con TODAS las variables sin valor "
                          "por defecto, y un placeholder que diga cómo generar "
                          "cada secreto")
        return

    texto = repo.texto(".env.example") or ""
    lineas = texto.splitlines()
    declaradas = {m.group("clave") for l in lineas if (m := ASIGNACION_ENV.match(l))}

    faltan = [v for v in BASE if v not in declaradas]
    if faltan:
        r.bloquea("D-06", ".env.example",
                  f"faltan variables base: {', '.join(faltan)}",
                  "el despliegue supone que existen: sin DATABASE_HOST el backend "
                  "intenta conectar a localhost y falla en silencio, y sin "
                  "APP_PORT el smoke test construye una URL inválida",
                  arreglo="declarar las seis: " + ", ".join(BASE))

    # `APP_PORT` lo extrae el pipeline con `grep '^APP_PORT=' .env | cut -d= -f2`.
    # Comillas o espacios producen `"8125"` y una URL inválida en el smoke test.
    for i, l in enumerate(lineas):
        m = ASIGNACION_ENV.match(l)
        if not m or m.group("clave") != "APP_PORT":
            continue
        valor = m.group("valor")
        if valor != valor.strip() or valor.strip().strip("\"'") != valor.strip():
            r.bloquea("D-06", ".env.example",
                      "`APP_PORT` lleva comillas o espacios alrededor del valor",
                      "el smoke test lo extrae con `cut -d= -f2`, así que "
                      'APP_PORT="8125" produce la URL http://127.0.0.1:"8125"/health '
                      "y el despliegue sale rojo con un error que no se entiende",
                      linea=i + 1, arreglo="escribir APP_PORT=8125 y nada más")

    if "DATABASE_URL" in declaradas:
        r.bloquea("D-06", ".env.example",
                  "`DATABASE_URL` como variable de entorno",
                  "una URL única esconde la contraseña dentro de una cadena que "
                  "acaba en logs y trazas, y rompe la convención que el resto de "
                  "la flota y los scripts de respaldo dan por supuesta",
                  linea=next((i + 1 for i, l in enumerate(lineas)
                              if l.startswith("DATABASE_URL")), None),
                  arreglo="componerla en el código desde las cinco variables (D-06)")


def comprobar_grafia_de_sesion(repo: Repo, r: Resultado) -> None:
    """`SESSION_` y `SESION_` conviviendo en los archivos de entorno.

    Una sola S no rompe nada visible: la aplicación arranca igual, la variable
    simplemente no se lee y toma su valor por defecto. Si esa variable es
    `SESSION_HTTPS_ONLY`, la cookie de sesión viaja SIN el atributo `Secure`
    sobre un sitio HTTPS, y no hay una sola línea en ningún log que lo delate.

    No se juzga el código Python: `COIPO_ENTREGA_PLANTA/backend/app/config.py`
    tiene una tabla ALIAS_ERRONEOS que NOMBRA la grafía mala justamente para
    cazarla al arrancar. Marcar esa tabla sería marcar la defensa.
    """
    con_dos, con_una = {}, {}
    for ruta in _archivos_env(repo):
        for i, l in enumerate(repo.lineas(ruta)):
            m = ASIGNACION_ENV.match(l)
            if not m:
                continue
            clave = m.group("clave")
            if clave.startswith("SESSION_"):
                con_dos.setdefault(clave, (ruta, i + 1))
            elif clave.startswith("SESION_"):
                con_una.setdefault(clave, (ruta, i + 1))

    if not (con_dos and con_una):
        return

    ruta, linea = next(iter(con_una.values()))
    lineas = repo.lineas(ruta)
    if (motivo := suprimido(lineas, linea - 1, "D-08")):
        r.supresiones.append(f"{ruta}:{linea} grafía de sesión — {motivo}")
        return

    r.bloquea("D-08", ruta,
              "conviven las dos grafías: "
              f"{', '.join(sorted(con_dos))} junto a {', '.join(sorted(con_una))}",
              "con dos convenciones activas, escribir SESION_HTTPS_ONLY donde el "
              "código espera SESSION_HTTPS_ONLY hace que la app arranque igual y "
              "que la cookie de sesión viaje sin `Secure` sobre HTTPS; nada en "
              "los logs lo delata",
              linea=linea,
              arreglo="unificar en SESSION_ (dos S) y añadir una tabla de alias "
                      "erróneos que ABORTE el arranque nombrando la correcta")


def comprobar_versiones(repo: Repo, r: Resultado) -> None:
    """Lo que el CI prueba tiene que ser lo que la imagen construye.

    `coipo_prensa2` construye con `python:3.14` y `node:26`, y su CI ejecuta la
    suite con python 3.11 y node 22. Todo lo que el CI declara verde está
    probado sobre un intérprete que no llega nunca a producción.
    """
    de_imagen: dict[str, set[str]] = {}
    for ruta in repo.versionados():
        if Path(ruta).name != "Dockerfile" and not ruta.endswith(".Dockerfile"):
            continue
        for m in FROM_IMAGEN.finditer(repo.texto(ruta) or ""):
            de_imagen.setdefault(m.group("lenguaje"), set()).add(m.group("version"))

    del_ci: dict[str, set[tuple[str, str]]] = {}
    for ruta in repo.versionados():
        if not re.match(r"\.github/workflows/.*\.ya?ml$", ruta):
            continue
        for m in VERSION_CI.finditer(repo.texto(ruta) or ""):
            del_ci.setdefault(m.group("lenguaje"), set()).add((m.group("version"), ruta))

    if not de_imagen:
        r.no_evaluado.append(
            "no hay Dockerfile con `FROM python:` ni `FROM node:`: no hay "
            "versiones que contrastar (normal en un encuadre operativo)")
        return
    if not del_ci:
        r.avisa("D-28", "", "ningún workflow fija la versión de python o node",
                "la suite corre con lo que traiga el runner ese día, que puede "
                "no ser lo que construye la imagen; el día que cambie, nada avisa",
                arreglo="fijar python-version y node-version en el CI, iguales a "
                        "las del Dockerfile")
        return

    for lenguaje, versiones in del_ci.items():
        imagenes = de_imagen.get(lenguaje)
        if not imagenes:
            continue
        for version, ruta in sorted(versiones):
            # `3.1` casaría con `3.13` por prefijo; se compara por componentes.
            partes = version.split(".")
            if any(i.split(".")[:len(partes)] == partes for i in imagenes):
                continue
            r.bloquea("D-28", ruta,
                      f"el CI prueba con {lenguaje} {version} y ninguna imagen se "
                      f"construye con esa versión (las imágenes usan "
                      f"{', '.join(sorted(imagenes))})",
                      "todo lo que el CI declara verde está probado sobre un "
                      "intérprete que no llega a producción; el fallo aparece "
                      "solo en el servidor y sin ninguna pista de por qué",
                      arreglo=f"igualar la versión del CI a la del Dockerfile")

    for lenguaje, versiones in de_imagen.items():
        if len(versiones) > 1:
            r.avisa("D-28", "",
                    f"las imágenes de este repositorio usan varias versiones de "
                    f"{lenguaje}: {', '.join(sorted(versiones))}",
                    "un sub-stack que se queda atrás recibe parches de seguridad "
                    "distintos que el resto, y nadie lleva la cuenta",
                    arreglo="una sola versión por lenguaje y por repositorio")


def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.tiene_git():
        r.no_evaluado.append(f"{repo.raiz} no es un repositorio git")
        return
    comprobar_ejemplo(repo, r)
    comprobar_grafia_de_sesion(repo, r)
    comprobar_versiones(repo, r)


if __name__ == "__main__":
    ejecutar("j06", "superficie de configuración: .env.example, grafías y versiones "
                    "(D-06, D-08, D-28)", comprobar)
