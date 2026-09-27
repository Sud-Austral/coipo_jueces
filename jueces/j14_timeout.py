#!/usr/bin/env python3
"""j14 — `timeout-minutes` en un job que llama a un workflow reutilizable.

QUE ES EL DEFECTO
=================
Un job cuyo cuerpo es `uses:` no ejecuta pasos: delega en otro workflow. Sus
claves validas son un conjunto CERRADO, y `timeout-minutes` no esta en el. Lo
caro no es que el job falle: **GitHub rechaza el archivo de workflow ENTERO**.
No hay jobs, no hay log, no hay paso rojo que mirar — solo un «workflow file
issue» en la pestana Actions. El repositorio se queda sin esa via de despliegue
y el error no se parece en nada a su causa.

Esa forma de fallo NO es hipotetica en esta flota, y esta medida: el 2026-09-08
`v2.0.3` de este mismo repositorio salio con dos claves `env:` en el mismo paso
de `verificar.yml`. La suite estaba verde y el paso «El YAML del reusable
parsea» tambien. GitHub rechazo el archivo entero y **todo consumidor de `@v2`
quedo sin gate** hasta que el tag volvio atras (tests/test_workflows_yaml.py,
cabecera). Es exactamente la misma manifestacion: una clave invalida en un sitio
valido tumba el archivo completo, no la linea.

POR QUE SOLO SE DENUNCIA `timeout-minutes`
==========================================
La documentacion de GitHub lista mas claves prohibidas en un job con `uses:`
—`runs-on`, `steps`, `env`, `container`, `services`, `defaults`…— pero **esa
lista no esta escrita en ningun documento de esta flota**: se busco el
2026-09-27 en los 32 repositorios de `D:/GitHub` con `.github/workflows/` y en
`coipo_master_produccion`, y no aparece. Un juez que denunciara una lista que no
puede citar estaria inventandose la regla, que es justo lo que `REGLAS.md`
existe para impedir (el episodio `DECRETOS.md`).

Asi que este juez denuncia UNA clave, la que la gente pone por costumbre porque
la escribe en todos sus demas jobs. Ampliar la lista es un cambio de regla y
necesita que alguien escriba la fuente primero. Esta decision esta tambien en
`REGLAS.md`, fila `WF-1`.

LO QUE **NO** ES UN HALLAZGO, Y ES LA MITAD DEL TRABAJO
=======================================================
`timeout-minutes` es perfectamente valido en los otros dos sitios donde aparece,
y los dos son comunes en esta flota:

  - a nivel de job CON `steps:`  -> `coipo_api/.github/workflows/ci.yml` lo lleva
                                    en sus tres jobs (lineas 75, 197 y 333), y
                                    `verificar.yml` de este repo en el suyo
                                    (linea 78, con el motivo escrito al lado).
  - dentro de un `step`          -> mismo caso, un nivel mas adentro.

Y dentro del workflow LLAMADO tambien es valido: el job que tiene `uses:` es el
llamante; el llamado tiene sus propios jobs con `steps:`.

Un aviso falso sobre cualquiera de esos tres sitios ensenaria a suprimir al
juez, que es el modo de fallo que `j06_config.es_desplegable` documenta. Por eso
el troceado de mas abajo mira la INDENTACION y no el texto: hace falta saber en
que job esta la linea, y una regex con `re.MULTILINE` no lo sabe.

CALIBRACION INVERSA (medida el 2026-09-27 sobre los 32 repositorios de
`D:/GitHub` que tienen `.github/workflows/`)
  60 workflows versionados troceados, 126 jobs, **39 de ellos llamadas a un
  reusable** (el 31 %: el dominio de esta regla no es marginal). Resultado:

    hallazgos `WF-1` .................  0
    jueces reventados ................  0
    ficheros que no se pudieron trocear  0
    veredicto ........................  OK en los 32, salida 0 en los 32

  Los mas cargados: `coipo_atraso_personal` (6 jobs con `uses:` de 13),
  `coipo_api`, `C2F-W` y `coipo_grafana` (4 cada uno). Y los que llevan
  `timeout-minutes` LEGITIMO en un job con `steps:` —`coipo_api` en sus tres,
  `coipo_boton_rojo`, y este repositorio en `verificar.yml:78` y
  `autotest.yml:27`— salen limpios, que es la mitad que importa.

  CERO HALLAZGOS NO ES CERO VALOR, Y HAY QUE DECIR POR QUE. Un juez que no
  encuentra nada y no se ha probado contra un caso que DEBE encontrar no vale
  nada, asi que la deteccion se midio al reves: **inyectando** un
  `timeout-minutes` junto al `uses:` de esos 39 jobs reales, uno por uno. El
  troceado lo detecta en los 39, con sus sangrias de 2 y de 4, con `if: >-` de
  doce lineas, con `needs:` en linea y con `with:` debajo. La deteccion positiva
  sobre casos escritos a mano vive en `tests/test_j14_timeout.py`.

  Y por que la regla se enciende AHORA teniendo cero casos: el 2026-09-26 la
  organizacion agoto los 2.000 min/mes de Actions y la flota esta reescribiendo
  jobs para sacarlos de los runners de pago. Mover un job de `runs-on:` +
  `timeout-minutes:` a una llamada a un reusable es exactamente la edicion que
  introduce este defecto, y el dia que pase, el sintoma sera un repositorio sin
  via de despliegue y un error que no se parece a su causa.

REGISTRO DE SEVERIDAD
=====================
AVISA y no BLOQUEA, por la doctrina de `comun.Severidad` y porque `WF-1` esta en
la tabla «Reglas sin fuente escrita» de `REGLAS.md`: ningun documento de la
flota dice esto todavia. `tests/test_reglas_citadas.py::PruebaSeveridad` lo hace
cumplir solo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, suprimido  # noqa: E402

PERFILES = ("aplicacion", "encuadre_operativo")

REGLA = "WF-1"

# La clave que se denuncia. Una sola, y el porque esta en la cabecera.
CLAVE_PROHIBIDA = "timeout-minutes"

# `[^/]*` y no `.*`: GitHub lee los workflows del directorio
# `.github/workflows/` y NO de sus subdirectorios. Un `.yml` guardado en
# `.github/workflows/plantillas/` no lo ejecuta nadie, asi que denunciarlo seria
# un aviso sobre un archivo que no puede romper nada.
RUTA_WORKFLOW = re.compile(r"\.github/workflows/[^/]*\.ya?ml$")

# `clave: valor`, con la clave opcionalmente entrecomillada. El `\s` obligatorio
# tras los dos puntos NO es un descuido: en YAML `timeout-minutes:10` sin espacio
# NO abre un mapa, es el escalar "timeout-minutes:10". Exigirlo evita leer como
# clave algo que YAML tampoco lee como clave.
_CLAVE = re.compile(r"^(?P<clave>\"[^\"]*\"|'[^']*'|[^#\s][^:]*?)\s*:(?P<resto>\s.*|)$")

# `|`, `>`, `|-`, `>2`... abren un escalar de bloque: lo de dentro es TEXTO y no
# se mira. Sin esto, un `run: |` que contenga la palabra `timeout-minutes` —o un
# ejemplo de YAML dentro de un `echo`— se leeria como una clave real.
_MARCADOR_BLOQUE = re.compile(r"^[|>][+-]?\d*$")


def _sin_comentario(linea: str) -> str:
    """Quita el comentario final respetando comillas.

    DUPLICADO CONSCIENTE de `comun._sin_comentario` (comun.py:325-340). Es
    privada de ese modulo y el contrato de esta casa dice que un juez nuevo no
    toca `comun.py`; copiarla cuesta doce lineas y evita convertir un ayudante
    privado del parser de compose en interfaz publica por la puerta de atras. Si
    algun dia se publica alli, esta copia se borra.
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


