#!/usr/bin/env python3
"""j16 — código mantenible: tamaño de archivo, TypeScript y capas.

Implementa la regla 9 de `AGENTS.md` de `coipo_master_produccion`, detallada en
`docs/ESTANDAR_CODIGO.md` de ese repositorio. La decidió Luis Monsalve el
2026-10-24: «buenas prácticas, arquitectura hexagonal, TypeScript, ningún archivo
con más de 800 líneas, máximo 1000. Eso debería ser regla de la fábrica: tampoco
queremos producir código espagueti en la fábrica».

  COD-1  Ningún archivo de código pasa de 1000 líneas; sobre 800, aviso.
  COD-2  El frontend es TypeScript estricto: nada de `.js`/`.jsx` en
         `frontend/src/`, y un `tsconfig` con `"strict": true`.
  COD-3  Arquitectura hexagonal: el dominio (`frontend/src/dominio/`,
         `backend/app/dominio/` y la carpeta `dominio/` de cualquier servicio
         hermano, como `collector/`) no importa la interfaz, la red, la base de
         datos ni el sistema (`os`; en Node, `fs`, `http`, `process.env`...).

MIRA HACIA ADELANTE, NO HACIA ATRÁS (`FILOSOFIA.md` de la fábrica, §3 y §4)
  «Las soluciones que ya generamos no serán retrocompatibles y está bien; lo
  importante es que de aquí en adelante se hagan las cosas mejor.» Por eso la
  severidad depende de la FECHA DE SIEMBRA, que `sembrar.py` escribe en
  `.semilla` como `fabrica: AAAA-MM-DD`:

    fabrica >= VIGENCIA   -> BLOQUEA. Nació con la regla y la semilla ya la cumple.
    fabrica <  VIGENCIA   -> AVISA. La deuda se ve; el despliegue no se detiene.
    sin `fabrica:`        -> AVISA. Adopta un estándar, o se sembró antes de que
                             existiera la clave.
    sin `.semilla`        -> NO_APLICA. Como `j13`: el alcance se declara.

  La franja de 801 a 1000 líneas AVISA siempre: es el margen para partir antes
  de llegar al techo, no un defecto.

CALIBRACIÓN INVERSA (2026-10-24, sobre los clones de D:\\GitHub)
  coipo_n8n, COIPO_USUARIOS,
  coipo_jueces, coipo_maqueta   -> NO_APLICA: sin `.semilla`.
  coipo_prensa2                 -> AVISA (COD-1 x2, COD-2 x2, COD-3), CERO bloqueos:
                                   adopta `interfaz` sin `fabrica:`.
  coipo_atraso_personal, coipo_firms, coipo_visor_saff, coipo_anillo_evacuacion,
  coipo_api, coipo_avisete,
  coipo_prevension_ministerial  -> AVISA, CERO bloqueos: sembrados antes de la
                                   vigencia (el `fabrica:` más reciente del disco es
                                   2026-10-23). Su deuda se ve y nada se detiene.
  Una app sembrada de la semilla del 2026-10-24 -> TIENE QUE salir OK antes de mover
  el tag con este juez (FILOSOFIA.md, §5). Pendiente hasta que la semilla migre.

COD-3 EN LOS SERVICIOS HERMANOS (2026-10-25). Hasta ese día sólo se miraban
`backend/app/dominio/` y `frontend/src/dominio/`: un `import httpx` y un `import os`
metidos en `collector/colector/dominio/` de una aplicación de prueba dejaban el gate
en cero hallazgos. Ahora se descubre toda carpeta `dominio/` versionada (fuera de
pruebas y de lo generado) y se juzga con las reglas de su lenguaje. Calibración
sobre los 88 repositorios `coipo*` con git de D:\\GitHub y las tres apps de prueba:
  CERO hallazgos de diferencia con la versión anterior en los 91.
  coipo_prensa2 (colector JS hexagonal en producción, 21 archivos en
  `collector/src/dominio/`)       -> limpio en COD-3: sus imports son relativos y
                                   dentro del dominio.
  coipo_prueba_divisas (colector Python, `collector/colector/dominio/`) -> OK; con
                                   `import httpx` e `import os` añadidos, 2 BLOQUEA y
                                   exit 1 en modo bloqueante (antes: OK, exit 0).

La medida que la funda:
45 de los 89 repositorios `coipo*` con git del disco tienen al menos un archivo de
más de 800 líneas, y `coipo_prensa2`, el repositorio más sano de la flota, uno de
1985 (`frontend/src/estilos.css`). Con BLOQUEA para todos, el gate se apagaba
el primer día; con esta asimetría, prensa2 sólo avisa.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, leer_fabrica, suprimido  # noqa: E402

PERFILES = ("aplicacion",)

COD_1 = "COD-1"
COD_2 = "COD-2"
COD_3 = "COD-3"

# El día en que la regla entró. Una aplicación sembrada desde entonces la cumple
# desde su primer commit, porque la semilla ya la cumple (`FILOSOFIA.md`, §5).
VIGENCIA = "2026-10-24"

MARCADOR = ".semilla"

TECHO = 1000
AVISO = 800

EXTENSIONES_DE_CODIGO = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css", ".scss",
    ".html", ".vue", ".svelte", ".sql", ".sh",
})
# Lo generado o de terceros no lo escribió nadie de la flota: partirlo no se puede.
GENERADO = re.compile(r"(^|/)(node_modules|dist|build|vendor|\.venv|venv|coverage)(/|$)|\.min\.")

# ── COD-3 ─────────────────────────────────────────────────────────────────────
IMPORT_JS = re.compile(
    r"""(?:\bimport\b[^'"`;]*?\bfrom\s*|\bimport\s*\(\s*|\bimport\s+|\brequire\s*\(\s*)['"]([^'"]+)['"]""")
# La interfaz (React, hojas de estilo) y, para un dominio que corre en Node —el
# colector de `coipo_prensa2`—, la red, la base de datos y el sistema: los módulos
# de Node que hablan con afuera y los clientes de red y de base más comunes.
PROHIBIDO_JS_MODULO = re.compile(
    r"^(react|react-dom)(/|$)|\.css$"
    r"|^(node:)?(fs|fs/promises|http|https|http2|net|tls|dgram|child_process)$"
    r"|^(pg|mysql2?|mongodb|axios|node-fetch|undici)(/|$)")
# Las capas de afuera, con los nombres de la semilla (`aplicacion/`, `adaptadores/`,
# `componentes/`, `vistas/`, `estilos/`) y el genérico `interfaz/`.
PROHIBIDO_JS_CAPA = re.compile(r"(^|/)(aplicacion|adaptadores|componentes|vistas|estilos|interfaz)(/|$)")
# El lookbehind descarta `puerto.fetch(` o `noticia.document.x`: un método de un
# puerto inyectado no es la red, y una propiedad que se llama `document` no es el DOM.
PROHIBIDO_JS_USO = re.compile(
    r"(?<![\w$.])(fetch\s*\(|window\.|document\.|localStorage\b|sessionStorage\b|process\.env\b)")
IMPORT_PY = re.compile(r"^[ \t]*(?:from[ \t]+([\w.]+)[ \t]+import|import[ \t]+([\w.]+))", re.MULTILINE)
# Python: la lista del dominio de `backend/tests/arquitectura/test_capas.py`, pieza
# CONGELADA de la semilla, en lo que ya miraba este juez más `os` («en el dominio,
# `os.environ` sería una regla de negocio que depende del entorno, y una regla que
# cambia con una variable no se puede probar», dice esa prueba).
PROHIBIDO_PY = re.compile(r"^(fastapi|starlette|sqlalchemy|httpx|requests|psycopg2?|asyncpg|os)(\.|$)")
# Y las capas de afuera por NOMBRE DE SEGMENTO, no por paquete: el colector de una
# aplicación no se llama `app` (`colector.adaptadores`), y un import relativo
# (`from ..adaptadores import x`) no lleva paquete.
PROHIBIDO_PY_CAPA = frozenset({"adaptadores", "composicion"})

# Dónde hay un dominio además de `frontend/src/dominio/` y `backend/app/dominio/`:
# un servicio hermano —`collector/`— con su propia carpeta `dominio/`. Se descubre
# por la carpeta, no por una lista de servicios: la flota los nombra como quiere.
EXT_PY = frozenset({".py"})
EXT_JS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})
DOMINIOS_PROPIOS = ("frontend/src/dominio", "backend/app/dominio")
# Una carpeta `dominio/` dentro de pruebas, fixtures o lo generado no es un dominio.
NO_ES_DOMINIO = frozenset({"tests", "test", "__tests__", "spec", "fixtures", "node_modules",
                           "dist", "build", "vendor", ".venv", "venv", "coverage"})


