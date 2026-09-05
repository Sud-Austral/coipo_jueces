#!/usr/bin/env python3
"""j02 — identidad del despliegue: nombre del repositorio y APP_PORT.

Implementa los puntos 1 y 2 de la Guía 8.

  Punto 1. El workflow arma la ruta del servidor con el nombre del repositorio,
  así que ese nombre ES el nombre de la carpeta en `/opt/apps/`. Un repositorio
  en mayúsculas se crea así por defecto y nadie se acuerda de renombrarlo hasta
  que el primer push a `main` ya creó la carpeta.

  Punto 2. `APP_PORT` tiene que ser único por VM: si dos apps comparten puerto,
  el smoke test de una puede dar VERDE contra el `/health` de la otra y el
  despliegue parece correcto estando roto.

LO QUE ESTE JUEZ NO PUEDE COMPROBAR, Y POR QUÉ LO DICE EN VOZ ALTA
  La unicidad del punto 2 es una propiedad de la VM, no del repositorio. Desde
  dentro de un solo repositorio es IMPOSIBLE saber si otro se quedó con el
  puerto. Este juez comprueba lo único que sí es local —que el compose publica
  por `${APP_PORT}` y no cablea un número— y registra la unicidad como NO
  EVALUADA.

  Es deliberado: la alternativa era traerse aquí la tabla de asignación de
  puertos de la flota, y este repositorio es PÚBLICO. Publicar el mapa
  puerto -> aplicación de las VM del Estado para ahorrarse una comprobación
  manual es un mal negocio.

CALIBRACIÓN INVERSA (medida el 2026-09-05)
  `coipo_prensa2`, `coipo_dendroenergia` y `coipo_n8n` están en minúsculas y
  deben salir VERDES. `COIPO_ENTREGA_PLANTA` y `COIPO_USUARIOS` están en
  MAYÚSCULAS y deben salir ROJOS: los dos ya desplegaron, así que su carpeta en
  el servidor lleva el nombre en mayúsculas y renombrar ahora exige tocar la VM.
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

# Nombre valido para `/opt/apps/<nombre>/` y para un hostname: minusculas,
# digitos, guion bajo y guion. El punto queda fuera a proposito.
NOMBRE_VALIDO = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

def _lado_host(valor: object) -> str | None:
    """El lado del HOST de un `ports:`, que es el que colisiona entre apps.

    Se parte por el ULTIMO `:` y no con una expresion regular. La primera
    version usaba `[^":]+` para el lado izquierdo y por eso NUNCA casaba la
    forma correcta —`${APP_PORT:-8080}:8000`—, porque el `:-` del valor por
    defecto la cortaba por la mitad. El efecto era el peor posible: los
    repositorios bien configurados salian verdes sin haber sido examinados, y
    publicar por una variable equivocada era indetectable.
    """
    v = str(valor).strip().strip('"').strip("'")
    izquierda, sep, derecha = v.rpartition(":")
    if not sep or not derecha.isdigit():
        return None  # `8000` a secas: expone al contenedor, no al host
    if izquierda.startswith("${"):
        return izquierda
    # `127.0.0.1:8113:8000` -> el puerto del host es el ultimo trozo.
    return izquierda.rpartition(":")[2] or izquierda


def _ruta_compose(repo: Repo) -> str | None:
    return next((n for n in COMPOSE if repo.existe(n)), None)


def comprobar_nombre(repo: Repo, r: Resultado) -> None:
    """Guía 8, punto 1 — el nombre del repositorio es el de la carpeta del servidor."""
    nombre = repo.nombre
    r.comprobo(f"nombre del repositorio (`{nombre}`)")

    if nombre != nombre.lower():
        r.bloquea(
            "G8-1", "", f"el repositorio se llama `{nombre}`, con mayúsculas",
            "el workflow arma la ruta `/opt/apps/<nombre-del-repo>/` con este "
            "nombre tal cual, así que la carpeta del servidor queda en mayúsculas. "
            "Si el repositorio ya desplegó alguna vez, renombrarlo después deja la "
            "carpeta vieja huérfana en la VM y el `rsync --delete` empieza a "
            "sincronizar contra una ruta nueva y vacía",
            arreglo=f"`gh repo rename {nombre.lower()} --repo <org>/{nombre}` ANTES "
                    f"del primer push a main. Si ya desplegó, hay que renombrar "
                    f"también la carpeta en la VM, y eso no se hace sin avisar: "
                    f"confirmar el nombre final con el responsable primero "
                    f"(Guía 8, punto 1)",
        )
    elif not NOMBRE_VALIDO.match(nombre):
        r.bloquea(
            "G8-1", "",
            f"el nombre `{nombre}` sale de [a-z0-9_-] o no empieza por letra o dígito",
            "se usa como nombre de carpeta y como parte de nombres de contenedor; "
            "un carácter raro rompe el despliegue en un punto que no dice por qué",
            arreglo="renombrar el repositorio a minúsculas, dígitos, `_` y `-`",
        )


def comprobar_puerto(repo: Repo, r: Resultado) -> None:
    """Guía 8, punto 2 — APP_PORT declarado, plausible y no cableado."""
    ruta = _ruta_compose(repo)
    if ruta is None:
        r.no_evaluado.append("sin docker-compose.yml: no hay APP_PORT que verificar")
        return

    texto = repo.texto(ruta) or ""
    try:
        compose = carga_yaml(texto)
    except YamlNoSoportado as e:
        r.no_evaluado.append(f"{ruta}: {e}. No se pudo leer el puerto publicado.")
        return

    r.comprobo(f"APP_PORT publicado ({ruta})")
    servicios = compose.get("services") or {}
    if isinstance(servicios, dict):
        for nombre, s in servicios.items():
            if not isinstance(s, dict):
                continue
            for p in (s.get("ports") or []):
                host = _lado_host(p)
                if host:
                    _juzgar_publicacion(r, ruta, texto, nombre, host)

    # NO se juzga el valor de APP_PORT en `.env.example`. La primera version de
    # este juez avisaba si el numero caia fuera del rango de la flota, y la
    # calibracion la tumbo: `coipo_prensa2` y `coipo_dendroenergia` declaran ahi
    # `APP_PORT=8080` —el mismo default que `${APP_PORT:-8080}`— mientras sus
    # puertos reales son 8101 y 8103, que viven en el `.env` del servidor y
    # nunca pasan por git. Un `.env.example` es un EJEMPLO: exigirle el valor de
    # produccion es pedirle al repositorio que publique la configuracion real.

    # LO QUE NO SE PUEDE COMPROBAR DESDE AQUI. Se dice, no se calla: un juez que
    # se guarda lo que no miro deja creer que lo miro.
    r.no_evaluado.append(
        "unicidad de APP_PORT en la VM: es una propiedad del servidor, no de este "
        "repositorio. Verificar a mano con `sudo ss -tlnp | grep :<puerto>` contra "
        "el registro de puertos antes de desplegar (Guía 8, punto 2)."
    )


def _juzgar_publicacion(r: Resultado, ruta: str, texto: str,
                        servicio: str, host: str) -> None:
    # `${APP_PORT:-8080}` es la forma correcta: el valor real lo pone el `.env`
    # del servidor y el default solo sirve para levantar en local.
    if "${" in host:
        if "APP_PORT" not in host:
            r.bloquea(
                "G8-2", ruta,
                f"el servicio `{servicio}` publica `{host}`, que no es `APP_PORT`",
                "el bootstrap del servidor y el smoke test del despliegue usan "
                "`APP_PORT`; publicar por otra variable significa que el "
                "`curl -sf http://127.0.0.1:$APP_PORT/health` apunta a un puerto "
                "donde no hay nadie, o peor, donde hay otra aplicación",
                linea=numero_de_linea(texto, "ports:"),
                arreglo='publicar `"${APP_PORT:-8080}:8000"`',
            )
        return

    if not host.isdigit():
        return

    n = numero_de_linea(texto, host) or 1
    if (motivo := suprimido(texto.splitlines(), n - 1, "G8-2")):
        r.supresiones.append(f"{ruta}:{n} puerto cableado — {motivo}")
        return
    r.bloquea(
        "G8-2", ruta,
        f"el servicio `{servicio}` cablea el puerto {host} en el compose",
        "el puerto deja de venir del `.env` del servidor, así que reasignarlo exige "
        "editar y desplegar el repositorio. Y si dos apps cablean el mismo número, "
        "el smoke test de una puede dar VERDE contra el `/health` de la otra: el "
        "despliegue parece correcto estando roto",
        linea=n,
        arreglo='publicar `"${APP_PORT:-8080}:8000"` y fijar el número real en el '
                '`.env` del servidor (Guía 8, punto 2)',
    )


def comprobar(repo: Repo, r: Resultado) -> None:
    comprobar_nombre(repo, r)
    comprobar_puerto(repo, r)


if __name__ == "__main__":
    ejecutar("j02", "identidad del despliegue: nombre del repositorio y APP_PORT "
                    "(Guía 8, puntos 1 y 2)", comprobar)
