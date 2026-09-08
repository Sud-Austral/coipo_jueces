#!/usr/bin/env python3
"""j13 — la interfaz: foco, tema oscuro y movimiento reducido.

Implementa tres reglas del estándar de interfaz de la flota.

  LAS TRES BLOQUEAN desde el **2026-09-07**, día en que se firmó
  `identidad/ESTANDAR_UI.md` de `coipo_master_produccion` (Luis Monsalve,
  Profesional UIA). Hasta entonces avisaban, y no por prudencia: un documento
  generado por IA y sin firmar no es una fuente escrita en el sentido que esa
  palabra tiene en `REGLAS.md`, así que los códigos `UI-N` vivían en la tabla
  «Reglas sin fuente escrita» y `tests/test_reglas_citadas.py::PruebaSeveridad`
  fallaba si una regla de esa tabla llamaba a `bloquea()`.

  **La prueba es lo que hizo cumplir la firma**, y sigue vigente en la otra
  dirección: para revocar esto se devuelven las filas a esa tabla y se cambian
  estas llamadas a `r.avisa(`; `PruebaSeveridad` vuelve a impedir el paso sola.

  Esta cabecera decía lo contrario —«TODAS AVISAN … está en cuarentena y sin
  firmar»— hasta el 2026-09-08, mientras el código de más abajo ya llamaba a
  `bloquea()`. El commit de la firma cambió las llamadas y no tocó el docstring.
  Quien abriera este archivo para entender por qué su build se puso rojo leía que
  este juez no podía bloquear.

LAS TRES, Y POR QUÉ ESTAS Y NO OTRAS
  Son las únicas del estándar que se pueden comprobar leyendo archivos sin
  levantar un navegador. Las demás —contraste de un chip sobre su fondo, los ocho
  estados, que un estado no se codifique sólo por color— exigen pintar, y un
  juez que las adivinara desde el CSS produciría falsos positivos. El resto del
  estándar se verifica con `verify-banner.mjs` y con revisión humana.

  UI-10  Un `outline:0` sin sustituto deja el teclado sin saber dónde está.
  UI-3   Un token de color que no se redefine en el tema oscuro no desaparece:
         se queda con el valor claro. Medido en `coipo_prensa2`, el peor caso da
         1,38:1 sobre la tarjeta oscura — texto presente e ilegible, que es peor
         que ausente porque nada lo delata.
  UI-15  Un bloque de `prefers-reduced-motion` que apaga una transición y deja
         ocho vivas cumple la letra y no la función. Es el caso real medido.

CALIBRACIÓN INVERSA (medida el 2026-09-07, con el alcance ya declarado)
  coipo_atraso_personal -> OK. Es el ÚNICO repositorio del disco con `.semilla`,
                    o sea el único proyecto sembrado, y sale limpio.
  coipo_prensa2         -> NO_APLICA. No declara. Y ojo: SÍ tiene los defectos
                    —`--verde` y `--verde-oscuro` sin redefinir en oscuro, con
                    el anillo de foco a 2,99:1, y un bloque de movimiento
                    reducido que apaga una de nueve transiciones—. No se juzgan
                    aquí a propósito: son anteriores al estándar, y su sitio es
                    la ficha de alineación del repositorio, no su CI diario.
  COIPO_USUARIOS        -> NO_APLICA. Ídem.
  COIPO_ENTREGA_PLANTA  -> NO_APLICA. Ídem.
  coipo_n8n             -> NO_APLICA. Encuadre operativo, software de terceros.
  coipo_jueces          -> NO_APLICA. No tiene frontend.

  Antes de declarar el alcance, este juez daba HALLAZGOS sobre prensa2 y
  USUARIOS. Eran ciertos, pero encender 32 frontends heredados con cada regla
  nueva del estándar enseña una sola cosa: a ignorar la salida del gate.

  Si un día este juez BLOQUEA a un repositorio sin `.semilla`, el error está en
  el juez: no debería ni haberlo mirado.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (Repo, Resultado, ejecutar, leer_adopcion,  # noqa: E402
                   suprimido)

PERFILES = ("aplicacion",)

# Un `encuadre_operativo` es software de terceros: su interfaz no es nuestra.

# EL ALCANCE SE DECLARA, NO SE INFIERE. Sin este archivo en la raíz, NO_APLICA.
#
# El mismo marcador que usa `j12`, y por la misma lección: su primera versión no
# lo exigía y puso rojos a cuatro repositorios por tener su propio `Dockerfile`.
# «Hay cosas que hay que declarar.»
#
# Y la dirección importa. Una bandera que dijera «soy legado, exígeme menos» es
# una bandera que cualquiera con prisa pone, y sería el repositorio
# declarándose a sí mismo N/A — la puerta que `comun.py` cierra a propósito:
# «si pudiera, ésta sería la puerta por la que todo se pone verde». Ésta dice lo
# contrario: reclama MÁS obligación, así que nadie la pone para escapar.
#
# Sale gratis, además: `sembrar.py` ya lo escribe en todo proyecto nuevo, así
# que el corte entre lo nuevo y lo heredado no cuesta editar ni un archivo.
MARCADOR = ".semilla"

# La capa que este juez exige que `.semilla` declare adoptar. Un repositorio que
# NO se sembro puede adoptar solo esta -- `adopta: interfaz` -- y entonces j12
# se declara N/A sin que sus piezas propias salgan rojas. Ver comun.py.
CAPA = "interfaz"

ES_CSS = re.compile(r"\.css$", re.IGNORECASE)
ES_PRUEBA = re.compile(
    r"(^|/)(tests?|__tests__|spec|fixtures|node_modules|dist|build)(/|$)")

# `outline:0`, `outline:none`, `outline: 0px`. No casa `outline-offset`.
SIN_CONTORNO = re.compile(r"\boutline\s*:\s*(?:0(?:px)?|none)\s*(?:!important)?\s*[;}]")
HAY_FOCO_VISIBLE = re.compile(r":focus-visible")

# Una declaración de custom property cuyo valor parece un color.
TOKEN_COLOR = re.compile(
    r"(--[a-zA-Z0-9_-]+)\s*:\s*"
    r"(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|color-mix\([^)]*\))")

# El bloque `:root` y los selectores de tema oscuro que la flota usa.
#
# Se corta en el PRIMER `}` y no en uno precedido de salto de línea. La primera
# versión exigía `\n\s*\}` y por tanto sólo veía bloques multilínea: sobre un CSS
# minificado —que es exactamente la forma en que el bundle llega al servidor— no
# encontraba ningún bloque de tema oscuro y el juez declaraba «no evaluado» en
# silencio. Un juez que no mira nada y no lo dice es peor que no tenerlo.
BLOQUE_RAIZ = re.compile(r":root\s*\{([^}]*)\}")
BLOQUE_OSCURO = re.compile(
    r"(?:\[data-theme\s*=\s*['\"]?oscuro['\"]?\]|prefers-color-scheme\s*:\s*dark)"
    r"[^{]*\{(.*?)\}", re.DOTALL)

# Usos que exigen contraste: texto, borde y anillo de foco.
USO_QUE_EXIGE_CONTRASTE = re.compile(
    r"(?:^|[;{])\s*(?:color|border(?:-[a-z]+)?|outline(?:-color)?|fill|stroke)"
    r"\s*:[^;}]*var\(\s*(--[a-zA-Z0-9_-]+)")

MOVIMIENTO_REDUCIDO = re.compile(r"prefers-reduced-motion")
HAY_MOVIMIENTO = re.compile(r"\b(?:transition|animation)(?:-[a-z]+)?\s*:")


def _hojas(repo: Repo) -> list[str]:
    """Las hojas de estilo VERSIONADAS que son del proyecto, no de una dependencia.

    Por el índice de git y no por el disco: lo que importa es lo que llega al
    servidor. Un `.css` generado en `dist/` no se juzga.
    """
    return [r for r in repo.versionados()
            if ES_CSS.search(r) and not ES_PRUEBA.search(r)]


def comprobar_foco(repo: Repo, r: Resultado, hojas: list[str]) -> None:
    """UI-10 — un `outline:0` sin sustituto deja el teclado a ciegas.

    Conservador a propósito: basta con que el MISMO archivo declare algún
    `:focus-visible` para dar el caso por cubierto. Un juez que exigiera
    emparejar cada supresión con su reemplazo produciría falsos positivos sobre
    CSS legítimo, y un falso positivo enseña a suprimir al juez.
    """
    r.comprobo("anillo de foco: `outline:0` con sustituto")

    for ruta in hojas:
        texto = repo.texto(ruta)
        if texto is None:
            continue
        if HAY_FOCO_VISIBLE.search(texto):
            continue

        lineas = texto.splitlines()
        for n, linea in enumerate(lineas):
            if not SIN_CONTORNO.search(linea):
                continue
            if (motivo := suprimido(lineas, n, "UI-10")):
                r.supresiones.append(f"{ruta}:{n + 1} outline suprimido — {motivo}")
                continue
            r.bloquea(
                "UI-10", ruta,
                "quita el contorno del foco y este archivo no declara ningún "
                "`:focus-visible` que lo sustituya",
                "quien navega con teclado deja de ver dónde está: el foco existe "
                "pero es invisible, y la pantalla parece no responder a la "
                "tabulación. Es WCAG 2.4.11, y es el defecto de accesibilidad "
                "más frecuente y más barato de arreglar",
                linea=n + 1,
                arreglo="declarar un `:focus-visible` con el token del estándar "
                        "—`outline: var(--foco-ancho) solid var(--foco-color)`— "
                        "en vez de apagar el contorno sin reemplazo",
            )
            break  # uno por archivo: el defecto es del archivo, no de la línea


def comprobar_tema_oscuro(repo: Repo, r: Resultado, hojas: list[str]) -> None:
    """UI-3 — un token de color que no se redefine en oscuro se queda claro.

    Sólo se miran los tokens que ADEMÁS se usan como texto, borde o foco: un
    token de color usado sólo como fondo puede ser legítimo en los dos temas.
    """
    con_tema = []
    for ruta in hojas:
        texto = repo.texto(ruta)
        if texto and BLOQUE_OSCURO.search(texto):
            con_tema.append((ruta, texto))

    if not con_tema:
        r.no_evaluado.append(
            "tema oscuro: ninguna hoja declara `[data-theme=oscuro]` ni "
            "`prefers-color-scheme: dark`. O esta aplicación no lo tiene todavía "
            "—y entonces le falta, porque el tema oscuro es obligatorio— o lo "
            "resuelve por una vía que este juez no reconoce")
        return

    r.comprobo("tema oscuro: los tokens de color de texto y borde se redefinen")

    for ruta, texto in con_tema:
        en_raiz = {}
        for bloque in BLOQUE_RAIZ.findall(texto):
            for nombre, _valor in TOKEN_COLOR.findall(bloque):
                en_raiz[nombre] = True
        if not en_raiz:
            continue

        redefinidos = set()
        for bloque in BLOQUE_OSCURO.findall(texto):
            for nombre, _valor in TOKEN_COLOR.findall(bloque):
                redefinidos.add(nombre)

        usados = set(USO_QUE_EXIGE_CONTRASTE.findall(texto))
        huerfanos = sorted(t for t in en_raiz if t in usados and t not in redefinidos)
        if not huerfanos:
            continue

        lineas = texto.splitlines()
        n = next((i for i, l in enumerate(lineas) if huerfanos[0] in l), 0)
        if (motivo := suprimido(lineas, n, "UI-3")):
            r.supresiones.append(f"{ruta}:{n + 1} tokens sin redefinir — {motivo}")
            continue

        muestra = ", ".join(f"`{t}`" for t in huerfanos[:5])
        cola = f" y {len(huerfanos) - 5} más" if len(huerfanos) > 5 else ""
        r.bloquea(
            "UI-3", ruta,
            f"{len(huerfanos)} token(es) de color se usan como texto, borde o "
            f"foco y NO se redefinen en el tema oscuro: {muestra}{cola}",
            "el token no desaparece: se queda con su valor claro sobre una "
            "superficie oscura. Medido en coipo_prensa2, el peor caso da 1,38:1 "
            "—texto presente e ilegible—, y el anillo de foco cae a 2,99:1, por "
            "debajo del 3:1 de WCAG 2.4.11. Nada lo delata en el navegador de "
            "quien lo escribió, porque casi nadie desarrolla en oscuro",
            linea=n + 1,
            arreglo="redefinir cada uno en el bloque del tema oscuro con un paso "
                    "derivado que alcance 4,5:1 en texto y 3:1 en borde y foco; "
                    "no corregir el color medido del banner, que sobre su propia "
                    "superficie es correcto",
        )


def _cuerpo_del_media(texto: str, desde: int) -> str:
    """El cuerpo del `@media` que empieza en `desde`, por conteo de llaves."""
    profundidad, cuerpo = 0, []
    for ch in texto[desde:]:
        if ch == "{":
            profundidad += 1
        elif ch == "}":
            profundidad -= 1
            if profundidad <= 0:
                break
        if profundidad >= 1:
            cuerpo.append(ch)
    return "".join(cuerpo)


def _es_universal(texto: str) -> bool:
    """¿Tiene este archivo un `prefers-reduced-motion` con selector universal?"""
    m = MOVIMIENTO_REDUCIDO.search(texto)
    if not m:
        return False
    bloque = _cuerpo_del_media(texto, m.end())
    return bool(re.search(r"(?:^|[,{\s])\*(?:[,\s{]|::)", bloque))


def comprobar_movimiento_reducido(repo: Repo, r: Resultado, hojas: list[str]) -> None:
    """UI-15 — apagar una transición y dejar ocho vivas cumple la letra, no la función."""
    con_movimiento = []
    for ruta in hojas:
        texto = repo.texto(ruta)
        if texto and HAY_MOVIMIENTO.search(texto):
            con_movimiento.append((ruta, texto))

    if not con_movimiento:
        return

    r.comprobo("movimiento reducido: existe y no es selectivo")

    completo = any(MOVIMIENTO_REDUCIDO.search(t) for _ruta, t in con_movimiento)
    total = sum(len(HAY_MOVIMIENTO.findall(t)) for _ruta, t in con_movimiento)
    ruta_principal = max(con_movimiento, key=lambda p: len(HAY_MOVIMIENTO.findall(p[1])))[0]

    if not completo:
        r.bloquea(
            "UI-15", ruta_principal,
            f"el repositorio declara {total} transición(es) o animación(es) y "
            f"ninguna hoja tiene un bloque `prefers-reduced-motion`",
            "quien ha pedido al sistema operativo que reduzca el movimiento —por "
            "vértigo, migraña o trastorno vestibular— recibe la interfaz "
            "completa igual. No es una preferencia estética: es la razón por la "
            "que existe el ajuste",
            arreglo="un bloque `@media (prefers-reduced-motion: reduce)` con "
                    "selector universal que baje `transition-duration` y "
                    "`animation-duration` a `.01ms !important`",
        )
        return

    # ¿Hay en ALGÚN archivo un bloque universal? Si lo hay, el repositorio está
    # cubierto y no se mira nada más.
    #
    # La comprobación es del REPOSITORIO, no de cada archivo. La primera versión
    # miraba archivo por archivo y marcaba un falso positivo sobre la propia
    # semilla: su bloque universal vive en `estilos/interfaz.css`, y el CSS de un
    # componente puede tener además el suyo, específico —el giro de un botón, que
    # no basta con acelerar: hay que dejarlo quieto en una posición y no a
    # medias—. Marcar eso es castigar la práctica correcta, y un falso positivo
    # no se discute: se suprime el juez.
    if any(_es_universal(t) for _ruta, t in con_movimiento):
        return

    for ruta, texto in con_movimiento:
        m = MOVIMIENTO_REDUCIDO.search(texto)
        if not m:
            continue
        bloque = _cuerpo_del_media(texto, m.end())
        if not bloque:
            continue

        propios = len(HAY_MOVIMIENTO.findall(texto))
        apagados = len(re.findall(r"[{;]\s*(?:transition|animation)[^;}]*", bloque))
        if apagados >= propios:
            continue

        lineas = texto.splitlines()
        n = texto[:m.start()].count("\n")
        if (motivo := suprimido(lineas, n, "UI-15")):
            r.supresiones.append(f"{ruta}:{n + 1} movimiento reducido — {motivo}")
            continue

        r.bloquea(
            "UI-15", ruta,
            f"el bloque `prefers-reduced-motion` es selectivo: apaga "
            f"{apagados} de {propios} declaración(es) de movimiento de este archivo",
            "cumple la letra y no la función. Quien pidió reducir el movimiento "
            "sigue recibiendo la mayor parte, y además con la peor cara: unas "
            "cosas se mueven y otras no, que es más desconcertante que el "
            "movimiento completo",
            linea=n + 1,
            arreglo="usar el selector universal `*, *::before, *::after` y bajar "
                    "`transition-duration` y `animation-duration` a `.01ms "
                    "!important`, en vez de enumerar selectores que hay que "
                    "acordarse de ampliar cada vez que se añade una transición",
        )


def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.tiene_git():
        r.no_evaluado.append(
            "no es un repositorio git: este juez lee `git ls-files` para saber "
            "qué hojas de estilo llegan al servidor, y sin índice no puede")
        return

    # El estándar de interfaz es para PROYECTOS NUEVOS. Una aplicación anterior
    # no lo incumple: es que no existía cuando se escribió.
    if not repo.existe(MARCADOR):
        r.no_corresponde(
            f"no hay `{MARCADOR}` en la raíz: este repositorio no declara seguir "
            "el estándar de interfaz de la flota, y el estándar es para proyectos "
            "NUEVOS. Una aplicación anterior no lo incumple — no existía cuando "
            "se escribió. Se adopta añadiendo el marcador, que es lo que hace "
            "`semilla/sembrar.py` en todo proyecto sembrado")
        return

    # El marcador existe, pero puede declarar que adopta otras capas y no ésta.
    adopcion = leer_adopcion(repo.texto(MARCADOR))
    if not adopcion.adopta(CAPA):
        razon = (f"{adopcion.cita(MARCADOR)} y no incluye `{CAPA}`, así que este "
                 "repositorio no declara seguir el estándar de interfaz. Quitar la "
                 "capa no arregla nada: los defectos siguen ahí, sin nadie que los "
                 "cuente.")
        r.no_corresponde(razon)
        # Se cuenta como supresión: es la única vía por la que un repositorio se
        # apaga un juez a sí mismo, y esa puerta se paga. Ver comun.py.
        r.supresiones.append(f"{MARCADOR} declara no adoptar `{CAPA}` — {razon}")
        return

    hojas = _hojas(repo)
    if not hojas:
        r.no_corresponde(
            "no hay ninguna hoja de estilo versionada fuera de pruebas y "
            "dependencias: esta aplicación no tiene interfaz propia que juzgar. "
            "Es lo correcto para un backend, un colector o un encuadre operativo "
            "de software de terceros")
        return

    comprobar_foco(repo, r, hojas)
    comprobar_tema_oscuro(repo, r, hojas)
    comprobar_movimiento_reducido(repo, r, hojas)


if __name__ == "__main__":
    ejecutar("j13", "la interfaz: foco, tema oscuro y movimiento reducido", comprobar)