def _clave_y_valor(cuerpo: str) -> tuple[str | None, str]:
    """`"clave": valor` -> ("clave", "valor"). (None, "") si no es un mapa."""
    m = _CLAVE.match(cuerpo)
    if not m:
        return None, ""
    clave = m.group("clave").strip()
    if len(clave) >= 2 and clave[0] == clave[-1] and clave[0] in "\"'":
        clave = clave[1:-1]
    return clave, (m.group("resto") or "").strip()


# NI `@dataclass` NI `NamedTuple` AQUI, Y NO ES ESTILO: es que el juez no carga.
#
# `correr.py:58-62` importa cada juez con `spec_from_file_location` +
# `module_from_spec` + `exec_module`, y NO lo registra en `sys.modules`. Con
# `from __future__ import annotations` las anotaciones son cadenas, asi que
# `@dataclass` intenta resolverlas y hace `sys.modules.get(cls.__module__).__dict__`
# (dataclasses.py:749) para saber si alguna es `ClassVar`/`InitVar`: como el
# modulo no esta registrado, eso es `None.__dict__` y revienta con un
# `AttributeError` A NIVEL DE MODULO. Y `descubrir()` se llama FUERA de cualquier
# try (correr.py:150), asi que no es un juez reventado: es correr.py muerto sin
# resumen para las 24 aplicaciones.
#
# Medido el 2026-09-27: con `@dataclass` los 32 repositorios de la flota salian
# con codigo 1 y cero jueces ejecutados. Ningun juez de esta casa usa
# `dataclasses`, y esta es la razon por la que no puede empezar a usarlos.
class _Linea:
    """Una linea con contenido: numero 1-based, sangria y cuerpo ya limpio."""

    __slots__ = ("numero", "sangria", "cuerpo")

    def __init__(self, numero, sangria, cuerpo):
        self.numero = numero      # 1-based, como exige `Hallazgo.linea`
        self.sangria = sangria
        self.cuerpo = cuerpo      # sin comentario y sin espacios en los extremos


