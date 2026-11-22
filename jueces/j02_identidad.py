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
  deben salir VERDES. `COIPO_ENTREGA_PLANTA` y `COIPO_USUARIOS` estaban en
  MAYÚSCULAS y debían salir ROJOS.

  CORRECCIÓN DEL 2026-11-22. El nombre que se juzga es el del REMOTO `origin`
  (`Repo.nombre`), no el de la carpeta: el despliegue usa
  `github.event.repository.name`. `COIPO_USUARIOS` ya se llama `coipo_usuarios`
  en GitHub; su clon local seguía en una carpeta en mayúsculas y salía rojo por
  un defecto del juez, no del repositorio. En el CI no cambia nada: la carpeta
  del checkout se llama como el repositorio.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    Repo,
    Resultado,
    YamlNoSoportado,
    carga_yaml,
    ejecutar,
    numero_de_linea,
    suprimido,
)

PERFILES = ("aplicacion", "encuadre_operativo")

# Qué compose hay en la raíz lo dice `Repo.compose()` de comun.py: era una de cuatro copias.

# Nombre valido para `/opt/apps/<nombre>/` y para un hostname: minusculas,
# digitos, guion bajo y guion. El punto queda fuera a proposito.
NOMBRE_VALIDO = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

PROTOCOLO = re.compile(r"/(?:tcp|udp|sctp)$", re.IGNORECASE)
# `${NOMBRE}`, `${NOMBRE:-x}`, `${NOMBRE:?mensaje}`, `${NOMBRE-x}`... y `$NOMBRE`. El
# nombre es lo que va ANTES del modificador; el mensaje de una guarda no es la variable.
# El resto, hasta la última llave, puede llevar otra variable anidada como valor por
# defecto: `${APP_PORT:-${PUERTO_PUBLICADO:-3000}}` (coipo_meteodmc) publica APP_PORT.
VARIABLE = re.compile(
    r"^\$(?:\{(?P<llaves>[A-Za-z_][A-Za-z0-9_]*)(?:[:?\-+=].*)?\}"
    r"|(?P<suelta>[A-Za-z_][A-Za-z0-9_]*))$"
)


def _trozos(spec: str) -> list[str]:
    """`spec` partido por los `:` que NO están dentro de `${...}` ni de `[...]` (IPv6)."""
    trozos, actual, profundidad = [], [], 0
    for i, ch in enumerate(spec):
        if ch in "{[" and (ch == "[" or spec[i - 1 : i] == "$"):
            profundidad += 1
        elif ch in "}]" and profundidad:
            profundidad -= 1
        elif ch == ":" and not profundidad:
            trozos.append("".join(actual))
            actual = []
            continue
        actual.append(ch)
    trozos.append("".join(actual))
    return trozos


def _lado_host(valor: object) -> str | None:
    """El lado del HOST de un `ports:`, que es el que colisiona entre apps.

    La primera versión usaba `[^":]+` para el lado izquierdo y por eso NUNCA casaba
    la forma correcta —`${APP_PORT:-8080}:8000`—: el `:-` del valor por defecto la
    cortaba por la mitad, y los repositorios bien configurados salían verdes sin
    haber sido examinados. La segunda partía por el ÚLTIMO `:` y luego por el último
    `:` del resto, y con una guarda `:?` volvía a cortar dentro de la variable: la
    línea que siembra la fábrica, `127.0.0.1:${APP_PORT:?falta APP_PORT en el .env
    del servidor}:8000`, daba `?falta APP_PORT en el .env del servidor}`, que ni se
    juzgaba (2026-11-21). Ahora se parte sólo por los `:` de fuera de `${...}`:
    `[IP:]HOST:CONTENEDOR[/protocolo]`.
    """
    v = PROTOCOLO.sub("", str(valor).strip().strip('"').strip("'"))
    trozos = _trozos(v)
    if len(trozos) < 2 or not trozos[-1].isdigit():
        return None  # `8000` a secas: expone al contenedor, no al host
    return trozos[-2] or None


def _variable(host: str) -> str | None:
    """El NOMBRE de la variable con que se publica (`APP_PORT`), o None si no es una."""
    m = VARIABLE.match(host.strip())
    return (m.group("llaves") or m.group("suelta")) if m else None


def comprobar_nombre(repo: Repo, r: Resultado) -> None:
    """Guía 8, punto 1 — el nombre del repositorio es el de la carpeta del servidor."""
    nombre = repo.nombre
    r.comprobo(f"nombre del repositorio (`{nombre}`)")

    if nombre != nombre.lower():
        r.bloquea(
            "G8-1",
            "",
            f"el repositorio se llama `{nombre}`, con mayúsculas",
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
            "G8-1",
            "",
            f"el nombre `{nombre}` sale de [a-z0-9_-] o no empieza por letra o dígito",
            "se usa como nombre de carpeta y como parte de nombres de contenedor; "
            "un carácter raro rompe el despliegue en un punto que no dice por qué",
            arreglo="renombrar el repositorio a minúsculas, dígitos, `_` y `-`",
        )


def comprobar_puerto(repo: Repo, r: Resultado) -> None:
    """Guía 8, punto 2 — APP_PORT declarado, plausible y no cableado."""
    ruta = repo.compose()
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
            for p in s.get("ports") or []:
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


def _juzgar_publicacion(r: Resultado, ruta: str, texto: str, servicio: str, host: str) -> None:
    # `${APP_PORT:-8080}` es la forma correcta: el valor real lo pone el `.env`
    # del servidor y el default solo sirve para levantar en local. Se compara el
    # NOMBRE de la variable, no el texto: `${PUERTO:?defina APP_PORT}` es PUERTO.
    if "$" in host:
        if _variable(host) != "APP_PORT":
            r.bloquea(
                "G8-2",
                ruta,
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
    if motivo := suprimido(texto.splitlines(), n - 1, "G8-2"):
        r.supresiones.append(f"{ruta}:{n} puerto cableado — {motivo}")
        return
    r.bloquea(
        "G8-2",
        ruta,
        f"el servicio `{servicio}` cablea el puerto {host} en el compose",
        "el puerto deja de venir del `.env` del servidor, así que reasignarlo exige "
        "editar y desplegar el repositorio. Y si dos apps cablean el mismo número, "
        "el smoke test de una puede dar VERDE contra el `/health` de la otra: el "
        "despliegue parece correcto estando roto",
        linea=n,
        arreglo='publicar `"${APP_PORT:-8080}:8000"` y fijar el número real en el '
        "`.env` del servidor (Guía 8, punto 2)",
    )


def comprobar(repo: Repo, r: Resultado) -> None:
    comprobar_nombre(repo, r)
    comprobar_puerto(repo, r)


if __name__ == "__main__":
    ejecutar(
        "j02",
        "identidad del despliegue: nombre del repositorio y APP_PORT (Guía 8, puntos 1 y 2)",
        comprobar,
    )
