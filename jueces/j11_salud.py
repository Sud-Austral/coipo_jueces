#!/usr/bin/env python3
"""j11 — `/health`: que un fallo no se disfrace de aplicación sana.

Implementa los puntos **9 y 11 de la Guía 8** y la regla del healthcheck de
`DOCKER.md`. La propia guía llama al punto 11 «el que más caro salió», y lo
describe así:

    El seed de catálogo moría con KeyError: 'comunas', el código atrapaba la
    excepción para no dejar el contenedor en crash-loop, y la app arrancaba con
    /health respondiendo 200 y la base VACÍA. El deploy salió verde, el smoke
    test también, y nadie se enteró.

El smoke test del despliegue es **un solo** `curl -sf http://127.0.0.1:$APP_PORT/health`.
`curl -sf` falla con cualquier código >= 400 y NO sigue redirecciones. Todo lo
que este juez comprueba sale de esa única línea.

QUÉ COMPRUEBA, Y DE DÓNDE SALE CADA REGLA

  1. Existe un endpoint `/health`.                        Guía 8, punto 9
  2. No exige autenticación.                              Guía 8, punto 9
     Un 401 o un 302 a login hacen fallar el despliegue.
  3. `execute()` con string crudo.                        fastapi-postgresql-conexion.md
     En SQLAlchemy 2.x lanza ArgumentError. La versión ANTERIOR de ese propio
     documento traía el ejemplo sin `text()`, así que quien copió de ahí tiene
     el `/health` roto o «pasando» por el except.
  4. Un `except` que devuelve sin cambiar el código.      Guía 8, punto 11
     `{"status": "error"}` con código 200 hace que el smoke test dé VERDE con la
     base caída.
  5. El `test:` del healthcheck y el `/health` real       DOCKER.md
     apuntan al mismo sitio. Hoy `coipo_cabania` lleva días `unhealthy` mientras
     su `/health` devuelve 200 (hallazgo H9): el contenedor queda marcado mal
     para siempre sin que nada se rompa, y ese `unhealthy` permanente esconderá
     un problema real el día que lo haya.

LO QUE NO COMPRUEBA, Y ES DELIBERADO
  No exige 503 ante un fallo de DATOS. La Guía 8 pide que ese estado sea
  VISIBLE, y ofrece tres caminos: 503 en `/health`, un `/ready` aparte, o
  validar el dato en el Dockerfile con un `RUN` (build roto = los contenedores
  viejos siguen sirviendo). `COIPO_ENTREGA_PLANTA` eligió el tercero a
  propósito, y su comentario explica por qué el 503 no le sirve: `app` depende
  de `service_healthy`, así que un 503 por datos dejaría el sitio entero abajo.
  Exigir un único camino convertiría una decisión correcta en un hallazgo.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    Repo, Resultado, YamlNoSoportado, carga_yaml, ejecutar, suprimido,
)

PERFILES = ("aplicacion",)

RUTA_SALUD = re.compile(r'["\']/health/?["\']')

# `Depends(...)` cuyo nombre huele a autenticación. La lista es corta y
# deliberada: se prefiere no cazar un guard exótico a marcar como hallazgo un
# `Depends(get_db)`, que es legítimo y está en el ejemplo del propio documento.
DEPENDENCIA_DE_AUTH = re.compile(
    r"(usuario_actual|current_user|get_current|require_|requerir_|exigir_"
    r"|obtener_sesion|sesion_requerida|solo_admin|verify_token|auth)",
    re.IGNORECASE,
)

# `db.execute("SELECT 1")` — string crudo. En SQLAlchemy 2.x lanza
# ArgumentError: Textual SQL expression should be explicitly declared as text().
EJECUTA_CRUDO = re.compile(r"\.execute\(\s*[\"'](?:\s*--)?\s*(SELECT|select)\b")

# El comando del healthcheck del compose: se le extrae la URL.
URL_EN_HEALTHCHECK = re.compile(r"https?://[^\s'\"\)]+", re.IGNORECASE)


def _archivos_python(repo: Repo) -> list[str]:
    return [r for r in repo.versionados()
            if r.endswith(".py") and "/tests/" not in r and not r.startswith("tests/")]


def _modulo_con_salud(repo: Repo) -> tuple[str, str] | None:
    """(ruta, texto) del módulo que declara la ruta /health, o None."""
    for ruta in _archivos_python(repo):
        texto = repo.texto(ruta)
        if texto and RUTA_SALUD.search(texto) and "@" in texto:
            return ruta, texto
    return None


def _funcion_de_salud(arbol: ast.Module) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """La función decorada con una ruta `/health`.

    Se parsea con `ast` y no se busca por nombre: una función puede llamarse
    `salud`, `health` o `estado`, y lo que la define es su decorador.
    """
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in nodo.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            for arg in dec.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.rstrip("/") == "/health":
                        return nodo
    return None


def comprobar_endpoint(repo: Repo, r: Resultado) -> None:
    hallado = _modulo_con_salud(repo)
    if hallado is None:
        r.bloquea(
            "G8-9", "", "no se encontró ningún endpoint `/health`",
            "el smoke test del despliegue hace `curl -sf http://127.0.0.1:$APP_PORT/health` "
            "y es lo ÚNICO que verifica que la aplicación quedó viva; sin ese endpoint el "
            "despliegue falla siempre, o peor, nadie sabe si funcionó",
            arreglo="exponer GET /health devolviendo 200 con un JSON simple, sin "
                    "autenticación y sin redirecciones (Guía 8, punto 9)",
        )
        return

    ruta, texto = hallado
    r.comprobo(f"endpoint /health ({ruta})")
    lineas = texto.splitlines()

    try:
        arbol = ast.parse(texto)
    except SyntaxError as e:
        r.no_evaluado.append(f"{ruta}: no se pudo parsear ({e}). El /health no se verificó.")
        return

    fn = _funcion_de_salud(arbol)
    if fn is None:
        r.no_evaluado.append(
            f"{ruta} menciona /health pero no se encontró la función decorada. "
            f"Puede ser un montaje dinámico; hay que mirarlo a mano."
        )
        return

    _comprobar_sin_auth(fn, ruta, lineas, r)
    _comprobar_sql_crudo(fn, ruta, texto, lineas, r)
    _comprobar_except_mudo(fn, ruta, lineas, r, repo)


def _comprobar_sin_auth(fn, ruta: str, lineas: list[str], r: Resultado) -> None:
    """Guía 8, punto 9: sin autenticación y sin 3xx.

    `curl -sf` falla con cualquier código >= 400 y no sigue redirecciones, así
    que un 401 o un 302 a login rompen el despliegue entero.
    """
    r.comprobo("/health sin autenticación")
    for arg in list(fn.args.args) + list(fn.args.kwonlyargs):
        anot = ast.unparse(arg.annotation) if arg.annotation else ""
        if DEPENDENCIA_DE_AUTH.search(anot) or DEPENDENCIA_DE_AUTH.search(arg.arg):
            if suprimido(lineas, fn.lineno - 1, "G8-9"):
                r.supresiones.append(f"{ruta}:{fn.lineno} /health con dependencia de auth")
                return
            r.bloquea(
                "G8-9", ruta,
                f"`/health` recibe `{arg.arg}`, que parece una dependencia de autenticación",
                "el smoke test usa `curl -sf`, que falla con cualquier código >= 400 y no "
                "sigue redirecciones: un 401 o un 302 a login hacen fallar el despliegue "
                "entero aunque la aplicación esté perfectamente sana",
                linea=fn.lineno,
                arreglo="dejar /health sin ninguna dependencia de sesión (Guía 8, punto 9)",
            )
            return


def _comprobar_sql_crudo(fn, ruta: str, texto: str, lineas: list[str], r: Resultado) -> None:
    """`db.execute("SELECT 1")` — roto en SQLAlchemy 2.x.

    Lo advierte el propio `fastapi-postgresql-conexion.md`, y con una razón
    incómoda: su VERSIÓN ANTERIOR traía el ejemplo sin `text()`. Quien copió de
    ahí tiene el /health roto, o «pasando» silenciosamente por el except — que
    es justo el punto 11.
    """
    if "sqlalchemy" not in texto.lower():
        return
    r.comprobo("/health: text() en las consultas (SQLAlchemy 2.x)")
    segmento = ast.get_source_segment(texto, fn) or ""
    m = EJECUTA_CRUDO.search(segmento)
    if not m:
        return
    n = fn.lineno + segmento[:m.start()].count("\n")
    if suprimido(lineas, n - 1, "G8-9"):
        r.supresiones.append(f"{ruta}:{n} execute con string crudo")
        return
    r.bloquea(
        "G8-9", ruta,
        "`execute()` con un string crudo dentro de `/health`",
        "SQLAlchemy 2.x lanza ArgumentError con un string crudo, así que el /health "
        "falla SIEMPRE — o peor, si está dentro de un try/except, «pasa» por el except "
        "y devuelve 200 con la base caída",
        linea=n,
        arreglo='envolver en text(): db.execute(text("SELECT 1"))',
    )


def _hay_valvula_de_escape(repo: Repo) -> str | None:
    """¿Existe alguna de las OTRAS dos vías que ofrece la Guía 8, punto 11?

    La guía pide que el estado degradado sea VISIBLE, y da tres caminos:
    503 en `/health`, un endpoint aparte que nada use como sonda, o validar el
    dato en el `Dockerfile` con un `RUN` (build roto = los contenedores viejos
    siguen sirviendo). Devuelve cuál se encontró, o None.
    """
    for ruta in repo.versionados():
        if ruta.endswith(".py") and "/tests/" not in ruta:
            texto = repo.texto(ruta) or ""
            if re.search(r'["\']/(ready|health/detalle|healthz|estado)["\']', texto):
                return f"endpoint aparte en {ruta}"
        if Path(ruta).name.startswith("Dockerfile"):
            texto = repo.texto(ruta) or ""
            # Un `RUN python -c ...` que valida el dato de arranque: si el dato
            # es inválido se rompe el BUILD, y los contenedores viejos siguen
            # sirviendo. Es lo que hace COIPO_ENTREGA_PLANTA con su catálogo.
            if re.search(r"^\s*RUN\s+(python|node|sh -c).*(valid|catalog|catálogo|seed|check)",
                         texto, re.MULTILINE | re.IGNORECASE):
                return f"validación en build ({ruta})"
    return None


def _comprobar_except_mudo(fn, ruta: str, lineas: list[str], r: Resultado,
                           repo: Repo) -> None:
    """Guía 8, punto 11: que el estado degradado NO sea invisible.

    OJO — ESTE JUEZ NO EXIGE 503, Y ES DELIBERADO.

    La Guía 8 dice «devolver 503, no 200». La flota entera hace lo contrario, y
    las tres implementaciones escribieron la misma razón:

      coipo_prensa2/backend/app/routers/salud.py
        «Deliberadamente se responde 200 y no 503: un 503 dejaría el contenedor
         unhealthy y, por el depends_on de docker-compose, `app` no arrancaría
         — un 502 mudo en vez de una pantalla que dice qué falta.»

    No es indisciplina: es que el estándar se contradice consigo mismo.
    `DOCKER.md` prescribe `app` con `depends_on: condition: service_healthy`, y
    la Guía 8 exige 503 ante fallo. Juntas, cualquier fallo del backend deja el
    sitio entero abajo en vez de degradado.

    Así que lo que se comprueba es lo que la guía de verdad quiere: **que el
    estado degradado sea VISIBLE EN ALGUNA PARTE**. Devolver 200 está bien si
    existe una de las otras dos válvulas. Devolver 200 y que no exista ninguna
    es el incidente del catálogo vacío.
    """
    r.comprobo("/health: el estado degradado es visible en alguna parte")
    for nodo in ast.walk(fn):
        if not isinstance(nodo, ast.ExceptHandler):
            continue
        cuerpo = "\n".join(ast.unparse(s) for s in nodo.body)
        if "return" not in cuerpo and "raise" not in cuerpo:
            continue
        if "raise" in cuerpo:
            continue  # re-lanza: el framework decide el código, es correcto
        fija_estado = re.search(
            r"status_code|SERVICE_UNAVAILABLE|\b503\b|HTTPException|Response\(", cuerpo
        )
        if fija_estado:
            continue  # devuelve 503: la vía directa de la Guía 8. Correcto.

        valvula = _hay_valvula_de_escape(repo)
        if valvula:
            # Devuelve 200 a propósito Y el estado degradado se ve en otro sitio.
            # Es lo que hacen prensa2, ENTREGA_PLANTA y dendroenergia, cada uno
            # con su razón escrita. No es un hallazgo.
            r.comprobo(f"estado degradado visible por otra vía: {valvula}")
            continue

        n = nodo.lineno
        if suprimido(lineas, n - 1, "G8-11"):
            r.supresiones.append(f"{ruta}:{n} except sin código de estado ni válvula")
            continue

        # AVISA, NO BLOQUEA — y la razón es de plataforma, no de este repositorio.
        #
        # Devolver 200 con `{"status": "error"}` en el cuerpo SÍ hace visible el
        # estado, pero nada automatizado lo lee: el smoke test del despliegue es
        # `curl -sf .../health` y solo mira el código HTTP. Arreglarlo de verdad
        # exige que el smoke test lea el cuerpo, y ese smoke test vive en
        # `infra-docker-base`, que por contrato «no se edita por app».
        #
        # O sea: ninguna aplicación puede cerrar este hueco sola. Bloquear su
        # despliegue por algo que no está en su mano es exactamente el falso
        # positivo que enseña a la gente a suprimir al juez.
        r.avisa(
            "G8-11", ruta,
            "el `except` de `/health` devuelve 200 y ninguna sonda automatizada "
            "lee el estado degradado",
            "el smoke test solo mira el código HTTP, así que el despliegue sale VERDE "
            "con la base caída. Es el incidente que la Guía 8 llama «el que más caro "
            "salió»: el seed murió, /health respondió 200, la base quedó vacía y nadie "
            "se enteró durante días",
            linea=n,
            arreglo="tres vías en el repositorio (Guía 8, punto 11): fijar "
                    "response.status_code = 503 si `app` no depende de service_healthy; "
                    "exponer /ready o /health/detalle que ninguna sonda use como "
                    "dependencia; o validar el dato en el Dockerfile con un RUN. "
                    "La cuarta, y la única que cierra el hueco de verdad, es de "
                    "PLATAFORMA: que el smoke test de infra-docker-base lea el cuerpo "
                    "y no solo el código.",
        )


def comprobar_coherencia_healthcheck(repo: Repo, r: Resultado) -> None:
    """DOCKER.md: «el healthcheck y el /health tienen que apuntar al mismo sitio».

    Está pasando hoy con `coipo_cabania`: `unhealthy` desde hace ocho días
    mientras su `/health` devuelve 200. No rompe nada —el smoke test solo mira
    el curl— pero deja un `unhealthy` permanente que esconderá un problema real
    el día que lo haya.
    """
    ruta_compose = next((c for c in ("docker-compose.yml", "docker-compose.yaml",
                                     "compose.yml", "compose.yaml") if repo.existe(c)), None)
    if ruta_compose is None:
        r.no_evaluado.append("sin docker-compose.yml: no hay healthcheck que contrastar")
        return

    texto = repo.texto(ruta_compose) or ""
    try:
        compose = carga_yaml(texto)
    except YamlNoSoportado as e:
        r.no_evaluado.append(f"{ruta_compose}: {e}. El healthcheck no se verificó.")
        return

    servicios = compose.get("services")
    if not isinstance(servicios, dict):
        return

    r.comprobo("coherencia healthcheck del compose ↔ /health")
    for nombre, s in servicios.items():
        if not isinstance(s, dict):
            continue
        hc = s.get("healthcheck")
        if not isinstance(hc, dict):
            continue
        test = hc.get("test")
        comando = " ".join(str(x) for x in test) if isinstance(test, list) else str(test or "")
        urls = URL_EN_HEALTHCHECK.findall(comando)
        if not urls:
            continue
        for url in urls:
            camino = re.sub(r"^https?://[^/]+", "", url).split("?")[0].rstrip("/")
            if camino and camino != "/health":
                r.avisa(
                    "DOCKER-hc", ruta_compose,
                    f"el healthcheck de `{nombre}` apunta a `{camino}`, no a `/health`",
                    "si el `test:` no mira donde el endpoint real, el contenedor queda "
                    "`unhealthy` para siempre sin que nada se rompa, y ese `unhealthy` "
                    "permanente esconderá un problema real el día que lo haya "
                    "(está pasando con coipo_cabania desde hace días)",
                    arreglo="apuntar el healthcheck al mismo /health que expone el backend, "
                            "o documentar por qué son rutas distintas",
                )


def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.tiene_git():
        r.no_evaluado.append(f"{repo.raiz} no es un repositorio git")
        return
    comprobar_endpoint(repo, r)
    comprobar_coherencia_healthcheck(repo, r)


if __name__ == "__main__":
    ejecutar("j11", "/health: que un fallo no se disfrace de app sana "
                    "(Guía 8, puntos 9 y 11; DOCKER.md)", comprobar)
