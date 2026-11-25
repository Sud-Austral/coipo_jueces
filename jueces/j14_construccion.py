#!/usr/bin/env python3
"""j14 — construir con la fábrica: `docs/CONSTRUCCION.md` completo y con rastro.

Implementa la mitad «¿construyó con ellas?» de la regla 8 de `AGENTS.md` de
`coipo_master_produccion` (sección 3): antes de la primera línea de código se
ejecuta `prompts/05-consultar-la-fabrica.md` —la metodología «Construir una
aplicación COIPO con la fábrica» en IGNUS, el grafo y el instrumento—, y todo deja
rastro en `docs/CONSTRUCCION.md` con los `correlation_id` de IGNUS: «es lo único
que distingue un archivo escrito tras consultar de uno escrito de memoria».

  FAB-8  `docs/CONSTRUCCION.md` existe (y está versionado, si hay git), no le queda
         ningún `[PENDIENTE]` ni `[VERIFICAR]` de la plantilla de la semilla,
         declara `metodologia:`, `instancia:`, `objetivos:` y `consultas:`, cita
         una metodología de IGNUS (`smb-metodologia-…`) y al menos un
         `correlation_id` con forma válida (`corr-<10+ dígitos>-<6+ hex>`, o
         `corr-maestro-…`). Sin `registrado:` sólo avisa. Desde el 2026-11-24 el MCP
         es recomendado, no obligatorio: sin `correlation_id`, una línea
         `copia-local metodologia_coipo.json <fecha> sha256:<64 hex>` (la copia
         versionada de la fábrica) baja el hallazgo a AVISA.

LA LÓGICA DE REFERENCIA es `flota/herramientas_de_fabrica.py --construccion` de la
fábrica (`juzgar_construccion`, que desde el 2026-11-21 vive en
`flota/herramientas_de_fabrica_construccion.py`), calibrada allí: mismas
expresiones, mismos campos. Esa fábrica prueba la PARIDAD de los dos lectores con
`test_paridad_con_j14_de_coipo_jueces_si_esta_clonado_al_lado`
(`flota/probar_herramientas_de_fabrica_construccion.py`) cuando este
repositorio está clonado al lado: sobre los mismos textos, buenos y rotos, el
instrumento da HALLAZGOS si y sólo si este juez BLOQUEA (con `fabrica:` vigente).
Esa prueba crea la aplicación SIN git: por eso este juez lee el disco y sólo
exige «versionado» cuando hay repositorio.

LÍMITE CONOCIDO, Y SE DICE: ESTE JUEZ SÓLO MIRA LA FORMA. No llama a IGNUS: en el
CI no tiene red hacia `mcp.conaf.cl` ni `MCP_API_KEY`, y no debe tenerla (es un
workflow público que corre en el CI de cualquier aplicación). Un `correlation_id`
inventado con la forma correcta pasa. Que la metodología y las llamadas existan de
verdad lo comprueba el instrumento de la fábrica con la clave en el entorno
(`herramientas_de_fabrica.py --construccion`), y el juez lo anota como no
evaluado cada vez, para que el verde no se lea como más de lo que es.

MIRA HACIA ADELANTE (`FILOSOFIA.md` de la fábrica, §3 y §4), como `j16`:

    fabrica >= VIGENCIA (2026-10-20), adopta semilla -> BLOQUEA. Desde ese día la
                                    semilla trae la plantilla y la skill
                                    `construir-con-la-fabrica` que lleva al paso 05.
    fabrica >= VIGENCIA, sin `semilla` en `adopta:` -> AVISA, y se CUENTA COMO
                                    SUPRESIÓN: es reclamar menos de lo que
                                    corresponde (ver `adopta:` en comun.py).
    `adopta:` vacía                 -> SIN_EVALUAR, con la línea: una declaración
                                    rota no se juzga (la semántica única de
                                    `adopta:`, en comun_semilla.py, desde el
                                    2026-10-25; antes se juzgaba como «todo»).
    fabrica <  VIGENCIA, o sin ella -> AVISA. La deuda se ve; nada se detiene.
    sin `.semilla`                  -> NO_APLICA: el alcance se declara.
    perfil `encuadre_operativo`     -> no corre (`PERFILES`): software de terceros.

LA FECHA, 2026-10-20, no la eligió este juez: es la de `AGENTS.md` §3.8 («bloquea
en lo sembrado desde el 2026-10-20 —el `.semilla` lleva `fabrica: AAAA-MM-DD`— y
avisa en lo anterior»), el día de la segunda generación que «escribió todos los
archivos a mano» (`docs/APRENDIZAJES-DE-GENERACION.md`).

CALIBRACIÓN INVERSA (2026-10-25, sobre los 88 repositorios `coipo*` con git de
D:\\GitHub y las tres aplicaciones de prueba sembradas el 2026-10-24)
  coipo_prueba_biblioteca, coipo_prueba_huerto,
  coipo_prueba_divisas          -> OK: `CONSTRUCCION.md` completo, `fabrica:` 2026-10-24.
  coipo_firms                   -> OK: sembrado el 2026-10-23 y con el archivo
                                   completo (seis `correlation_id`). Es el único del
                                   disco con `fabrica:` vigente; despliega en advisory.
  coipo_atraso_personal, coipo_prensa2, coipo_anillo_evacuacion, coipo_api,
  coipo_avisete, coipo_camara_deteccion, coipo_gestion_incendio,
  coipo_prevension_ministerial, coipo_saff_paralelo, coipo_visor_saff,
  coipo_visor_sidco             -> AVISA (sin el archivo), CERO bloqueos: no tienen
                                   `fabrica:` (anteriores a la clave).
  los 76 sin `.semilla`, entre ellos coipo_n8n, coipo_jueces y COIPO_USUARIOS
                                -> NO_APLICA.
  Controles negativos: la plantilla de la semilla tal cual, con `fabrica:` vigente,
  BLOQUEA 16 veces (sus 15 `[PENDIENTE]`, cada uno con su línea, y la falta de
  `correlation_id`); una copia de coipo_prueba_divisas con los `correlation_id`
  borrados, o con la metodología borrada, BLOQUEA y sale 1 en modo bloqueante.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    Adopcion,
    Repo,
    Resultado,
    alcance_semilla,
    ejecutar,
    leer_siembra,
    sin_indice,
)

PERFILES = ("aplicacion",)

FAB_8 = "FAB-8"

# `AGENTS.md` de la fábrica, §3, punto 8. Ver el docstring.
VIGENCIA = "2026-10-20"

MARCADOR = ".semilla"
CAPA = "semilla"
CONSTRUCCION = "docs/CONSTRUCCION.md"

# Las mismas expresiones que `juzgar_construccion` de la fábrica: si una cambia
# allí, cambia aquí, y la prueba de paridad de la fábrica lo vigila.
CAMPOS = ("metodologia", "instancia", "objetivos", "consultas")
METODOLOGIA = re.compile(r"\bsmb-metodologia-[a-z0-9-]+\b")
CORRELACION = re.compile(r"\bcorr-(?:maestro-)?\d{10,}-[0-9a-f]{6,}\b")
PENDIENTE = re.compile(r"\[(?:PENDIENTE|VERIFICAR)\]")
REGISTRADO = re.compile(r"^\s*registrado:", re.MULTILINE | re.IGNORECASE)
# Sin MCP, la consulta se hace sobre la COPIA versionada de la metodología
# (`flota/metodologia_coipo.json` de la fábrica) y se cita con su sha256. Conectarse
# a IGNUS es lo recomendado, no una obligación: decisión de Luis Monsalve del
# 2026-11-24, después de que un colega quedara obligado a conectarse sólo para
# pasar este juez. Con la copia, FAB-8 avisa en vez de bloquear.
COPIA_LOCAL = re.compile(r"\bcopia-local\b[^\n]*\bmetodologia_coipo\.json\b[^\n]*\bsha256:[0-9a-f]{64}\b")

PASO = (
    "`prompts/05-consultar-la-fabrica.md` de coipo_master_produccion (la skill "
    "`construir-con-la-fabrica` de la semilla lleva allí)"
)

_MANIFESTACION = (
    "la aplicación no deja rastro de haber consultado IGNUS, el grafo ni el instrumento "
    "antes de escribirse, y entonces no se distingue de una escrita de memoria: así salió "
    "la generación del 2026-10-20, con catorce o quince hallazgos de los jueces por "
    "monitor, y nada lo detectó hasta la auditoría"
)


def _anota(r: Resultado, nuevo: bool, **datos: object) -> None:
    """BLOQUEA en lo sembrado desde la vigencia; AVISA en lo anterior.

    Dos llamadas explícitas y no una variable con el método: `test_reglas_citadas`
    lee las llamadas a `bloquea`/`avisa` del AST para saber qué emite cada juez."""
    if nuevo:
        r.bloquea(FAB_8, **datos)  # type: ignore[arg-type]
    else:
        r.avisa(FAB_8, **datos)  # type: ignore[arg-type]


def _severidad(marcador: str, adopcion: Adopcion, r: Resultado) -> tuple[bool, str]:
    """(¿bloquea?, contexto para el mensaje), desde `fabrica:` y `adopta:`.

    Las cuatro ramas y sus textos viven en `Siembra` (comun_semilla.py), compartidas
    con j16; aquí queda lo propio: la supresión cuando FAB-8 baja a AVISA."""
    siembra = leer_siembra(marcador, VIGENCIA, CAPA)
    if siembra.vigente and not siembra.adopta:
        razon = (
            f"{adopcion.cita(MARCADOR)} y no incluye `{CAPA}`: FAB-8 baja de BLOQUEA "
            f"a AVISA en un repositorio sembrado el {siembra.fecha}. Es legítimo sólo si "
            "el repositorio NO se sembró con la semilla."
        )
        r.supresiones.append(f"{MARCADOR} declara no adoptar `{CAPA}` — {razon}")
    return siembra.nuevo, siembra.contexto(CAPA, MARCADOR)


def comprobar(repo: Repo, r: Resultado) -> None:
    # Sin `.git` se lee el disco (la prueba de paridad de la fábrica crea la
    # aplicación así). Con un `.git` que git no puede leer, no se sabe si
    # `CONSTRUCCION.md` está versionado: no se dictamina (auditoría del 2026-10-25).
    if repo.tiene_git() and sin_indice(repo, r):
        return
    alcance = alcance_semilla(
        repo,
        r,
        f"no hay `{MARCADOR}`: el repositorio no declara haberse construido con la "
        "fábrica. Lo que existía antes de ella no se juzga con sus reglas nuevas "
        "(FILOSOFIA.md, §3).",
    )
    if alcance is None:
        return
    marcador, adopcion = alcance

    nuevo, contexto = _severidad(marcador, adopcion, r)

    ruta = repo.ruta(CONSTRUCCION)
    if not ruta.is_file():
        _anota(
            r,
            nuevo,
            archivo=CONSTRUCCION,
            mensaje=f"no existe `{CONSTRUCCION}` ({contexto})",
            manifestacion=_MANIFESTACION,
            arreglo=f"ejecutar {PASO} y dejar el archivo con la metodología, los "
            "objetivos aplicados y el `correlation_id` de cada consulta",
        )
        r.comprobo(f"FAB-8: buscado `{CONSTRUCCION}` ({contexto})")
        return
    r.comprobo(f"FAB-8: buscado `{CONSTRUCCION}` ({contexto})")

    _no_versionado(repo, r, nuevo, contexto)
    texto = repo.texto(CONSTRUCCION) or ""
    ids, correlaciones = _forma(r, nuevo, contexto, texto)

    _mirado(repo, r, marcador, texto)

    r.comprobo(
        f"FAB-8: `{CONSTRUCCION}` leído — {len(ids)} metodología(s) citada(s), "
        f"{len(correlaciones)} `correlation_id` con forma válida"
    )
    if ids or correlaciones:
        r.no_evaluado.append(
            "que la metodología y los `correlation_id` de `docs/CONSTRUCCION.md` existan "
            "DE VERDAD en IGNUS: este juez no tiene red ni `MCP_API_KEY` en el CI y sólo "
            "mira la forma. Lo comprueba `python flota/herramientas_de_fabrica.py "
            "--construccion <repo>` en la fábrica, con la clave en el entorno."
        )


def _no_versionado(repo: Repo, r: Resultado, nuevo: bool, contexto: str) -> None:
    if repo.tiene_git():
        versionados = repo.versionados()
        if versionados and CONSTRUCCION not in versionados:
            _anota(
                r,
                nuevo,
                archivo=CONSTRUCCION,
                mensaje=f"`{CONSTRUCCION}` existe en el disco pero no está versionado ({contexto})",
                manifestacion=(
                    "el rastro se queda en el equipo de quien construyó: el CI, "
                    "el despliegue y la persona que herede la aplicación no lo ven"
                ),
                arreglo=f"`git add {CONSTRUCCION}` y comprobar que `.gitignore` no lo excluye",
            )


def _forma(r: Resultado, nuevo: bool, contexto: str, texto: str) -> tuple[list[str], list[str]]:
    """La forma de `CONSTRUCCION.md`: sin pendientes, con sus campos, una metodología,
    algún `correlation_id` y `registrado:`. Devuelve (metodologías, correlation_id)."""
    for m in PENDIENTE.finditer(texto):
        _anota(
            r,
            nuevo,
            archivo=CONSTRUCCION,
            linea=texto.count("\n", 0, m.start()) + 1,
            mensaje=f"queda un `{m.group(0)}` de la plantilla de la semilla ({contexto})",
            manifestacion=(
                "la plantilla a medio rellenar se lee como hecha: el archivo "
                "existe y el paso de consultar la fábrica no se dio entero"
            ),
            arreglo=f"completar el campo con lo que de verdad se consultó ({PASO}); si no "
            "aplica, escribir «no aplica: <motivo>»",
        )

    for campo in CAMPOS:
        if not re.search(rf"^\s*{campo}:", texto, flags=re.MULTILINE | re.IGNORECASE):
            _anota(
                r,
                nuevo,
                archivo=CONSTRUCCION,
                mensaje=f"falta el campo `{campo}:` ({contexto})",
                manifestacion=_MANIFESTACION,
                arreglo=f"escribir `{campo}:` como en la plantilla de "
                "`semilla/ESQUELETO/docs/CONSTRUCCION.md`",
            )

    ids = list(dict.fromkeys(METODOLOGIA.findall(texto)))
    if not ids:
        _anota(
            r,
            nuevo,
            archivo=CONSTRUCCION,
            mensaje=f"no cita ninguna metodología de IGNUS (`smb-metodologia-…`) ({contexto})",
            manifestacion=_MANIFESTACION,
            arreglo=(
                "`metodologia:` con el `sombrero_id` de «Construir una aplicación "
                "COIPO con la fábrica» (empieza por "
                "`smb-metodologia-construir-una-aplicacion-coipo`), leída con "
                "`ver_metodologia`"
            ),
        )

    correlaciones = list(dict.fromkeys(CORRELACION.findall(texto)))
    if not correlaciones and COPIA_LOCAL.search(texto):
        r.avisa(
            FAB_8,
            CONSTRUCCION,
            "se consultó la copia local de la metodología, no IGNUS: vale, pero conectarse "
            "al MCP es lo recomendado",
            "la copia puede ir atrás de IGNUS y lo aprendido no queda registrado en el grafo",
            arreglo="cuando haya acceso a `mcp-metodologias`, repetir `ver_metodologia` y "
            "copiar su `correlation_id` en `consultas:`",
        )
    elif not correlaciones:
        _anota(
            r,
            nuevo,
            archivo=CONSTRUCCION,
            mensaje=f"ningún `correlation_id` con forma válida: no hay rastro de haber "
            f"consultado IGNUS ({contexto})",
            manifestacion=_MANIFESTACION,
            arreglo=(
                "copiar en `consultas:` el `correlation_id` de CADA respuesta de "
                "IGNUS (`corr-<dígitos>-<hex>`), con la herramienta y la fecha; o, sin "
                "MCP, `copia-local metodologia_coipo.json <fecha> sha256:<64 hex>` de la "
                "copia que se leyó"
            ),
        )

    if not REGISTRADO.search(texto):
        r.avisa(
            FAB_8,
            CONSTRUCCION,
            "no dice qué se registró en IGNUS al cerrar (`registrado:`)",
            "lo aprendido construyendo se queda en la sesión que lo aprendió: la "
            "siguiente aplicación tropieza con lo mismo",
            arreglo="`registrado:` con el `objetivo_id` creado en IGNUS y su "
            "`correlation_id`, o «no aplica: <motivo>»",
        )
    return ids, correlaciones


# ── FAB-9: alguien MIRÓ la interfaz antes de desplegar ───────────────────────
#
# coipo_catastro_equipo llegó al CI con un frontend que nadie construyó ni miró en la
# máquina que lo escribió (su CONSTRUCCION.md lo dice), y salió sin parecerse a la
# maqueta que el cliente había validado. Una verificación que lee el código no ve eso
# (2026-11-12, decisión de Luis Monsalve). FAB-9 pide el registro de lo que se miró:
# `mirado:` en CONSTRUCCION.md, con qué se miró (`npm run capturas`, `npm run
# comparar:maqueta`) y qué se vio. Sólo la forma: las capturas no se versionan.
FAB_9 = "FAB-9"
# Desde el día SIGUIENTE a su publicación: con el 2026-11-12, coipo_catastro_equipo y
# coipo_catastro_equipos (sembradas ese día, antes de que la regla existiera) pasaban de
# 0 a 1 bloqueante, y una regla que cambia el veredicto de lo que ya existe es mayor
# nueva (docs/VERSIONADO.md, enmienda del 2026-10-25). Medido sobre 84 repositorios.
VIGENCIA_MIRADO = "2026-11-13"
MIRADO = re.compile(
    r"^[ \t]*(?:-[ \t]*)?mirado[ \t]*:[ \t]*(?P<valor>[^\r\n]*)", re.MULTILINE | re.IGNORECASE
)


def _mirado(repo: Repo, r: Resultado, marcador: str, texto: str) -> None:
    if not repo.existe("frontend/package.json"):
        # N/A y no una comprobación: hasta el 2026-11-21 esto contaba como mirado.
        r.no_corresponde("FAB-9: no hay `frontend/package.json`; no hay interfaz que mirar")
        return
    siembra = leer_siembra(marcador, VIGENCIA_MIRADO, CAPA)
    nuevo = siembra.nuevo
    contexto = (
        f"sembrado el {siembra.fecha}, con la regla vigente desde el {VIGENCIA_MIRADO}"
        if nuevo
        else f"regla del {VIGENCIA_MIRADO}, anterior a esta aplicación o "
        "sin `semilla` adoptada: sólo aviso"
    )
    m = MIRADO.search(texto)
    valor = m.group("valor").strip() if m else ""
    if not (m and len(valor) >= 12 and not PENDIENTE.search(valor)):
        _sin_mirado(r, nuevo, contexto, texto, m)
    r.comprobo(f"FAB-9: buscado `mirado:` en `{CONSTRUCCION}` ({contexto})")


def _sin_mirado(
    r: Resultado, nuevo: bool, contexto: str, texto: str, m: re.Match[str] | None
) -> None:
    datos = dict(
        archivo=CONSTRUCCION,
        linea=texto.count("\n", 0, m.start()) + 1 if m else None,
        mensaje=(
            f"no dice qué se MIRÓ de la interfaz antes de desplegar (`mirado:` "
            f"{'vacío o pendiente' if m else 'ausente'}) ({contexto})"
        ),
        manifestacion=(
            "la interfaz llega a producción sin que nadie la haya visto: así salió "
            "coipo_catastro_equipo, sin parecerse a la maqueta que validó el cliente"
        ),
        arreglo=(
            "`npm run build` y `npm run capturas` (o `npm run comparar:maqueta` si hay "
            "maqueta), mirar los PNG y escribir `mirado: <fecha>, <comando>, <qué se vio>`"
        ),
    )
    if nuevo:
        r.bloquea(FAB_9, **datos)  # type: ignore[arg-type]
    else:
        r.avisa(FAB_9, **datos)  # type: ignore[arg-type]


if __name__ == "__main__":
    ejecutar(
        "j14", "construir con la fábrica: docs/CONSTRUCCION.md completo y con rastro", comprobar
    )
