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

CALIBRACIÓN INVERSA DEL HISTORIAL (2026-10-24, con el lock de 42 piezas y su
historial de 10 bloques sembrado desde git)
  Sobre las diez aplicaciones sembradas del disco que adoptan la semilla
  (`adopta:` con `semilla`, o sin la clave): `coipo_anillo_evacuacion`,
  `coipo_api`, `coipo_atraso_personal`, `coipo_avisete`, `coipo_camara_deteccion`,
  `coipo_firms`, `coipo_gestion_incendio`, `coipo_saff_paralelo`,
  `coipo_visor_saff` y `coipo_visor_sidco`.

  - El `j12` publicado (`c4fec81`) con ese mismo lock: las diez en rojo, 79
    `BLOQUEA` (7+8+10+6+7+7+7+9+9+9), casi todos por piezas sólo atrasadas.
  - Este `j12`: **5 `BLOQUEA` en 3 aplicaciones, y los 5 son ediciones de
    verdad**. Ninguna huella coincide con NINGUNA versión que la fábrica tuvo en
    git (no sólo las selladas), y el git log de cada aplicación tiene el commit
    que la editó: `coipo_api` (`clasificacion.py`, `conftest.py`,
    `test_la_semilla_importa.py`, sembrada el 2026-09-15 «con sus cuatro
    defectos corregidos» a mano), `coipo_atraso_personal` (`mapeo_claims.py`,
    2026-09-25) y `coipo_visor_saff` (`identidad.py`, 2026-10-07). Las otras
    siete, cero `BLOQUEA`. El resto —89 piezas— AVISA como atrasada.
  - Una aplicación sembrada de cero ese día (`git init` + `sembrar.py --gerencia
    1_SECOM`) sale `OK`, 42 de 42 presentes.
  - Lo que deja abierto: `.dockerignore` se selló hasta el 2026-09-09 y después
    la fábrica lo excluyó a propósito (`NO_SE_SELLA` de `sellar.py`: cada
    aplicación lo amplía). Las cinco que conservan el de esa fecha AVISAN como
    «retirada» hasta que lo adapten. No es falso —es la semilla de su fecha—,
    pero es un aviso que no pide nada urgente; si se vuelve ruido, el arreglo es
    de la fábrica (no meter en el historial lo que hoy está en `NO_SE_SELLA`),
    no una supresión aquí.

ATRASADA NO ES EDITADA: EL HISTORIAL (decisión del 2026-10-24)
===============================================================
Este juez no compara la aplicación contra la semilla: la compara contra el LOCK,
que es lo único que viaja al CI de cada aplicación (`docs/VERSIONADO.md`,
`v2.0.10`). Y el lock viaja con el tag móvil `v2`. Cada vez que se resella, `v2`
salta de golpe y TODA aplicación sembrada con la semilla anterior pasaba a `SEM-1`
«es una pieza CONGELADA y está editada» por un archivo que ella no tocó. Ya se
midió: el radio de explosión de `v2.0.11` dio tres `SEM-1` nuevos en cada una de
dos aplicaciones sembradas, por piezas que sólo estaban atrasadas (`VERSIONADO.md`,
tabla de `v2.0.11`; sólo no rompió el build porque iban en advisory).

Y la fábrica lo dice con todas las letras, en `FILOSOFIA.md`, §3, de
coipo_master_produccion: «Una pieza congelada de una versión anterior no es una
pieza editada. Es la fábrica de su fecha. Un juez que acusa de "editada" a una app
por tener el molde con el que nació viola este principio.» Lo decidió Luis
Monsalve el 2026-10-24: una pieza que sólo está atrasada AVISA SIEMPRE, sin
plazo; sólo una editada de verdad BLOQUEA.

Para distinguirlas, `semilla/sellar.py --escribir` de la fábrica mantiene junto al
lock un `semilla.lock.historial`: las huellas de CADA lock publicado antes del
vigente, en bloques que empiezan por `# vigente_hasta: AAAA-MM-DD`, la fecha en que
ese lock dejó de ser el vigente. Sólo crece. Para cada pieza que la aplicación
tiene, en este orden:

  1. coincide con el lock vigente          -> nada. Nunca hay hallazgo.
  2. lleva `coipo-jueces:ignorar(SEM-1)`   -> supresión contada, como siempre.
  3. coincide con una huella del historial -> AVISA «atrasada: es la versión de la
                                              semilla publicada hasta el AAAA-MM-DD»
                                              (la fecha más reciente en que esa
                                              huella fue la vigente), con
                                              `sembrar.py --actualizar` de arreglo.
  4. no coincide con ninguna               -> BLOQUEA «editada», como siempre.

