"""Lo que declara `.semilla`: las claves `adopta:`, `fabrica:`, `maqueta:` y `ajeno:`.

Vive aparte de `comun.py` desde el 2026-10-25 (`COD-1`). `comun.py` lo reexporta.
Las cuatro se leen con `leer_clave()` desde el 2026-11-21: la misma sangría, el
mismo comentario y la misma lista en bloque para todas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from comun_yaml import _sin_comentario

# ── El alcance declarado: la clave `adopta:` de `.semilla` ───────────────────
#
# `.semilla` empezó siendo un interruptor: existe o no existe. Encendía `j12`
# (las piezas congeladas vienen de la semilla) y `j13` (esta interfaz sigue el
# estándar) a la vez, porque `j13` reutilizó el marcador de `j12`.
#
# Eso se rompió al intentar declararlo en un repositorio REAL. `coipo_prensa2`
# puede y debe cumplir el estándar de interfaz, pero NUNCA se sembró: ocho de sus
# archivos coinciden en ruta con `semilla.lock` sin venir de ahí —su propio
# `backend/Dockerfile`, su propio `frontend/nginx.conf`, su `requirements.txt`—.
# Poner el marcador para adoptar la interfaz le habría encendido OCHO `SEM-1`
# bloqueantes sobre archivos legítimamente suyos: exactamente el desastre que
# `j12` documenta en su cabecera haber causado ya una vez.
#
# `adopta:` separa las dos declaraciones. La clave lista qué estándares reclama
# el repositorio; cada juez exige el suyo:
#
#     version: 2026-09-07
#     gerencia: 1_banner_SECOM
#     adopta: interfaz          -> j13 juzga; j12 NO_APLICA
#
# LA CLAVE AUSENTE ADOPTA TODO, y esa dirección es deliberada. Es lo que hace que
# nada de lo que hoy funciona cambie —los `.semilla` que `sembrar.py` escribió
# antes de esto no la llevan— y es también el valor SEGURO: olvidarla no relaja
# ninguna regla, la olvida hacia la exigencia.
#
# LO QUE ESTA CLAVE ROZA, Y POR QUÉ SE PAGA. `comun.py` cierra a propósito la
# puerta de que un repositorio se declare `no_aplica` a sí mismo: «si pudiera,
# ésta sería la puerta por la que todo se pone verde». `adopta:` la entreabre —
# antes, escapar de `j12` costaba borrar un archivo que grita `# NO LO BORRES` y
# que además apagaba `j13`; ahora cuesta una palabra, y el repositorio sigue
# pareciendo declarado. Tres cosas lo compensan, y ninguna es opcional:
#
#   1. El `no_aplica` CITA la línea literal y su número, así que en el resumen se
#      lee quién se apagó y con qué texto. Un N/A autodeclarado que no se puede
#      leer es indistinguible de uno honesto.
#   2. Se cuenta como SUPRESIÓN: `::warning::` y fila en `DEUDA.md`, no en la
#      sección informativa que no cuesta nada.
#   3. `sembrar.py` escribe `adopta: semilla, interfaz` EXPLÍCITO, de modo que
#      quitarle `semilla` a un repositorio sembrado es un diff visible en una
#      línea que dice lo que hace, no una ausencia.
#
# LA SEMÁNTICA, UNA SOLA Y LA MISMA EN j12, j13, j14 y j16 (desde el 2026-10-25;
# hasta ese día j16 no leía la clave, j14 trataba la vacía como «todo» y j12/j13
# como SIN_EVALUAR, y la lista YAML en bloque se leía vacía):
#
#   sin `.semilla`           -> NO_APLICA en los cuatro: el alcance se declara.
#   `.semilla` sin `adopta:` -> adopta TODO (`semilla` e `interfaz`).
#   `adopta:` con una lista  -> exactamente esas capas, escrita de cualquiera de
#                               las tres formas:
#                                   adopta: semilla, interfaz        (en línea)
#                                   adopta: [semilla, interfaz]      (flujo YAML;
#                                   adopta: "semilla, interfaz"       o entre comillas)
#                                   adopta:                          (bloque YAML)
#                                     - semilla
#                                     - interfaz
#                               Lo que NO adopta la capa de un juez: j12 (`semilla`)
#                               y j13 (`interfaz`) salen NO_APLICA; j14 y j16, cuyas
#                               reglas bloquean lo sembrado desde su fecha, sólo
#                               AVISAN (`docs/ESTANDAR_CODIGO.md` de la fábrica, línea
#                               13: «AVISA … en lo que sólo adopta un estándar»). En
#                               los cuatro se cuenta como SUPRESIÓN cuando apaga algo
#                               que regiría.
#   `adopta:` vacía          -> `adopta:`, `adopta: []`, `adopta: ""`, `adopta: ,`:
#                               un error de declaración. Los cuatro lo anotan en
#                               `no_evaluado` con la línea y NO dictaminan
#                               (SIN_EVALUAR, que en perfil `aplicacion` y modo
#                               bloqueante detiene el gate). No es una supresión:
#                               no declara nada que suprimir.
#
# Una capa que no existe (`adopta: semila`) cuenta como escrita —no adopta
# `semilla`— y la cita lo dice, para que el typo se lea en el resumen.
#
# Una línea comentada NO declara nada: `^\s*adopta` no casa con `# adopta: x`,
# porque `#` no es espacio en blanco. Hay una prueba que lo fija.
_ITEM = re.compile(r"^(?P<sangria>[ \t]*)-(?:[ \t]+(?P<valor>.*))?$")

CAPAS_CONOCIDAS = frozenset({"semilla", "interfaz"})


# ── Un solo lector de claves (2026-11-21) ─────────────────────────────────────
#
# Hasta ese día cada clave tenía su expresión: `adopta:` y `fabrica:` aceptaban
# sangría y `maqueta:` y `ajeno:` no; sólo `adopta:` leía la lista YAML en bloque
# (`ajeno:` la leía vacía y medía igual las carpetas declaradas), y `maqueta:` se
# quedaba con las comillas. Ahora las cuatro se leen aquí, igual: la PRIMERA línea
# `<clave>:` no comentada (con o sin sangría), su valor sin comentario y, si está
# vacío, los ítems de la lista en bloque que la sigue.


@dataclass(frozen=True)
class Clave:
    """Una clave de `.semilla` tal como está escrita."""

    numero: int  # línea de la clave, desde 1
    linea: str  # la línea literal, con su sangría
    valor: str  # lo que va a la derecha de `:`, sin comentario y sin espacios
    items: tuple[str, ...] = ()  # los ítems de una lista en bloque, si `valor` está vacío
    hasta: int = 0  # la última línea de esa lista (= `numero` si no hay)


def leer_clave(texto: str | None, nombre: str) -> Clave | None:
    """La clave `nombre:` de un `.semilla`, o None si no está.

    Una línea comentada no declara nada: `^[ \\t]*clave` no casa con `# clave: x`,
    porque `#` no es espacio en blanco."""
    if not texto:
        return None
    m = re.search(rf"^(?P<sangria>[ \t]*){re.escape(nombre)}[ \t]*:[ \t]*(?P<resto>[^\r\n]*)",
                  texto, re.MULTILINE)
    if not m:
        return None
    numero = texto[: m.start()].count("\n") + 1
    valor = _sin_comentario(m.group("resto")).strip()
    if valor:
        return Clave(numero, m.group(0), valor, (), numero)
    # Sin nada a la derecha: puede abrir una lista YAML en bloque. Los ítems van a la
    # sangría de la clave o más adentro; se saltan líneas en blanco y comentarios, y la
    # lista termina en la primera línea que no es un ítem.
    sangria = len(m.group("sangria").expandtabs())
    items: list[str] = []
    hasta = numero
    for n, linea in enumerate(texto[m.end():].splitlines()[1:], start=numero + 1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        item = _ITEM.match(linea)
        if not item or len(item.group("sangria").expandtabs()) < sangria:
            break
        items.append(_sin_comentario(item.group("valor") or "").strip())
        hasta = n
    return Clave(numero, m.group(0), "", tuple(items), hasta)


def _sin_comillas(valor: str) -> str:
    v = valor.strip()
    return v[1:-1].strip() if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def _capas(crudo: str) -> list[str]:
    """`semilla, interfaz` | `[semilla, 'interfaz']` | `"semilla interfaz"` -> capas."""
    t = crudo.strip()
    if t.startswith("["):
        t = t[1:-1] if t.endswith("]") else t[1:]
    elif len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        t = t[1:-1]
    capas = (p.strip().strip("\"'").strip().lower() for p in re.split(r"[,\s]+", t))
    return [c for c in capas if c]


@dataclass(frozen=True)
class Adopcion:
    """Lo que un `.semilla` declara adoptar, con la línea que lo dice.

    `declarado is None` significa que la clave NO está, y entonces se adopta
    todo. No es lo mismo que `adopta:` vacío, que es una declaración de que no se
    adopta nada y por tanto un error del que hay que avisar.
    """

    declarado: frozenset[str] | None
    numero: int | None = None
    linea: str | None = None
    forma: str = ""
    hasta: int | None = None  # última línea de una lista en bloque

    @property
    def vacia(self) -> bool:
        """`adopta:` presente y sin ninguna capa: `adopta:`, `adopta: []`, `adopta: ,`.

        No es «adopta todo» ni «no adopta nada»: es un error de escritura, y un
        juez que lo leyera como N/A se apagaria en silencio con exit 0. Medido el
        2026-09-08. Se reporta como NO EVALUADO, con la linea, y no cuenta como
        supresion porque no declara nada que suprimir.
        """
        return self.declarado is not None and not self.declarado

    @property
    def desconocidas(self) -> frozenset[str]:
        return (self.declarado or frozenset()) - CAPAS_CONOCIDAS

    def adopta(self, capa: str) -> bool:
        return self.declarado is None or capa in self.declarado

    def cita(self, marcador: str = ".semilla") -> str:
        """`.semilla:7` declara «adopta: interfaz» — para la razón del N/A.

        Dice la forma y, si la hay, la capa que no existe: un mensaje que llama
        «vacía» a una lista que no lo está manda a buscar el error donde no está."""
        if self.declarado is None:
            return f"`{marcador}` sin clave `adopta:`"
        if self.hasta and self.hasta != self.numero:
            # La lista en bloque ocupa varias líneas: se cita normalizada y con el rango.
            capas = ", ".join(sorted(self.declarado))
            texto = (f"`{marcador}:{self.numero}-{self.hasta}` declara «adopta: [{capas}]» "
                     f"({self.forma})")
        else:
            # En una línea se cita LITERAL: se lee quién se apagó y con qué texto.
            texto = f"`{marcador}:{self.numero}` declara «{(self.linea or '').strip()}»"
        if self.desconocidas:
            texto += (f" — capa desconocida: {', '.join(f'`{c}`' for c in sorted(self.desconocidas))}"
                      f"; las que existen son {', '.join(f'`{c}`' for c in sorted(CAPAS_CONOCIDAS))}")
        return texto

    def motivo_vacia(self, marcador: str = ".semilla") -> str:
        """El `no_evaluado` de una `adopta:` vacía: el mismo texto en los cuatro jueces."""
        return (f"`{marcador}:{self.numero}` declara «{(self.linea or '').strip()}» y la lista "
                "está VACÍA: no declara ninguna capa. Este juez no dictamina con una "
                "declaración rota. O se quita la clave (= adopta todo) o se listan las "
                "capas: `adopta: semilla, interfaz`.")


def leer_adopcion(texto: str | None) -> Adopcion:
    """Lee la clave `adopta:` de un `.semilla`, en cualquiera de sus tres formas.

    Ausente = adopta todo. Ver la semántica completa arriba."""
    clave = leer_clave(texto, "adopta")
    if clave is None:
        return Adopcion(None)
    crudo = clave.valor
    if crudo:
        forma = ("lista en línea YAML" if crudo.startswith("[")
                 else "entre comillas" if crudo[0] in "\"'" else "en línea")
        return Adopcion(frozenset(_capas(crudo)), clave.numero, clave.linea, forma)
    capas = [c for item in clave.items for c in _capas(item)]
    forma = "lista en bloque YAML" if clave.hasta != clave.numero else "sin capas"
    return Adopcion(frozenset(capas), clave.numero, clave.linea, forma, clave.hasta)


# ── La fecha de siembra: la clave `fabrica:` de `.semilla` ───────────────────
#
# `sembrar.py` (vía `semilla/siembra/aplicacion.py` de la fábrica) la escribe con
# la fecha REAL del día en que se sembró. La leen los jueces que miran hacia
# adelante (`FILOSOFIA.md` de la fábrica, §3 y §4): una regla nueva bloquea sólo
# lo sembrado desde su vigencia y avisa en lo anterior. `j16` la leía con su
# propia expresión; `j14` es el segundo lector y por eso vive aquí, una sola vez.
# Como `adopta:`, una línea comentada no declara nada.
_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")


def leer_fabrica(texto: str | None) -> str | None:
    """`AAAA-MM-DD` de la clave `fabrica:` de un `.semilla`, o None si no la lleva."""
    clave = leer_clave(texto, "fabrica")
    m = _FECHA.match(_sin_comillas(clave.valor)) if clave else None
    return m.group(0) if m else None


# ── La maqueta validada: la clave `maqueta:` de `.semilla` ────────────────────
#
# Una aplicación sembrada con `sembrar.py --maqueta` (coipo_master_produccion, desde el
# 2026-11-12) lleva `maqueta: <origen>@<commit>` y `adopta: semilla` SIN `interfaz`: su
# cara es la de una maqueta que validó el cliente, no la de la flota
# (identidad/ESTANDAR_UI.md §1-bis, enmienda del 2026-11-12, decisión de Luis Monsalve).
# No adoptar `interfaz` ahí NO es una supresión: el aspecto tiene otra fuente, con
# nombre y commit. j13 lo lee para no contarla; j16 para no medir la referencia; j12
# para comprobar que la cara copiada no se editó (MAQ-1).


# ── Código ajeno: la clave `ajeno:` de `.semilla` ──────────────────────────────
#
# Carpetas versionadas que NO son código de la aplicación y que nadie va a partir ni a
# pasar a TypeScript: una librería copiada, un visor de terceros, datos congelados con
# forma de código. `ajeno: vendor/visor/, frontend/public/libs/`. j16 no las mide, y
# CADA una se cuenta como supresión y sale publicada (AGENTS.md §5): declarar ajeno
# apaga una medición, y esa puerta se paga. La maqueta validada NO va por aquí: tiene
# su propia clave y no es supresión (2026-11-12).


def leer_ajeno(texto: str | None) -> list[str]:
    """Prefijos de ruta declarados ajenos, con barra final. Vacío si no hay clave.

    En línea (`ajeno: a/, b/`), en flujo (`[a/, b/]`) o en bloque (`- a/`)."""
    clave = leer_clave(texto, "ajeno")
    if clave is None:
        return []
    crudo = " ".join((clave.valor, *clave.items))
    rutas = (p.strip().strip("\"'[]").strip() for p in re.split(r"[,\s]+", crudo))
    return [r if r.endswith("/") else r + "/" for r in rutas if r and r not in {"/", "./"}]


def leer_maqueta(texto: str | None) -> tuple[int, str] | None:
    """(línea, `origen@commit`) de la clave `maqueta:`, o None si no la lleva."""
    clave = leer_clave(texto, "maqueta")
    valor = _sin_comillas(clave.valor).split() if clave else []
    return (clave.numero, valor[0]) if clave and valor else None


