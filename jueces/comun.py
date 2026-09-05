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
        if self.comprobado:
            return "HALLAZGOS" if self.hallazgos else "OK"
        if self.no_aplica:
            return "NO_APLICA"
        return "SIN_EVALUAR"


# --------------------------------------------------------------------------
# El repositorio bajo examen
# --------------------------------------------------------------------------


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
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                # Sin git no se puede afirmar nada sobre lo versionado. Se
                # devuelve vacío y el juez lo declara como no evaluado; NUNCA
                # se cae al recorrido del disco, que daría el veredicto
                # contrario al correcto sobre un `.env` local legítimo.
                self._versionados = []
        return self._versionados

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
            return p.read_text(encoding="utf-8", errors="replace")
        except (OSError, IsADirectoryError):
            return None

    def lineas(self, relativa: str) -> list[str]:
        t = self.texto(relativa)
        return t.splitlines() if t is not None else []

    def buscar(self, *patrones: str) -> Iterator[str]:
        """Rutas versionadas cuyo nombre casa con alguno de los patrones glob."""
        from fnmatch import fnmatch

        for r in self.versionados():
            if any(fnmatch(r, p) for p in patrones):
                yield r


# --------------------------------------------------------------------------
# YAML: el subconjunto que usa esta flota, y NADA MÁS
# --------------------------------------------------------------------------


class YamlNoSoportado(Exception):
    """El archivo usa una construcción que este parser no entiende.

    Se lanza en vez de adivinar. Un parser que interpreta mal en silencio es
    exactamente el modo de fallo que estos jueces existen para prevenir: daría
    un verde por el motivo equivocado, que es peor que un rojo ruidoso.
    """


def _desescalar(texto: str) -> Any:
    """Escalar YAML -> valor Python. Sin sorpresas de tipado."""
    t = texto.strip()
    if not t:
        return ""
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        return t[1:-1]
    if t in ("true", "True", "yes", "on"):
        return True
    if t in ("false", "False", "no", "off"):
        return False
    if t in ("null", "~"):
        return None
    if t.lstrip("-").isdigit():
        return int(t)
    return t


def _flow(texto: str) -> list[Any]:
    """Secuencia en línea: `["CMD", "python", "-c", "..."]`.

    Se parte respetando comillas, porque los healthcheck de esta flota llevan
    comas DENTRO del comando de python.
    """
    t = texto.strip()
    if not (t.startswith("[") and t.endswith("]")):
        raise YamlNoSoportado(f"secuencia en línea mal formada: {texto[:60]}")
    cuerpo, piezas, actual, comilla, prof = t[1:-1], [], [], None, 0
    for ch in cuerpo:
        if comilla:
            if ch == comilla:
                comilla = None
            actual.append(ch)
        elif ch in "\"'":
            comilla = ch
            actual.append(ch)
        elif ch in "[{":
            prof += 1
            actual.append(ch)
        elif ch in "]}":
            prof -= 1
            actual.append(ch)
        elif ch == "," and prof == 0:
            piezas.append("".join(actual))
            actual = []
        else:
            actual.append(ch)
    piezas.append("".join(actual))
    return [_desescalar(p) for p in piezas if p.strip()]