Una pieza que la semilla RETIRÓ del lock (`db/0000_plataforma.sql`, partido el
2026-10-24 en `db/0000_0N_*.sql`) sigue en el historial: si la aplicación la tiene
tal cual, AVISA como atrasada —con un arreglo distinto, porque `--actualizar` trae
las piezas nuevas pero no borra la vieja—; si no coincide con nada, no se juzga:
ya no es una pieza congelada, y las reglas miran hacia adelante (`FILOSOFIA.md`, §4).

Esto reemplaza la «ventana de compatibilidad» de D2 (2026-10-12): un único
`semilla.lock.anterior` que avisaba 30 días y después bloqueaba como «desfasada».
El plazo de 30 días no tenía fuente: fue un valor por omisión que eligió una IA al
registrar D2, nadie lo midió ni lo fijó Luis, y la decisión del 2026-10-24 lo
elimina. Este juez ya no lee `semilla.lock.anterior`; `sellar.py --escribir` lo
incorpora al historial y lo borra.

LO QUE EL HISTORIAL NO ES, porque es lo que habría que vigilar:
  - No es una supresión ni lo elige la aplicación. Lo escribe la fábrica, viaja en
    el tag publicado y se lee de un archivo que el repositorio de la aplicación no
    contiene.
  - No relaja nada sobre una pieza EDITADA. Sólo reconoce un contenido que fue,
    byte a byte, el vigente de la semilla en algún lock publicado; cualquier
    diferencia cae en 4.
  - Ante la duda, no es más indulgente. Sin historial (un lock publicado antes del
    2026-10-24, o un checkout que no lo trae) el juez se comporta como antes de
    D2: atrasada = editada, y lo anota en `no_evaluado`. Con un historial que
    existe y no se entiende —sin `# formato: 1`, una fecha imposible, una entrada
    fuera de bloque, un bloque vacío, bytes que no son UTF-8— se IGNORA entero y
    se anota: un archivo roto no puede ocultar un bloqueo.

LÍMITES CONOCIDOS, sin disimular:
  - El historial se sembró, el 2026-10-24, desde la historia de git de
    `semilla.lock` en coipo_jueces (`sellar.py --con-historia-git`). La fecha de
    cada bloque es la del commit que lo reemplazó, no la del movimiento del tag
    `v2`. Una aplicación sembrada desde un árbol de la fábrica que nunca se selló
    (copió una pieza entre dos resellados) tiene una huella que ningún lock
    publicó, y se juzga como editada.
  - La huella atrasada se reconoce por pieza, no por lock entero: una aplicación
    con piezas de tres semillas distintas avisa tres veces, cada una con su fecha.
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


# El contrato de `semilla.lock.historial` con `semilla/sellar.py` de la fábrica,
# que lo escribe con estas mismas expresiones (se repiten allí: la dependencia va
# al revés, por el lock). Espacios y tabuladores, no `\s`: `\s` cruzaría un salto de
# línea. `CABECERA_DE_BLOQUE` reconoce la intención y `VIGENTE_HASTA` la forma
# completa: una cabecera de bloque con la fecha mal escrita hace ilegible el
# archivo, no se lee como un comentario más.
FORMATO_HISTORIAL = "1"
FORMATO = re.compile(r"^#[ \t]*formato:[ \t]*(\S+)[ \t]*$")
CABECERA_DE_BLOQUE = re.compile(r"^#[ \t]*vigente_hasta:")
VIGENTE_HASTA = re.compile(r"^#[ \t]*vigente_hasta:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$")


def _ruta_historial() -> Path:
    """`semilla.lock.historial`, junto al lock. Sale de `LOCK` para que las pruebas,
    que parchean `LOCK`, parcheen también éste sin saberlo."""
    return LOCK.with_name(LOCK.name + ".historial")


