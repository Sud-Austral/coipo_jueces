#!/usr/bin/env python3
"""j08 — qué se ignora y qué llega al servidor.

Implementa los puntos 8 y 10 de la Guía 8. Los dos hablan de lo mismo visto
desde dos lados: qué archivos existen en el repositorio y cuáles de ellos acaban
en `/opt/apps/<app>/` de la VM.

El despliegue sincroniza con:

    rsync -a --delete --exclude='/.git' --exclude='/.env' --exclude='/data/'

Los tres patrones están ANCLADOS a la raíz, y eso cambió en agosto de 2026. Las
consecuencias son concretas:

  - Un `.env` en un subdirectorio (`web/.env`, `frontend/.env`) YA NO está
    excluido: **llega al servidor**. Antes no llegaba.
  - Un `data/` anidado (`frontend/src/data/`) ahora SÍ se sincroniza, y también
    se BORRA como cualquier otro archivo.
  - Lo que esté versionado dentro del `data/` de la raíz no llega nunca: está
    excluido en los dos sentidos.

Y el punto 8 añade el error de `.gitignore` que la guía dice que ya ocurrió y
hubo que corregir: escribir `data/` sin barra inicial ignora CUALQUIER carpeta
llamada `data` a cualquier profundidad, incluida `frontend/src/data/`, que es
donde suele vivir un catálogo generado que sí se quiere versionar.

CALIBRACIÓN INVERSA (medida el 2026-09-05, sobre `git ls-files`)
  COIPO_ENTREGA_PLANTA -> VERDE: `.gitignore` con `/data/` anclado.
  coipo_prensa2        -> VERDE.
  coipo_dendroenergia  -> VERDE.
  coipo_n8n            -> VERDE: `/.env` anclado.
  COIPO_USUARIOS       -> ROJO doble: `data/` SIN anclar, y `.env` versionado
                          pese a figurar en el `.gitignore` —porque
                          `.gitignore` no se aplica a lo que ya está trackeado.
  COIPO_DIRECTORIO     -> ROJO: versiona `frontend/.env`, que desde agosto de
                          2026 llega al servidor.
  coipo_seguimiento_madera y coipo_vista_catastro -> AVISO: versionan archivos
                          dentro del `data/` de la raíz, que el rsync excluye:
                          esos archivos NO existen en el servidor.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, suprimido  # noqa: E402

PERFILES = ("aplicacion", "encuadre_operativo")

# Lo que el reusable excluye, anclado a la raiz del repositorio.
EXCLUIDO_ANCLADO = ("/.git", "/.env", "/data/")

# `.env`, `web/.env`, `frontend/.env`: el archivo de secretos por convencion.
ENV_EXACTO = re.compile(r"(^|/)\.env$")
# `.env.production`, `.env.local`: convencion de Vite/Next. Suelen llevar
# configuracion de build y no secretos, asi que avisan en vez de bloquear.
ENV_VARIANTE = re.compile(r"(^|/)\.env\.[A-Za-z0-9_-]+$")
ENV_EJEMPLO = re.compile(r"(^|/)\.env\.(example|sample|template|dist)$")

EN_DATA_RAIZ = re.compile(r"^data/")


def _entradas_gitignore(repo: Repo) -> list[tuple[int, str]]:
    salida = []
    for i, linea in enumerate(repo.lineas(".gitignore"), start=1):
        limpia = linea.strip()
        if limpia and not limpia.startswith("#"):
            salida.append((i, limpia))
    return salida


def comprobar_gitignore(repo: Repo, r: Resultado) -> None:
    """Guía 8, punto 8 — las rutas van ANCLADAS con barra inicial."""
    if not repo.existe(".gitignore"):
        # La severidad la fija lo que hay en juego, no la regla. Un repositorio
        # que despliega va a tener un `.env` con credenciales de produccion en el
        # servidor; uno que no despliega todavia, no. Bloquear a los dos por igual
        # convierte al juez en ruido justo en los repositorios donde no importa.
        desplegable = any(repo.existe(n) for n in
                          ("docker-compose.yml", "docker-compose.yaml",
                           "compose.yml", "compose.yaml"))
        anota = r.bloquea if desplegable else r.avisa
        anota(
            "G8-8", "", "no hay `.gitignore`",
            "nada impide que el `.env` de desarrollo, un volcado de base de datos "
            "o un directorio de datos acaben versionados de un `git add -A`"
            + (". Y este repositorio tiene compose, así que en el servidor va a "
               "existir un `.env` con credenciales de producción" if desplegable else ""),
            arreglo="crear `.gitignore` con al menos `/.env` y `/data/`",
        )
        return

    entradas = _entradas_gitignore(repo)
    r.comprobo(".gitignore: rutas ancladas")
    lineas = repo.lineas(".gitignore")
    patrones = {p for _, p in entradas}

    if not ({".env", "/.env", ".env*", "*.env"} & patrones):
        r.bloquea(
            "G8-8", ".gitignore", "`.env` no está ignorado",
            "el `.env` real lo crea el bootstrap del servidor y nunca se commitea; "
            "sin esta línea, el primer `git add -A` de alguien con prisa publica las "
            "credenciales de producción en el historial, de donde ya no salen",
            arreglo="añadir `/.env`, anclado a la raíz",
        )

    # El error documentado: `data/` sin barra inicial casa a CUALQUIER profundidad.
    for n, patron in entradas:
        if patron.rstrip("/") != "data" or patron.startswith("/"):
            continue
        if (motivo := suprimido(lineas, n - 1, "G8-8")):
            r.supresiones.append(f".gitignore:{n} `{patron}` sin anclar — {motivo}")
            continue
        anidados = sorted(
            str(p.relative_to(repo.raiz)).replace("\\", "/")
            for p in repo.raiz.glob("*/**/data")
            if p.is_dir() and ".git" not in p.parts
        )[:3]
        evidencia = (f" En este repositorio ya existe {', '.join(anidados)}."
                     if anidados else "")
        r.bloquea(
            "G8-8", ".gitignore", f"`{patron}` no está anclado con barra inicial",
            "git ignora CUALQUIER carpeta llamada `data` a cualquier profundidad, "
            "incluida `frontend/src/data/`, que es donde suele vivir un catálogo "
            "generado que sí hay que versionar. El archivo desaparece del "
            "repositorio sin error, y en el servidor la aplicación arranca sin "
            "él." + evidencia,
            linea=n,
            arreglo="escribir `/data/`, con barra inicial (Guía 8, punto 8)",
        )


def comprobar_lo_que_viaja(repo: Repo, r: Resultado) -> None:
    """Guía 8, punto 10 — qué sincroniza el rsync y qué no."""
    versionados = repo.versionados()
    if not versionados:
        r.no_evaluado.append(
            "`git ls-files` no devolvió nada: sin la lista de archivos versionados "
            "no se puede saber qué llega al servidor.")
        return

    r.comprobo(f"archivos versionados frente al rsync anclado ({len(versionados)})")

    for ruta in versionados:
        if ENV_EJEMPLO.search(ruta):
            continue

        if ENV_EXACTO.search(ruta):
            if ruta == ".env":
                # En la raiz el rsync SI lo excluye, asi que no llega al
                # servidor. El problema es otro y es peor: esta en git.
                r.bloquea(
                    "G8-8", ruta, "`.env` está versionado",
                    "figure o no en el `.gitignore`, git no ignora lo que ya está "
                    "trackeado: el archivo sigue en el repositorio y en todo su "
                    "historial, accesible para cualquiera que tenga acceso de "
                    "lectura, y borrarlo en un commit nuevo no lo saca del pasado",
                    arreglo="`git rm --cached .env`, rotar TODO lo que contenía "
                            "—porque hay que darlo por comprometido— y solo después "
                            "purgar el historial",
                )
            else:
                r.bloquea(
                    "G8-10", ruta, f"`{ruta}` es un `.env` en un subdirectorio",
                    "el rsync excluye `/.env` ANCLADO a la raíz, así que este "
                    "archivo NO está excluido y llega al servidor en cada "
                    "despliegue. Antes de agosto de 2026 no llegaba, de modo que "
                    "un repositorio escrito antes de ese cambio lo da por local",
                    arreglo="sacarlo de git (`git rm --cached`), añadirlo al "
                            "`.gitignore`, y si tenía valores reales, rotarlos "
                            "(Guía 8, punto 10)",
                )

        elif ENV_VARIANTE.search(ruta):
            r.avisa(
                "G8-10", ruta, f"`{ruta}` viaja al servidor en cada despliegue",
                "el rsync solo excluye `/.env` de la raíz. Un `.env.production` de "
                "Vite suele llevar configuración de build y no secretos, pero "
                "cualquier token que tenga queda en el disco del servidor y en el "
                "repositorio",
                arreglo="comprobar que no lleva ningún valor real. Si lo lleva, "
                        "sacarlo de git y rotarlo",
            )

        elif EN_DATA_RAIZ.match(ruta):
            r.avisa(
                "G8-10", ruta, f"`{ruta}` está versionado dentro del `data/` de la raíz",
                "el rsync excluye `/data/` en los dos sentidos, así que este archivo "
                "NUNCA llega al servidor. Si la aplicación lo necesita en tiempo de "
                "ejecución, en producción no está y el fallo aparece lejos de aquí",
                arreglo="si hace falta en runtime, moverlo fuera de `data/` o "
                        "copiarlo en el bootstrap del servidor. Si es un insumo que "
                        "solo se usa en desarrollo, dejarlo donde está y anotarlo",
            )


def comprobar(repo: Repo, r: Resultado) -> None:
    comprobar_gitignore(repo, r)
    comprobar_lo_que_viaja(repo, r)


if __name__ == "__main__":
    ejecutar("j08", "`.gitignore` anclado y qué llega al servidor "
                    "(Guía 8, puntos 8 y 10)", comprobar)
