#!/usr/bin/env python3
"""j12 — las piezas congeladas de la semilla no se editan por aplicación.

EL PROBLEMA QUE RESUELVE
========================
Toda la arquitectura de esta flota se apoya en una medición: **la copia no
propaga**. `DOCKER.md` vive hoy en 10 repositorios con 3 contenidos distintos, y
al único repositorio sin CI le tocó la copia de la Guía 8 con 9 puntos en vez de
11 —le faltaban justo los dos que más caros salieron—. Tasa de propagación por
copia: 22 %. Por `uses:` a un reusable: 100 %.

Y sin embargo, la semilla se distribuye copiando. No por descuido: **la mitad de
sus archivos no puede distribuirse de otra forma**. Docker lee el `Dockerfile`
del disco, nginx lee su `.conf`, Compose lee el `docker-compose.yml`. No existe
un `uses:` para un archivo de configuración.

Este juez no elimina la copia. Hace que **deje de pudrirse en silencio**: el día
que alguien edite el `nginx.conf` de su aplicación, su despliegue lo dice, con la
ruta y con el motivo.

SE DECLARA, NO SE INFIERE: EL ARCHIVO `.semilla`
================================================
Este juez SÓLO actúa sobre repositorios que llevan un archivo `.semilla` en la
raíz, que la propia semilla trae.

La primera versión no lo exigía y comparaba por ruta. Fue un desastre medible:
puso rojos a `coipo_prensa2`, `COIPO_USUARIOS`, `COIPO_ENTREGA_PLANTA` y
`coipo_dendroenergia` por tener su propio `backend/Dockerfile`, su propio
`frontend/nginx.conf` y su propio `requirements.txt`. **Ninguno de los cuatro se
sembró jamás con esta semilla.** Sus archivos se llaman igual porque toda
aplicación web tiene un Dockerfile, no porque los hayan copiado de aquí.

Es la misma lección que ya costó una vez en esta flota al intentar deducir las
capacidades de un repositorio leyendo su código: **hay cosas que hay que
declarar**. Un `Dockerfile` no dice de dónde vino; el `.semilla` sí.

LO QUE TAMPOCO ES UN HALLAZGO
=============================
Que un archivo del lock NO exista en una aplicación sembrada. No toda aplicación
usa todas las piezas. Exigir la presencia convertiría este juez en «todas las
aplicaciones tienen que ser iguales», que es lo contrario de lo que la flota
necesita: `coipo_n8n` tiene el mejor `docker-compose.yml` de todas precisamente
porque no sigue el molde.

EL FIN DE LÍNEA SE NORMALIZA, Y ES LO QUE HACE QUE ESTO SIRVA
=============================================================
Medido el 2026-09-05: `coipo_prensa2` tiene 293 archivos con CRLF en su árbol de
trabajo y `COIPO_USUARIOS` 219. Es lo normal en Windows con `text=auto`. Un
`sha256` del archivo tal cual pondría rojos a esos repositorios por un motivo
que no tiene nada que ver con su contenido, y un juez que falla por algo que no
importa se suprime en una semana. Se compara el contenido con `\\r\\n` pasado a
`\\n`, que es lo que git guarda.

CALIBRACIÓN INVERSA (medida el 2026-09-05)
  Ningún repositorio de la flota se sembró con esta semilla todavía, así que
  NINGUNO tiene estos archivos y todos deben salir `NO_APLICA`. Si alguno sale
  rojo hoy, el juez está mal.

  La semilla materializada, en cambio, tiene que salir VERDE con 22
  comprobaciones: es lo que verifica que el lock esté al día.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, suprimido  # noqa: E402

PERFILES = ("aplicacion", "encuadre_operativo")

LOCK = Path(__file__).resolve().parents[1] / "semilla.lock"

# `<sha256>  <ruta>`, como la salida de `sha256sum`.
ENTRADA = re.compile(r"^(?P<huella>[0-9a-f]{64})\s+(?P<ruta>\S.*)$")


def _lock() -> dict[str, str]:
    """ruta -> huella esperada. Vacío si el lock no está."""
    if not LOCK.exists():
        return {}
    salida: dict[str, str] = {}
    for linea in LOCK.read_text(encoding="utf-8").splitlines():
        if (m := ENTRADA.match(linea.strip())):
            salida[m.group("ruta")] = m.group("huella")
    return salida


def _huella(ruta: Path) -> str | None:
    try:
        crudo = ruta.read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return None
    return hashlib.sha256(crudo).hexdigest()


MARCADOR = ".semilla"
VERSION = re.compile(r"^\s*version:\s*(?P<version>\S+)", re.MULTILINE)


def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.existe(MARCADOR):
        # Que un repositorio tenga `backend/Dockerfile` no significa que lo haya
        # copiado de aquí: toda aplicación web tiene uno. Sin declaración, no hay
        # nada que comparar.
        r.no_corresponde(
            f"no hay `{MARCADOR}` en la raíz: este repositorio no se sembró con la "
            "semilla de la flota, así que sus archivos son suyos aunque se llamen "
            "igual. Si SÍ se sembró y alguien borró el marcador, restaurarlo es lo "
            "que vuelve a encender esta comprobación.")
        return

    esperado = _lock()
    if not esperado:
        # Ruidoso a propósito. Un juez cuyo catálogo no está no se declara
        # conforme: se declara incapaz de mirar.
        r.no_evaluado.append(
            f"no se pudo leer {LOCK.name}: sin él este juez no sabe qué archivos "
            "están congelados. Se regenera con `python semilla/sellar.py "
            "--escribir <ruta>/semilla.lock` en coipo_master_produccion.")
        return

    m = VERSION.search(repo.texto(MARCADOR) or "")
    version = m.group("version") if m else "sin declarar"

    presentes = [ruta for ruta in esperado if repo.existe(ruta)]
    if not presentes:
        r.no_evaluado.append(
            f"hay `{MARCADOR}` (version {version}) pero no está ninguno de los "
            f"{len(esperado)} archivos congelados. O el marcador quedó de un "
            f"borrado, o la siembra no llegó a copiarse: las dos hay que mirarlas.")
        return

    r.comprobo(f"piezas congeladas de la semilla {version} "
               f"({len(presentes)} de {len(esperado)} presentes)")

    for ruta in sorted(presentes):
        actual = _huella(repo.ruta(ruta))
        if actual is None:
            r.no_evaluado.append(f"{ruta}: no se pudo leer.")
            continue
        if actual == esperado[ruta]:
            continue

        lineas = repo.lineas(ruta)
        if (motivo := suprimido(lineas, 0, "SEM-1")):
            r.supresiones.append(f"{ruta} pieza congelada editada — {motivo}")
            continue

        r.bloquea(
            "SEM-1", ruta, "es una pieza CONGELADA de la semilla y está editada",
            "este archivo es idéntico en toda la flota a propósito: cierra un fallo "
            "que ya ocurrió y la corrección tiene que llegar a todas las "
            "aplicaciones a la vez. Una copia editada deja de recibir las "
            "correcciones y nadie se entera — es exactamente cómo `DOCKER.md` acabó "
            "en 10 repositorios con 3 contenidos distintos",
            arreglo="si el cambio sólo sirve para esta aplicación, sácalo a un "
                    "archivo propio que NO esté en el lock. Si el cambio es bueno "
                    "para toda la flota, hazlo en `semilla/CONGELADO/` de "
                    "coipo_master_produccion, vuelve a sellar, y llega a todas. "
                    "Si de verdad hace falta la excepción aquí, suprímela con "
                    "`coipo-jueces:ignorar(SEM-1) <motivo>` en la primera línea: "
                    "se cuenta y se publica.",
        )


if __name__ == "__main__":
    ejecutar("j12", "las piezas congeladas de la semilla no se editan por aplicación",
             comprobar)
