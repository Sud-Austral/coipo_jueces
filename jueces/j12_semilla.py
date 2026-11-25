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
  vivo, porque sólo hay un repositorio sembrado (era así en septiembre de 2026; el
  2026-10-24 ya eran diez, ver más abajo). Medir una regla nueva contra un
  patrón sucio no distingue si falló la regla o el repositorio. Antes de tocar
  `j12` o `j13`, comprobar que ese patrón esté limpio.

  La semilla materializada tiene que salir VERDE. Registra una comprobación por cosa
  mirada, con el recuento dentro del mensaje: las piezas congeladas («45 de 45
  presentes»), SEM-3 y, si las hay, SEM-2 y MAQ-1. Medido el 2026-11-21 sobre una
  siembra fresca: OK, con las tres primeras. (Esta línea decía «1 comprobación, no
  22»: dejó de ser cierto con SEM-2, MAQ-1 y SEM-3.)

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

UNA RUTA RECIÉN SELLADA NO ES UNA PIEZA EDITADA (decisión del 2026-11-21)
  Cuando un resellado añade una pieza en una ruta nueva —`rutas/autenticacion.py`,
  `middleware_acceso.py`, `postgres/auditor.py` y `backend/ruff.toml` entraron el
  2026-11-21—, una aplicación sembrada ANTES puede tener ya en esa ruta un archivo
  PROPIO: su login con el IAM, su auditor. No editó nada de la semilla; la semilla
  ocupó una ruta que era suya. Medido ese día con `consumidores.py`: cuatro
  aplicaciones, cinco archivos. Llamarlo «pieza editada» es el falso positivo de
  `FILOSOFIA.md` §3, y bloquearlo contradice el §4 (lo nuevo sólo bloquea en lo
  sembrado desde su vigencia).
  Una pieza que no aparece en NINGÚN bloque del historial es nueva en el lock
  vigente, que rige desde el `vigente_hasta` más reciente del historial; su
  vigencia es el día siguiente, como `AUD-1`. Sembrada antes (o sin `fabrica:`),
  la aplicación AVISA; sembrada después, una diferencia es una edición y BLOQUEA.
  Sin historial no se sabe qué pieza es nueva: BLOQUEA, como siempre.

  LA VIGENCIA ES POR PIEZA (2026-11-22). Al resellar, el lock anterior entra al
  historial, y con la vara de arriba sus rutas recién selladas dejaban de ser
  nuevas: `consumidores.py --lock-candidato` midió cinco aplicaciones que pasaban
  de AVISA a BLOQUEA sin que nadie tocara nada. Ahora cada pieza rige desde el día
  siguiente al último bloque que todavía no la nombraba, contado por posición
  (`historial_semilla.py`), y lo sellado antes de que existiera la regla
  (`GRACIA_DESDE`) se juzga como siempre.