def _lineas_de(repo: Repo, ruta: str) -> int | None:
    try:
        datos = repo.ruta(ruta).read_bytes()
    except OSError:
        return None
    if not datos:
        return 0
    return datos.count(b"\n") + (0 if datos.endswith(b"\n") else 1)


def _suprimido_en_cabecera(repo: Repo, ruta: str, regla: str) -> str | None:
    """Una supresión vale en las tres primeras líneas: un shebang o un `<!doctype>`
    ocupan la primera y no admiten comentario."""
    lineas = repo.lineas(ruta)[:3]
    for i in range(len(lineas)):
        if (motivo := suprimido(lineas, i, regla)):
            return motivo
    return None


def _sin_comentarios_js(texto: str) -> str:
    """Quita `/* */` y `//` conservando los saltos de línea (para el número)."""
    texto = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.DOTALL)
    return re.sub(r"(^|[^:\\])//[^\n]*", r"\1", texto)


def _linea_de(texto: str, posicion: int) -> int:
    return texto.count("\n", 0, posicion) + 1


# ── COD-1 ─────────────────────────────────────────────────────────────────────

def _tamano(repo: Repo, r: Resultado, nuevo: bool, contexto: str) -> None:
    medidos = 0
    for ruta in repo.versionados():
        if PurePosixPath(ruta).suffix.lower() not in EXTENSIONES_DE_CODIGO or GENERADO.search(ruta):
            continue
        n = _lineas_de(repo, ruta)
        if n is None:
            r.no_evaluado.append(f"{ruta}: no se pudo leer para contar sus líneas.")
            continue
        medidos += 1
        if n <= AVISO:
            continue
        if (motivo := _suprimido_en_cabecera(repo, ruta, COD_1)):
            r.supresiones.append(f"{ruta} ({n} líneas) — {motivo}")
            continue
        datos = dict(
            archivo=ruta,
            manifestacion=(
                "un asistente no lee entero un archivo de este tamaño: lo lee a trozos, "
                "edita lo que vio y rompe lo que no vio. Y una persona que hereda la "
                "aplicación no sabe por dónde empezar"),
            arreglo=(
                "partirlo por responsabilidad, no por número de línea: los estilos por "
                "componente, el SQL por tema en archivos ordenados, las pruebas por lo que "
                "prueban. Si de verdad no se puede, `coipo-jueces:ignorar(COD-1) <motivo>` "
                "en una de sus tres primeras líneas: se cuenta y se publica"),
        )
        if n > TECHO:
            mensaje = f"{n} líneas: pasa el techo de {TECHO} ({contexto})"
            if nuevo:
                r.bloquea(COD_1, mensaje=mensaje, **datos)
            else:
                r.avisa(COD_1, mensaje=mensaje, **datos)
        else:
            r.avisa(COD_1, mensaje=f"{n} líneas: pasa de {AVISO}; conviene partirlo antes de {TECHO}",
                    **datos)
    r.comprobo(f"COD-1: tamaño de {medidos} archivo(s) de código versionados")


