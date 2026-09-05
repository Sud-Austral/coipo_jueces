#!/usr/bin/env python3
"""j01 — el sobre de despliegue: compose, contexto de build y nginx interno.

Verifica el contrato que el pipeline de la flota da por supuesto y que hoy no
comprueba nadie. Todas las reglas vienen de un fallo que ya ocurrió.

CALIBRACIÓN INVERSA (medida el 2026-09-05)
  `coipo_n8n` es la referencia y debe salir VERDE: es el único compose de la
  flota con `mem_limit` en los cuatro servicios, healthcheck en casi todos,
  guards `${VAR:?mensaje}` en cada secreto, volúmenes con nombre y `resolver`
  en el nginx interno. Si este juez pone rojo a n8n, el juez está mal.

  Los otros tres deben salir ROJO, y por defectos reales y distintos:
    COIPO_ENTREGA_PLANTA -> sin `.dockerignore` en la raíz con `context: .`
    COIPO_USUARIOS       -> `.dockerignore` que no excluye `.env`
    coipo_prensa2        -> `proxy_pass` con nombre literal en el nginx interno

PERFILES
  Un proyecto `encuadre_operativo` (software de terceros: el patrón coipo_n8n)
  puede saltarse los tests y el Dockerfile, pero NO el sobre de despliegue: un
  solo `ports:`, `/health` que responda, `.env` fuera del contexto de build.
  Por eso este juez corre en los dos perfiles.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    Repo, Resultado, YamlNoSoportado, carga_yaml, ejecutar, numero_de_linea, suprimido,
)

PERFILES = ("aplicacion", "encuadre_operativo")

COMPOSE = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")

# Motores de base de datos que NUNCA van en el compose de una app: el Postgres
# de esta flota es COMPARTIDO, vive fuera de Docker en otra máquina y lo
# administra otro equipo.
IMAGENES_DE_BASE = re.compile(r"^(postgres|mysql|mariadb|mongo|mssql|oracle)", re.IGNORECASE)

# `proxy_pass http://backend:8000/` — nombre literal de servicio de Docker.
# Se excluyen las IP (el vhost del host proxea a 127.0.0.1:APP_PORT, que es
# correcto) y las variables (que son justamente el arreglo).
PROXY_LITERAL = re.compile(
    r"^\s*proxy_pass\s+https?://(?P<destino>[a-zA-Z][a-zA-Z0-9_.-]*)(?::\d+)?", re.MULTILINE
)
RESOLVER = re.compile(r"^\s*resolver\s+", re.MULTILINE)

# Rutas donde vive el nginx que corre DENTRO del contenedor `app`. El vhost del
# host (ops/nginx-host/, INSUMO_PRODUCCION/) es otra cosa y no se juzga aquí.
NGINX_INTERNO = ("frontend/nginx.conf", "ops/nginx/app.conf", "nginx/app.conf",
                 "nginx.conf", "web/nginx.conf")

EXCLUYE_ENV = {".env", ".env*", "/.env", "**/.env", ".env.*", "*.env"}


# --------------------------------------------------------------------------


def _ruta_compose(repo: Repo) -> str | None:
    return next((c for c in COMPOSE if repo.existe(c)), None)


def _servicios(compose: dict) -> dict:
    s = compose.get("services")
    return s if isinstance(s, dict) else {}


def _contexto_de_build(servicio: dict) -> str | None:
    """`build:` puede ser una cadena o un mapa. Devuelve el context, o None."""
    b = servicio.get("build")
    if isinstance(b, str):
        return b
    if isinstance(b, dict):
        c = b.get("context")
        return c if isinstance(c, str) else "."
    return None


def comprobar_compose(repo: Repo, r: Resultado) -> None:
    ruta = _ruta_compose(repo)
    if ruta is None:
        r.no_evaluado.append(
            "no hay docker-compose.yml en la raíz: este repositorio no despliega "
            "con el pipeline de la flota, o lo hace de una forma que este juez no conoce"
        )
        return

    texto = repo.texto(ruta) or ""
    try:
        compose = carga_yaml(texto)
    except YamlNoSoportado as e:
        # Ruidoso a propósito. Un compose que el parser no entiende NO se
        # declara correcto: se declara no evaluado, y alguien tiene que mirarlo.
        r.no_evaluado.append(f"{ruta}: {e}. El compose no se pudo verificar.")
        return

    r.comprobo(f"docker-compose ({ruta})")
    if "version" in compose:
        r.bloquea("G8-7", ruta, "el compose declara `version:`",
                  "Compose v2+ la ignora y emite un aviso en cada `up`; el aviso "
                  "entrena a la gente a no leer la salida del despliegue",
                  linea=numero_de_linea(texto, "version:"),
                  arreglo="borrar la línea")

    servicios = _servicios(compose)
    if not servicios:
        r.bloquea("G8-7", ruta, "el compose no define ningún servicio",
                  "`docker compose up` no levanta nada y el smoke test recibe "
                  "connection-refused")
        return

    # ---- exactamente un servicio publica puerto ----
    con_puerto = [n for n, s in servicios.items() if isinstance(s, dict) and s.get("ports")]
    if len(con_puerto) == 0:
        r.bloquea("G8-7", ruta, "ningún servicio publica un puerto al host",
                  "nada es alcanzable desde el nginx del servidor: el smoke test "
                  "`curl -sf http://127.0.0.1:$APP_PORT/health` no puede pasar",
                  arreglo="publicar `${APP_PORT:-8080}:8000` en el servicio `app` "
                          "y solo en ese")
    elif len(con_puerto) > 1:
        r.bloquea("G8-7", ruta,
                  f"{len(con_puerto)} servicios publican puerto: {', '.join(con_puerto)}",
                  "más superficie expuesta de la que el registro de puertos "
                  "conoce, y un segundo puerto sin registrar puede colisionar con "
                  "otra app de la VM sin que nada avise",
                  linea=numero_de_linea(texto, "ports:"),
                  arreglo="solo el servicio `app` publica puerto; el backend habla "
                          "por la red interna de Docker")

    # ---- la base de datos no vive aquí ----
    for nombre, s in servicios.items():
        if not isinstance(s, dict):
            continue
        imagen = s.get("image")
        if isinstance(imagen, str) and IMAGENES_DE_BASE.match(imagen):
            r.bloquea("DK-3", ruta,
                      f"el servicio `{nombre}` levanta un motor de base de datos",
                      "el Postgres de esta flota es compartido, vive fuera de "
                      "Docker y lo administra otro equipo; una base propia en el "
                      "compose queda fuera de los respaldos y de la retención legal",
                      linea=numero_de_linea(texto, f"image: {imagen}"),
                      arreglo="conectar al Postgres compartido con las cinco "
                              "variables DATABASE_* (Guía 8, punto 3)")

    # ---- avisos de robustez, uno por servicio ----
    for nombre, s in servicios.items():
        if not isinstance(s, dict):
            continue
        if "healthcheck" not in s and "image" not in s:
            r.avisa("G8-7", ruta, f"el servicio `{nombre}` no tiene healthcheck",
                    "`docker compose ps` lo da por sano pase lo que pase; "
                    "coipo_cabania lleva días `unhealthy` sin que nadie se entere",
                    arreglo="añadir un healthcheck, aunque sea de proceso vivo")
        if "mem_limit" not in s and "deploy" not in s:
            r.avisa("OPS-1", ruta, f"el servicio `{nombre}` no declara `mem_limit`",
                    "un servicio que se desboca se lleva por delante a las demás "
                    "apps de la misma VM",
                    arreglo="MEDIR la RAM de la VM antes de fijar el valor: un "
                            "límite mal puesto es un OOM kill silencioso, que es "
                            "peor que no tenerlo")
        if "restart" not in s:
            r.avisa("G8-7", ruta, f"el servicio `{nombre}` no declara `restart:`",
                    "tras un reinicio del servidor el servicio no vuelve solo",
                    arreglo="`restart: unless-stopped`, salvo en tareas de un "
                            "solo tiro, donde `restart: \"no\"` es lo correcto")


def comprobar_contexto_de_build(repo: Repo, r: Resultado) -> None:
    """`.dockerignore` cuando el contexto de build es la raíz del repositorio.

    `COIPO_ENTREGA_PLANTA` construye sus tres imágenes con `context: .` y NO
    tiene `.dockerignore` en la raíz: el repositorio entero —`.git`, `docs/`,
    `node_modules/`, `dist/`, `INSUMO_*` y un MP4 de 21 MB— viaja al daemon en
    cada build de cada imagen. Y con él, cualquier `.env` presente en el disco
    del servidor.
    """
    ruta = _ruta_compose(repo)
    if ruta is None:
        return
    try:
        compose = carga_yaml(repo.texto(ruta) or "")
    except YamlNoSoportado:
        return

    contextos = {
        _contexto_de_build(s)
        for s in _servicios(compose).values()
        if isinstance(s, dict) and _contexto_de_build(s) is not None
    }
    if not contextos:
        return  # no se construye nada: un encuadre operativo con `image:` a secas

    r.comprobo(".dockerignore frente al contexto de build")
    raiz_en_contexto = any(c in (".", "./") for c in contextos)
    if not repo.existe(".dockerignore"):
        if raiz_en_contexto:
            r.bloquea("DK-4", "", "falta `.dockerignore` en la raíz y hay builds con `context: .`",
                      "el repositorio entero viaja al daemon en cada build —incluido "
                      "el `.git` y cualquier `.env` del servidor— y lo que entra al "
                      "contexto puede acabar en una capa de la imagen",
                      arreglo="crear .dockerignore con al menos .git, .env, "
                              "node_modules, dist e INSUMO_*")
        else:
            r.avisa("DK-4", "", "no hay `.dockerignore` en la raíz",
                    "los builds con contexto acotado no sufren hoy, pero el primer "
                    "`context: .` que alguien añada lo hará sin avisar")
        return

    lineas = repo.lineas(".dockerignore")
    patrones = {l.strip() for l in lineas if l.strip() and not l.startswith("#")}
    if not (patrones & EXCLUYE_ENV):
        r.bloquea("DK-4", ".dockerignore", "el `.dockerignore` no excluye `.env`",
                  "el archivo con las credenciales de producción entra en el "
                  "contexto de build; un `COPY . .` lo deja dentro de la imagen, "
                  "donde sobrevive a cualquier borrado posterior",
                  arreglo="añadir una línea `.env`")


def comprobar_nginx_interno(repo: Repo, r: Resultado) -> None:
    """`proxy_pass` con nombre literal resuelve UNA sola vez, al cargar nginx.

    Si el contenedor del backend cambia de IP —cualquier `up -d` que lo
    recree—, nginx sigue apuntando a la anterior: 502 con el backend
    perfectamente sano al lado y `docker compose ps` todo en verde. Ya rompió un
    despliegue a uat (`exit 22` en el smoke test). La corrección —`resolver
    127.0.0.11` más el upstream en una variable— existe hoy solo en
    COIPO_USUARIOS y en coipo_n8n; prensa2 y ENTREGA_PLANTA siguen expuestos.
    """
    for ruta in NGINX_INTERNO:
        texto = repo.texto(ruta)
        if texto is None:
            continue
        r.comprobo(f"nginx interno ({ruta})")
        lineas = texto.splitlines()
        tiene_resolver = bool(RESOLVER.search(texto))
        for m in PROXY_LITERAL.finditer(texto):
            destino = m.group("destino")
            if destino in ("localhost",) or tiene_resolver:
                continue
            n = texto[:m.start()].count("\n")
            if (motivo := suprimido(lineas, n, "NG-1")):
                r.supresiones.append(f"{ruta}:{n + 1} proxy_pass literal — {motivo}")
                continue
            r.bloquea("NG-1", ruta,
                      f"`proxy_pass` al nombre literal `{destino}` sin `resolver`",
                      "nginx resuelve el nombre una sola vez al arrancar; cuando el "
                      "contenedor de destino se recrea con otra IP, responde 502 con "
                      "el backend sano al lado y el compose en verde",
                      linea=n + 1,
                      arreglo="añadir `resolver 127.0.0.11 valid=10s ipv6=off;` y "
                              f"pasar el upstream por variable: "
                              f"`set $destino {destino}; proxy_pass http://$destino:8000$request_uri;`")


def comprobar(repo: Repo, r: Resultado) -> None:
    comprobar_compose(repo, r)
    comprobar_contexto_de_build(repo, r)
    comprobar_nginx_interno(repo, r)


if __name__ == "__main__":
    ejecutar("j01", "sobre de despliegue: compose, contexto de build y nginx (Guía 8 punto 7; DOCKER.md; nginx)",
             comprobar)