def _historial() -> dict[str, dict[str, datetime.date]] | None:
    """ruta -> {huella -> hasta cuándo fue la vigente}, o None.

    None significa SÓLO «no hay `semilla.lock.historial`». Si el archivo existe pero
    no se puede usar, LEVANTA `ValueError` con el motivo: un archivo roto que se
    leyera como «no hay historial» sería indistinguible de uno que nunca se publicó,
    y nadie se enteraría de que el historial prometido no está funcionando.

    Una huella que aparece en varios bloques (la pieza no cambió entre dos
    resellados) se queda con la fecha MÁS RECIENTE: es hasta cuándo la semilla la
    estuvo publicando.
    """
    ruta = _ruta_historial()
    if not ruta.exists():
        return None
    try:
        texto = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"no se pudo leer el archivo ({type(e).__name__})") from e

    formato = None
    hasta: datetime.date | None = None
    en_el_bloque = 0
    salida: dict[str, dict[str, datetime.date]] = {}
    for n, crudo in enumerate(texto.splitlines(), start=1):
        linea = crudo.strip()
        if (m := FORMATO.match(linea)):
            formato = m.group(1)
            continue
        if CABECERA_DE_BLOQUE.match(linea):
            m = VIGENTE_HASTA.match(linea)
            if not m:
                raise ValueError(f"línea {n}: `vigente_hasta:` sin una fecha AAAA-MM-DD")
            if hasta is not None and en_el_bloque == 0:
                raise ValueError(f"el bloque `vigente_hasta: {hasta}` no tiene entradas")
            try:
                hasta = datetime.date.fromisoformat(m.group(1))
            except ValueError as e:
                raise ValueError(f"línea {n}: `{m.group(1)}` no es una fecha") from e
            en_el_bloque = 0
            continue
        if (m := ENTRADA.match(linea)):
            if hasta is None:
                raise ValueError(f"línea {n}: una entrada antes de cualquier `# vigente_hasta:`")
            en_el_bloque += 1
            por_huella = salida.setdefault(m.group("ruta"), {})
            previa = por_huella.get(m.group("huella"))
            por_huella[m.group("huella")] = hasta if previa is None else max(previa, hasta)
    if formato is None:
        raise ValueError("falta la línea `# formato: 1`: no es un historial")
    if formato != FORMATO_HISTORIAL:
        raise ValueError(f"`formato: {formato}` no es uno que este juez sepa leer "
                         f"(lee el {FORMATO_HISTORIAL})")
    if hasta is not None and en_el_bloque == 0:
        raise ValueError(f"el bloque `vigente_hasta: {hasta}` no tiene entradas")
    return salida


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

ACTUALIZAR = (
    "desde el checkout de coipo_master_produccion, `python semilla/sembrar.py "
    "--destino <ruta-de-esta-aplicacion> --actualizar` (documentado en "
    "`semilla/README.md`; con la fábrica al lado, desde esta aplicación sirve "
    "`--destino .` con `python ../coipo_master_produccion/semilla/sembrar.py`). "
    "Reescribe SÓLO las piezas selladas y deja intacto lo que la aplicación adaptó; "
    "exige el árbol de trabajo limpio, para que el diff se pueda revisar.")


def _atrasada(r: Resultado, ruta: str, hasta: datetime.date) -> None:
    """Una pieza que es, byte a byte, la de un lock publicado antes: atrasada, no editada.

    AVISA siempre, sin plazo (FILOSOFIA.md §3 y la decisión del 2026-10-24): es la
    fábrica de su fecha, y la aplicación se pone al día cuando quiera."""
    r.avisa(
        "SEM-1", ruta,
        f"pieza CONGELADA atrasada: es la versión de la semilla publicada hasta el "
        f"{hasta}. No está editada: la semilla la mejoró después",
        "la aplicación sigue funcionando con el Dockerfile, el nginx o el archivo que "
        f"sea de la semilla vigente hasta el {hasta}; las correcciones que la semilla "
        "trajo después no le llegan hasta que se actualice",
        arreglo="ponla al día cuando convenga, no la edites a mano: " + ACTUALIZAR,
    )