# ── COD-2 ─────────────────────────────────────────────────────────────────────

def _typescript(repo: Repo, r: Resultado, nuevo: bool, contexto: str) -> None:
    if not repo.existe("frontend/package.json"):
        r.comprobo("COD-2: no hay `frontend/package.json`; no hay frontend que juzgar")
        return
    versionados = repo.versionados()
    js = [p for p in versionados
          if p.startswith("frontend/src/") and PurePosixPath(p).suffix.lower() in (".js", ".jsx")]
    ts = [p for p in versionados
          if p.startswith("frontend/src/") and PurePosixPath(p).suffix.lower() in (".ts", ".tsx")]
    r.comprobo(f"COD-2: {len(ts)} archivo(s) TypeScript y {len(js)} JavaScript en `frontend/src/`")

    if js:
        muestra = ", ".join(f"`{p}`" for p in js[:5]) + (f" y {len(js) - 5} más" if len(js) > 5 else "")
        datos = dict(
            archivo=js[0],
            mensaje=f"{len(js)} archivo(s) JavaScript en `frontend/src/` ({contexto}): {muestra}",
            manifestacion=(
                "sin tipos, la forma de los datos se adivina: un campo que el backend "
                "renombra llega como `undefined` y la pantalla muestra un vacío en vez de "
                "un error, sin que nada lo detecte antes de producción"),
            arreglo=(
                "renombrar a `.ts`/`.tsx` y tiparlo; `tsc --noEmit` en el CI lo hace "
                "cumplir. La semilla desde el 2026-10-24 ya viene así"),
        )
        if nuevo:
            r.bloquea(COD_2, **datos)
        else:
            r.avisa(COD_2, **datos)

    configuraciones = [p for p in versionados if re.fullmatch(r"frontend/tsconfig[\w.-]*\.json", p)]
    estricto = any(re.search(r'"strict"\s*:\s*true', repo.texto(p) or "") for p in configuraciones)
    if not estricto:
        datos = dict(
            archivo=configuraciones[0] if configuraciones else "frontend/tsconfig.json",
            mensaje=("no hay `frontend/tsconfig*.json` con `\"strict\": true`"
                     f" ({contexto})"),
            manifestacion=(
                "TypeScript sin `strict` deja pasar `null` y `any` implícitos: compila "
                "verde y falla igual que JavaScript en la pantalla de la persona"),
            arreglo="un `frontend/tsconfig.json` con `\"strict\": true`, como el de la semilla",
        )
        if nuevo:
            r.bloquea(COD_2, **datos)
        else:
            r.avisa(COD_2, **datos)


