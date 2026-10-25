"""El parser YAML de los jueces: el subconjunto que usan los compose de la flota.

Vive aparte de `comun.py` desde el 2026-10-25 para que ningún archivo del motor
pase de 800 líneas (regla 9 de `AGENTS.md` de la fábrica, `COD-1`). `comun.py`
lo reexporta: los jueces siguen importando `carga_yaml` desde `comun`.

Sólo biblioteca estándar, como todo el motor: no hay PyYAML en el CI de las
aplicaciones y no se instala nada.
"""

from __future__ import annotations

import copy
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


def _partir_en_comas(cuerpo: str) -> list[str]:
    """Trozos de una colección en línea, separados por comas de primer nivel.

    Respeta comillas y anidamiento: los healthcheck de esta flota llevan comas
    DENTRO del comando de python."""
    piezas, actual, comilla, prof = [], [], None, 0
    for ch in cuerpo:
        if comilla:
            if ch == comilla:
                comilla = None
        elif ch in "\"'":
            comilla = ch
        elif ch in "[{":
            prof += 1
        elif ch in "]}":
            prof -= 1
        elif ch == "," and prof == 0:
            piezas.append("".join(actual))
            actual = []
            continue
        actual.append(ch)
    piezas.append("".join(actual))
    return [p.strip() for p in piezas if p.strip()]


def _partir_clave(texto: str) -> tuple[str, str] | None:
    """`clave: resto` -> (clave, resto), o None si no es una entrada de mapa.

    El separador es el primer `:` seguido de espacio o fin de línea: `8080:80` y
    `http://x` son escalares, no mapas. Una clave entre comillas puede llevar `:`."""
    inicio = 0
    if texto[:1] in "\"'":
        cierre = texto.find(texto[0], 1)
        if cierre < 0:
            return None
        inicio = cierre + 1
    for i in range(inicio, len(texto)):
        if texto[i] == ":" and (i + 1 == len(texto) or texto[i + 1] in " \t"):
            return texto[:i].strip().strip("\"'"), texto[i + 1:]
    return None


_ENCABEZADO_BLOQUE = re.compile(r"^([|>])([-+]?)(\d?)([-+]?)$")
_ANCLA = re.compile(r"^&([^\s\[\]{},]+)\s*(.*)$")
_ES_ITEM = re.compile(r"^-(?:\s|$)")


