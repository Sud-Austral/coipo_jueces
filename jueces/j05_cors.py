#!/usr/bin/env python3
"""j05 — CORS por dominio, nunca por IP ni comodín.

Implementa el punto 5 de la Guía 8.

  El navegador arma la cabecera `Origin` con el dominio de la barra de
  direcciones, NUNCA con la IP del servidor. Así que un origen escrito por IP no
  calza jamás con una petición real —es configuración muerta que parece
  configuración— y `"*"` abre el servicio a cualquier origen de internet.

DOS DEFECTOS DISTINTOS, Y EL SEGUNDO ES PEOR
  1. `allow_origins=["*"]`: el servicio acepta a cualquiera.
  2. El repositorio declara `CORS_ORIGINS` en su `.env.example`, lo lee en su
     configuración... y el middleware no lo usa. Entonces alguien escribe
     `CORS_ORIGINS=https://iam.conaf.cl` en el `.env` del servidor, lo da por
     cerrado, y no pasa absolutamente nada. Una variable inerte es peor que una
     variable ausente: la ausente se nota.

NO USAR CORS NO ES UN DEFECTO
  `coipo_prensa2` y `COIPO_ENTREGA_PLANTA` no registran `CORSMiddleware` en
  absoluto, y es correcto: el nginx del contenedor `app` sirve el frontend y
  proxea el backend bajo el MISMO origen, así que el navegador nunca emite una
  petición cruzada. Ahí no hay nada que juzgar, y este juez lo declara NO
  EVALUADO en vez de inventarse un hallazgo.

CALIBRACIÓN INVERSA (medida el 2026-09-05)
  coipo_dendroenergia  -> VERDE: `allow_origins=settings.cors_origins`, y su
                          `.env.example` trae un dominio real.
  coipo_prensa2        -> NO EVALUADO: no usa CORS (mismo origen).
  COIPO_ENTREGA_PLANTA -> NO EVALUADO: no usa CORS (mismo origen).
  COIPO_USUARIOS       -> ROJO por los dos defectos a la vez: `backend/main.py`
                          cablea `allow_origins=["*"]` mientras
                          `core/config.py` define `cors_origins_list`, que no
                          usa nadie. Y es el IAM: el servicio del que dependen
                          las demás aplicaciones de la flota.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, suprimido  # noqa: E402

PERFILES = ("aplicacion",)

# Un origen escrito por IP: `http://172.31.2.41:8111`. El navegador nunca manda
# esto como Origin, asi que la entrada no casa nunca con una peticion real.
ORIGEN_POR_IP = re.compile(r"^https?://(\d{1,3}\.){3}\d{1,3}(:\d+)?/?$")

ES_PRUEBA = re.compile(
    r"(^|/)(tests?|__tests__|spec|fixtures)(/|$)"
    r"|(^|/)conftest\.py$|(^|/)test_[^/]*$|[^/]*(_test|\.test)\.py$")


def _archivos_python(repo: Repo) -> list[str]:
    return [r for r in repo.versionados()
            if r.endswith(".py") and not ES_PRUEBA.search(r)]


def _literales(nodo: ast.AST) -> list[str] | None:
    """Devuelve la lista de textos si el nodo es una lista/tupla literal."""
    if not isinstance(nodo, (ast.List, ast.Tuple)):
        return None
    valores = []
    for e in nodo.elts:
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            valores.append(e.value)
        else:
            return None  # mezcla literal y no literal: no se juzga a ciegas
    return valores


def _llamadas_cors(arbol: ast.Module):
    """`app.add_middleware(CORSMiddleware, ...)`, en cualquiera de sus formas."""
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        nombre = f.attr if isinstance(f, ast.Attribute) else \
            f.id if isinstance(f, ast.Name) else None
        if nombre not in ("add_middleware", "CORSMiddleware"):
            continue
        primero = nodo.args[0] if nodo.args else None
        es_cors = nombre == "CORSMiddleware" or (
            isinstance(primero, ast.Name) and primero.id == "CORSMiddleware") or (
            isinstance(primero, ast.Attribute) and primero.attr == "CORSMiddleware")
        if es_cors:
            yield nodo


def _declara_cors_origins(repo: Repo) -> bool:
    for linea in repo.lineas(".env.example"):
        limpia = linea.strip()
        if not limpia.startswith("#") and limpia.split("=")[0].strip() == "CORS_ORIGINS":
            return True
    return False


def comprobar(repo: Repo, r: Resultado) -> None:
    encontrado = False

    for ruta in _archivos_python(repo):
        texto = repo.texto(ruta)
        if texto is None or "CORSMiddleware" not in texto:
            continue
        try:
            arbol = ast.parse(texto, filename=ruta)
        except SyntaxError as e:
            # Ruidoso a proposito: un archivo que no parsea no se declara limpio.
            r.no_evaluado.append(f"{ruta}: no se pudo parsear ({e.msg}).")
            continue

        lineas = texto.splitlines()
        for llamada in _llamadas_cors(arbol):
            encontrado = True
            r.comprobo(f"CORS ({ruta}:{llamada.lineno})")
            _juzgar(repo, r, ruta, lineas, llamada)

    if not encontrado:
        # NO es un hallazgo: detras del nginx del contenedor `app` el frontend y
        # el backend comparten origen y el navegador no emite peticion cruzada.
        r.no_corresponde(
            "no se registra `CORSMiddleware` en ningún archivo versionado: esta "
            "aplicación sirve su frontend y su API bajo el mismo origen detrás del "
            "nginx del contenedor `app`, así que el navegador nunca emite una "
            "petición cruzada y no hay CORS que configurar. OJO: si en el futuro "
            "otra aplicación CONAF va a consumir esta API desde otro dominio, "
            "entonces sí hará falta (Guía 8, punto 5)."
        )


def _juzgar(repo: Repo, r: Resultado, ruta: str,
            lineas: list[str], llamada: ast.Call) -> None:
    origenes = next((k for k in llamada.keywords if k.arg == "allow_origins"), None)
    if origenes is None:
        return

    n = origenes.value.lineno
    valores = _literales(origenes.value)

    if valores is None:
        # Viene de la configuracion (`settings.cors_origins`): la forma correcta.
        # El valor real lo pone el `.env` del servidor y no pasa por git.
        return

    if (motivo := suprimido(lineas, n - 1, "G8-5")):
        r.supresiones.append(f"{ruta}:{n} allow_origins literal — {motivo}")
        return

    credenciales = next((k for k in llamada.keywords
                         if k.arg == "allow_credentials"), None)
    con_credenciales = not (
        isinstance(getattr(credenciales, "value", None), ast.Constant)
        and credenciales.value.value is False)

    if "*" in valores:
        agravante = (
            " Y `allow_credentials` no está en False, así que un sitio hostil puede "
            "leer respuestas autenticadas con la sesión de la persona."
            if con_credenciales else
            " `allow_credentials=False` limita el daño —el navegador no adjunta la "
            "cookie— pero deja abierto todo lo que responda sin autenticación."
        )
        r.bloquea(
            "G8-5", ruta, "`allow_origins` acepta `*`",
            "cualquier página de internet puede llamar a esta API desde el navegador "
            "de un funcionario." + agravante,
            linea=n,
            arreglo="lista explícita de dominios leída de `CORS_ORIGINS`, nunca `*` "
                    "(Guía 8, punto 5)",
        )

    for v in valores:
        if ORIGEN_POR_IP.match(v.strip()):
            r.bloquea(
                "G8-5", ruta, f"`allow_origins` incluye la IP `{v}`",
                "el navegador arma `Origin` con el dominio de la barra de "
                "direcciones, nunca con la IP del servidor: esa entrada no va a "
                "casar jamás con una petición real. Es configuración muerta que "
                "parece configuración, y la petición legítima se rechaza",
                linea=n,
                arreglo="escribir el dominio (`https://<app>.conaf.cl`). No hace "
                        "falta que exista todavía en el DNS para configurarlo",
            )

    # El defecto peor: la variable existe, se documenta... y no la usa nadie.
    if _declara_cors_origins(repo):
        r.bloquea(
            "G8-5", ruta,
            "`allow_origins` está cableado en el código mientras el repositorio "
            "declara `CORS_ORIGINS` en su `.env.example`",
            "quien despliegue va a escribir `CORS_ORIGINS=https://...` en el `.env` "
            "del servidor, va a dar el asunto por cerrado, y no va a pasar nada: la "
            "variable es inerte. Una variable que miente es peor que una ausente, "
            "porque la ausente se nota",
            linea=n,
            arreglo="pasar la lista desde la configuración —`allow_origins="
                    "settings.cors_origins`— o borrar `CORS_ORIGINS` del "
                    "`.env.example` para que nadie crea que sirve",
        )


if __name__ == "__main__":
    ejecutar("j05", "CORS por dominio, nunca por IP ni `*` (Guía 8, punto 5)", comprobar)