# ── COD-3 ─────────────────────────────────────────────────────────────────────

_MANIFESTACION_CAPAS = (
    "el dominio es lo que la aplicación sabe hacer. Si conoce la interfaz, la red o la "
    "base de datos, cambiar cualquiera obliga a reescribirlo, y probarlo exige levantar "
    "un navegador o una base: las pruebas se vuelven lentas y se dejan de correr")


def _capas_frontend(repo: Repo, r: Resultado, nuevo: bool, contexto: str) -> None:
    if not repo.existe("frontend/package.json"):
        return
    dominio = [p for p in repo.versionados()
               if p.startswith("frontend/src/dominio/")
               and PurePosixPath(p).suffix.lower() in (".ts", ".tsx", ".js", ".jsx")]
    if not dominio:
        datos = dict(
            archivo="frontend/src/dominio/",
            mensaje=f"el frontend no tiene `src/dominio/` ({contexto})",
            manifestacion=_MANIFESTACION_CAPAS,
            arreglo=("separar en `src/dominio/` (puro), `src/puertos/`, `src/adaptadores/` "
                     "y `src/interfaz/`, como la semilla desde el 2026-10-24"),
        )
        if nuevo:
            r.bloquea(COD_3, **datos)
        else:
            r.avisa(COD_3, **datos)
        r.comprobo("COD-3: buscado `frontend/src/dominio/`")
        return

    for ruta in dominio:
        _anotar_capas(repo, r, nuevo, ruta, _motivos_js(repo.texto(ruta) or ""))
    r.comprobo(f"COD-3: {len(dominio)} archivo(s) de `frontend/src/dominio/` sin interfaz, red ni navegador")


