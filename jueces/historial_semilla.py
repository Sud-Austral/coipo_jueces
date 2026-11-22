"""`semilla.lock.historial`: lo que la semilla publicó antes del lock vigente, y desde cuándo
rige cada pieza. Lo lee `j12_semilla.py`, que explica en su docstring para qué sirve.

Se separó de `j12_semilla.py` el 2026-11-22, cuando el juez llegó a 794 líneas y la vigencia
por pieza no cabía sin pasar de 800 (COD-1, `docs/ESTANDAR_CODIGO.md` de la fábrica).

EL CONTRATO CON LA FÁBRICA
==========================
Lo escribe `semilla/sellar.py --escribir` de coipo_master_produccion con estas mismas
expresiones (se repiten allí: la dependencia va al revés, por el lock). Espacios y
tabuladores, no `\\s`: `\\s` cruzaría un salto de línea. `CABECERA_DE_BLOQUE` reconoce la
intención y `VIGENTE_HASTA` la forma completa: una cabecera de bloque con la fecha mal escrita
hace ilegible el archivo, no se lee como un comentario más.

Los bloques van en orden cronológico, el más antiguo primero, y dos resellados del mismo día
dan dos bloques con la misma fecha: por eso la primera aparición de una pieza se cuenta por
POSICIÓN de bloque, no por fecha.

DESDE CUÁNDO RIGE UNA PIEZA (2026-11-22)
========================================
Rige desde el día siguiente al último bloque que todavía NO la nombraba: ése es el día en que
el lock que la trajo pasó a ser el vigente. Una pieza nueva en el lock vigente (ningún bloque
la nombra) rige desde el día siguiente al último bloque, como desde el 2026-11-21.

Hasta el 2026-11-22 sólo se calculaba para las piezas que ningún bloque nombraba, y eso tenía
un defecto que se vio antes de publicar: al resellar, el lock anterior entra al historial y sus
piezas recién selladas dejaban de contar como nuevas. `consumidores.py --lock-candidato` midió
cinco piezas en cinco aplicaciones que pasaban de AVISA a BLOQUEA sin que nadie tocara nada.

La vigencia por pieza vale para las que la semilla selló desde que existe la regla (su primera
vigencia fue el 2026-11-22, `GRACIA_DESDE`). Una pieza sellada antes conserva el juicio de
siempre: también lo que relaja mira hacia adelante (`FILOSOFIA.md` §4 de la fábrica).
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

# `<sha256>  <ruta>`, como la salida de `sha256sum`: la línea del lock y la del historial.
ENTRADA = re.compile(r"^(?P<huella>[0-9a-f]{64})\s+(?P<ruta>\S.*)$")

FORMATO_HISTORIAL = "1"
FORMATO = re.compile(r"^#[ \t]*formato:[ \t]*(\S+)[ \t]*$")
CABECERA_DE_BLOQUE = re.compile(r"^#[ \t]*vigente_hasta:")
VIGENTE_HASTA = re.compile(r"^#[ \t]*vigente_hasta:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$")

GRACIA_DESDE = datetime.date(2026, 11, 22)
UN_DIA = datetime.timedelta(days=1)


@dataclass(frozen=True)
class Historial:
    """Las huellas publicadas y el orden de los bloques.

    `huellas`: ruta -> {huella -> hasta cuándo fue la vigente}; una huella que aparece en
    varios bloques se queda con la fecha MÁS RECIENTE. `fechas`: el `vigente_hasta` de cada
    bloque, en el orden del archivo. `primera`: ruta -> posición del primer bloque que la nombra.
    """

    huellas: dict[str, dict[str, datetime.date]] = field(default_factory=dict)
    fechas: tuple[datetime.date, ...] = ()
    primera: dict[str, int] = field(default_factory=dict)

    def vigencia(self, ruta: str) -> datetime.date | None:
        """Desde cuándo rige `ruta` con gracia para lo sembrado antes, o None si no la tiene.

        None: sin historial no se sabe qué es nuevo; una pieza que ya estaba en el bloque más
        antiguo se selló antes de que hubiera historial; y una sellada antes de `GRACIA_DESDE`
        se juzga como siempre. En los tres casos, una diferencia es una edición.
        """
        if not self.fechas:
            return None
        posicion = self.primera.get(ruta)
        if posicion is None:
            return max(self.fechas) + UN_DIA
        anteriores = self.fechas[:posicion]
        if not anteriores:
            return None
        desde = max(anteriores) + UN_DIA
        return desde if desde >= GRACIA_DESDE else None


class Lector:
    """Las líneas de `semilla.lock.historial`, una a una. Levanta `ValueError` con el motivo
    en cuanto algo no cuadra: un archivo roto no puede leerse como «no hay historial»."""

    def __init__(self) -> None:
        self.formato: str | None = None
        self.hasta: datetime.date | None = None
        self.en_el_bloque = 0
        self.huellas: dict[str, dict[str, datetime.date]] = {}
        self.fechas: list[datetime.date] = []
        self.primera: dict[str, int] = {}

    def leer(self, n: int, linea: str) -> None:
        if m := FORMATO.match(linea):
            self.formato = m.group(1)
        elif CABECERA_DE_BLOQUE.match(linea):
            self._bloque(n, linea)
        elif m := ENTRADA.match(linea):
            self._entrada(n, m)

    def _bloque(self, n: int, linea: str) -> None:
        m = VIGENTE_HASTA.match(linea)
        if not m:
            raise ValueError(f"línea {n}: `vigente_hasta:` sin una fecha AAAA-MM-DD")
        self._cerrar_bloque()
        try:
            self.hasta = datetime.date.fromisoformat(m.group(1))
        except ValueError as e:
            raise ValueError(f"línea {n}: `{m.group(1)}` no es una fecha") from e
        self.fechas.append(self.hasta)
        self.en_el_bloque = 0

    def _cerrar_bloque(self) -> None:
        if self.hasta is not None and self.en_el_bloque == 0:
            raise ValueError(f"el bloque `vigente_hasta: {self.hasta}` no tiene entradas")

    def _entrada(self, n: int, m: re.Match[str]) -> None:
        if self.hasta is None:
            raise ValueError(f"línea {n}: una entrada antes de cualquier `# vigente_hasta:`")
        self.en_el_bloque += 1
        ruta = m.group("ruta")
        self.primera.setdefault(ruta, len(self.fechas) - 1)
        por_huella = self.huellas.setdefault(ruta, {})
        previa = por_huella.get(m.group("huella"))
        por_huella[m.group("huella")] = self.hasta if previa is None else max(previa, self.hasta)

    def fin(self) -> Historial:
        if self.formato is None:
            raise ValueError("falta la línea `# formato: 1`: no es un historial")
        if self.formato != FORMATO_HISTORIAL:
            raise ValueError(
                f"`formato: {self.formato}` no es uno que este juez sepa leer "
                f"(lee el {FORMATO_HISTORIAL})"
            )
        self._cerrar_bloque()
        return Historial(self.huellas, tuple(self.fechas), self.primera)


def leer(ruta: Path) -> Historial | None:
    """El historial de `ruta`, o None SÓLO si el archivo no existe. Si existe y no se puede
    usar, LEVANTA `ValueError` con el motivo."""
    if not ruta.exists():
        return None
    try:
        texto = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"no se pudo leer el archivo ({type(e).__name__})") from e
    lector = Lector()
    for n, crudo in enumerate(texto.splitlines(), start=1):
        lector.leer(n, crudo.strip())
    return lector.fin()