def _sin_comentario(linea: str) -> str:
    """Quita el comentario final respetando comillas.

    `# ` dentro de un valor entrecomillado es contenido, no comentario: el
    healthcheck de esta flota lleva un `python -c` con almohadillas dentro.
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


def carga_yaml(texto: str) -> dict[str, Any]:
    """Parser del subconjunto YAML que usan los docker-compose de la flota.

    Soporta: mapas anidados por indentación, secuencias de bloque (`- x` y
    `- k: v`), secuencias en línea (`[a, b]`), escalares entrecomillados y
    comentarios.

    NO soporta —y lo dice lanzando `YamlNoSoportado`—: anclas y alias
    (`&x` / `*x`), escalares de bloque (`|`, `>`), mapas en línea (`{...}`) y
    documentos múltiples. Ninguno aparece en los nueve compose de la flota; si
    algún día aparecen, es mejor un juez que se queja que un juez que miente.
    """
    raiz: dict[str, Any] = {}
    # pila de (indentacion, contenedor). El contenedor es dict o list.
    pila: list[tuple[int, Any]] = [(-1, raiz)]

    lineas = texto.splitlines()
    for n, cruda in enumerate(lineas, start=1):
        linea = _sin_comentario(cruda).rstrip()
        if not linea.strip():
            continue

        sangria = len(linea) - len(linea.lstrip(" "))
        if "\t" in cruda[:sangria]:
            raise YamlNoSoportado(f"línea {n}: tabulación en la indentación")
        cuerpo = linea.strip()

        if cuerpo.startswith(("&", "*")):
            raise YamlNoSoportado(f"línea {n}: anclas/alias no soportados")
        if cuerpo == "---":
            raise YamlNoSoportado(f"línea {n}: documentos múltiples no soportados")

        while pila and sangria <= pila[-1][0]:
            pila.pop()
        if not pila:
            raise YamlNoSoportado(f"línea {n}: indentación inconsistente")
        _, contenedor = pila[-1]

        # ---- elemento de secuencia ----
        if cuerpo.startswith("- "):
            item = cuerpo[2:].strip()
            if not isinstance(contenedor, list):
                raise YamlNoSoportado(f"línea {n}: '-' fuera de una secuencia")
            if ":" in item and not item.startswith(("[", "\"", "'")):
                clave, _, resto = item.partition(":")
                mapa: dict[str, Any] = {}
                contenedor.append(mapa)
                resto = resto.strip()
                if resto:
                    mapa[clave.strip()] = _flow(resto) if resto.startswith("[") else _desescalar(resto)
                else:
                    pila.append((sangria + 2, mapa))
            else:
                contenedor.append(_desescalar(item))
            continue

        # ---- clave: valor ----
        if ":" not in cuerpo:
            raise YamlNoSoportado(f"línea {n}: no es 'clave: valor' ni '- item': {cuerpo[:60]}")
        clave, _, valor = cuerpo.partition(":")
        clave, valor = clave.strip().strip("\"'"), valor.strip()
        if not isinstance(contenedor, dict):
            raise YamlNoSoportado(f"línea {n}: clave dentro de una secuencia sin '-'")

        if valor in ("|", ">", "|-", ">-", "|+", ">+"):
            raise YamlNoSoportado(f"línea {n}: escalar de bloque no soportado")
        if valor.startswith("{"):
            raise YamlNoSoportado(f"línea {n}: mapa en línea no soportado")

        if not valor:
            # Puede abrir un mapa o una secuencia: se decide mirando la
            # siguiente línea con contenido.
            siguiente = _proxima_significativa(lineas, n)
            if siguiente is not None and siguiente[1].startswith("- ") and siguiente[0] > sangria:
                hijo: Any = []
            else:
                hijo = {}
            contenedor[clave] = hijo
            pila.append((sangria, hijo))
        elif valor.startswith("["):
            contenedor[clave] = _flow(valor)
        else:
            contenedor[clave] = _desescalar(valor)

    return raiz


def _proxima_significativa(lineas: list[str], desde: int) -> tuple[int, str] | None:
    for cruda in lineas[desde:]:
        linea = _sin_comentario(cruda).rstrip()
        if linea.strip():
            return len(linea) - len(linea.lstrip(" ")), linea.strip()
    return None


def numero_de_linea(texto: str, aguja: str) -> int | None:
    """Primera línea que contiene `aguja`. Para anclar hallazgos.

    El parser pierde los números de línea a propósito (mantenerlos duplicaría
    su complejidad), así que se recuperan por búsqueda de texto. Es aproximado
    y basta: el hallazgo ya nombra el archivo y la regla.
    """
    for i, linea in enumerate(texto.splitlines(), start=1):
        if aguja in linea:
            return i
    return None


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


def _anotacion_github(h: Hallazgo, juez: str) -> str:
    """Anotación de GitHub Actions, para que salga en el diff del PR.

    `::error::` incluso cuando el modo es advisory sería mentir sobre el
    estado del build; en advisory todo baja a `::warning::`.
    """
    nivel = "error" if h.severidad is Severidad.BLOQUEA else "warning"
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
            print(_anotacion_github(h, resultado.juez))

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
