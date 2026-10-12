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

CALIBRACIÓN INVERSA (vuelta a medir el 2026-09-07, sobre los 15 repositorios
`coipo_*` del disco)
  De los quince, **catorce salen `NO_APLICA`**: no llevan `.semilla`, así que sus
  archivos son suyos aunque se llamen igual. Eso es lo correcto y es lo que este
  juez existe para no romper.

  El decimoquinto es `coipo_atraso_personal`, **el único de la flota que sí se
  sembró**, y sale con **1 `SEM-1` bloqueante** sobre `frontend/nginx.conf` por
  tres líneas de comentario: conserva la justificación del `resolver` con un
  incidente que la fábrica borró DESPUÉS de sembrarlo. El hallazgo es correcto
  —el archivo está editado respecto del lock— pero la causa está en la fábrica,
  no en la aplicación.

  Hasta el 2026-09-08 esta sección decía «ningún repositorio se sembró todavía,
  así que NINGUNO tiene estos archivos … si alguno sale rojo hoy, el juez está
  mal». Dejó de ser cierto en cuanto se sembró el primero, y nadie lo actualizó.
  Leída al pie de la letra, mandaba concluir que el juez estaba mal cuando lo que
  estaba desalineado era la semilla de ese repositorio.

  **Lo que importa del episodio:** este juez sólo tiene UN patrón de calibración
  vivo, porque sólo hay un repositorio sembrado. Medir una regla nueva contra un
  patrón sucio no distingue si falló la regla o el repositorio. Antes de tocar
  `j12` o `j13`, comprobar que ese patrón esté limpio.

  La semilla materializada tiene que salir VERDE. Registra **1 comprobación**, no
  22: `comprobar()` llama a `r.comprobo()` una sola vez, con el recuento dentro
  del mensaje —«21 de 21 presentes»—. El «22» de esta línea nunca correspondió a
  nada que el juez emitiera.

LA VENTANA DE COMPATIBILIDAD: DESFASADA NO ES EDITADA (D2, 2026-10-12)
======================================================================
Este juez no compara la aplicación contra la semilla: la compara contra el LOCK,
que es lo único que viaja al CI de cada aplicación (`docs/VERSIONADO.md`,
`v2.0.10`). Y el lock viaja con el tag móvil `v2`. Cada vez que se resella, `v2`
salta de golpe y TODA aplicación sembrada con la semilla anterior pasa a `SEM-1`
«es una pieza CONGELADA y está editada» por un archivo que ella no tocó. Ya se
midió: el radio de explosión de `v2.0.11` dio tres `SEM-1` nuevos en cada una de
dos aplicaciones sembradas, por piezas que sólo estaban atrasadas (`VERSIONADO.md`,
tabla de `v2.0.11`; sólo no rompió el build porque iban en advisory). Acusar a
alguien de lo que no hizo es la
receta del falso positivo que enseña a suprimir al juez, y la regla es otra:
editada y desfasada son dos defectos distintos, con dos mensajes y dos plazos.

Para distinguirlos, `semilla/sellar.py --escribir` de la fábrica deja junto al
lock un `semilla.lock.anterior`: el lock que había ANTES del último resellado, con
dos fechas en la cabecera (`# movido:` y `# ventana_hasta:`). Para cada pieza que
no coincide con el lock vigente, en este orden:

  1. coincide con el vigente              -> nada. Nunca hay hallazgo.
  2. lleva `coipo-jueces:ignorar(SEM-1)`  -> supresión contada, como siempre. Va
                                             ANTES que la ventana: quien se suprime
                                             a sí mismo paga lo mismo en cualquier
                                             fecha.
  3. coincide con el ANTERIOR, y hoy <= `ventana_hasta` (inclusive)
                                          -> AVISA, con las dos fechas en el mensaje.
  4. coincide con el ANTERIOR, y hoy >  `ventana_hasta`
                                          -> BLOQUEA: «desfasada», no «editada».
  5. no coincide con ninguno              -> BLOQUEA «editada», exactamente como
                                             antes de existir la ventana.

LO QUE LA VENTANA NO ES, porque es lo que habría que vigilar:
  - No es una supresión ni la elige la aplicación. La fija la fábrica, viaja en el
    tag publicado y se lee en un archivo que el repositorio de la aplicación no
    contiene.
  - No relaja nada sobre una pieza EDITADA. Sólo reconoce un contenido que fue,
    byte a byte, el vigente de la semilla; cualquier diferencia cae en 5.
  - No tiene interruptor externo. La fecha de hoy sale de `_hoy()` y no de una
    variable de entorno a propósito: una variable que mueva «hoy» sería una forma
    de prorrogar la ventana sin que nada lo cuente, que es justo lo que la
    supresión paga. Las pruebas parchean `_hoy`, como parchean `LOCK`.
  - Ante la duda bloquea. Si `semilla.lock.anterior` existe y no se puede leer
    —sin fecha, fecha imposible, sin entradas— se IGNORA y se anota en
    `no_evaluado`, de modo que el resultado es el de antes de la ventana: un
    archivo roto no puede ocultar un bloqueo, y tampoco puede romperse en silencio.