class Trabajo:
    """Un job del workflow, con sus claves DIRECTAS y donde estan."""

    __slots__ = ("identificador", "numero", "claves", "problema")

    def __init__(self, identificador, numero):
        self.identificador = identificador
        self.numero = numero
        self.claves = {}          # clave -> numero de linea 1-based
        self.problema = None      # por que no se pudo decidir sobre este job


def _significativas(lineas: list[str]) -> tuple[list[_Linea], str | None]:
    """Lineas con contenido, fuera de los escalares de bloque.

    Devuelve `(lineas, problema)`. `problema` no es None cuando el archivo tiene
    algo que impide medir la sangria con seguridad; entonces la lista que lo
    acompana no sirve y el juez lo reporta como NO EVALUADO. Nunca lanza: un juez
    que revienta hace salir 1 en cualquier modo (correr.py:282-287), asi que un
    YAML raro tiene que salir por la puerta de «no pude mirarlo».
    """
    salida: list[_Linea] = []
    bloque: int | None = None
    for numero, cruda in enumerate(lineas, start=1):
        blanco = cruda[: len(cruda) - len(cruda.lstrip(" \t"))]
        if "\t" in blanco:
            # GitHub rechaza el archivo por esto solo, y la sangria deja de ser
            # medible en columnas. Decirlo es mas util que adivinarla.
            return [], f"linea {numero}: tabulacion en la sangria"
        sangria = len(blanco)

        # EL ORDEN IMPORTA: primero el escalar de bloque y despues el comentario.
        # Dentro de un `run: |`, una linea que empieza por `#` es CONTENIDO, no
        # un comentario, y tratarla al reves cerraria el bloque antes de tiempo.
        if bloque is not None:
            if not cruda.strip():
                continue
            if sangria > bloque:
                continue
            bloque = None

        cuerpo = _sin_comentario(cruda).strip()
        if not cuerpo or cuerpo in ("---", "..."):
            continue
        salida.append(_Linea(numero, sangria, cuerpo))

        # Un `- clave: |` tiene la clave DOS columnas mas adentro que el guion.
        # Usar la sangria del guion se comia la clave hermana del mismo paso
        # (`- run: |` seguido de `timeout-minutes:` del propio step).
        interior = cuerpo[2:].lstrip() if cuerpo.startswith("- ") else cuerpo
        efectiva = sangria + 2 if cuerpo.startswith("- ") else sangria
        _, valor = _clave_y_valor(interior)
        if valor and _MARCADOR_BLOQUE.match(valor):
            bloque = efectiva
    return salida, None


