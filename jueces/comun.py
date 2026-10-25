"""Infraestructura compartida de los jueces COIPO.

Un juez es un script autónomo que recibe la RUTA de un repositorio y emite
hallazgos. No importa nada fuera de la biblioteca estándar: los jueces se
distribuyen como *workflow reusable* y tienen que poder ejecutarse en el CI de
cualquier app y también a mano, sin instalar nada.

    python jueces/j09_secretos.py --repo D:/GitHub/coipo_prensa2 --modo advisory

DOS MODOS, Y LA DIFERENCIA IMPORTA
  advisory   -> se imprime todo y el proceso sale 0. Sirve para MEDIR sin
                romper el despliegue de una flota que hoy no cumple.
  bloqueante -> un hallazgo de severidad BLOQUEA hace salir 1.

La transición de uno a otro es por regla y con fecha escrita, no
por criterio del que corre el comando. Encender todas las reglas de golpe deja a
la flota sin poder desplegar — incluidos los arreglos urgentes — y el resultado
previsible es que alguien desactive el juez entero.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

# Los módulos hermanos (`comun_yaml`, `comun_semilla`) se importan por nombre: este
# directorio tiene que estar en la ruta aunque quien importe `comun` no lo haya
# puesto (la prueba de paridad de la fábrica carga `j14` por ruta).
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun_yaml import (  # noqa: E402,F401  (reexportados: los jueces los importan de aquí)
    YamlNoSoportado, _sin_comentario, carga_yaml, numero_de_linea,
)
from comun_semilla import Adopcion, leer_adopcion, leer_fabrica  # noqa: E402,F401

# --------------------------------------------------------------------------
# Hallazgos
# --------------------------------------------------------------------------


class Severidad(str, Enum):
    """Solo dos niveles a propósito.

    Un tercer nivel intermedio ("importante", "menor") se convierte siempre en
    un cajón donde va lo que nadie quiere arreglar ni discutir. Si algo no
    justifica bloquear un despliegue el día que la regla se encienda, es AVISA.
    """

    BLOQUEA = "BLOQUEA"
    AVISA = "AVISA"


@dataclass(frozen=True)
class Hallazgo:
    """Un defecto concreto, en un archivo concreto.

    `manifestacion` no es decoración: es el campo que separa un hallazgo de una
    opinión. Si no se puede escribir cómo se ve este defecto en producción, el
    hallazgo no debería existir. Es el mismo contrato que se le exige al agente
    adversario en docs/ADVERSARIAL.md.
    """

    regla: str  # "G8-4", "DK-3"... REGLAS.md dice qué documento la respalda
    severidad: Severidad
    archivo: str  # relativo al repo. "" si es del repo entero
    mensaje: str  # qué está mal
    manifestacion: str  # cómo se ve esto en producción
    linea: int | None = None
    arreglo: str = ""  # qué hacer, concreto

    def ubicacion(self) -> str:
        if not self.archivo:
            return "(repositorio)"
        return f"{self.archivo}:{self.linea}" if self.linea else self.archivo


@dataclass
class Resultado:
    """Lo que devuelve un juez."""

    juez: str
    descripcion: str
    hallazgos: list[Hallazgo] = field(default_factory=list)
    # Comprobaciones que el juez NO pudo hacer (archivo ausente, git no
    # disponible...). Se reportan aparte: un juez que no pudo mirar no es un
    # juez que miró y no encontró nada, y confundirlos es cómo un control se
    # apaga sin que nadie se entere.
    no_evaluado: list[str] = field(default_factory=list)
    # Hallazgos silenciados con un marcador en el código. Se CUENTAN y se
    # publican siempre. Un verificador cuyas supresiones nadie mira está
    # desactivado de hecho a los tres meses, y el número creciendo es la única
    # señal temprana de que eso está pasando.
    supresiones: list[str] = field(default_factory=list)
    # Lo que este juez SÍ llegó a comprobar. Sin esto, un juez que no pudo
    # mirar nada devuelve cero hallazgos y se lee como «está todo bien».
    #
    # EL INCIDENTE QUE FUNDA ESTE CAMPO no es hipotético y es de esta misma
    # organización. En COIPO_PDF_EXCEL un comprobante se clasificó mal durante
    # meses: no generó NINGUNA comparación, y como la pantalla contaba totales
    # *fallidos*, cero de cero daba «todos los totales cuadran» mientras una
    # columna salía en 0 para los 3.610 trabajadores. Su corrección fue pasar de
    # un booleano a TRES estados, donde «no hay con qué comprobarlo» es distinto
    # de «está bien». Es la misma corrección que se aplica aquí.
    comprobado: list[str] = field(default_factory=list)
    # «Esto no corresponde en esta aplicación, y es correcto que no corresponda.»
    #
    # Es el `[N/A]` que la propia Guía 8 usa en su checklist, y NO es lo mismo
    # que `no_evaluado`. La diferencia importa porque decide si el despliegue se
    # detiene:
    #
    #   no_evaluado -> "no pude mirarlo". Puede que el repositorio no sea lo que
    #                  declara, o que la detección esté rota. Es sospechoso y
    #                  frena un perfil `aplicacion`.
    #   no_aplica   -> "lo miré y aquí no hay nada que comprobar". `coipo_prensa2`
    #                  y `COIPO_ENTREGA_PLANTA` no registran CORS porque su nginx
    #                  sirve frontend y API bajo el MISMO origen: el navegador
    #                  nunca emite una petición cruzada. Detener su despliegue
    #                  por eso es el falso positivo que enseña a suprimir jueces.
    #
    # ASIMETRÍA DELIBERADA: solo un JUEZ puede declarar `no_aplica`, y solo desde
    # evidencia que encontró en el código. Un repositorio NO puede declararse a
    # sí mismo N/A. Si pudiera, esta sería la puerta por la que todo se pone
    # verde. Por eso además se cuenta y se publica, igual que las supresiones.
    no_aplica: list[str] = field(default_factory=list)

    def no_corresponde(self, razon: str) -> None:
        """Marca este juez como `[N/A]` en este repositorio, con el porqué."""
        self.no_aplica.append(razon)

    def anota(self, *args: Any, **kwargs: Any) -> None:
        self.hallazgos.append(Hallazgo(*args, **kwargs))

    def bloquea(self, regla: str, archivo: str, mensaje: str, manifestacion: str,
                linea: int | None = None, arreglo: str = "") -> None:
        self.anota(regla, Severidad.BLOQUEA, archivo, mensaje, manifestacion, linea, arreglo)

    def avisa(self, regla: str, archivo: str, mensaje: str, manifestacion: str,
              linea: int | None = None, arreglo: str = "") -> None:
        self.anota(regla, Severidad.AVISA, archivo, mensaje, manifestacion, linea, arreglo)

    def comprobo(self, que: str) -> None:
        """Registra una comprobacion REALIZADA. Se llama aunque salga limpia."""
        self.comprobado.append(que)

    @property
    def bloqueantes(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.severidad is Severidad.BLOQUEA]

    @property
    def veredicto(self) -> str:
        """Nunca dos estados.

        SIN_EVALUAR no es un aprobado silencioso: es la respuesta honesta a
        "no habia con que comprobarlo", y tiene que verse distinta de OK.

        NO_APLICA es el cuarto, y es el `[N/A]` de la Guia 8. Se separa de
        SIN_EVALUAR porque uno frena el despliegue y el otro no: ver el
        comentario del campo `no_aplica`.
        """
        # Los hallazgos mandan. j11, j06 y j08 anotan la AUSENCIA de /health,
        # .env.example o .gitignore antes de llamar a comprobo(), y el informe
        # decia "este juez NO comprobo nada" mientras emitia ::error:: y exit 1.
        # Dos estados a la vez, que es justo lo que este metodo promete no dar.
        if self.hallazgos:
            return "HALLAZGOS"
        if self.comprobado:
            return "OK"
        if self.no_aplica:
            return "NO_APLICA"
        return "SIN_EVALUAR"


# --------------------------------------------------------------------------
# El repositorio bajo examen
# --------------------------------------------------------------------------


# Los nombres con que Docker Compose busca el archivo, en su orden. Estaba copiada
# en j01, j02 y j06, y j11 leía sólo el primero: su excepción de software de
# terceros no veía un `compose.yaml` (auditoría del 2026-10-25).
COMPOSE = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")


class Repo:
    """Acceso de solo lectura al repositorio que se está juzgando.

    Se apoya en `git ls-files` y no en un recorrido del disco: lo que importa
    para casi todas las reglas es qué está VERSIONADO. Un `.env` presente en el
    disco de trabajo y no trackeado es correcto; el mismo archivo en
    `git ls-files` es el incidente de COIPO_USUARIOS.
    """

    def __init__(self, raiz: str | os.PathLike[str]) -> None:
        self.raiz = Path(raiz).resolve()
        if not self.raiz.is_dir():
            raise SystemExit(f"[jueces] no existe el directorio: {self.raiz}")
        self._versionados: list[str] | None = None
        self._fallo_git: str | None = None

    @property
    def nombre(self) -> str:
        return self.raiz.name

    def versionados(self) -> list[str]:
        """Rutas relativas con barras `/`, tal como las emite git."""
        if self._versionados is None:
            try:
                salida = subprocess.run(
                    ["git", "-C", str(self.raiz), "ls-files", "-z"],
                    # `encoding` EXPLICITO: con `text=True` a secas Python
                    # decodifica con el codec del locale (cp1252 en las
                    # maquinas Windows del equipo) y un solo byte no-ASCII
                    # en un nombre de archivo hace estallar el hilo lector
                    # de subprocess. Paso con COIPO_ENTREGA_PLANTA: el juez
                    # moria antes de mirar nada.
                    capture_output=True, check=True,
                    encoding="utf-8", errors="replace",
                )
                self._versionados = [r for r in (salida.stdout or "").split("\0") if r]
            except subprocess.CalledProcessError as e:
                # Sin git no se puede afirmar nada sobre lo versionado. Se
                # devuelve vacío y se GUARDA EL PORQUÉ: `indice_roto()` lo da, y
                # el juez lo declara no evaluado (`sin_indice`). NUNCA se cae al
                # recorrido del disco, que daría el veredicto contrario al
                # correcto sobre un `.env` local legítimo.
                #
                # Hasta el 2026-10-25 este comentario prometía lo mismo y nadie
                # lo cumplía: vacío y fallido eran indistinguibles, y j13 salía
                # NO_APLICA y j16 OK sobre un `.git` roto. Cero de cero.
                error = (e.stderr or "").strip().splitlines()
                self._fallo_git = (f"`git ls-files` salió {e.returncode}"
                                   + (f": {error[0][:160]}" if error else ""))
                self._versionados = []
            except (FileNotFoundError, OSError) as e:
                self._fallo_git = f"`git ls-files` no se pudo ejecutar ({type(e).__name__}: {e})"
                self._versionados = []
        return self._versionados

    def indice_roto(self) -> str | None:
        """Por qué no se puede leer lo versionado, o None si se puede.

        Distingue «falló» de «vacío»: un repositorio git sano sin un solo archivo
        devuelve `[]` y None; uno con el `.git` roto devuelve `[]` y el motivo."""
        if not self.tiene_git():
            return f"`git ls-files` no aplica: {self.raiz.name} no tiene `.git`"
        self.versionados()
        return self._fallo_git

    def tiene_git(self) -> bool:
        return (self.raiz / ".git").exists()

    def ruta(self, relativa: str) -> Path:
        return self.raiz / relativa

    def existe(self, relativa: str) -> bool:
        return (self.raiz / relativa).exists()

    def texto(self, relativa: str) -> str | None:
        """Contenido de un archivo de texto, o None si no se puede leer.

        `errors="replace"` a propósito: un juez no puede caerse porque un
        archivo tenga un byte raro. Prefiere ver un carácter de reemplazo a
        abortar la sesión entera de verificación.
        """
        p = self.raiz / relativa
        try:
            # utf-8-sig y no utf-8: un BOM al inicio de .env.example o .gitignore
            # dejaba "﻿DATABASE_HOST=" fuera de `^\s*CLAVE=` y producia
            # bloqueantes falsos en j06, j08, j09 y j01. Sin BOM lee identico.
            return p.read_text(encoding="utf-8-sig", errors="replace")
        except (OSError, IsADirectoryError):
            return None

    def lineas(self, relativa: str) -> list[str]:
        t = self.texto(relativa)
        return t.splitlines() if t is not None else []

    def compose(self) -> str | None:
        """El compose de la raíz, con cualquiera de los cuatro nombres que acepta Docker."""
        return next((c for c in COMPOSE if self.existe(c)), None)

    def buscar(self, *patrones: str) -> Iterator[str]:
        """Rutas versionadas cuyo nombre casa con alguno de los patrones glob."""
        from fnmatch import fnmatch

        for r in self.versionados():
            if any(fnmatch(r, p) for p in patrones):
                yield r


def sin_indice(repo: Repo, r: Resultado) -> bool:
    """True, y lo anota en `no_evaluado`, si no se puede leer lo versionado.

    Todo juez que decide sobre `git ls-files` lo llama ANTES de dictaminar nada:
    con el índice ilegible no sale OK ni NO_APLICA, sale SIN_EVALUAR."""
    motivo = repo.indice_roto()
    if motivo is None:
        return False
    r.no_evaluado.append(
        f"{motivo}. Sin la lista de archivos versionados este juez no puede afirmar "
        "nada: cero archivos leídos no es «nada que juzgar»")
    return True


# --------------------------------------------------------------------------
# Supresiones
# --------------------------------------------------------------------------

# Marcador para silenciar un hallazgo concreto. Formato, en la MISMA línea o en
# la inmediatamente anterior:
#
#     coipo-jueces:ignorar(G8-4) fixture sintético del test de secretos
#
# El motivo es obligatorio y de al menos 12 caracteres. Un marcador sin motivo
# no suprime nada: si silenciar cuesta lo mismo que arreglar, se arregla.
_MARCADOR = re.compile(
    r"coipo-jueces:\s*ignorar\(\s*(?P<regla>[A-Za-z0-9_\-\.]+)\s*\)\s*(?P<motivo>.*)"
)


def suprimido(lineas: list[str], indice: int, regla: str) -> str | None:
    """Motivo de la supresión de `regla` en `lineas[indice]`, o None.

    Se mira la línea y la anterior porque hay formatos —YAML, .env, SQL— donde
    no cabe un comentario al final sin cambiar el valor.

    `indice` es 0-based.
    """
    for i in (indice, indice - 1):
        if 0 <= i < len(lineas):
            m = _MARCADOR.search(lineas[i])
            if m and m.group("regla") == regla:
                motivo = m.group("motivo").strip().rstrip("-*#/ ").strip()
                if len(motivo) >= 12:
                    return motivo
    return None


# --------------------------------------------------------------------------
# Reporte y CLI
# --------------------------------------------------------------------------

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
_ROJO, _AMARILLO, _VERDE, _GRIS, _FIN = (
    ("\033[31m", "\033[33m", "\033[32m", "\033[90m", "\033[0m") if _COLOR else ("",) * 5
)


def _anotacion_github(h: Hallazgo, juez: str, modo: str) -> str:
    """Anotación de GitHub Actions, para que salga en el diff del PR.

    `::error::` incluso cuando el modo es advisory sería mentir sobre el
    estado del build; en advisory todo baja a `::warning::`. Hasta el 2026-10-25
    esto lo decía sólo este docstring: el código no recibía el modo y emitía
    `::error::` para todo BLOQUEA (lo fija `tests/test_anotaciones.py`).
    """
    nivel = "error" if (modo == "bloqueante" and h.severidad is Severidad.BLOQUEA) else "warning"
    partes = [f"file={h.archivo}"] if h.archivo else []
    if h.linea:
        partes.append(f"line={h.linea}")
    loc = ",".join(partes)
    return f"::{nivel} {loc}::[{juez}/{h.regla}] {h.mensaje} — {h.manifestacion}"


def informar(resultado: Resultado, *, modo: str, en_github: bool) -> None:
    print(f"\n{'=' * 78}\n{resultado.juez} — {resultado.descripcion}\n{'=' * 78}")

    marca = {"OK": _VERDE, "HALLAZGOS": _AMARILLO,
             "SIN_EVALUAR": _AMARILLO, "NO_APLICA": _GRIS}[resultado.veredicto]
    print(f"{marca}  veredicto: {resultado.veredicto}"
          f"  ({len(resultado.comprobado)} comprobacion/es realizadas){_FIN}")
    if resultado.veredicto == "SIN_EVALUAR":
        print(f"{_AMARILLO}  este juez NO comprobo nada. Cero hallazgos aqui NO significa "
              f"que este bien.{_FIN}")
        if en_github:
            print(f"::warning::[{resultado.juez}] no comprobo nada: "
                  f"cero hallazgos no equivale a conforme")

    for razon in resultado.no_aplica:
        print(f"{_GRIS}  no aplica: {razon}{_FIN}")
        if en_github:
            print(f"::notice::[{resultado.juez}] no aplica: {razon}")

    for nota in resultado.no_evaluado:
        print(f"{_GRIS}  no evaluado: {nota}{_FIN}")
        if en_github:
            print(f"::notice::[{resultado.juez}] no evaluado: {nota}")

    for s in resultado.supresiones:
        print(f"{_AMARILLO}  suprimido: {s}{_FIN}")
    if resultado.supresiones:
        n = len(resultado.supresiones)
        print(f"{_AMARILLO}  {n} supresión(es) activa(s){_FIN}")
        if en_github:
            print(f"::warning::[{resultado.juez}] {n} supresión(es) activa(s). "
                  f"Cada una exige una fila en DEUDA.md.")

    if not resultado.hallazgos:
        if resultado.comprobado:
            print(f"{_VERDE}  sin hallazgos{_FIN}")
        return

    for h in resultado.hallazgos:
        color = _ROJO if h.severidad is Severidad.BLOQUEA else _AMARILLO
        etiqueta = h.severidad.value if modo == "bloqueante" else "AVISA"
        print(f"{color}  [{etiqueta}] {h.regla}  {h.ubicacion()}{_FIN}")
        print(f"           {h.mensaje}")
        print(f"           {_GRIS}en producción: {h.manifestacion}{_FIN}")
        if h.arreglo:
            print(f"           {_GRIS}arreglo: {h.arreglo}{_FIN}")
        if en_github:
            print(_anotacion_github(h, resultado.juez, modo))

    b = len(resultado.bloqueantes)
    print(f"\n  {len(resultado.hallazgos)} hallazgo(s), {b} de severidad BLOQUEA")


def ejecutar(juez: str, descripcion: str,
             comprobar: Callable[[Repo, Resultado], None]) -> None:
    """Punto de entrada común de todos los jueces.

    El código de salida es 1 SOLO en modo bloqueante y con hallazgos
    bloqueantes. En advisory el juez informa y sale 0 aunque el repo esté
    lleno de defectos: es lo que permite conectarlo a los 22 repos existentes
    el primer día sin dejar a la flota sin desplegar.
    """
    p = argparse.ArgumentParser(description=descripcion)
    p.add_argument("--repo", default=".", help="raíz del repositorio a juzgar")
    p.add_argument("--modo", choices=("advisory", "bloqueante"), default="advisory")
    p.add_argument("--json", dest="json_salida", default=None,
                   help="escribir los hallazgos como JSON en esta ruta")
    p.add_argument("--github", action="store_true",
                   help="emitir anotaciones de GitHub Actions")
    args = p.parse_args()

    en_github = args.github or os.environ.get("GITHUB_ACTIONS") == "true"
    resultado = Resultado(juez=juez, descripcion=descripcion)
    comprobar(Repo(args.repo), resultado)
    informar(resultado, modo=args.modo, en_github=en_github)

    if args.json_salida:
        Path(args.json_salida).write_text(
            json.dumps(
                {
                    "juez": resultado.juez,
                    "modo": args.modo,
                    "no_evaluado": resultado.no_evaluado,
                    "no_aplica": resultado.no_aplica,
                    "supresiones": resultado.supresiones,
                    "veredicto": resultado.veredicto,
                    "comprobado": resultado.comprobado,
                    "hallazgos": [asdict(h) for h in resultado.hallazgos],
                },
                ensure_ascii=False, indent=2, default=str,
            ),
            encoding="utf-8",
        )

    sys.exit(1 if (args.modo == "bloqueante" and resultado.bloqueantes) else 0)