def _motivos_js(crudo: str) -> list[tuple[int, str]]:
    texto = _sin_comentarios_js(crudo)
    motivos: list[tuple[int, str]] = []
    for m in IMPORT_JS.finditer(texto):
        destino = m.group(1)
        if PROHIBIDO_JS_MODULO.search(destino) or PROHIBIDO_JS_CAPA.search(destino):
            motivos.append((_linea_de(texto, m.start()), f"importa `{destino}`"))
    for m in PROHIBIDO_JS_USO.finditer(texto):
        motivos.append((_linea_de(texto, m.start()), f"usa `{m.group(1).strip()}`"))
    return motivos


def _importa_py_prohibido(modulo: str, nivel: int) -> bool:
    """`modulo` sin los puntos del import relativo; `nivel` es cuántos llevaba.

    Un import relativo no nombra un paquete de terceros (`from . import os` es un
    módulo propio que se llama así): de él sólo cuenta si cruza a una capa de afuera."""
    if nivel == 0 and PROHIBIDO_PY.search(modulo):
        return True
    return any(segmento in PROHIBIDO_PY_CAPA for segmento in modulo.split("."))


def _motivos_py(texto: str) -> list[tuple[int, str]]:
    """Los imports prohibidos de un archivo Python, con su línea.

    Con `ast` y no con una expresión: una expresión no ve `import sys, os` ni
    `from ..adaptadores import x`, y sí ve un `import httpx` escrito en un docstring.
    Si el archivo no compila se vuelve a la expresión, que algo mira."""
    try:
        arbol = ast.parse(texto)
    except (SyntaxError, ValueError):
        return [(_linea_de(texto, m.start()), f"importa `{m.group(1) or m.group(2)}`")
                for m in IMPORT_PY.finditer(texto)
                if _importa_py_prohibido(m.group(1) or m.group(2), 0)]
    motivos: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if _importa_py_prohibido(alias.name, 0):
                    motivos.append((nodo.lineno, f"importa `{alias.name}`"))
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            candidatos = [base] + [f"{base}.{a.name}" if base else a.name for a in nodo.names]
            visto = "." * nodo.level + base
            if any(c and _importa_py_prohibido(c, nodo.level) for c in candidatos):
                motivos.append((nodo.lineno, f"importa `{visto or '.'}`"))
    return sorted(set(motivos))


def _capas_backend(repo: Repo, r: Resultado, nuevo: bool) -> None:
    dominio = [p for p in repo.versionados() if p.startswith("backend/app/dominio/") and p.endswith(".py")]
    if not dominio:
        return
    for ruta in dominio:
        _anotar_capas(repo, r, nuevo, ruta, _motivos_py(repo.texto(ruta) or ""))
    r.comprobo(f"COD-3: {len(dominio)} archivo(s) de `backend/app/dominio/` sin framework ni base de datos")


def _dominios_hermanos(versionados: list[str]) -> dict[str, list[str]]:
    """raíz del dominio (`collector/colector/dominio`) -> sus archivos de código.

    La raíz es la ruta hasta el PRIMER segmento `dominio`. Las dos que ya tienen su
    propia comprobación, y lo que vive dentro de pruebas o de lo generado, no cuentan."""
    hermanos: dict[str, list[str]] = {}
    for ruta in versionados:
        if PurePosixPath(ruta).suffix.lower() not in EXT_PY | EXT_JS:
            continue
        partes = ruta.split("/")
        if "dominio" not in partes[:-1]:
            continue
        i = partes.index("dominio")
        raiz = "/".join(partes[:i + 1])
        if raiz in DOMINIOS_PROPIOS or any(p in NO_ES_DOMINIO for p in partes[:i]):
            continue
        hermanos.setdefault(raiz, []).append(ruta)
    return hermanos