LÍMITES CONOCIDOS, sin disimular:
  - El archivo guarda sólo el lock INMEDIATAMENTE anterior. Una aplicación dos
    resellados atrás no está cubierta y se juzga como editada.
  - «Hoy» es la fecha local de la máquina que corre el juez (UTC en un runner de
    GitHub). El último día puede cerrar unas horas antes o después según la zona.
  - Pasada la ventana el archivo debería retirarse en el siguiente resellado.
    Mientras siga ahí, bloquea con el mensaje de «desfasada», que es más exacto
    que «editada» y lleva el mismo arreglo.
"""

from __future__ import annotations

import datetime
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (Repo, Resultado, ejecutar, leer_adopcion,  # noqa: E402
                   suprimido)

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


# Las dos fechas de la cabecera de `semilla.lock.anterior`. Se anclan al inicio de
# línea, tras el `#`, y exigen una fecha completa: una línea de prosa del
# encabezado que mencione «movido:» no cuenta como declaración. Espacios y
# tabuladores, no `\s`: `\s` cruzaría un salto de línea y casaría `#` solo en una
# línea con una fecha en la siguiente.
MOVIDO = re.compile(r"^#[ \t]*movido:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$", re.MULTILINE)
VENTANA_HASTA = re.compile(
    r"^#[ \t]*ventana_hasta:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$", re.MULTILINE)


def _ruta_anterior() -> Path:
    """`semilla.lock.anterior`, junto al lock. Sale de `LOCK` para que las pruebas,
    que parchean `LOCK`, parcheen también este sin saberlo."""
    return LOCK.with_name(LOCK.name + ".anterior")


def _hoy() -> datetime.date:
    """La fecha de hoy, en una función de módulo para que sea INYECTABLE.

    Sin variable de entorno a propósito: ver «Lo que la ventana no es» en el
    docstring del módulo. Las pruebas parchean esta función, no el reloj."""
    return datetime.date.today()


def _anterior() -> tuple[dict[str, str], datetime.date, datetime.date] | None:
    """(ruta -> huella del lock anterior, movido, ventana_hasta), o None.

    None significa SÓLO «no hay `semilla.lock.anterior`»: sin ventana, el juez se
    comporta como antes de que existiera.

    Si el archivo existe pero no se puede usar, LEVANTA `ValueError` con el
    motivo, y no devuelve None. Son dos situaciones distintas y confundirlas es el
    fallo que este repositorio denuncia en todas partes: un archivo roto que se
    leyera como «no hay ventana» sería indistinguible de uno que nunca se publicó,
    y nadie se enteraría de que la ventana prometida no está funcionando.
    """
    ruta = _ruta_anterior()
    if not ruta.exists():
        return None
    try:
        texto = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"no se pudo leer el archivo ({type(e).__name__})") from e

    fechas = []
    for nombre, patron in (("movido", MOVIDO), ("ventana_hasta", VENTANA_HASTA)):
        m = patron.search(texto)
        if not m:
            raise ValueError(f"falta la cabecera `# {nombre}: AAAA-MM-DD`")
        try:
            fechas.append(datetime.date.fromisoformat(m.group(1)))
        except ValueError as e:
            raise ValueError(f"`{nombre}: {m.group(1)}` no es una fecha") from e
    movido, ventana_hasta = fechas
    if ventana_hasta < movido:
        raise ValueError(f"`ventana_hasta` ({ventana_hasta}) es anterior a "
                         f"`movido` ({movido}): la ventana nacería cerrada")

    hashes: dict[str, str] = {}
    for linea in texto.splitlines():
        if (m := ENTRADA.match(linea.strip())):
            hashes[m.group("ruta")] = m.group("huella")
    if not hashes:
        raise ValueError("no tiene ninguna entrada `<sha256>  <ruta>`")
    return hashes, movido, ventana_hasta


def _huella(ruta: Path) -> str | None:
    try:
        crudo = ruta.read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return None
    return hashlib.sha256(crudo).hexdigest()


MARCADOR = ".semilla"

# La capa que este juez exige que `.semilla` declare adoptar. Ver comun.py.
CAPA = "semilla"
VERSION = re.compile(r"^\s*version:\s*(?P<version>\S+)", re.MULTILINE)


def _desfasada(r: Resultado, ruta: str, movido: datetime.date,
               ventana_hasta: datetime.date, hoy: datetime.date) -> None:
    """Una pieza que es, byte a byte, la del lock ANTERIOR: atrasada, no editada.

    AVISA hasta `ventana_hasta` inclusive y BLOQUEA después. El arreglo es el mismo
    en los dos lados de la fecha —`sembrar.py --actualizar`—; lo que cambia es sólo
    si el plazo ya venció, y por eso la severidad es lo único que depende de `hoy`.
    """
    arreglo = (
        "ponla al día, no la edites a mano: desde el checkout de "
        "coipo_master_produccion, `python semilla/sembrar.py --destino "
        "<ruta-de-esta-aplicacion> --actualizar` (documentado en `semilla/README.md`; "
        "con la fábrica al lado, desde esta aplicación sirve `--destino .` con "
        "`python ../coipo_master_produccion/semilla/sembrar.py`). "
        "Reescribe SÓLO las piezas selladas y deja intacto lo que la aplicación "
        "adaptó; exige el árbol de trabajo limpio, para que el diff se pueda revisar.")

    if hoy <= ventana_hasta:
        r.avisa(
            "SEM-1", ruta,
            f"pieza CONGELADA de una versión ANTERIOR de la semilla (se movió el "
            f"{movido}): no está editada, está sin actualizar. La ventana de "
            f"compatibilidad llega hasta el {ventana_hasta} inclusive; desde el "
            f"{ventana_hasta + datetime.timedelta(days=1)} esto pasa a bloquear",
            "la aplicación sigue funcionando con el Dockerfile, el nginx o el "
            "archivo que sea de la versión anterior de la semilla; no recibe las "
            f"correcciones que la semilla trae desde el {movido} y el defecto que "
            "cerraron sigue vivo en esta aplicación hasta que se actualice",
            arreglo=arreglo,
        )
        return

    r.bloquea(
        "SEM-1", ruta,
        f"pieza CONGELADA desfasada: coincide con una versión ANTERIOR de la "
        f"semilla (se movió el {movido}) y la ventana de compatibilidad venció el "
        f"{ventana_hasta}. No está editada: está sin actualizar",
        "la aplicación corre con la versión anterior de esta pieza y no recibe las "
        f"correcciones de la semilla desde el {movido}; el plazo para ponerla al "
        "día venció, y desfasada y editada acaban en lo mismo —la corrección no "
        "llega a esta aplicación y nadie se entera—",
        arreglo=arreglo + " Sólo si de verdad no se puede actualizar todavía, "
                "suprímela con `coipo-jueces:ignorar(SEM-1) <motivo>` en la primera "
                "línea: se cuenta y se publica.",
    )


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

    # El marcador existe, pero puede declarar que adopta OTRA capa y no ésta. Ver
    # `leer_adopcion` en comun.py: la clave ausente adopta todo, así que esto sólo
    # se dispara cuando alguien la escribió a propósito.
    adopcion = leer_adopcion(repo.texto(MARCADOR))
    if adopcion.vacia:
        r.no_evaluado.append(
            f"{adopcion.cita(MARCADOR)}: la clave `adopta:` esta VACIA. No declara "
            "nada, y leerla como N/A apagaria este juez en silencio. O se quita la "
            "clave (= adopta todo) o se listan las capas.")
        return
    if not adopcion.adopta(CAPA):
        razon = (f"{adopcion.cita(MARCADOR)} y no incluye `{CAPA}`, así que las "
                 "piezas congeladas de este repositorio NO se comparan contra el "
                 "lock. Es legítimo en una aplicación que adopta un estándar de la "
                 "flota sin haberse sembrado con la semilla; deja de serlo si el "
                 "repositorio SÍ se sembró.")
        r.no_corresponde(razon)
        # Y se cuenta como supresión, no sólo como aviso informativo: esta es la
        # única vía por la que un repositorio puede apagarse un juez a sí mismo, y
        # `comun.py` explica por qué esa puerta se paga. Sale con `::warning::` y
        # exige su fila en DEUDA.md, igual que un `coipo-jueces:ignorar`.
        r.supresiones.append(f"{MARCADOR} declara no adoptar `{CAPA}` — {razon}")
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

    # La ventana de compatibilidad (ver el docstring del módulo). Se lee ANTES del
    # bucle y no cuando aparece la primera diferencia, para que un archivo roto se
    # anote siempre y no sólo cuando casualmente hace falta.
    anterior = None
    try:
        anterior = _anterior()
    except ValueError as e:
        r.no_evaluado.append(
            f"{_ruta_anterior().name} existe pero no se pudo leer: {e}. Se IGNORA la "
            "ventana de compatibilidad, así que una pieza que coincida con la semilla "
            "anterior se juzgará como EDITADA, igual que antes de que la ventana "
            "existiera. Lo escribe `python semilla/sellar.py --escribir "
            "<ruta>/semilla.lock` en coipo_master_produccion.")
    hoy = _hoy() if anterior else None

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

        if anterior and anterior[0].get(ruta) == actual:
            _desfasada(r, ruta, anterior[1], anterior[2], hoy)
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