def _retirada(r: Resultado, ruta: str, hasta: datetime.date) -> None:
    """Una pieza que el lock vigente ya no nombra, tal como la publicó una semilla anterior."""
    r.avisa(
        "SEM-1", ruta,
        f"pieza CONGELADA atrasada: es la versión de la semilla publicada hasta el "
        f"{hasta}, y el lock de hoy ya no la sella (la semilla la partió en otras, o "
        "dejó de congelarla)",
        f"la aplicación conserva esta pieza como era en la semilla vigente hasta el "
        f"{hasta}; lo que la semilla cambió después en su lugar no le llega",
        arreglo="ya no es una pieza sellada, así que `sembrar.py --actualizar` no la "
                "toca y este aviso no se cierra solo. Mira qué hizo la semilla con ella "
                f"(`git log -- semilla/CONGELADO/{ruta}` en coipo_master_produccion). "
                "Si la partió en otras —`db/0000_plataforma.sql` pasó a "
                "`db/0000_0N_*.sql` el 2026-10-24—, `--actualizar` trae las nuevas SIN "
                "borrar ésta y quedarían las dos: con una base ya desplegada, decide "
                "antes cuál se aplica. Si dejó de congelarla porque cada aplicación la "
                "amplía —`.dockerignore`, desde el 2026-09-09—, es tuya: adáptala o "
                "tráela de la semilla de hoy, y el aviso desaparece.",
    )


def _editada(r: Resultado, ruta: str) -> None:
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


def _leer_historial(r: Resultado) -> dict[str, dict[str, datetime.date]]:
    """El historial, o `{}` con la razón anotada en `no_evaluado`. Nunca más indulgente."""
    nombre = _ruta_historial().name
    regenerar = ("Lo escribe `python semilla/sellar.py --escribir <ruta>/semilla.lock` "
                 "en coipo_master_produccion.")
    try:
        historial = _historial()
    except ValueError as e:
        r.no_evaluado.append(
            f"{nombre} existe pero no se pudo leer: {e}. Se IGNORA entero, así que una "
            "pieza de una semilla anterior se juzgará como EDITADA, nunca con más "
            "indulgencia. " + regenerar)
        return {}
    if historial is None:
        r.no_evaluado.append(
            f"no hay {nombre} junto al lock: este juez no puede distinguir una pieza "
            "ATRASADA de una EDITADA y juzga las dos como editadas, como antes del "
            "2026-10-24. " + regenerar)
        return {}
    return historial


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
        # Un error de declaración: no se dictamina (la semántica, en comun_semilla.py).
        r.no_evaluado.append(adopcion.motivo_vacia(MARCADOR))
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

    # Se lee ANTES del bucle y no cuando aparece la primera diferencia, para que
    # un archivo roto o ausente se anote siempre y no sólo cuando hace falta.
    historial = _leer_historial(r)

    for ruta in sorted(presentes):
        actual = _huella(repo.ruta(ruta))
        if actual is None:
            r.no_evaluado.append(f"{ruta}: no se pudo leer.")
            continue
        if actual == esperado[ruta]:
            continue

        if (motivo := suprimido(repo.lineas(ruta), 0, "SEM-1")):
            r.supresiones.append(f"{ruta} pieza congelada editada — {motivo}")
            continue

        if (hasta := historial.get(ruta, {}).get(actual)) is not None:
            _atrasada(r, ruta, hasta)
            continue

        _editada(r, ruta)

    # Las piezas que la semilla RETIRÓ del lock y siguen en el historial. Sólo se
    # mira si coinciden con lo que se publicó: si no coinciden, ya no son piezas
    # congeladas y no hay regla que mire hacia atrás (FILOSOFIA.md, §4).
    for ruta in sorted(set(historial) - set(esperado)):
        if not repo.existe(ruta):
            continue
        actual = _huella(repo.ruta(ruta))
        if actual is None or (hasta := historial[ruta].get(actual)) is None:
            continue
        if (motivo := suprimido(repo.lineas(ruta), 0, "SEM-1")):
            r.supresiones.append(f"{ruta} pieza retirada de la semilla — {motivo}")
            continue
        _retirada(r, ruta, hasta)


if __name__ == "__main__":
    ejecutar("j12", "las piezas congeladas de la semilla no se editan por aplicación",
             comprobar)