def _claves_directas(bloque: list[_Linea]) -> dict[str, int]:
    """Claves del PROPIO job: las de la primera sangria del bloque.

    La parte que decide el falso positivo obvio es la secuencia. En el estilo
    «a ras»

        steps:
        - uses: actions/checkout@...
        timeout-minutes: 5

    el `- uses:` esta a la MISMA sangria que las claves del job. Contarlo como
    clave del job convertiria cualquier job normal con pasos en un hallazgo:
    seria un aviso sobre la practica correcta y en casi todos los repositorios,
    que es exactamente lo que ensena a suprimir a un juez.
    """
    if not bloque:
        return {}
    sangria = bloque[0].sangria
    claves: dict[str, int] = {}
    secuencia: int | None = None
    for l in bloque:
        if secuencia is not None:
            if l.sangria > secuencia:
                continue
            if l.sangria == secuencia and l.cuerpo.startswith("-"):
                continue
            secuencia = None
        if l.cuerpo.startswith("- ") or l.cuerpo == "-":
            secuencia = l.sangria
            continue
        if l.sangria != sangria:
            continue
        clave, _ = _clave_y_valor(l.cuerpo)
        if clave is not None:
            claves.setdefault(clave, l.numero)
    return claves


def _trabajos(lineas: list[str]) -> tuple[list[Trabajo], str | None]:
    """Los jobs del workflow con sus claves directas.

    NO ES UN PARSER YAML y no pretende serlo. `comun.carga_yaml` rechaza el 75 %
    de los workflows de la flota (medido el 2026-09-27: 45 de 60 archivos lanzan
    `YamlNoSoportado`, casi todos por un `with:` debajo de un `- uses:`), asi que
    usarlo aqui seria reventar en tres de cada cuatro repositorios. Esto es lo
    justo para este defecto, en la linea de `tests/test_workflows_yaml.py:23-61`:
    un mapa es el conjunto de claves con la misma sangria bajo el mismo padre, un
    `- ` abre un elemento de secuencia cuyas claves NO son del padre, y lo de
    dentro de un escalar de bloque no se mira.
    """
    sig, problema = _significativas(lineas)
    if problema:
        return [], problema
    if not sig:
        return [], "el archivo no tiene ninguna linea con contenido"

    # La `jobs:` de menor sangria. Coger «la primera» bastaria hoy, pero una
    # `jobs:` anidada que apareciera antes convertiria todo el troceado en basura
    # silenciosa, y este juez prefiere no evaluar antes que mentir.
    candidatas = [l for l in sig if l.cuerpo == "jobs:"]
    if not candidatas:
        return [], "no hay una clave `jobs:` de nivel superior"
    cabecera = min(candidatas, key=lambda l: (l.sangria, l.numero))

    dentro: list[_Linea] = []
    for l in sig[sig.index(cabecera) + 1:]:
        if l.sangria <= cabecera.sangria:
            break
        dentro.append(l)
    if not dentro:
        return [], "la clave `jobs:` no tiene ningun job debajo"

    sangria_job = dentro[0].sangria
    trabajos: list[Trabajo] = []
    for i, l in enumerate(dentro):
        if l.sangria != sangria_job or l.cuerpo.startswith("-"):
            continue
        identificador, valor = _clave_y_valor(l.cuerpo)
        if identificador is None:
            continue
        bloque = []
        for siguiente in dentro[i + 1:]:
            if siguiente.sangria <= sangria_job:
                break
            bloque.append(siguiente)
        t = Trabajo(identificador, l.numero)
        if valor.startswith("{"):
            # `deploy: {uses: ./x.yml, timeout-minutes: 5}`. Legal en YAML, y
            # este troceado no lo abre. Callarse aqui seria apagar la regla en
            # silencio justo sobre el unico caso que no cubre.
            t.problema = (f"el job `{identificador}` esta escrito como mapa en "
                          f"linea (`{{...}}`), que este troceado no abre")
        elif valor.startswith("*"):
            t.problema = (f"el job `{identificador}` es un alias YAML "
                          f"(`{valor}`): su contenido esta en otro sitio")
        else:
            t.claves = _claves_directas(bloque)
            if "<<" in t.claves:
                t.problema = (f"el job `{identificador}` fusiona un ancla "
                              f"(`<<:`): sus claves reales no estan aqui")
        trabajos.append(t)

    if not trabajos:
        return [], "no se reconocio ningun job bajo `jobs:`"
    return trabajos, None


