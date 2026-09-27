#!/usr/bin/env python3
"""j15 — un job de pago en el `needs:` de un job que corre gratis.

EL INCIDENTE QUE FUNDA ESTA REGLA
=================================
El 2026-09-26 la organización agotó los 2.000 min/mes de Actions del plan Free
(2.086 facturables medidos) y **se quedó sin poder desplegar a producción**. La
causa raíz no fue el gasto: fue la FORMA del grafo. Siete repositorios tenían su
job de `deploy` —que corre en un runner self-hosted y por tanto es GRATIS— con un
`needs:` hacia una compuerta que corría en un runner ALOJADO de GitHub, o sea de
pago. Sin cuota, la compuerta no arranca; y lo que cuelga de un `needs:` que no
arranca no se ejecuta nunca. El despliegue gratis murió por una dependencia que
no lo era.

Se volvió a ver medido el 2026-09-27, en un mismo run de
`coipo_master_produccion`: los tres jobs del runner propio arrancaron con 21, 18
y 11 pasos, y el único en `windows-latest` salió con **runner vacío y cero
pasos**, con la anotación literal «The job was not started because recent account
payments have failed or your spending limit needs to be increased».

Esa anotación es la manifestación de esta regla, y no hay que inventarla.

QUÉ CUENTA COMO «GRATIS» Y QUÉ COMO «DE PAGO», Y POR QUÉ SE RAZONA ASÍ
======================================================================
Lo que hace facturable a un runner es **ser de GitHub**, no ser distinto de las
etiquetas de esta casa. La lista de GitHub es cerrada y conocida —`ubuntu-*`,
`windows-*`, `macos-*`, incluidas las variantes `*-cores` y `*-arm`—, así que se
razona por ella y **cualquier otra etiqueta se trata como self-hosted**. Contadas
hoy (2026-09-27) en los workflows de la flota local: `conaf-ci` 82 usos,
`conaf-uat` 18, `conaf-prod` 8. No están cableadas como lista blanca a propósito:
el día que aparezca `conaf-vm4`, el juez la entiende sin tocar una línea.

EL PRECIO, QUE MERECE SALIR EN EL MENSAJE: los runners Windows de GitHub facturan
al DOBLE que los Linux y los macOS al DIEZ POR UNO. Un minuto de `macos-latest`
en el `needs:` de un despliegue gratis gasta diez veces más rápido la cuota que
va a dejar ese despliegue sin arrancar.

LO DIFÍCIL: HAY QUE RESOLVER CADENAS
====================================
Un job puede ser facturable de dos maneras, y la segunda es la que importa:

  (a) directamente, con `runs-on:`;
  (b) a través de un `uses:` a un workflow reutilizable, que es EL QUE DECIDE el
      runner. Puede ser local (`./.github/workflows/ci.yml`) —y entonces se lee—
      o de otro repositorio, y entonces no.

Y un reusable puede recibir el runner como INPUT. Es exactamente el caso de
`coipo_jueces/.github/workflows/verificar.yml`, que desde `v2.0.9` acepta
`runner:` con `default: ubuntu-latest`: **un job que pasa `runner: conaf-ci` es
gratis y uno que no pasa nada es de pago por el valor por defecto**. Esa
distinción es el corazón de este juez, y es la que ya cerró el incidente en
`coipo_prensa2`, `coipo_api` y `coipo_atraso_personal`.

LA REGLA DE ORO: SIN_EVALUAR, Y NUNCA SILENCIO
==============================================
Cuando la cadena no se puede resolver —el reusable vive en un repositorio que
este juez no puede abrir, la etiqueta viene de una expresión, el runner llega por
`matrix`— el veredicto es `no_evaluado` **con el nombre del job, la ruta y el
`uses:` literal**, nunca silencio. «No lo sé» es una respuesta útil; «no encontré
nada» presentado como «no hay nada» es el fallo que este repositorio documenta
una y otra vez (comun.py:82-86).

POR QUÉ NO EXIGE QUE EL JOB GRATIS SEA «EL DESPLIEGUE»
======================================================
El encargo se titula «job facturable en el `needs:` de un despliegue», y la
tentación es filtrar por eso. No se hace, y conviene saber por qué.

`j01_despliegue.py:81-94` y `j08_rsync.py:104-110` sí identifican despliegues,
pero lo hacen A NIVEL DE REPOSITORIO y con una sola señal: **existe un compose en
la raíz**, porque `rsync` + `docker compose up` + `curl /health` es todo lo que
hace el reusable de la flota. Ese criterio se reutiliza aquí tal cual —se llama
`repositorio_desplegable()` y es una copia consciente de `es_desplegable()`— y
sirve para redactar el hallazgo. Pero **no dice qué JOB es el despliegue**, y
dentro de un workflow no hay ninguna señal que lo diga sin adivinar por el
nombre, que es justo lo que el encargo prohíbe.

Así que la regla se apoya en el mecanismo, que es el mismo en los dos casos: un
job gratis con una dependencia de pago **no se ejecuta cuando se agota la cuota**.
Si ese job es el despliegue, para la producción (2026-09-26); si es la compuerta
que protege el despliegue, para la compuerta, y un despliegue sin compuerta es el
defecto que `coipo_atraso_personal/deploy.yml:17-24` documenta haber cerrado. Los
dos merecen el mismo aviso. Y el error de clasificación es asimétrico: gatear por
«¿es el deploy?» y equivocarse esconde el incidente entero, mientras que no
gatear cuesta un AVISA con una frase de más.

LAS DOS PUERTAS QUE EVITAN EL FALSO POSITIVO, Y SON LAS QUE PIDE EL ENCARGO
===========================================================================
  1. Un `needs:` hacia un job alojado NO es un defecto si el job que depende
     TAMBIÉN es alojado: si los dos son de pago, la cuota los mata a los dos y no
     hay nada gratis que rescatar.
  2. Tampoco lo es en un repositorio sin ningún runner propio: el hallazgo exige
     que el job dependiente esté resuelto como GRATIS, así que un repositorio
     entero en runners de GitHub no produce ni un aviso.

CALIBRACIÓN INVERSA (medida el 2026-09-27)
==========================================
Una regla nueva se valida contra el código que YA SE SABE BUENO, y esta tiene
algo que casi ninguna tiene: **el mismo repositorio en sus dos estados**, antes
y después del arreglo. Las dos mitades se midieron.

A. EL ESTADO DE HOY — los 32 repositorios de `D:/GitHub` con
   `.github/workflows/`: 60 archivos, 126 jobs, 55 aristas de `needs:`.
     60 de 60 workflows troceados · 0 jueces reventados · 0 `no_evaluado`
     **0 hallazgos**, los 32 en verde.
   Es lo que tiene que salir: la flota SE CORRIGIÓ entre el 26 y el 27 de
   septiembre, y ocho de esos repositorios llevan el comentario del arreglo
   escrito en su propio YAML.

B. EL ESTADO ANTERIOR AL INCIDENTE — el mismo juez, sin tocar una línea, sobre
   el último commit de cada repositorio anterior al 2026-09-26, reconstruido con
   `git show <sha>:<workflow>`:

     coipo_prensa2                 2 avisos  `deploy` y `deploy-uat` de ci.yml
     coipo_grafana                 2 avisos  deploy-prod.yml y deploy-uat.yml
     coipo_api                     1 aviso
     coipo_atraso_personal         1 aviso
     coipo_umami                   1 aviso
     coipo_prevension_ministerial  1 aviso
     COIPO_USUARIOS                1 aviso
     coipo_boton_rojo              1 aviso
     coipo_master_produccion       0 — correcto: sus jobs no cuelgan de nada
                                       de pago, y su job de `windows-latest`
                                       no está en el `needs:` de nadie
     ------------------------------------------------------------------
     8 repositorios · 10 avisos · 0 `no_evaluado` · 0 reventados

   Los ocho son los «siete repositorios» que el incidente nombra más
   `coipo_boton_rojo`. **El juez distingue el commit roto del commit arreglado
   sobre código real**, que es lo más cerca que se puede estar de saber que una
   regla sirve.

LO QUE ESTA CALIBRACIÓN NO DEMUESTRA, Y HAY QUE DECIRLO
  Que hoy salgan 0 hallazgos NO es evidencia de que el juez funcione: un juez
  vacío daría lo mismo. Lo que lo demuestra es la mitad B, y dentro de este
  repositorio —que es público y no puede llevar un YAML privado de fixture— esa
  evidencia vive en los positivos sintéticos de `tests/test_j15_cuota.py`, que
  reproducen el grafo del incidente a mano. `PruebaDelPropioJuez` existe
  precisamente para que vaciar `comprobar()` no deje la suite en verde.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, suprimido  # noqa: E402

PERFILES = ("aplicacion", "encuadre_operativo")

REGLA = "CUOTA-1"

RUTA_WORKFLOW = re.compile(r"^\.github/workflows/.*\.ya?ml$")

# Las etiquetas de GitHub, por FAMILIA y no por lista blanca de esta casa: la
# lista de GitHub es cerrada, la de la flota crece. Cubre `ubuntu-latest`,
# `ubuntu-22.04`, `ubuntu-24.04-arm`, `windows-2025`, `macos-15`,
# `macos-13-xlarge` y los runners grandes `*-4-cores`, que son los mismos
# minutos multiplicados.
FAMILIA_ALOJADA = re.compile(r"^(?P<familia>ubuntu|windows|macos)-[A-Za-z0-9._-]+$",
                             re.IGNORECASE)

# Multiplicadores de facturación de GitHub, para que el coste salga en el
# mensaje cuando aplique. Linux es 1 y no se nombra.
MULTIPLICADOR = {"windows": "el DOBLE", "macos": "DIEZ VECES"}

# La palabra reservada de GitHub. Si está en la lista, el runner es propio
# aunque lleve al lado una etiqueta con pinta de imagen de GitHub.
SELF_HOSTED = "self-hosted"

# El valor por defecto del input `runner` del reusable de este repositorio.
#
# Se escribe como CONSTANTE y no se lee del disco a propósito: cuando un
# repositorio de la flota llama a `verificar.yml@v2.0.9` desde otro repositorio,
# el archivo que manda es el de ESA referencia, no el que haya aquí hoy. La
# constante se cruza contra `.github/workflows/verificar.yml` en
# `tests/test_j15_cuota.py`, así que no puede quedarse atrás en silencio.
#
# Verificado el 2026-09-27 en verificar.yml:52-59. Y antes de que el input
# existiera (hasta v2.0.8) el job llevaba `runs-on: ubuntu-latest` cableado, de
# modo que «sin `runner:` en el `with:` → de pago» vale para todas las versiones
# publicadas de `v2`.
DEFECTO_RUNNER_VERIFICAR = "ubuntu-latest"

# Reusables de OTRO repositorio cuyo runner se conoce por DECLARACIÓN, no por
# lectura. Un juez recibe una sola raíz y no puede abrir el repositorio de al
# lado, así que sin esta tabla las dos formas más comunes de la flota —la
# compuerta y el despliegue— quedarían las dos como «no pude mirarlo» y la regla
# no podría encenderse nunca sobre el grafo que causó el incidente.
#
# Lo que se paga por tenerla: es una afirmación sobre un archivo que este juez no
# lee, y puede quedarse vieja. Por eso cada entrada lleva la fecha en que se
# midió, el hallazgo CITA que el dato viene de aquí, y todo lo que no esté en la
# tabla es `no_evaluado` con el `uses:` literal.
#
#   ("input", nombre_del_input, valor_por_defecto) -> lo decide el `with:` del
#        llamante, y si no lo pasa, el valor por defecto.
#   ("fijo", etiquetas)                            -> lo decide el reusable.
REUSABLES_EXTERNOS: dict[str, tuple] = {
    # Medido el 2026-09-27 en este mismo repositorio, verificar.yml:52-59 y :74.
    "sud-austral/coipo_jueces/.github/workflows/verificar.yml":
        ("input", "runner", DEFECTO_RUNNER_VERIFICAR),
    # Medido el 2026-09-27 en infra-docker-base/.github/workflows/deploy.yml:73
    # y deploy-uat.yml:57. Es el reusable de despliegue de la flota: `rsync` +
    # `docker compose up` + smoke test, en el runner propio de la VM. GRATIS, y
    # por eso es la mitad gratis del grafo del 2026-09-26.
    "sud-austral/infra-docker-base/.github/workflows/deploy.yml":
        ("fijo", "self-hosted, conaf-prod"),
    "sud-austral/infra-docker-base/.github/workflows/deploy-uat.yml":
        ("fijo", "self-hosted, conaf-uat"),
}

COMPOSE = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")

# Profundidad máxima de la cadena de reusables. Cuatro es más de lo que hay en la
# flota (el caso más largo es deploy.yml -> ci.yml -> verificar.yml, o sea 3) y
# el tope existe para que una llamada circular termine en `no_evaluado` y no en
# una recursión que reventaría el juez, que es el único fallo que este juez no se
# puede permitir (correr.py:282-287).
PROFUNDIDAD_MAXIMA = 4


# --------------------------------------------------------------------------
# El troceado de `jobs:` — un escáner de indentación, NO un parser de YAML
# --------------------------------------------------------------------------
#
# `comun.carga_yaml` NO sirve aquí y no es una cuestión de gusto: medido el
# 2026-09-27 sobre los 60 workflows de la flota local, **45 de 60 (75 %) lanzan
# YamlNoSoportado** —24 por un `with:` debajo de un `- uses:`, 9 por un `---`
# inicial, 6 por un `run: |`—, incluidos los dos workflows de este repositorio.
# Un juez que lo llamara reventaría sobre su propio repo, y reventar sale 1 en
# cualquier modo.
#
# `j06_config.py` lee workflows con regex sobre el texto crudo, y eso tampoco
# basta: una regex no sabe en qué JOB está la línea que casó, y este juez
# necesita precisamente eso. Así que aquí va un escáner de bloques por
# indentación, del estilo de `claves_duplicadas` en
# `tests/test_workflows_yaml.py:23-61` —«un mapa es el conjunto de claves con la
# misma indentación bajo el mismo padre; `- ` abre un mapa nuevo; `|` y `>` abren
# un escalar en bloque cuyas líneas no se miran. No es un parser YAML: es lo
# justo para este defecto»—. Ese escáner vive en `tests/`, que no se puede
# importar desde `jueces/`, de modo que esto es una DUPLICACIÓN CONSCIENTE y está
# dicha en el informe.


class EstructuraIlegible(Exception):
    """El troceado no pudo con este archivo.

    Se lanza y se captura DENTRO de este módulo, y termina siempre en
    `r.no_evaluado`. Nunca llega a `correr.py`: un juez que revienta hace salir 1
    en cualquier modo (correr.py:282-287), así que un YAML raro de cualquiera de
    las 24 aplicaciones podría bloquear despliegues por un defecto del juez.
    """


def _sin_comentario(linea: str) -> str:
    """Quita el comentario final respetando comillas.

    Copia consciente de `comun._sin_comentario` (comun.py:325-340). Se duplica en
    vez de importarse porque allí es privado y `comun` es infraestructura común
    que este encargo no toca. Son quince líneas y no crecen.
    """
    comilla = None
    for i, ch in enumerate(linea):
        if comilla:
            if ch == comilla:
                comilla = None
        elif ch in "\"'":
            comilla = ch
        elif ch == "#" and (i == 0 or linea[i - 1] in " \t"):
            return linea[:i]
    return linea


# `run: |`, `description: >-`, `if: >-`. Lo que va debajo no se mira: la palabra
# `runs-on` dentro de un `echo` de un `run:` no es una clave.
ABRE_ESCALAR = re.compile(r":\s*[|>][+-]?\d*\s*$")

CLAVE = re.compile(r"^(?P<clave>[A-Za-z0-9_.\-]+)\s*:(?P<resto>.*)$")


def _sangria(linea: str) -> int:
    return len(linea) - len(linea.lstrip(" "))


def _significativas(texto: str) -> list[tuple[int, str]]:
    """(número 1-based, línea sin comentario) de las líneas que cuentan."""
    salida: list[tuple[int, str]] = []
    escalar_desde: int | None = None
    for n, cruda in enumerate(texto.splitlines(), start=1):
        if escalar_desde is not None:
            if not cruda.strip():
                continue
            if len(cruda) - len(cruda.lstrip(" \t")) > escalar_desde:
                # Cuerpo de un escalar en bloque: puede llevar tabulaciones, la
                # palabra `needs:` dentro de un `echo`, cualquier cosa.
                continue
            escalar_desde = None
        limpia = _sin_comentario(cruda).rstrip()
        if not limpia.strip():
            continue
        blancos = cruda[: len(cruda) - len(cruda.lstrip())]
        if "\t" in blancos:
            # GitHub también rechaza el archivo entero por esto. Mejor declararse
            # incapaz que trocear una indentación que no se sabe medir.
            raise EstructuraIlegible(f"línea {n}: tabulación en la indentación")
        if ABRE_ESCALAR.search(limpia):
            escalar_desde = _sangria(limpia)
        salida.append((n, limpia))
    return salida


def _hijos(lineas: list[tuple[int, str]], i: int,
           sangria: int) -> tuple[list[tuple[int, str]], int]:
    """Las líneas que cuelgan de `lineas[i]`, y el índice de la siguiente hermana.

    Se aceptan también las líneas a la MISMA indentación que empiezan por `- `:
    YAML permite escribir una secuencia al nivel de su clave, y

        needs:
        - a
        - b

    es la misma cosa que `needs: [a, b]`. Sin esta rama el juez leería
    `needs:` vacío y dejaría pasar la dependencia — un falso negativo silencioso,
    que es el modo de fallo que este repositorio persigue.
    """
    j = i + 1
    while j < len(lineas):
        s = _sangria(lineas[j][1])
        if s > sangria or (s == sangria and lineas[j][1].strip().startswith("- ")):
            j += 1
            continue
        break
    return lineas[i + 1: j], j


class Entrada:
    """Una clave de un mapa: dónde está, qué vale y qué cuelga de ella.

    CLASE NORMAL Y NO `@dataclass`, Y NO ES ESTILO: MEDIDO EL 2026-09-27.
    `correr.py:58-62` carga cada juez con `spec_from_file_location` +
    `exec_module` y NO lo registra en `sys.modules`. `dataclasses` resuelve las
    anotaciones —que aquí son cadenas por `from __future__ import annotations`—
    con `sys.modules.get(cls.__module__).__dict__`, que en ese modo es `None`, y
    el módulo revienta al importarse con

        AttributeError: 'NoneType' object has no attribute '__dict__'

    `descubrir()` se llama FUERA de cualquier try (correr.py:150): eso no es un
    juez reventado, es `correr.py` tumbado sin resumen para las 24 aplicaciones.
    `comun.py` sí puede usar `@dataclass` porque llega por un `import` normal y
    está en `sys.modules`; un juez, no. Probado: con `@dataclass` los 32
    repositorios de la flota salían con traceback y exit 1.
    """

    def __init__(self, numero: int, valor: str,
                 hijos: list[tuple[int, str]] | None = None,
                 items: list[str] | None = None) -> None:
        self.numero = numero
        self.valor = valor
        self.hijos = hijos if hijos is not None else []
        self.items = items if items is not None else []


def _mapa(lineas: list[tuple[int, str]]) -> dict[str, Entrada]:
    """Mapa del nivel MÁS SUPERFICIAL de `lineas`. Lo más profundo se ignora."""
    candidatas = [l for _, l in lineas
                  if not l.strip().startswith("- ") and CLAVE.match(l.strip())]
    if not candidatas:
        return {}
    sangria = min(_sangria(l) for l in candidatas)
    salida: dict[str, Entrada] = {}
    i = 0
    while i < len(lineas):
        n, linea = lineas[i]
        cuerpo = linea.strip()
        if _sangria(linea) != sangria or cuerpo.startswith("- "):
            i += 1
            continue
        m = CLAVE.match(cuerpo)
        if not m:
            i += 1
            continue
        hijos, siguiente = _hijos(lineas, i, sangria)
        secuencia = [l for _, l in hijos if l.strip().startswith("- ")]
        items: list[str] = []
        if secuencia:
            s_min = min(_sangria(l) for l in secuencia)
            items = [l.strip()[2:].strip() for l in secuencia if _sangria(l) == s_min]
        # La última gana, como hace GitHub con una clave repetida. Un workflow con
        # claves duplicadas lo rechaza GitHub entero; no es este juez quien lo
        # tiene que cazar (eso es tests/test_workflows_yaml.py).
        salida[m.group("clave")] = Entrada(n, m.group("resto").strip(), hijos, items)
        i = siguiente if siguiente > i else i + 1
    return salida


def _lista(entrada: Entrada | None) -> list[str]:
    """Las tres formas de escribir una lista en YAML, reducidas a una."""
    if entrada is None:
        return []
    v = entrada.valor.strip()
    if v.startswith("[") and v.endswith("]"):
        return [p.strip().strip("\"'") for p in v[1:-1].split(",") if p.strip()]
    if v:
        return [v.strip("\"'")]
    return [i.strip().strip("\"'") for i in entrada.items if i.strip()]


class Job:
    """Un job de un workflow. Clase normal, por lo mismo que `Entrada`."""

    def __init__(self, nombre: str, numero: int, claves: dict[str, Entrada]) -> None:
        self.nombre = nombre
        self.numero = numero
        self.claves = claves

    @property
    def needs(self) -> list[str]:
        return _lista(self.claves.get("needs"))

    @property
    def runs_on(self) -> list[str]:
        return _lista(self.claves.get("runs-on"))

    @property
    def uses(self) -> str:
        e = self.claves.get("uses")
        return e.valor.strip().strip("\"'") if e else ""

    @property
    def linea_needs(self) -> int | None:
        e = self.claves.get("needs")
        return e.numero if e else None

    def entrada_with(self, clave: str) -> str | None:
        e = self.claves.get("with")
        if e is None:
            return None
        sub = _mapa(e.hijos).get(clave)
        return sub.valor.strip().strip("\"'") if sub else None


def jobs_del_workflow(texto: str) -> dict[str, Job]:
    """nombre -> Job. Lanza `EstructuraIlegible` si no se puede trocear."""
    lineas = _significativas(texto)
    raiz = _mapa(lineas)
    if "jobs" not in raiz:
        raise EstructuraIlegible("no se encontró la clave `jobs:` en el nivel raíz")
    salida: dict[str, Job] = {}
    for nombre, entrada in _mapa(raiz["jobs"].hijos).items():
        salida[nombre] = Job(nombre, entrada.numero, _mapa(entrada.hijos))
    if not salida:
        raise EstructuraIlegible("`jobs:` no declara ningún job legible")
    return salida


def entrada_por_defecto(texto: str, nombre: str) -> str | None:
    """`on.workflow_call.inputs.<nombre>.default` de un reusable LOCAL.

    `on` se lee como TEXTO y no como el booleano que YAML 1.1 haría de él: aquí no
    hay parser de YAML, hay un escáner de indentación. El límite conocido es
    `"on":` entrecomillado, que este escáner no ve; medido el 2026-09-27, no lo
    usa ninguno de los 60 workflows de la flota. Si algún día aparece, la clave no
    se encuentra y el juez devuelve None, que acaba en `no_evaluado` — se degrada
    hacia «no lo sé», nunca hacia «está bien».
    """
    raiz = _mapa(_significativas(texto))
    if "on" not in raiz:
        return None
    llamada = _mapa(raiz["on"].hijos).get("workflow_call")
    if llamada is None:
        return None
    entradas = _mapa(llamada.hijos).get("inputs")
    if entradas is None:
        return None
    uno = _mapa(entradas.hijos).get(nombre)
    if uno is None:
        return None
    defecto = _mapa(uno.hijos).get("default")
    if defecto is not None and defecto.valor.strip():
        return defecto.valor.strip().strip("\"'")
    return None


# --------------------------------------------------------------------------
# De etiquetas a dinero
# --------------------------------------------------------------------------

PROPIO, PAGO, DESCONOCIDO = "PROPIO", "PAGO", "DESCONOCIDO"


class Runner:
    """Dónde corre un job y quién lo paga. Clase normal, por lo mismo que `Entrada`."""

    def __init__(self, clase: str, detalle: str, familia: str = "") -> None:
        self.clase = clase
        self.detalle = detalle
        self.familia = familia

    def __repr__(self) -> str:  # para que un fallo de test se lea solo
        return f"Runner({self.clase}, {self.detalle!r})"


def clasificar(etiquetas: list[str], origen: str = "") -> Runner:
    """PROPIO (gratis) / PAGO (runner de GitHub) / DESCONOCIDO, con el porqué."""
    sufijo = f" [{origen}]" if origen else ""
    if not etiquetas:
        return Runner(DESCONOCIDO, f"`runs-on:` sin etiquetas legibles{sufijo}")
    for e in etiquetas:
        if "${{" in e:
            return Runner(DESCONOCIDO,
                          f"la etiqueta viene de una expresión: `{e}`{sufijo}")
    bajas = [e.strip().lower() for e in etiquetas]
    if SELF_HOSTED in bajas:
        return Runner(PROPIO, f"`{', '.join(etiquetas)}`{sufijo}")
    for e, baja in zip(etiquetas, bajas):
        m = FAMILIA_ALOJADA.match(baja)
        if m:
            return Runner(PAGO, f"`{e}`, imagen de GitHub{sufijo}",
                          m.group("familia"))
    # Ninguna etiqueta es de GitHub: es un runner de la casa. Lo que hace
    # facturable a un runner es ser de GitHub, no ser distinto de `conaf-ci`.
    return Runner(PROPIO, f"`{', '.join(etiquetas)}`, runner propio{sufijo}")


def _combinar(runners: list[Runner]) -> Runner:
    """El runner de un job que llama a un reusable con VARIOS jobs.

    El job llamante termina cuando terminan TODOS los del reusable, así que basta
    uno de pago para que la cuota lo deje colgado.
    """
    for r in runners:
        if r.clase == PAGO:
            return r
    for r in runners:
        if r.clase == DESCONOCIDO:
            return r
    return runners[0]


def resolver(repo: Repo, ruta: str, job: Job, *, profundidad: int = 0,
             visitados: frozenset[str] = frozenset()) -> Runner:
    """Dónde corre este job: directo, o siguiendo la cadena de `uses:`."""
    if job.runs_on:
        return clasificar(job.runs_on)

    usa = job.uses
    if not usa:
        # GitHub rechaza un job sin `runs-on:` y sin `uses:`, así que llegar aquí
        # significa casi siempre que el troceado no encontró la clave. Se dice con
        # la ruta para que se pueda mirar a mano, y NO se supone gratis: suponer
        # gratis convertiría un fallo del escáner en un verde.
        return Runner(DESCONOCIDO,
                      f"el job `{job.nombre}` de `{ruta}` no declara `runs-on:` ni "
                      f"`uses:`, o el troceado no los encontró")

    if profundidad >= PROFUNDIDAD_MAXIMA:
        return Runner(DESCONOCIDO,
                      f"cadena de `uses:` de más de {PROFUNDIDAD_MAXIMA} saltos: "
                      f"`{usa}`")

    # ---- reusable de OTRO repositorio: solo por declaración ----
    if not usa.startswith("./"):
        sin_ref = usa.split("@")[0].strip().lower()
        conocido = REUSABLES_EXTERNOS.get(sin_ref)
        if conocido is None:
            return Runner(DESCONOCIDO,
                          f"llama a `{usa}`, un reusable de otro repositorio que "
                          f"este juez no puede leer")
        if conocido[0] == "fijo":
            return clasificar([e.strip() for e in conocido[1].split(",")],
                              origen=f"declarado para `{sin_ref}`, medido el 2026-09-27")
        _, nombre_input, defecto = conocido
        pasado = job.entrada_with(nombre_input)
        if pasado:
            return clasificar([pasado],
                              origen=f"`{nombre_input}:` del `with:` de `{job.nombre}`")
        return clasificar([defecto],
                          origen=f"valor por defecto de `{nombre_input}` en "
                                 f"`{sin_ref}`, sin `with:` que lo cambie")

    # ---- reusable LOCAL: se lee ----
    relativa = usa[2:].split("@")[0].strip()
    if relativa in visitados:
        return Runner(DESCONOCIDO, f"`uses:` circular sobre `{relativa}`")
    texto = repo.texto(relativa)
    if texto is None:
        return Runner(DESCONOCIDO,
                      f"llama a `{usa}` y ese archivo no se pudo leer en este "
                      f"repositorio")
    try:
        llamados = jobs_del_workflow(texto)
    except EstructuraIlegible as e:
        return Runner(DESCONOCIDO, f"llama a `{usa}` y su `jobs:` no se pudo trocear ({e})")

    dentro: list[Runner] = []
    for hijo in llamados.values():
        r = resolver(repo, relativa, hijo, profundidad=profundidad + 1,
                     visitados=visitados | {relativa})
        # Un `runs-on: ${{ inputs.X }}` dentro del reusable se resuelve con el
        # `with:` del llamante, y si no lo pasa, con el `default:` del reusable.
        # SIN ESTO EL JUEZ NO ENTIENDE EL CASO CENTRAL: la compuerta de la flota
        # es un reusable parametrizado por runner, y el defecto del 2026-09-26 fue
        # exactamente no pasarle el parámetro.
        if r.clase == DESCONOCIDO and "${{" in "".join(hijo.runs_on):
            m = re.search(r"\$\{\{\s*inputs\.(?P<nombre>[A-Za-z0-9_-]+)\s*\}\}",
                          "".join(hijo.runs_on))
            if m:
                nombre_input = m.group("nombre")
                pasado = job.entrada_with(nombre_input)
                if pasado and "${{" not in pasado:
                    r = clasificar([pasado],
                                   origen=f"`{nombre_input}:` del `with:` de `{job.nombre}`")
                else:
                    # `entrada_por_defecto` relee el archivo y puede declararlo
                    # ilegible. Aquí eso NO puede abortar la resolución del job:
                    # el resultado correcto es DESCONOCIDO con el porqué, que ya
                    # trae `r`. Medido con 4.016 entradas hostiles el 2026-09-27:
                    # es el único camino por el que algo salía de este módulo.
                    try:
                        defecto = entrada_por_defecto(texto, nombre_input)
                    except EstructuraIlegible:
                        defecto = None
                    if defecto and "${{" not in defecto:
                        r = clasificar([defecto],
                                       origen=f"valor por defecto de `{nombre_input}` "
                                              f"en `{relativa}`")
        dentro.append(r)
    if not dentro:
        return Runner(DESCONOCIDO, f"`{usa}` no declara ningún job legible")
    return _combinar(dentro)


# --------------------------------------------------------------------------
# El juez
# --------------------------------------------------------------------------


def repositorio_desplegable(repo: Repo) -> bool:
    """¿Lo despliega el pipeline de la flota?

    Copia consciente de `j06_config.es_desplegable()` (j06_config.py:81-94), que
    es a su vez el criterio de `j01` y `j08`: el compose es la señal, porque
    `rsync` + `docker compose up` + `curl /health` es todo lo que hace el
    reusable de despliegue. Aquí NO es una puerta —el defecto existe igual en un
    repositorio que no despliega— sino EVIDENCIA para el mensaje: si hay compose,
    lo que la cuota agotada deja colgado es un despliegue a producción, y eso hay
    que decirlo con esas palabras.
    """
    return any(repo.existe(c) for c in COMPOSE)


def _pista_de_despliegue(job: Job) -> str:
    """Evidencia, no clasificación: ¿a qué delega este job?"""
    usa = job.uses
    if not usa:
        return ""
    nombre = usa.split("@")[0].rstrip("/").split("/")[-1]
    if nombre.lower().startswith("deploy"):
        return (f" Y este job delega en `{usa}`, o sea que lo que queda sin "
                f"ejecutar es el despliegue.")
    return ""


def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.tiene_git():
        # Sin git no hay `git ls-files`, y este juez solo mira workflows
        # VERSIONADOS: un workflow que no está en el índice no lo ejecuta GitHub.
        r.no_evaluado.append(
            f"{repo.raiz} no es un repositorio git: sin `git ls-files` no se sabe "
            "qué workflows existen de verdad para GitHub")
        return

    rutas = [x for x in repo.versionados() if RUTA_WORKFLOW.match(x)]
    if not rutas:
        r.no_corresponde(
            "no hay ningún `.github/workflows/*.yml` versionado: este repositorio "
            "no ejecuta nada en Actions, así que no hay ningún grafo de `needs:` "
            "que una cuota agotada pueda dejar colgado. La comprobación se vuelve "
            "a encender el día que se añada un workflow.")
        return

    total_jobs = 0
    total_aristas = 0
    mirados = 0

    for ruta in sorted(rutas):
        texto = repo.texto(ruta)
        if texto is None:
            r.no_evaluado.append(f"{ruta}: no se pudo leer el archivo")
            continue
        try:
            jobs = jobs_del_workflow(texto)
        except EstructuraIlegible as e:
            r.no_evaluado.append(
                f"{ruta}: no se pudo analizar la estructura de jobs ({e}). Un "
                f"workflow que no se puede trocear NO se declara correcto.")
            continue
        except Exception as e:  # noqa: BLE001
            # Último cerrojo por archivo. Un juez que revienta sale 1 en CUALQUIER
            # modo (correr.py:282-287), así que un workflow raro de cualquiera de
            # las 24 aplicaciones bloquearía despliegues por un defecto de aquí.
            # Termina en `no_evaluado`, nunca en `pass`.
            r.no_evaluado.append(
                f"{ruta}: el troceado de jobs falló con {type(e).__name__}: {e}. "
                f"Este archivo quedó SIN MIRAR y hay que mirarlo a mano.")
            continue

        mirados += 1
        total_jobs += len(jobs)
        lineas = repo.lineas(ruta)

        for nombre, job in jobs.items():
            necesita = job.needs
            if not necesita:
                continue
            try:
                mio = resolver(repo, ruta, job)
            except Exception as e:  # noqa: BLE001
                r.no_evaluado.append(
                    f"{ruta}: no se pudo resolver el runner del job `{nombre}` "
                    f"({type(e).__name__}: {e})")
                continue

            # UN HALLAZGO POR JOB DEPENDIENTE, NO POR ARISTA.
            #
            # Medido el 2026-09-27 sobre el estado de `coipo_prensa2` anterior al
            # arreglo: sus dos despliegues cuelgan de SEIS jobs cada uno, y con un
            # hallazgo por arista salían DOCE avisos idénticos anclados en dos
            # líneas. Es el defecto que `j12_semilla.py:78-81` documenta para el
            # contador de comprobaciones: inflar el número no informa de nada y
            # entierra los hallazgos distintos. El arreglo es uno: mover esos jobs
            # de runner, y se hace una sola vez.
            de_pago: list[tuple[str, Runner]] = []
            for dep in necesita:
                total_aristas += 1
                if dep not in jobs:
                    r.no_evaluado.append(
                        f"{ruta}: el job `{nombre}` declara `needs: {dep}` y en este "
                        f"archivo no hay ningún job con ese nombre; no se puede "
                        f"saber dónde corre")
                    continue
                try:
                    suyo = resolver(repo, ruta, jobs[dep])
                except Exception as e:  # noqa: BLE001
                    r.no_evaluado.append(
                        f"{ruta}: no se pudo resolver el runner del job `{dep}` "
                        f"({type(e).__name__}: {e})")
                    continue
                if suyo.clase == PAGO:
                    de_pago.append((dep, suyo))

            if not de_pago:
                continue

            citas = "; ".join(f"`{d}` ({s.detalle})" for d, s in de_pago)
            nombres = ", ".join(f"`{d}`" for d, _ in de_pago)

            if mio.clase == DESCONOCIDO:
                # LA REGLA DE ORO. No se puede afirmar el hallazgo, y callarse es
                # peor: ésta es la forma exacta del 2026-09-26.
                r.no_evaluado.append(
                    f"{ruta}: el job `{nombre}` tiene en su `needs:` {len(de_pago)} "
                    f"job(s) en runner DE PAGO —{citas}— y NO se pudo determinar "
                    f"dónde corre `{nombre}` ({mio.detalle}). Si `{nombre}` es "
                    f"self-hosted, éste es el grafo que dejó a la organización sin "
                    f"desplegar el 2026-09-26, y hay que mirarlo a mano.")
                continue
            if mio.clase != PROPIO:
                continue

            linea = job.linea_needs
            if linea and (motivo := suprimido(lineas, linea - 1, REGLA)):
                r.supresiones.append(
                    f"{ruta}:{linea} `{nombre}` cuelga de {nombres} (de pago) — {motivo}")
                continue

            extra = ""
            for familia in sorted({s.familia for _, s in de_pago if s.familia}):
                coste = MULTIPLICADOR.get(familia)
                if coste:
                    extra += (f" Y los runners {familia} de GitHub facturan {coste} "
                              f"que los Linux, así que esta dependencia agota la "
                              f"cuota más rápido de lo que parece.")
            if repositorio_desplegable(repo):
                extra += (" Este repositorio tiene compose en la raíz —el criterio "
                          "de j01 y j08—, o sea que lo despliega el pipeline de la "
                          "flota: lo que la cuota agotada detiene aquí es un "
                          "despliegue a producción.")
            extra += _pista_de_despliegue(job)

            r.avisa(
                REGLA, ruta,
                f"el job `{nombre}` corre GRATIS ({mio.detalle}) y su `needs:` "
                f"incluye {len(de_pago)} job(s) en un runner DE PAGO: {citas}",
                "cuando se agota la cuota de Actions el job de pago no arranca "
                "—runner vacío, cero pasos y la anotación «The job was not "
                "started because recent account payments have failed or your "
                "spending limit needs to be increased»— y todo lo que cuelga de "
                "su `needs:` queda sin ejecutar. El 2026-09-26 la organización "
                "agotó los 2.000 min/mes del plan Free (2.086 facturables "
                "medidos) y siete repositorios se quedaron sin poder desplegar "
                "a producción por esta forma exacta: el despliegue era gratis y "
                "su compuerta no." + extra,
                linea=linea,
                arreglo=f"mover {nombres} a un runner propio (`runs-on: conaf-ci`), "
                        f"o, si alguno llama al reusable de los jueces, pasarle "
                        f"`runner: conaf-ci` en su `with:` (input añadido en "
                        f"coipo_jueces v2.0.9; con un `uses:` anterior GitHub "
                        f"rechaza el archivo entero, así que el `uses:` y el "
                        f"`runner:` se mueven juntos). Si tiene que seguir siendo "
                        f"de pago, sacarlo del `needs:` lo arregla pero deja de ser "
                        f"compuerta, y eso hay que decirlo en vez de descubrirlo.")

    if not mirados:
        # Se encontraron workflows y NINGUNO se pudo trocear. No es «está todo
        # bien»: es «no pude mirar». Los `no_evaluado` de arriba ya dicen por qué.
        return

    r.comprobo(f"cadenas `needs:` frente al runner que paga "
               f"({mirados} de {len(rutas)} workflow(s) troceados, "
               f"{total_jobs} jobs, {total_aristas} aristas de `needs:`)")


if __name__ == "__main__":
    ejecutar("j15", "un job de pago en el `needs:` de un job que corre gratis: "
                    "sin cuota de Actions no arranca, y arrastra al despliegue "
                    "(incidente del 2026-09-26)", comprobar)
