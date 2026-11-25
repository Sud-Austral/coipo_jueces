"""Lo que el repositorio dice de sí mismo coincide con lo que es.

Este repositorio documenta mucho y con fecha, y aun así el 2026-11-24 se contradecía:

  - `v2.0.23` estaba publicado como tag y `docs/VERSIONADO.md` no lo nombraba. Era la
    tercera vez (`v2.0.12`, `v2.0.13`); la segunda dejó escrita una enmienda, y la enmienda
    no impidió la tercera.
  - `CLAUDE.md` no nombraba tres módulos de `jueces/` ni ocho pruebas transversales.
  - `REGLAS.md` declaraba un prefijo `H-N` que ninguna regla usa y no declaraba `AUD-N`
    ni `MAQ-N`, que así caían en «sin fuente escrita» mientras `AUD-1` bloquea.
  - el README prometía una calibración en el docstring de cada juez y `j11` no la tenía.
  - había dos binarios de ofimática versionados, y uno contradecía al catálogo.

Ninguna prueba miraba nada de eso: sólo `REGLAS.md` contra el código y los `@vN` de los
ejemplos tenían guardián. La lección no es nueva en esta flota: una cifra o una lista
tecleada envejece sola, y corregirla a mano sólo la deja lista para envejecer otra vez.
Aquí cada una se compara con su fuente. Lo que no se puede comparar se quita del
documento (el README ya no dice cuántos jueces hay: dice cómo se cuentan).
"""

from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
JUECES = RAIZ / "jueces"
TESTS = RAIZ / "tests"
sys.path.insert(0, str(JUECES))

import correr  # noqa: E402
from comun import Repo  # noqa: E402

