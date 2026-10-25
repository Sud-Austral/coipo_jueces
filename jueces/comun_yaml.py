"""El parser YAML de los jueces: el subconjunto que usan los compose de la flota.

Vive aparte de `comun.py` desde el 2026-10-25 para que ningún archivo del motor
pase de 800 líneas (regla 9 de `AGENTS.md` de la fábrica, `COD-1`). `comun.py`
lo reexporta: los jueces siguen importando `carga_yaml` desde `comun`.
"""

from __future__ import annotations

import re
from typing import Any

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
    # `re.fullmatch` y no `lstrip("-").isdigit()`: "--5" pasaba el segundo y
    # reventaba en int(), tumbando al juez entero con un ValueError por un
    # `command: --5` en el compose. Medido el 2026-09-08.
    if re.fullmatch(r"-?\d+", t):
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

        # En YAML real la ancla va en posicion de VALOR (`x-comun: &comun`), el
        # alias en `<<: *comun` o en `- *puerto`. Solo mirar el inicio de linea
        # los dejaba pasar y los colgaba de la raiz como cadenas. Medido el
        # 2026-09-08 con un compose de anclas: el parser lo interpretaba mal EN
        # SILENCIO, que es lo contrario de lo que promete el docstring.
        if (cuerpo.startswith(("&", "*", "<<"))
                or re.search(r"(?::\s*|^-\s+)[&*][A-Za-z0-9_.-]+\s*$", cuerpo)):
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