"""

from __future__ import annotations

import datetime
import hashlib
import re
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    Repo,
    Resultado,
    Siembra,
    alcance_semilla,
    ejecutar,
    leer_maqueta,
    leer_siembra,  # noqa: E402
    no_adopta,
    suprimido,
)
from comun_auditoria import ARREGLO as ARREGLO_AUDITORIA  # noqa: E402
from comun_auditoria import MANIFESTACION as MANIFESTACION_AUDITORIA  # noqa: E402
from comun_auditoria import lo_que_falta  # noqa: E402
from historial_semilla import (  # noqa: E402 — el historial y sus expresiones (2026-11-22)
    CABECERA_DE_BLOQUE,
    ENTRADA,
    FORMATO,
    FORMATO_HISTORIAL,
    VIGENTE_HASTA,
    Historial,
    leer,
)

__all__ = ["CABECERA_DE_BLOQUE", "ENTRADA", "FORMATO", "FORMATO_HISTORIAL", "VIGENTE_HASTA"]

PERFILES = ("aplicacion", "encuadre_operativo")

LOCK = Path(__file__).resolve().parents[1] / "semilla.lock"


def _lock() -> dict[str, str]:
    """ruta -> huella esperada. Vacío si el lock no está."""
    if not LOCK.exists():
        return {}
    salida: dict[str, str] = {}
    for linea in LOCK.read_text(encoding="utf-8").splitlines():
        if m := ENTRADA.match(linea.strip()):
            salida[m.group("ruta")] = m.group("huella")
    return salida


def _ruta_historial() -> Path:
    """`semilla.lock.historial`, junto al lock. Sale de `LOCK` para que las pruebas,
    que parchean `LOCK`, parcheen también éste sin saberlo."""
    return LOCK.with_name(LOCK.name + ".historial")


def _historial() -> dict[str, dict[str, datetime.date]] | None:
    """ruta -> {huella -> hasta cuándo fue la vigente}, o None si no hay historial.

    Si el archivo existe pero no se puede usar, LEVANTA `ValueError` con el motivo: ver
    `historial_semilla.leer`, que es quien lo lee desde el 2026-11-22.
    """
    h = leer(_ruta_historial())
    return None if h is None else h.huellas


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
    "exige el árbol de trabajo limpio, para que el diff se pueda revisar."
)


def _atrasada(r: Resultado, ruta: str, hasta: datetime.date) -> None:
    """Una pieza que es, byte a byte, la de un lock publicado antes: atrasada, no editada.

    AVISA siempre, sin plazo (FILOSOFIA.md §3 y la decisión del 2026-10-24): es la
    fábrica de su fecha, y la aplicación se pone al día cuando quiera."""
    r.avisa(
        "SEM-1",
        ruta,
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
        "SEM-1",
        ruta,
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


def _propia_antes_del_sello(r: Resultado, ruta: str, contexto: str) -> None:
    """La aplicación tenía un archivo PROPIO en una ruta que la semilla selló después."""
    r.avisa(
        "SEM-1",
        ruta,
        "ruta que la semilla selló DESPUÉS de sembrar esta aplicación, que ya tenía aquí "
        f"un archivo propio ({contexto}): no es una pieza editada",
        "la aplicación sigue con su propia versión en esta ruta y no recibe la pieza "
        "sellada ni lo que trae; en el despliegue no cambia nada hasta que la adopte",
        arreglo="compara la tuya con `semilla/CONGELADO/" + ruta + "` de "
        "coipo_master_produccion. Lo que sólo sirve a esta aplicación, llévalo a un "
        "archivo que NO esté en el lock (`git mv`), haz commit y trae la sellada con "
        "`sembrar.py --destino . --actualizar --reponer " + ruta + "`: mientras la ruta "
        "tenga tu archivo, `--actualizar` no la pisa.",
    )


def _editada(r: Resultado, ruta: str) -> None:
    r.bloquea(
        "SEM-1",
        ruta,
        "es una pieza CONGELADA de la semilla y está editada",
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


def _leer_historial(r: Resultado) -> Historial:
    """El historial, o uno vacío con la razón anotada en `no_evaluado`. Nunca más indulgente."""
    nombre = _ruta_historial().name
    regenerar = (
        "Lo escribe `python semilla/sellar.py --escribir <ruta>/semilla.lock` "
        "en coipo_master_produccion."
    )
    try:
        historial = leer(_ruta_historial())
    except ValueError as e:
        r.no_evaluado.append(
            f"{nombre} existe pero no se pudo leer: {e}. Se IGNORA entero, así que una "
            "pieza de una semilla anterior se juzgará como EDITADA, nunca con más "
            "indulgencia. " + regenerar
        )
        return Historial()
    if historial is None:
        r.no_evaluado.append(
            f"no hay {nombre} junto al lock: este juez no puede distinguir una pieza "
            "ATRASADA de una EDITADA y juzga las dos como editadas, como antes del "
            "2026-10-24. " + regenerar
        )
        return Historial()
    return historial


def comprobar(repo: Repo, r: Resultado) -> None:
    # Que un repositorio tenga `backend/Dockerfile` no significa que lo haya copiado
    # de aquí: toda aplicación web tiene uno. Sin declaración, no hay nada que comparar.
    # El alcance (sin `.semilla`, `adopta:` vacía) lo resuelve `alcance_semilla`.
    alcance = alcance_semilla(
        repo,
        r,
        f"no hay `{MARCADOR}` en la raíz: este repositorio no se sembró con la "
        "semilla de la flota, así que sus archivos son suyos aunque se llamen "
        "igual. Si SÍ se sembró y alguien borró el marcador, restaurarlo es lo "
        "que vuelve a encender esta comprobación.",
    )
    if alcance is None:
        return
    texto_marcador, adopcion = alcance
    # El marcador puede declarar que adopta OTRA capa y no ésta: N/A, citando la
    # línea, y contado como supresión (`no_adopta` en comun.py).
    if not adopcion.adopta(CAPA):
        no_adopta(
            r,
            adopcion,
            CAPA,
            "así que las piezas congeladas de este repositorio NO se comparan contra "
            "el lock. Es legítimo en una aplicación que adopta un estándar de la "
            "flota sin haberse sembrado con la semilla; deja de serlo si el "
            "repositorio SÍ se sembró.",
        )
        return

    esperado = _lock()
    if not esperado:
        # Ruidoso a propósito. Un juez cuyo catálogo no está no se declara
        # conforme: se declara incapaz de mirar.
        r.no_evaluado.append(
            f"no se pudo leer {LOCK.name}: sin él este juez no sabe qué archivos "
            "están congelados. Se regenera con `python semilla/sellar.py "
            "--escribir <ruta>/semilla.lock` en coipo_master_produccion."
        )
        return

    m = VERSION.search(texto_marcador)
    version = m.group("version") if m else "sin declarar"

    presentes = [ruta for ruta in esperado if repo.existe(ruta)]
    if not presentes:
        r.no_evaluado.append(
            f"hay `{MARCADOR}` (version {version}) pero no está ninguno de los "
            f"{len(esperado)} archivos congelados. O el marcador quedó de un "
            f"borrado, o la siembra no llegó a copiarse: las dos hay que mirarlas."
        )
        return

    r.comprobo(
        f"piezas congeladas de la semilla {version} ({len(presentes)} de {len(esperado)} presentes)"
    )

    # Se lee ANTES del bucle y no cuando aparece la primera diferencia, para que
    # un archivo roto o ausente se anote siempre y no sólo cuando hace falta.
    historial = _leer_historial(r)

    def gracia(ruta: str) -> Siembra | None:
        # La siembra frente a la vigencia de ESA pieza (historial_semilla.py); None si no la tiene.
        vigencia = historial.vigencia(ruta)
        return (
            None if vigencia is None else leer_siembra(texto_marcador, vigencia.isoformat(), CAPA)
        )

    _juzgar_presentes(repo, r, presentes, esperado, historial.huellas, gracia)
    _juzgar_retiradas(repo, r, esperado, historial.huellas)
    _pruebas_ausentes(repo, r, esperado)
    _maqueta(repo, r)
    _paquetes_sistema(repo, r)
    _auditoria_siempre(repo, r, texto_marcador)


# AUD-1 bloquea en lo sembrado desde el día SIGUIENTE a su publicación, como FAB-9 y el
# UI-3 sin tema oscuro: lo sembrado antes no tenía cómo traerlo (FILOSOFIA.md §4).
VIGENCIA_AUDITORIA = "2026-11-22"


def _auditoria_siempre(repo: Repo, r: Resultado, texto_marcador: str) -> None:
    """AUD-1: la auditoría y el último ingreso de cada persona están (lo mira comun_auditoria)."""
    faltas = lo_que_falta(repo)
    if faltas is None:
        r.no_corresponde("AUD-1: no hay `backend/app/` en el que mirar la auditoría")
        return
    siembra = leer_siembra(texto_marcador, VIGENCIA_AUDITORIA, CAPA)
    contexto = siembra.contexto(CAPA, MARCADOR)
    for falta in faltas:
        mensaje = f"{falta.mensaje} ({contexto})"
        if siembra.nuevo:
            r.bloquea(
                "AUD-1", falta.archivo, mensaje, MANIFESTACION_AUDITORIA, arreglo=ARREGLO_AUDITORIA
            )
        else:
            r.avisa(
                "AUD-1", falta.archivo, mensaje, MANIFESTACION_AUDITORIA, arreglo=ARREGLO_AUDITORIA
            )
    r.comprobo(f"AUD-1: la auditoría siempre y el último ingreso ({contexto})")


def _juzgar_presentes(
    repo: Repo,
    r: Resultado,
    presentes: list[str],
    esperado: dict[str, str],
    historial: dict[str, dict[str, datetime.date]],
    gracia: Callable[[str], Siembra | None],
) -> None:
    """Cada pieza del lock que la aplicación tiene: vigente, suprimida, atrasada, propia de
    antes del sello o editada."""
    for ruta in sorted(presentes):
        actual = _huella(repo.ruta(ruta))
        if actual is None:
            r.no_evaluado.append(f"{ruta}: no se pudo leer.")
            continue
        if actual == esperado[ruta]:
            continue

        if motivo := suprimido(repo.lineas(ruta), 0, "SEM-1"):
            r.supresiones.append(f"{ruta} pieza congelada editada — {motivo}")
            continue

        if (hasta := historial.get(ruta, {}).get(actual)) is not None:
            _atrasada(r, ruta, hasta)
            continue

        # La semilla selló esta ruta DESPUÉS de sembrar la aplicación (su vigencia, pieza a
        # pieza, en historial_semilla.py): el archivo es suyo, no una edición.
        siembra = gracia(ruta)
        if siembra is not None and not siembra.nuevo:
            _propia_antes_del_sello(r, ruta, siembra.contexto(CAPA, MARCADOR))
            continue

        _editada(r, ruta)


def _juzgar_retiradas(
    repo: Repo,
    r: Resultado,
    esperado: dict[str, str],
    historial: dict[str, dict[str, datetime.date]],
) -> None:
    """Las piezas que la semilla RETIRÓ del lock y siguen en el historial. Sólo se mira
    si coinciden con lo que se publicó: si no coinciden, ya no son piezas congeladas y
    no hay regla que mire hacia atrás (FILOSOFIA.md, §4)."""
    for ruta in sorted(set(historial) - set(esperado)):
        if not repo.existe(ruta):
            continue
        actual = _huella(repo.ruta(ruta))
        if actual is None or (hasta := historial[ruta].get(actual)) is None:
            continue
        if motivo := suprimido(repo.lineas(ruta), 0, "SEM-1"):
            r.supresiones.append(f"{ruta} pieza retirada de la semilla — {motivo}")
            continue
        _retirada(r, ruta, hasta)


# ── SEM-3: una prueba sellada que falta ───────────────────────────────────────
#
# Que falte una pieza del lock NO es un hallazgo (ver la cabecera): no toda aplicación
# usa todas. Las de `backend/tests/` son otra cosa. Son las pruebas de contrato y de
# arquitectura —y su arnés— que `semilla/README.md` de la fábrica declara CONGELADAS
# («los tests de contrato») y que «por tanto corre[n] en cada aplicación»: borrar una no
# rompe nada, la CALLA, y hasta el 2026-11-21 el gate seguía en verde. AVISA: o se borró,
# o la semilla la trajo después de sembrar esta aplicación (`--actualizar` la trae).
PRUEBAS_SELLADAS = "backend/tests/"


def _pruebas_ausentes(repo: Repo, r: Resultado, esperado: dict[str, str]) -> None:
    if not repo.existe("backend/app"):
        return  # sin backend no hay pruebas del backend que exigir
    marcador = repo.lineas(MARCADOR)
    ausentes = sorted(
        ruta for ruta in esperado if ruta.startswith(PRUEBAS_SELLADAS) and not repo.existe(ruta)
    )
    for ruta in ausentes:
        # Un archivo que no está no admite marcador: la supresión va en `.semilla`,
        # nombrando la pieza en la misma línea que el marcador.
        motivo = next(
            (
                m
                for i, linea in enumerate(marcador)
                if ruta in linea and (m := suprimido(marcador, i, "SEM-3"))
            ),
            None,
        )
        if motivo:
            r.supresiones.append(f"{ruta} prueba sellada ausente — {motivo}")
            continue
        r.avisa(
            "SEM-3",
            ruta,
            f"falta una pieza sellada de `{PRUEBAS_SELLADAS}` (las pruebas "
            "de la semilla y su arnés)",
            "la guarda que esta prueba aplica en cada aplicación de la flota deja de "
            "correr aquí, y nada se pone rojo: el CI pasa porque hay una prueba menos, no "
            "porque el código cumpla",
            arreglo="traerla de la semilla —" + ACTUALIZAR + " Si de verdad no aplica, "
            f"`# coipo-jueces:ignorar(SEM-3) {ruta}: <motivo>` en `.semilla`: se "
            "cuenta y se publica.",
        )
    r.comprobo(
        f"SEM-3: {sum(1 for p in esperado if p.startswith(PRUEBAS_SELLADAS))} "
        f"prueba(s) sellada(s) de `{PRUEBAS_SELLADAS}`, {len(ausentes)} ausente(s)"
    )


PAQUETES = "backend/paquetes-sistema.txt"
_COMPILADOR = re.compile(r"^(gcc|g\+\+|make|build-essential|.+-dev)$")
_MANIFESTACION_PAQ = (
    "un paquete de sistema sin motivo no lo retira nadie y la imagen crece en cada "
    "aplicación; un compilador en la imagen de producción es superficie de ataque y "
    "builds de minutos"
)


def _paquetes_sistema(repo: Repo, r: Resultado) -> None:
    """SEM-2: la lista apt que lee el `backend/Dockerfile` sellado (desde el 2026-11-20).

    Cada línea lleva su motivo y ninguna instala un compilador. AVISA, no bloquea
    (FILOSOFIA.md §4 de la fábrica: una regla nueva mira hacia adelante): la regla es
    nueva y la lista es de la aplicación.
    """
    texto = repo.texto(PAQUETES)
    if texto is None:
        return
    lineas = texto.splitlines()
    r.comprobo(f"SEM-2: {PAQUETES}")
    for n, linea in enumerate(lineas, start=1):
        datos, _, motivo = linea.partition("#")
        for paquete in datos.split():
            if _COMPILADOR.match(paquete):
                r.avisa(
                    "SEM-2",
                    PAQUETES,
                    f"línea {n}: `{paquete}` es para compilar, no para ejecutar",
                    _MANIFESTACION_PAQ,
                    arreglo="usar la versión de la dependencia que trae rueda "
                    "precompilada; si de verdad hay que compilar, en una "
                    "etapa de build aparte, llevada a la semilla",
                )
        if datos.strip() and len(motivo.strip()) < 12:
            r.avisa(
                "SEM-2",
                PAQUETES,
                f"línea {n}: `{datos.strip()}` sin motivo (o de menos de 12 caracteres)",
                _MANIFESTACION_PAQ,
                arreglo="escribir en la misma línea qué dependencia lo exige: "
                "`libexpat1  # rasterio 1.5.2 la carga al importar`",
            )


PROCEDENCIA = "maqueta/PROCEDENCIA.md"
CARA = "frontend/src/maqueta/"
_FILA_HASH = re.compile(
    r"^\|\s*`(?P<ruta>[^`]+)`\s*\|\s*`(?P<sha>[0-9a-f]{64})`\s*\|", re.MULTILINE
)
_MANIFESTACION_MAQ = (
    "la aplicación deja de verse como la maqueta que validó el cliente, y nadie lo nota "
    "hasta que el cliente la abre: es lo que pasó con coipo_catastro_equipo"
)


def _maqueta(repo: Repo, r: Resultado) -> None:
    """MAQ-1: la cara copiada de la maqueta validada no se edita.

    `sembrar.py --maqueta` copia su CSS, fuentes e imágenes a `frontend/src/maqueta/` y
    deja el sha256 de cada uno en `maqueta/PROCEDENCIA.md`. AVISA, no bloquea (FILOSOFIA.md
    §4 de la fábrica: una regla nueva mira hacia adelante): la regla es del 2026-11-12 y
    todavía no se calibró sobre ninguna aplicación real.
    """
    maqueta = leer_maqueta(repo.texto(MARCADOR))
    if maqueta is None:
        return
    procedencia = repo.texto(PROCEDENCIA)
    arreglo = (
        "deshacer la edición y poner lo propio en una hoja aparte, importada "
        "después (prompts/06-portar-una-maqueta.md); si el cliente validó otra "
        "versión, `sembrar.py --maqueta <origen> --commit <sha> --solo-maqueta`"
    )
    if procedencia is None:
        r.avisa(
            "MAQ-1",
            PROCEDENCIA,
            f"`{MARCADOR}` declara la maqueta {maqueta[1]} y falta su procedencia",
            _MANIFESTACION_MAQ,
            arreglo=arreglo,
        )
        return
    filas = list(_FILA_HASH.finditer(procedencia))
    r.comprobo(f"MAQ-1: {len(filas)} archivo(s) de la cara de la maqueta contra su sha256")
    if not filas:
        r.no_evaluado.append(f"{PROCEDENCIA} no lista ningún sha256: no hay contra qué comparar.")
    for f in filas:
        ruta = CARA + f.group("ruta")
        if not repo.existe(ruta):
            r.avisa(
                "MAQ-1",
                ruta,
                "falta un archivo de la cara validada de la maqueta",
                _MANIFESTACION_MAQ,
                arreglo=arreglo,
            )
            continue
        # Con `\r\n` pasado a `\n`, como SEM-1 y como `siembra/maqueta.py`: git cambia los
        # finales de línea al hacer checkout, y eso no es editar la cara.
        actual = hashlib.sha256(repo.ruta(ruta).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != f.group("sha"):
            r.avisa(
                "MAQ-1",
                ruta,
                "el archivo de la maqueta validada no coincide con su "
                f"sha256 de {PROCEDENCIA}: alguien editó la cara que aprobó el cliente",
                _MANIFESTACION_MAQ,
                arreglo=arreglo,
            )


if __name__ == "__main__":
    ejecutar("j12", "las piezas congeladas de la semilla no se editan por aplicación", comprobar)
