"""Lo que declara `.semilla`: las claves `adopta:` y `fabrica:`.

Vive aparte de `comun.py` desde el 2026-10-25 (`COD-1`). `comun.py` lo reexporta.
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
_ADOPTA = re.compile(r"^(?P<sangria>[ \t]*)adopta[ \t]*:[ \t]*(?P<lista>[^\r\n]*)", re.MULTILINE)
_ITEM = re.compile(r"^(?P<sangria>[ \t]*)-(?:[ \t]+(?P<valor>.*))?$")

CAPAS_CONOCIDAS = frozenset({"semilla", "interfaz"})


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
    if not texto:
        return Adopcion(None)
    m = _ADOPTA.search(texto)
    if not m:
        return Adopcion(None)
    numero = texto[: m.start()].count("\n") + 1
    crudo = _sin_comentario(m.group("lista")).strip()
    if crudo:
        forma = ("lista en línea YAML" if crudo.startswith("[")
                 else "entre comillas" if crudo[0] in "\"'" else "en línea")
        return Adopcion(frozenset(_capas(crudo)), numero, m.group(0), forma)

    # Sin nada a la derecha: puede abrir una lista YAML en bloque. Los ítems van a
    # la sangría de la clave o más adentro; se saltan líneas en blanco y
    # comentarios, y la lista termina en la primera línea que no es un ítem.
    sangria = len(m.group("sangria").expandtabs())
    capas: list[str] = []
    hasta = numero
    for n, linea in enumerate(texto[m.end():].splitlines()[1:], start=numero + 1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        item = _ITEM.match(linea)
        if not item or len(item.group("sangria").expandtabs()) < sangria:
            break
        capas += _capas(_sin_comentario(item.group("valor") or ""))
        hasta = n
    forma = "lista en bloque YAML" if hasta != numero else "sin capas"
    return Adopcion(frozenset(capas), numero, m.group(0), forma, hasta)


# ── La fecha de siembra: la clave `fabrica:` de `.semilla` ───────────────────
#
# `sembrar.py` (vía `semilla/siembra/aplicacion.py` de la fábrica) la escribe con
# la fecha REAL del día en que se sembró. La leen los jueces que miran hacia
# adelante (`FILOSOFIA.md` de la fábrica, §3 y §4): una regla nueva bloquea sólo
# lo sembrado desde su vigencia y avisa en lo anterior. `j16` la leía con su
# propia expresión; `j14` es el segundo lector y por eso vive aquí, una sola vez.
# Como `adopta:`, una línea comentada no declara nada.
_FABRICA = re.compile(r"^[ \t]*fabrica[ \t]*:[ \t]*(\d{4}-\d{2}-\d{2})", re.MULTILINE)


def leer_fabrica(texto: str | None) -> str | None:
    """`AAAA-MM-DD` de la clave `fabrica:` de un `.semilla`, o None si no la lleva."""
    if not texto:
        return None
    m = _FABRICA.search(texto)
    return m.group(1) if m else None