def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.tiene_git():
        r.no_evaluado.append(f"{repo.raiz} no es un repositorio git")
        return

    versionados = repo.versionados()
    if not versionados:
        # `versionados()` devuelve [] tambien cuando `git` no esta en el PATH
        # (comun.py:211-216). Leerlo como «este repositorio no tiene workflows»
        # seria declarar N/A por una averia del entorno, y el N/A solo se declara
        # desde evidencia encontrada en el codigo (comun.py:118-122).
        r.no_evaluado.append(
            "`git ls-files` no devolvio nada: o falta `git` en el PATH, o el "
            "repositorio no tiene ningun archivo versionado. En los dos casos "
            "este juez no puede afirmar que no haya workflows.")
        return

    rutas = [ruta for ruta in versionados if RUTA_WORKFLOW.match(ruta)]
    if not rutas:
        r.no_corresponde(
            "no hay ningun `.github/workflows/*.yml` versionado: este "
            "repositorio no ejecuta nada en GitHub Actions, asi que no hay un "
            "archivo de workflow que GitHub pueda rechazar. La comprobacion se "
            "vuelve a encender sola el dia que se anada el primer workflow.")
        return

    mirados = jobs_totales = jobs_con_uses = 0
    for ruta in sorted(rutas):
        try:
            lineas = repo.lineas(ruta)
            if not lineas:
                r.no_evaluado.append(f"{ruta}: vacio o ilegible")
                continue
            trabajos, problema = _trabajos(lineas)
            if problema:
                r.no_evaluado.append(
                    f"{ruta}: no se pudo analizar la estructura de jobs "
                    f"({problema}). Sin saber en que job cae cada clave este "
                    f"juez no puede decidir, y callar seria peor que decirlo.")
                continue

            mirados += 1
            jobs_totales += len(trabajos)
            for t in trabajos:
                if t.problema:
                    r.no_evaluado.append(f"{ruta}:{t.numero}: {t.problema}")
                    continue
                if "uses" not in t.claves:
                    continue
                jobs_con_uses += 1
                linea = t.claves.get(CLAVE_PROHIBIDA)
                if linea is None:
                    continue
                if (motivo := suprimido(lineas, linea - 1, REGLA)):
                    r.supresiones.append(
                        f"{ruta}:{linea} `{CLAVE_PROHIBIDA}` en el job "
                        f"`{t.identificador}`, que llama a un reusable — {motivo}")
                    continue
                r.avisa(
                    REGLA, ruta,
                    f"el job `{t.identificador}` llama a un workflow "
                    f"reutilizable (`uses:`) y declara `{CLAVE_PROHIBIDA}`, que "
                    f"no es una clave valida en ese tipo de job",
                    "GitHub no falla ese job: rechaza el ARCHIVO de workflow "
                    "entero con «workflow file issue», sin jobs, sin log y sin "
                    "paso rojo que mirar. El repositorio se queda sin esa via de "
                    "despliegue y el error no se parece a su causa. Esta flota ya "
                    "lo vivio el 2026-09-08 con `v2.0.3` de coipo_jueces: dos "
                    "`env:` en un mismo paso, la suite verde, y todo consumidor "
                    "de `@v2` sin gate hasta que el tag volvio atras",
                    linea=linea,
                    arreglo=f"quitar `{CLAVE_PROHIBIDA}` de este job. El limite "
                            f"de tiempo se pone DENTRO del workflow llamado, en "
                            f"su job con `steps:`, que es donde GitHub si lo "
                            f"acepta. Si hay que dejarlo aqui a proposito, "
                            f"suprimelo con `coipo-jueces:ignorar({REGLA}) "
                            f"<motivo>` en la linea anterior: se cuenta y se "
                            f"publica.")
        except Exception as e:  # noqa: BLE001
            # Un juez que revienta hace salir 1 en CUALQUIER modo
            # (correr.py:282-287), asi que ningun YAML de las 24 aplicaciones
            # puede tumbar el gate desde aqui. El except termina en no_evaluado y
            # nunca en `pass`: un control que se apaga sin que nadie se entere es
            # justo lo que `comun.py:82-86` prohibe.
            r.no_evaluado.append(
                f"{ruta}: no se pudo analizar ({type(e).__name__}: {e})")

    if mirados:
        # UN SOLO `comprobo()`, con el recuento dentro, como j12_semilla.py:187.
        # Inflar el contador con uno por archivo fue un defecto alli.
        r.comprobo(
            f"claves de nivel de job en los workflows ({jobs_con_uses} job/s con "
            f"`uses:` de {jobs_totales} en {mirados} de {len(rutas)} workflow/s)")


if __name__ == "__main__":
    ejecutar("j14", "`timeout-minutes` en un job que llama a un workflow "
                    "reutilizable: GitHub rechaza el archivo entero", comprobar)