class _Lector:
    """Parser por indentación, recursivo. Soporta (desde el 2026-10-25):

    mapas y secuencias de bloque, también una secuencia a la misma sangría que su
    clave; mapas de VARIAS claves dentro de una lista (`- type: bind` /
    `  source: x`); escalares en bloque `|` y `>` con `-`/`+` y sangría explícita,
    como valor y como ítem; anclas, alias y la fusión `<<: *x` / `<<: [*a, *b]`;
    colecciones en línea `[...]` y `{...}`, también partidas en varias líneas;
    escalares entrecomillados y planos (con continuación en líneas más sangradas);
    un `---` inicial.

    NO soporta —y lo dice con `YamlNoSoportado`—: etiquetas (`!reset`,
    `!override`, `!!str`), varios documentos, un alias a un ancla que no existe y
    tabulaciones en la sangría.
    """

    def __init__(self, texto: str) -> None:
        self.lineas = texto.splitlines()
        self.anclas: dict[str, Any] = {}

    # -- utilidades de línea ------------------------------------------------
    def _sig(self, i: int) -> int | None:
        while i < len(self.lineas):
            if _sin_comentario(self.lineas[i]).strip():
                return i
            i += 1
        return None

    def _sangria(self, i: int) -> int:
        linea = self.lineas[i]
        cabeza = linea[: len(linea) - len(linea.lstrip(" \t"))]
        if "\t" in cabeza:
            raise YamlNoSoportado(f"línea {i + 1}: tabulación en la indentación")
        return len(cabeza)

    def _cuerpo(self, i: int) -> str:
        return _sin_comentario(self.lineas[i]).strip()

    # -- entrada -------------------------------------------------------------
    def cargar(self) -> dict[str, Any]:
        i = self._sig(0)
        if i is not None and self._cuerpo(i) == "---":
            i = self._sig(i + 1)
        if i is None:
            return {}
        valor, fin = self._bloque(i, self._sangria(i))
        resto = self._sig(fin)
        if resto is not None:
            if self._cuerpo(resto) in ("---", "..."):
                raise YamlNoSoportado(f"línea {resto + 1}: documentos múltiples no soportados")
            raise YamlNoSoportado(f"línea {resto + 1}: indentación inconsistente")
        if not isinstance(valor, dict):
            raise YamlNoSoportado("la raíz del documento no es un mapa")
        return valor

    def _bloque(self, i: int, ind: int) -> tuple[Any, int]:
        if _ES_ITEM.match(self._cuerpo(i)):
            return self._secuencia(i, ind)
        return self._mapa(i, ind)

    # -- colecciones de bloque -------------------------------------------------
    def _mapa(self, i: int, ind: int) -> tuple[dict[str, Any], int]:
        mapa: dict[str, Any] = {}
        fusiones: list[Any] = []
        while (j := self._sig(i)) is not None:
            s = self._sangria(j)
            if s < ind:
                break
            cuerpo = self._cuerpo(j)
            if s > ind:
                raise YamlNoSoportado(f"línea {j + 1}: indentación inconsistente")
            if _ES_ITEM.match(cuerpo) or cuerpo in ("---", "..."):
                break
            partes = _partir_clave(cuerpo)
            if partes is None:
                raise YamlNoSoportado(f"línea {j + 1}: no es 'clave: valor' ni '- item': {cuerpo[:60]}")
            clave, resto = partes
            valor, i = self._valor(resto, j, ind, en_mapa=True)
            if clave == "<<":
                fusiones.extend(valor if isinstance(valor, list) else [valor])
            else:
                mapa[clave] = valor
        for f in fusiones:
            if not isinstance(f, dict):
                raise YamlNoSoportado("`<<:` fusiona algo que no es un mapa")
            for k, v in f.items():
                mapa.setdefault(k, copy.deepcopy(v))
        return mapa, i

    def _secuencia(self, i: int, ind: int) -> tuple[list[Any], int]:
        lista: list[Any] = []
        while (j := self._sig(i)) is not None:
            s = self._sangria(j)
            cuerpo = self._cuerpo(j)
            if s < ind or not _ES_ITEM.match(cuerpo):
                if s > ind:
                    raise YamlNoSoportado(f"línea {j + 1}: indentación inconsistente")
                break
            if s > ind:
                raise YamlNoSoportado(f"línea {j + 1}: indentación inconsistente")
            crudo = self.lineas[j]
            tras_guion = crudo[s + 1:]
            columna = s + 1 + len(tras_guion) - len(tras_guion.lstrip(" "))
            resto = cuerpo[1:].strip()
            if resto and (_ES_ITEM.match(resto) or (resto[0] not in "[{&*!|>" and _partir_clave(resto))):
                # `- clave: v` (mapa de una o VARIAS claves) o `- - x`: se reescribe la
                # línea como si el ítem empezara en su columna y se lee como bloque.
                self.lineas[j] = " " * columna + crudo[columna:]
                valor, i = self._bloque(j, columna)
            else:
                valor, i = self._valor(resto, j, ind, en_mapa=False)
            lista.append(valor)
        return lista, i

    # -- valores ---------------------------------------------------------------
    def _valor(self, resto: str, i: int, ind: int, *, en_mapa: bool) -> tuple[Any, int]:
        """El valor que empieza en `resto` (línea `i`, padre con sangría `ind`) y la
        siguiente línea por leer."""
        resto = resto.strip()
        ancla = None
        if (m := _ANCLA.match(resto)):
            ancla, resto = m.group(1), m.group(2).strip()
        if resto.startswith("!"):
            raise YamlNoSoportado(f"línea {i + 1}: etiquetas YAML (`{resto.split()[0]}`) no soportadas")
        if resto.startswith("*"):
            valor, sig = self._alias(resto, i), i + 1
        elif _ENCABEZADO_BLOQUE.match(resto):
            valor, sig = self._escalar_en_bloque(resto, i, ind)
        elif not resto:
            j = self._sig(i + 1)
            if j is not None and self._sangria(j) > ind:
                valor, sig = self._bloque(j, self._sangria(j))
            elif j is not None and en_mapa and self._sangria(j) == ind and _ES_ITEM.match(self._cuerpo(j)):
                valor, sig = self._secuencia(j, ind)  # `clave:` y la lista a su misma altura
            else:
                valor, sig = None, i + 1
        elif resto[0] in "[{":
            texto, sig = self._en_linea_completa(resto, i)
            valor = self._en_linea(texto, i)
        else:
            valor, sig = self._escalar(resto, i, ind)
        if ancla:
            self.anclas[ancla] = valor
        return valor, sig

    def _alias(self, texto: str, i: int) -> Any:
        nombre = texto[1:].strip()
        if nombre not in self.anclas:
            raise YamlNoSoportado(f"línea {i + 1}: alias `*{nombre}` sin ancla definida antes")
        return copy.deepcopy(self.anclas[nombre])

    def _escalar(self, texto: str, i: int, ind: int) -> tuple[Any, int]:
        sig = i + 1
        if texto[0] in "\"'" and (len(texto) < 2 or not texto.endswith(texto[0])):
            # Entre comillas y partido en varias líneas: hasta la comilla de cierre.
            while sig < len(self.lineas) and not texto.endswith(texto[0]):
                texto += " " + self.lineas[sig].strip()
                sig += 1
            return _desescalar(texto), sig
        # Un escalar plano sigue en las líneas MÁS sangradas que su padre.
        while (j := self._sig(sig)) is not None and j == sig and self._sangria(j) > ind:
            texto += " " + self._cuerpo(j)
            sig = j + 1
        return _desescalar(texto), sig

    def _escalar_en_bloque(self, cabecera: str, i: int, ind: int) -> tuple[str, int]:
        m = _ENCABEZADO_BLOQUE.match(cabecera)
        assert m
        estilo, mordida, explicita = m.group(1), m.group(2) or m.group(4), m.group(3)
        j = i + 1
        sangria = ind + int(explicita) if explicita else None
        cuerpo: list[str] = []
        while j < len(self.lineas):
            linea = self.lineas[j]
            if not linea.strip():
                cuerpo.append("")
                j += 1
                continue
            propia = len(linea) - len(linea.lstrip(" "))
            if sangria is None:
                if propia <= ind:
                    break
                sangria = propia
            if propia < sangria:
                break
            cuerpo.append(linea[sangria:])
            j += 1
        finales = 0  # líneas en blanco al final: sólo las conserva la mordida `+`
        while cuerpo and not cuerpo[-1]:
            cuerpo.pop()
            finales += 1
        if estilo == "|":
            texto = "\n".join(cuerpo)
        else:
            parrafos, actual = [], []
            for linea in cuerpo:
                if linea and not linea.startswith((" ", "\t")):
                    actual.append(linea)
                else:
                    if actual:
                        parrafos.append(" ".join(actual))
                        actual = []
                    parrafos.append(linea)
            if actual:
                parrafos.append(" ".join(actual))
            texto = "\n".join(parrafos)
        if not cuerpo or mordida == "-":
            return texto, j
        return texto + ("\n" * (1 + finales) if mordida == "+" else "\n"), j

    # -- colecciones en línea ----------------------------------------------------
    def _en_linea_completa(self, texto: str, i: int) -> tuple[str, int]:
        """Une las líneas de un `[...]`/`{...}` partido hasta que las llaves cuadren."""
        sig = i + 1
        while self._desbalance(texto) > 0:
            if sig >= len(self.lineas):
                raise YamlNoSoportado(f"línea {i + 1}: colección en línea sin cerrar")
            texto += " " + _sin_comentario(self.lineas[sig]).strip()
            sig += 1
        return texto, sig

    @staticmethod
    def _desbalance(texto: str) -> int:
        prof, comilla = 0, None
        for ch in texto:
            if comilla:
                if ch == comilla:
                    comilla = None
            elif ch in "\"'":
                comilla = ch
            elif ch in "[{":
                prof += 1
            elif ch in "]}":
                prof -= 1
        return prof

    def _en_linea(self, texto: str, i: int) -> Any:
        t = texto.strip()
        if t.startswith("*"):
            return self._alias(t, i)
        if t.startswith("!"):
            raise YamlNoSoportado(f"línea {i + 1}: etiquetas YAML no soportadas")
        if t.startswith("[") and t.endswith("]"):
            return [self._en_linea(p, i) for p in _partir_en_comas(t[1:-1])]
        if t.startswith("{") and t.endswith("}"):
            mapa: dict[str, Any] = {}
            for p in _partir_en_comas(t[1:-1]):
                partes = _partir_clave(p)
                if partes is None:
                    mapa[p.strip("\"'")] = None
                else:
                    mapa[partes[0]] = self._en_linea(partes[1], i)
            return mapa
        if t[:1] in "[{":
            raise YamlNoSoportado(f"línea {i + 1}: colección en línea mal formada: {t[:60]}")
        return _desescalar(t)


def carga_yaml(texto: str) -> dict[str, Any]:
    """Parser del subconjunto YAML que usan los docker-compose de la flota.

    Ver `_Lector` para lo que soporta y lo que rechaza. Hasta el 2026-10-25
    rechazaba anclas, escalares en bloque y mapas en línea, y leía MAL un mapa de
    varias claves dentro de una lista: tres compose sanos del disco
    (`coipo_cron_master`, `coipo_neo4j`, `coipo_seguimiento_madera`) quedaban «sin
    verificar» por su sintaxis, no por sus defectos.
    """
    return _Lector(texto).cargar()


def _flow(texto: str) -> list[Any]:
    """Secuencia en línea: `["CMD", "python", "-c", "..."]`. Se conserva por
    compatibilidad; el parser usa `_Lector._en_linea`."""
    t = texto.strip()
    if not (t.startswith("[") and t.endswith("]")):
        raise YamlNoSoportado(f"secuencia en línea mal formada: {texto[:60]}")
    return _Lector("")._en_linea(t, 0)


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
