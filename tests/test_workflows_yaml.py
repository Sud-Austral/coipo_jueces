"""Los workflows tienen que ser YAML que GITHUB acepte, no sólo que un parser trague.

El 2026-09-08 `v2.0.3` salió con dos claves `env:` en el mismo paso de
`verificar.yml`. PyYAML se queda con la última sin avisar; GitHub rechaza el
archivo entero con «workflow file issue», sin jobs ni log, y todo consumidor de
`@v2` quedó sin gate. El tag se publicó con la suite verde: ninguna prueba miraba
esto. Ésta sí — y sin PyYAML, que aquí no hay: el escáner es de indentación.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((RAIZ / ".github" / "workflows").glob("*.yml"))

_CLAVE = re.compile(r"""("[^"]*"|'[^']*'|[^\s#"'][^:#]*?):(\s|$)""")
_BLOQUE = re.compile(r"^[|>][+-]?\d*$")


def claves_duplicadas(texto: str) -> list[tuple[int, str]]:
    """(línea, clave) por cada clave repetida dentro del MISMO mapa.

    Un mapa es el conjunto de claves con la misma indentación bajo el mismo
    padre; `- ` abre un mapa nuevo; `|` y `>` abren un escalar en bloque cuyas
    líneas no se miran. No es un parser YAML: es lo justo para este defecto.
    """
    problemas: list[tuple[int, str]] = []
    pila: list[tuple[int, set[str]]] = []
    bloque_desde: int | None = None
    for n, linea in enumerate(texto.splitlines(), 1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        sangria = len(linea) - len(linea.lstrip(" "))
        if bloque_desde is not None and sangria > bloque_desde:
            continue
        bloque_desde = None
        cuerpo, sangria = _abrir_item(pila, linea.strip(), sangria)
        m = _CLAVE.match(cuerpo)
        if not m:
            continue
        mapa = _mapa_de(pila, sangria)
        if m.group(1) in mapa:
            problemas.append((n, m.group(1)))
        mapa.add(m.group(1))
        if _BLOQUE.match(cuerpo[m.end() :].strip()):
            bloque_desde = sangria
    return problemas


def _abrir_item(pila: list[tuple[int, set[str]]], cuerpo: str, sangria: int) -> tuple[str, int]:
    """`- clave: x` abre un mapa nuevo dos columnas más adentro."""
    if not cuerpo.startswith("- "):
        return cuerpo, sangria
    sangria += 2
    while pila and pila[-1][0] >= sangria:
        pila.pop()
    pila.append((sangria, set()))
    return cuerpo[2:].lstrip(), sangria


def _mapa_de(pila: list[tuple[int, set[str]]], sangria: int) -> set[str]:
    """Las claves ya vistas del mapa al que pertenece una clave con esta sangría."""
    while pila and pila[-1][0] > sangria:
        pila.pop()
    if not pila or pila[-1][0] < sangria:
        pila.append((sangria, set()))
    return pila[-1][1]


class PruebaWorkflowsSinClavesDuplicadas(unittest.TestCase):
    def test_hay_workflows(self):
        self.assertTrue(WORKFLOWS, "no hay workflows que comprobar")

    def test_ninguna_clave_repetida_en_ningun_workflow(self):
        for p in WORKFLOWS:
            with self.subTest(workflow=p.name):
                self.assertEqual([], claves_duplicadas(p.read_text(encoding="utf-8")))

    def test_ninguna_expresion_vacia(self):
        """El segundo defecto de v2.0.3: un `${{ }}` vacío en un COMENTARIO del
        `run:`. GitHub evalúa las expresiones también ahí, y una vacía invalida el
        archivo entero. actionlint lo señala; esto lo caza sin actionlint."""
        for p in WORKFLOWS:
            with self.subTest(workflow=p.name):
                t = p.read_text(encoding="utf-8")
                vacias = [
                    n
                    for n, linea in enumerate(t.splitlines(), 1)
                    if re.search(r"\$\{\{\s*\}\}", linea)
                ]
                self.assertEqual([], vacias)

    def test_el_detector_detecta_el_caso_de_v2_0_3(self):
        """Una prueba que nunca falla no prueba nada."""
        roto = (
            "jobs:\n  x:\n    steps:\n      - name: a\n        env:\n"
            "          A: 1\n        env:\n          B: 2\n        run: |\n"
            "          echo 'env: dentro de un bloque no cuenta'\n"
        )
        self.assertEqual([(7, "env")], claves_duplicadas(roto))

    def test_el_detector_no_confunde_pasos_ni_bloques(self):
        sano = (
            "on:\n  push:\n  pull_request:\n"
            "jobs:\n  x:\n    steps:\n"
            "      - name: a\n        run: |\n          name: repetido\n          name: y otra vez\n"
            "      - name: b\n        with:\n          ref: x\n"
            "      - name: c\n        with:\n          ref: y\n"
        )
        self.assertEqual([], claves_duplicadas(sano))


_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)
_FIJADO = re.compile(r"@[0-9a-f]{40}$")


def usos_sin_sha(texto: str) -> list[str]:
    """Los `uses:` externos que no van fijados a un SHA de 40 caracteres.

    Un `uses:` local (`./...`) no lleva referencia: es el archivo de la propia rama."""
    return [u for u in _USES.findall(texto) if not u.startswith("./") and not _FIJADO.search(u)]


class PruebaUsosFijados(unittest.TestCase):
    """Toda action ajena va fijada a un SHA, en los TRES workflows.

    Un `@v4` es un tag móvil: quien controle esa action cambia lo que corre en el CI de
    toda la flota sin tocar este repositorio. Hasta el 2026-11-25 esto lo comprobaba un
    `python -c` dentro de `autotest.yml`, y sólo sobre `verificar.yml`. `correr.py` explica
    por qué esa lógica no vive en el YAML: el YAML no se puede probar, y aquí sí hay una
    prueba que se ve fallar. Y sólo corría en CI: en la máquina de quien edita, nunca.
    """

    def test_ningun_uses_externo_sin_sha(self):
        for p in WORKFLOWS:
            with self.subTest(workflow=p.name):
                self.assertEqual([], usos_sin_sha(p.read_text(encoding="utf-8")))

    def test_el_reusable_tiene_usos_y_su_disparador(self):
        """Cero de cero: si el reusable dejara de declarar `uses:`, la prueba de arriba
        pasaría sin haber mirado nada."""
        texto = (RAIZ / ".github" / "workflows" / "verificar.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_call", texto, "el reusable perdió su disparador")
        self.assertTrue(_USES.findall(texto), "el reusable no declara ningún `uses:`")

    def test_el_detector_ve_un_tag_y_una_rama(self):
        """Una prueba que nunca falla no prueba nada."""
        sha = "a" * 40
        texto = (
            "jobs:\n  x:\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: otra\n        uses: alguien/accion@main\n"
            f"      - uses: alguien/accion@{sha} # v1.2.3\n"
            "  y:\n    uses: ./.github/workflows/verificar.yml\n"
        )
        self.assertEqual(["actions/checkout@v4", "alguien/accion@main"], usos_sin_sha(texto))


if __name__ == "__main__":
    unittest.main(verbosity=2)