ES_JUEZ = re.compile(r"^j\d{2}_[a-z_]+$")
NOMBRE_DE_JUEZ = re.compile(r"\bj\d{2}_[a-z_]+\b")
ID_DE_JUEZ = re.compile(r"\bj\d{2}\b")
ARCHIVO_PY = re.compile(r"`([\w./-]+\.py)`")
ACTIVAS = re.compile(r"\*\*(\d+) supresi(?:ón|ones) activas?\.\*\*")
FILA_DE_REGLA = re.compile(r"^\|\s*`([A-Z][A-Z0-9]{0,3})-(?:N|[0-9]+)`\s*\|", re.MULTILINE)
MAYOR_VIGENTE = re.compile(r"Hoy la mayor vigente es `v(\d+)`")
PISO_EN_CI = re.compile(r'python:\s*"(\d+\.\d+)"')
OFIMATICA = (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp")


def leer(relativa: str) -> str:
    return (RAIZ / relativa).read_text(encoding="utf-8")


def seccion(texto: str, desde: str, hasta: str | None = None) -> str:
    """Del encabezado que empieza por `desde` al siguiente que empieza por `hasta`."""
    lineas = texto.splitlines()
    inicio = next((i for i, linea in enumerate(lineas) if linea.startswith(desde)), None)
    if inicio is None:
        raise AssertionError(f"no se encontró el encabezado «{desde}»: la prueba no mira nada")
    if hasta is None:
        return "\n".join(lineas[inicio:])
    fin = next((i for i in range(inicio + 1, len(lineas)) if lineas[i].startswith(hasta)), None)
    if fin is None:
        raise AssertionError(f"no se encontró el encabezado «{hasta}» después de «{desde}»")
    return "\n".join(lineas[inicio:fin])


# ── Jueces, módulos y pruebas ────────────────────────────────────────────────


def jueces_del_disco() -> set[str]:
    return {p.stem for p in JUECES.glob("*.py") if ES_JUEZ.match(p.stem)}


def modulos_que_no_son_jueces() -> set[str]:
    return {p.name for p in JUECES.glob("*.py") if not ES_JUEZ.match(p.stem)}


def pruebas_transversales() -> set[str]:
    """Las `tests/test_*.py` que no son la prueba de un juez (`test_jNN_*.py`)."""
    return {p.name for p in TESTS.glob("test_*.py") if not re.match(r"test_j\d{2}_", p.name)}


def py_citados(texto: str) -> set[str]:
    """Los archivos `.py` que un documento nombra entre acentos graves, sin los patrones
    (`jNN_nombre.py`)."""
    return {Path(c).name for c in ARCHIVO_PY.findall(texto) if "NN" not in c}


def fantasmas(citados: set[str]) -> list[str]:
    """Citados con nombre de módulo o de prueba de este repositorio que no existen.

    `sellar.py` o `sembrar.py` son de la fábrica: no llevan nombre de aquí y no cuentan."""
    existentes = {p.name for carpeta in (JUECES, TESTS) for p in carpeta.glob("*.py")}
    de_aqui = re.compile(r"^(test_|comun|j\d{2}_|historial_|correr\.py$|ayuda\.py$)")
    return sorted(c for c in citados if de_aqui.match(c) and c not in existentes)


# Una SECCIÓN, no una mención: una línea de encabezado en mayúsculas, sin sangría, como
# «CALIBRACIÓN INVERSA (medida el …)» o «PRUEBA DE CALIBRACIÓN (…)». La primera versión de
# esta prueba buscaba la palabra en cualquier parte, y al quitarle la sección a `j11` seguía
# verde porque el texto nombraba «Calibración inversa» del README: se vio al mutarla.
SECCION_DE_CALIBRACION = re.compile(r"^[A-ZÁÉÍÓÚÑ ]*CALIBRACIÓN\b", re.MULTILINE)


def tiene_seccion_de_calibracion(fuente: str) -> bool:
    """¿El docstring del módulo lleva una sección de calibración?"""
    return bool(SECCION_DE_CALIBRACION.search(ast.get_docstring(ast.parse(fuente)) or ""))


# ── DEUDA.md ─────────────────────────────────────────────────────────────────


def deuda(texto: str) -> tuple[int, int]:
    """(el número que DEUDA.md declara, las filas de su tabla de supresiones)."""
    m = ACTIVAS.search(texto)
    if m is None:
        raise AssertionError("DEUDA.md no dice «**N supresión(es) activa(s).**»")
    filas = FILA_DE_REGLA.findall(seccion(texto, "## Supresiones activas"))
    return int(m.group(1)), len(filas)


def supresiones_del_gate() -> int:
    """Las que cuenta el gate sobre este repositorio, como en el paso de dogfood del CI."""
    modulos = correr.descubrir(correr.AQUI, "encuadre_operativo", [])
    with contextlib.redirect_stdout(io.StringIO()):
        resultados, reventados = correr._correr(modulos, Repo(RAIZ), "advisory", False)
    if reventados:
        raise AssertionError(f"reventaron al juzgar este repositorio: {reventados}")
    return sum(len(r.supresiones) for r in resultados)


# ── docs/VERSIONADO.md ───────────────────────────────────────────────────────


def versiones_con_encabezado(texto: str, mayor: int) -> set[tuple[int, int]]:
    """(menor, parche) de cada `vMAYOR.x.y` nombrado en un ENCABEZADO; el cuerpo no cuenta."""
    salida: set[tuple[int, int]] = set()
    for linea in re.findall(r"^#{2,4} .*$", texto, re.MULTILINE):
        salida |= {
            (int(menor), int(parche))
            for menor, parche in re.findall(rf"\bv{mayor}\.(\d+)\.(\d+)\b", linea)
        }
    return salida


def huecos(versiones: set[tuple[int, int]]) -> list[str]:
    """Los parches que faltan entre el 0 y el más alto de cada menor."""
    faltan: list[str] = []
    for menor in sorted({m for m, _ in versiones}):
        parches = {p for m, p in versiones if m == menor}
        faltan += [f"{menor}.{p}" for p in range(max(parches) + 1) if p not in parches]
    return faltan


def tags_de_la_mayor(mayor: int) -> set[tuple[int, int]]:
    try:
        salida = subprocess.run(
            ["git", "tag", "-l", f"v{mayor}.*"],
            cwd=RAIZ,
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {
        (int(m.group(1)), int(m.group(2)))
        for nombre in salida.split()
        if (m := re.fullmatch(rf"v{mayor}\.(\d+)\.(\d+)", nombre))
    }


# ── REGLAS.md ────────────────────────────────────────────────────────────────


def prefijos_declarados(texto: str) -> set[str]:
    """Los de la tabla «Documentos fuente»."""
    return set(FILA_DE_REGLA.findall(seccion(texto, "## Documentos fuente", "## Reglas vigentes")))


def prefijos_vigentes(texto: str) -> set[str]:
    """Los de las reglas de la tabla «Reglas vigentes»."""
    return set(
        FILA_DE_REGLA.findall(seccion(texto, "## Reglas vigentes", "## Reglas sin fuente escrita"))
    )


def prefijos_sin_fuente(texto: str) -> set[str]:
    return set(
        FILA_DE_REGLA.findall(
            seccion(texto, "## Reglas sin fuente escrita", "## Reglas de la Guía")
        )
    )


class PruebaJuecesYModulos(unittest.TestCase):
    def test_hay_jueces_modulos_y_pruebas_que_mirar(self):
        """Cero de cero: con un glob roto, todo lo de abajo pasaría en vacío."""
        self.assertIn("j09_secretos", jueces_del_disco())
        self.assertIn("comun.py", modulos_que_no_son_jueces())
        self.assertIn("test_reglas_citadas.py", pruebas_transversales())

    def test_el_readme_lista_exactamente_los_jueces_que_hay(self):
        citados = set(NOMBRE_DE_JUEZ.findall(seccion(leer("README.md"), "## Jueces", "### ")))
        self.assertEqual(jueces_del_disco(), citados)

    def test_claude_md_lista_exactamente_los_jueces_que_hay(self):
        citados = set(
            ID_DE_JUEZ.findall(seccion(leer("CLAUDE.md"), "## Estructura", "## Comandos"))
        )
        self.assertEqual({j[:3] for j in jueces_del_disco()}, citados)

    def test_claude_md_nombra_cada_modulo_y_cada_prueba_transversal(self):
        citados = py_citados(leer("CLAUDE.md"))
        esperados = modulos_que_no_son_jueces() | pruebas_transversales() | {"ayuda.py"}
        self.assertEqual(
            [],
            sorted(esperados - citados),
            "existen y `CLAUDE.md` no los nombra: quien lea la guía no sabrá que están",
        )

    def test_claude_md_no_nombra_archivos_que_no_existen(self):
        self.assertEqual([], fantasmas(py_citados(leer("CLAUDE.md"))))

    def test_cada_juez_tiene_su_prueba(self):
        """«Una prueba por juez», dice `CLAUDE.md`."""
        faltan = sorted(j for j in jueces_del_disco() if not (TESTS / f"test_{j}.py").exists())
        self.assertEqual([], faltan)

    def test_cada_juez_dice_contra_que_se_calibro(self):
        """El README: «cada juez dice en su docstring contra qué se calibró y cuándo»."""
        sin_calibracion = sorted(
            j
            for j in jueces_del_disco()
            if not tiene_seccion_de_calibracion((JUECES / f"{j}.py").read_text(encoding="utf-8"))
        )
        self.assertEqual([], sin_calibracion)


class PruebaDeuda(unittest.TestCase):
    def test_lo_que_declara_deuda_md_es_lo_que_cuenta_el_gate(self):
        """`DEUDA.md` dice que el contador de supresiones es la única señal temprana de que
        un gate se apaga. Hasta el 2026-11-25 nadie comparaba ese número con el gate."""
        motivo = Repo(RAIZ).indice_roto()
        if motivo:
            self.fail(
                f"esta prueba necesita el índice de git de este repositorio ({motivo}): sin "
                "él `j09` no mira nada y contaría cero supresiones"
            )
        declaradas, filas = deuda(leer("DEUDA.md"))
        self.assertEqual(declaradas, filas, "el número de DEUDA.md y las filas de su tabla")
        self.assertEqual(
            declaradas,
            supresiones_del_gate(),
            "DEUDA.md no declara las mismas supresiones que el gate cuenta sobre este "
            "repositorio: o falta una fila, o sobra",
        )


class PruebaVersionado(unittest.TestCase):
    def setUp(self):
        self.texto = leer("docs/VERSIONADO.md")
        m = MAYOR_VIGENTE.search(self.texto)
        self.assertIsNotNone(m, "docs/VERSIONADO.md no dice «Hoy la mayor vigente es `vN`»")
        self.mayor = int(m.group(1))
        self.encabezados = versiones_con_encabezado(self.texto, self.mayor)

    def test_hay_encabezados_que_mirar(self):
        self.assertIn((0, 0), self.encabezados)

    def test_ninguna_version_se_quedo_sin_su_entrada(self):
        """La que vale también sin tags: si existe la entrada de `v2.0.24`, tiene que
        existir la de `v2.0.23`."""
        self.assertEqual(
            [],
            [f"v{self.mayor}.{x}" for x in huecos(self.encabezados)],
            "versiones publicadas sin encabezado en docs/VERSIONADO.md: «resellar el lock es "
            "una publicación como cualquier otra»",
        )

    def test_cada_tag_publicado_tiene_su_entrada(self):
        tags = tags_de_la_mayor(self.mayor)
        if os.environ.get("GITHUB_ACTIONS"):
            self.assertTrue(
                tags, "el checkout de CI no trae tags: añade `fetch-depth: 0` (ver autotest.yml)"
            )
        self.assertEqual(
            [],
            sorted(f"v{self.mayor}.{m}.{p}" for m, p in tags - self.encabezados),
            "tags que existen y que docs/VERSIONADO.md no nombra en ningún encabezado",
        )


class PruebaCatalogo(unittest.TestCase):
    def setUp(self):
        self.texto = leer("REGLAS.md")

    def test_los_prefijos_declarados_son_los_de_las_reglas_vigentes(self):
        declarados, vigentes = prefijos_declarados(self.texto), prefijos_vigentes(self.texto)
        self.assertTrue(vigentes, "no se leyó ninguna regla vigente: la prueba no mira nada")
        self.assertEqual(
            [],
            sorted(vigentes - declarados),
            "reglas vigentes cuyo prefijo no está en «Documentos fuente»: según esa tabla "
            "caen en «otros: sin fuente escrita todavía»",
        )
        self.assertEqual(
            [],
            sorted(declarados - vigentes),
            "prefijos declarados en «Documentos fuente» que ninguna regla vigente usa",
        )

    def test_una_regla_sin_fuente_no_declara_fuente(self):
        self.assertTrue(prefijos_sin_fuente(self.texto))
        self.assertEqual(
            [], sorted(prefijos_sin_fuente(self.texto) & prefijos_declarados(self.texto))
        )


class PruebaArtefactos(unittest.TestCase):
    def test_ningun_binario_de_ofimatica_versionado(self):
        """Un `.xlsx` o un `.docx` no lo lee ningún juez ni ninguna prueba: lo que diga
        envejece sin que nada lo vea, y en un repositorio público sus metadatos también se
        publican. El 2026-11-24 había dos; uno contradecía a `REGLAS.md`."""
        repo = Repo(RAIZ)
        motivo = repo.indice_roto()
        if motivo:
            self.fail(f"esta prueba necesita el índice de git de este repositorio ({motivo})")
        self.assertTrue(repo.versionados())
        self.assertEqual([], sorted(p for p in repo.versionados() if p.lower().endswith(OFIMATICA)))


class PruebaPisoDePython(unittest.TestCase):
    def test_el_minimo_declarado_es_el_que_prueba_el_ci(self):
        """El mínimo se dice en tres sitios; el que manda es el que el CI ejecuta."""
        m = PISO_EN_CI.search(leer(".github/workflows/autotest.yml"))
        self.assertIsNotNone(m, 'autotest.yml no fija ninguna pierna `python: "X.Y"`')
        for documento in ("README.md", "CLAUDE.md"):
            with self.subTest(documento=documento):
                self.assertIn(f"Python {m.group(1)}", leer(documento))


class PruebaDeLosDetectores(unittest.TestCase):
    """Cada detector tiene que ver lo que dice ver, sobre texto sintético."""

    def test_seccion_corta_donde_debe_y_falla_si_no_encuentra(self):
        texto = "# T\n## Uno\na\n### Sub\nb\n## Dos\nc\n"
        self.assertEqual("## Uno\na\n### Sub\nb", seccion(texto, "## Uno", "## "))
        self.assertEqual("## Dos\nc", seccion(texto, "## Dos"))
        with self.assertRaises(AssertionError):
            seccion(texto, "## No existe")

    def test_una_mencion_no_es_una_seccion_de_calibracion(self):
        con = '"""j90 — x.\n\nCALIBRACIÓN INVERSA (medida el 2026-09-05)\n  tabla\n"""\n'
        prosa = '"""j90 — x.\n\nPRUEBA DE CALIBRACIÓN (obligatoria)\n  texto\n"""\n'
        sin = '"""j90 — x.\n\nMEDICIONES\n  ver «Calibración inversa» del README.\n"""\n'
        self.assertTrue(tiene_seccion_de_calibracion(con))
        self.assertTrue(tiene_seccion_de_calibracion(prosa))
        self.assertFalse(tiene_seccion_de_calibracion(sin))
        self.assertFalse(tiene_seccion_de_calibracion("x = 1\n"))

    def test_py_citados_y_fantasmas(self):
        texto = "`comun.py`, `tests/test_no_existe.py`, `jNN_nombre.py` y `sellar.py` de la fábrica"
        citados = py_citados(texto)
        self.assertEqual({"comun.py", "test_no_existe.py", "sellar.py"}, citados)
        self.assertEqual(["test_no_existe.py"], fantasmas(citados))

    def test_deuda_cuenta_el_numero_y_las_filas(self):
        texto = (
            "# Deuda\n\n## Supresiones activas\n\n| Regla | Dónde |\n|---|---|\n"
            "| `G8-4` | a |\n| `SEM-1` | b |\n\n**3 supresiones activas.** texto\n"
        )
        self.assertEqual((3, 2), deuda(texto))

    def test_un_encabezado_cuenta_y_el_cuerpo_no(self):
        texto = "### `v2.0.2` y `v2.0.3`, 2026-09-08\nse parece a v2.0.9\n#### `v2.1.0`\n"
        self.assertEqual({(0, 2), (0, 3), (1, 0)}, versiones_con_encabezado(texto, 2))

    def test_huecos_ve_la_version_que_falta(self):
        self.assertEqual(["0.2"], huecos({(0, 0), (0, 1), (0, 3)}))
        self.assertEqual(["0.0", "1.0"], huecos({(0, 1), (1, 1)}))
        self.assertEqual([], huecos({(0, 0), (0, 1), (1, 0)}))

    def test_prefijos_de_cada_tabla(self):
        texto = (
            "## Documentos fuente\n| Prefijo | Doc |\n|---|---|\n| `G8-N` | guía |\n| `H-N` | x |\n"
            "## Reglas vigentes\n| Código | Juez |\n|---|---|\n| `G8-1` | `j02` |\n| `AUD-1` | `j12` |\n"
            "## Reglas sin fuente escrita\n| `NG-1` | `j01` |\n## Reglas de la Guía 8\n"
        )
        self.assertEqual({"G8", "H"}, prefijos_declarados(texto))
        self.assertEqual({"G8", "AUD"}, prefijos_vigentes(texto))
        self.assertEqual({"NG"}, prefijos_sin_fuente(texto))


if __name__ == "__main__":
    unittest.main(verbosity=2)