def _capas_hermanos(repo: Repo, r: Resultado, nuevo: bool) -> None:
    """COD-3 en un servicio hermano: el colector, un worker, lo que tenga `dominio/`.

    Hasta el 2026-10-25 este juez sólo miraba `backend/app/dominio/` y
    `frontend/src/dominio/`: un `import httpx` y un `import os` metidos en
    `collector/colector/dominio/` de una aplicación de prueba dejaban el gate en
    cero hallazgos. El dominio de un colector es tan dominio como el del backend."""
    hermanos = _dominios_hermanos(repo.versionados())
    if not hermanos:
        r.comprobo("COD-3: ningún otro `dominio/` versionado fuera de `backend/app/` y `frontend/src/`")
        return
    for raiz, rutas in sorted(hermanos.items()):
        for ruta in rutas:
            texto = repo.texto(ruta) or ""
            es_py = PurePosixPath(ruta).suffix.lower() in EXT_PY
            _anotar_capas(repo, r, nuevo, ruta, _motivos_py(texto) if es_py else _motivos_js(texto))
        r.comprobo(f"COD-3: {len(rutas)} archivo(s) de `{raiz}/` sin interfaz, red ni base de datos")


def _anotar_capas(repo: Repo, r: Resultado, nuevo: bool, ruta: str, motivos: list[tuple[int, str]]) -> None:
    lineas = repo.lineas(ruta)
    for linea, motivo in motivos:
        if (razon := suprimido(lineas, linea - 1, COD_3)):
            r.supresiones.append(f"{ruta}:{linea} {motivo} — {razon}")
            continue
        datos = dict(
            archivo=ruta, linea=linea,
            mensaje=f"el dominio {motivo}",
            manifestacion=_MANIFESTACION_CAPAS,
            arreglo=("declarar lo que el dominio necesita como un puerto (`puertos/`) y "
                     "darle la implementación desde un adaptador; el dominio recibe datos, "
                     "no los va a buscar"),
        )
        if nuevo:
            r.bloquea(COD_3, **datos)
        else:
            r.avisa(COD_3, **datos)


# ── Entrada ───────────────────────────────────────────────────────────────────

def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.tiene_git():
        r.no_evaluado.append("no es un repositorio git: este juez mide lo VERSIONADO.")
        return
    marcador = repo.texto(MARCADOR)
    if marcador is None:
        r.no_corresponde(
            f"no hay `{MARCADOR}`: el repositorio no declara seguir un estándar de la "
            "flota. Lo que existía antes de la fábrica no se juzga con sus reglas "
            "nuevas (FILOSOFIA.md, §3).")
        return

    fecha = leer_fabrica(marcador)
    nuevo = fecha is not None and fecha >= VIGENCIA
    if nuevo:
        contexto = f"sembrado el {fecha}, con la regla ya vigente desde el {VIGENCIA}"
    elif fecha:
        contexto = f"sembrado el {fecha}, antes de la regla del {VIGENCIA}: sólo aviso"
    else:
        contexto = f"`{MARCADOR}` sin `fabrica:`: sólo aviso"

    _tamano(repo, r, nuevo, contexto)
    _typescript(repo, r, nuevo, contexto)
    _capas_frontend(repo, r, nuevo, contexto)
    _capas_backend(repo, r, nuevo)
    _capas_hermanos(repo, r, nuevo)


if __name__ == "__main__":
    ejecutar("j16", "código mantenible: tamaño, TypeScript y capas", comprobar)
