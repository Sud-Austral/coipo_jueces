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
# Una línea comentada NO declara nada: `^\s*adopta` no casa con `# adopta: x`,
# porque `#` no es espacio en blanco. Hay una prueba que lo fija.
_ADOPTA = re.compile(r"^[ \t]*adopta[ \t]*:[ \t]*(?P<lista>[^\r\n]*)", re.MULTILINE)


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

    @property
    def vacia(self) -> bool:
        """`adopta:` presente y sin ninguna capa: `adopta:` o `adopta: ,`.

        No es «adopta todo» ni «no adopta nada»: es un error de escritura, y un
        juez que lo leyera como N/A se apagaria en silencio con exit 0. Medido el
        2026-09-08. Se reporta como NO EVALUADO, con la linea, y no cuenta como
        supresion porque no declara nada que suprimir.
        """
        return self.declarado is not None and not self.declarado

    def adopta(self, capa: str) -> bool:
        return self.declarado is None or capa in self.declarado

    def cita(self, marcador: str = ".semilla") -> str:
        """`.semilla:7 declara «adopta: interfaz»` — para la razón del N/A."""
        if self.declarado is None:
            return f"`{marcador}` sin clave `adopta:`"
        return f"`{marcador}:{self.numero}` declara «{(self.linea or '').strip()}»"


def leer_adopcion(texto: str | None) -> Adopcion:
    """Lee la clave `adopta:` de un `.semilla`. Ausente = adopta todo."""
    if not texto:
        return Adopcion(None)
    m = _ADOPTA.search(texto)
    if not m:
        return Adopcion(None)
    crudo = _sin_comentario(m.group("lista"))
    capas = frozenset(
        parte.strip().lower()
        for parte in crudo.replace(",", " ").split()
        if parte.strip()
    )
    numero = texto[: m.start()].count("\n") + 1
    return Adopcion(capas, numero, m.group(0))


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


