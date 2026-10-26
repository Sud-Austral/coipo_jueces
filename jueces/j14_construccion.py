#!/usr/bin/env python3
"""j14 — la aplicación se construyó con la fábrica, y lo demuestra.

EL PROBLEMA QUE RESUELVE
========================
La regla 8 de `AGENTS.md` de la fábrica dice que n8n, Neo4j y el MCP de
metodologías (IGNUS) son con lo que la flota CONSTRUYE código, y nunca piezas
del producto. Tenía la mitad prohibitiva vigilada y la otra mitad en el aire, y
las dos generaciones de octubre de 2026 cayeron cada una por un lado:

  2026-10-19  tres proyectos «usando n8n, mcp y neo4j» salieron con n8n y Neo4j
              DENTRO del producto —variables, clientes, un cron nocturno— y sin
              lógica de negocio que los usara.
  2026-10-20  tres monitores salieron SIN usar ninguna herramienta, sin sembrar
              y sin consultar metodología alguna: `APP_PUERTO` en vez de
              `APP_PORT`, sin las seis variables base, sin healthcheck ni
              `mem_limit` en ningún servicio, `.gitignore` sin anclar... trece
              hallazgos de estos jueces por monitor, todos evitables con la
              semilla. La sesión lo dijo con claridad: «Escribí todos los
              archivos a mano». Nada la obligaba a otra cosa.

Una regla sin paso ni prueba no se cumple. Este juez lee la prueba.

LO QUE LEE: `docs/CONSTRUCCION.md`
==================================
La fábrica, desde el 2026-10-20, exige un paso ANTES de escribir código
(`prompts/05-consultar-la-fabrica.md`, skill `construir-con-la-fabrica` de la
semilla) que deja ese archivo con:

  metodologia:  el `sombrero_id` de IGNUS que se siguió (smb-metodologia-…)
  instancia:    la instancia de IGNUS consultada
  objetivos:    cuáles de sus objetivos se aplicaron y cómo
  consultas:    el rastro de las llamadas, con sus `correlation_id`
  registrado:   el objetivo creado en IGNUS con lo aprendido, o «no aplica: …»

Sin `correlation_id` no hay rastro de que IGNUS se haya consultado: un archivo
escrito de memoria se parece a uno escrito tras consultar, y la diferencia es
exactamente lo que este juez mira.

SEVERIDAD POR EVIDENCIA, NO POR FECHA DE CALENDARIO
===================================================
Ninguna aplicación anterior al 2026-10-20 tiene este archivo, y poner rojas 24
aplicaciones de golpe es la clase de cambio que `docs/VERSIONADO.md` reserva a
una mayor. Por eso:

  - el `.semilla` que escribe `sembrar.py` desde ese día lleva `fabrica: AAAA-MM-DD`;
    con esa clave en o después del 2026-10-20, la ausencia del archivo BLOQUEA;
  - sin esa clave —todo lo sembrado antes, y lo no sembrado— la ausencia AVISA;
  - un archivo que existe pero está a medias (marcadores `[PENDIENTE]`, sin
    metodología, sin `correlation_id`) BLOQUEA siempre: quien empezó el paso lo
    termina, sea cual sea la antigüedad del repositorio.

NO ES UN HALLAZGO
=================
Que el archivo cite una metodología que este juez no puede verificar en IGNUS:
el CI no tiene la clave del servidor, y no debe tenerla. La comprobación en
vivo la hace `flota/herramientas_de_fabrica.py --construccion` de la fábrica,
que sí corre con credenciales, en la sesión que construye.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar  # noqa: E402

PERFILES = ("aplicacion",)

REGLA = "FAB-8"
ARCHIVO = "docs/CONSTRUCCION.md"
# Desde este dia la semilla escribe `fabrica:` en `.semilla` y la fabrica exige
# el archivo. Antes, se avisa.
EXIGIDO_DESDE = "2026-10-20"

FECHA_FABRICA = re.compile(r"^\s*fabrica:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
MARCADOR_PENDIENTE = re.compile(r"\[(?:PENDIENTE|VERIFICAR)\]")
ID_METODOLOGIA = re.compile(r"\bsmb-metodologia-[a-z0-9-]+\b")
CORRELACION = re.compile(r"\bcorr-(?:maestro-)?\d{10,}-[0-9a-f]{6,}\b")
CAMPO = {
    "metodologia": re.compile(r"^\s*metodolog[ií]a:", re.IGNORECASE | re.MULTILINE),
    "instancia": re.compile(r"^\s*instancia:", re.IGNORECASE | re.MULTILINE),
    "objetivos": re.compile(r"^\s*objetivos:", re.IGNORECASE | re.MULTILINE),
    "consultas": re.compile(r"^\s*consultas:", re.IGNORECASE | re.MULTILINE),
    "registrado": re.compile(r"^\s*registrado:", re.IGNORECASE | re.MULTILINE),
}
ARREGLO = ("ejecutar el paso 05 de la fábrica (`prompts/05-consultar-la-fabrica.md`, "
           "skill `construir-con-la-fabrica`) y dejar `docs/CONSTRUCCION.md` con la "
           "metodología de IGNUS seguida, sus objetivos, los `correlation_id` de las "
           "llamadas y lo registrado al cerrar")


def _exigido(repo: Repo) -> tuple[bool, str]:
    """(exige, por qué): el `.semilla` con `fabrica:` desde EXIGIDO_DESDE exige."""
    semilla = repo.texto(".semilla")
    if not semilla:
        return False, "sin `.semilla`"
    m = FECHA_FABRICA.search(semilla)
    if not m:
        return False, "`.semilla` sin clave `fabrica:` (sembrado antes del 2026-10-20)"
    fecha = m.group(1)
    if fecha >= EXIGIDO_DESDE:
        return True, f"`.semilla` declara `fabrica: {fecha}`"
    return False, f"`.semilla` declara `fabrica: {fecha}`, anterior al {EXIGIDO_DESDE}"


def comprobar(repo: Repo, r: Resultado) -> None:
    exige, razon = _exigido(repo)

    if not repo.existe(ARCHIVO):
        anota = r.bloquea if exige else r.avisa
        anota(
            REGLA, ARCHIVO, "no hay `docs/CONSTRUCCION.md`",
            "no hay rastro de que la aplicación se haya construido con la fábrica: "
            "ni qué metodología de IGNUS se siguió, ni qué se consultó en el grafo, "
            "ni qué se registró al terminar. Las dos generaciones de octubre de 2026 "
            "fallaron por eso: una metió las herramientas en el producto y la otra no "
            "usó ninguna, y nada lo detectó hasta la auditoría"
            + (f". Este repositorio lo exige: {razon}" if exige
               else f". Aquí solo avisa: {razon}"),
            arreglo=ARREGLO,
        )
        return

    texto = repo.texto(ARCHIVO) or ""
    r.comprobo("`docs/CONSTRUCCION.md`: metodología, objetivos, rastro de llamadas y registro")

    pendientes = MARCADOR_PENDIENTE.findall(texto)
    if pendientes:
        r.bloquea(
            REGLA, ARCHIVO, f"quedan {len(pendientes)} marcador(es) `[PENDIENTE]`/`[VERIFICAR]`",
            "el archivo es la plantilla de la semilla a medio rellenar: declara un paso "
            "que no se dio. Un paso empezado se termina, sea cual sea la antigüedad "
            "del repositorio",
            arreglo="rellenar cada marcador con lo que se hizo, o escribir «no aplica: "
                    "<motivo>» donde de verdad no aplique",
        )

    faltan = [c for c, patron in CAMPO.items() if c != "registrado" and not patron.search(texto)]
    if faltan:
        r.bloquea(
            REGLA, ARCHIVO, f"faltan los campos {', '.join(f'`{c}:`' for c in faltan)}",
            "sin esos campos no se puede saber qué metodología se siguió ni con qué "
            "evidencia; el archivo no cumple la forma que la plantilla de la semilla fija",
            arreglo=ARREGLO,
        )

    if not ID_METODOLOGIA.search(texto):
        r.bloquea(
            REGLA, ARCHIVO, "no cita ninguna metodología de IGNUS (`smb-metodologia-…`)",
            "consultar IGNUS es el primer paso del 05: una construcción que no nombra la "
            "metodología que siguió no la siguió. La de la fábrica es «Construir una "
            "aplicación COIPO con la fábrica»; las de AIBO enseñan a meter n8n en el "
            "producto y no sirven aquí",
            arreglo="`listar_metodologias` en la instancia de la flota, elegir la de la "
                    "fábrica y anotar su `sombrero_id` en `metodologia:`",
        )

    if not CORRELACION.search(texto):
        r.bloquea(
            REGLA, ARCHIVO, "no hay ningún `correlation_id`: no hay rastro de haber consultado IGNUS",
            "cada respuesta de IGNUS trae un `correlation_id` (`corr-…`). Un archivo "
            "escrito de memoria se parece a uno escrito tras consultar; el "
            "`correlation_id` es la única diferencia observable, y es la que la "
            "generación del 2026-10-20 no pudo mostrar",
            arreglo="copiar en `consultas:` el `correlation_id` de cada llamada a IGNUS, "
                    "con la herramienta y la fecha",
        )

    if not CAMPO["registrado"].search(texto):
        r.avisa(
            REGLA, ARCHIVO, "no dice qué se registró al cerrar (`registrado:`)",
            "lo aprendido construyendo vuelve a IGNUS con `crear_objetivo` y a "
            "COIPO_ERRORES con `/bitacora`; sin la línea, la próxima sesión arranca de "
            "cero otra vez",
            arreglo="añadir `registrado:` con el `objetivo_id` creado, o «no aplica: "
                    "<motivo>»",
        )


if __name__ == "__main__":
    ejecutar("j14", "la aplicación se construyó con la fábrica y lo demuestra en "
                    "`docs/CONSTRUCCION.md` (AGENTS.md de la fábrica, sección 3, punto 8)",
             comprobar)
