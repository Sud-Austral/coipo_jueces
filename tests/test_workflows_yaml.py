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
        if bloque_desde is not None:
            if sangria > bloque_desde:
                continue
            bloque_desde = None
        cuerpo = linea.strip()
        if cuerpo.startswith("- "):
            cuerpo = cuerpo[2:].lstrip()
            sangria += 2
            while pila and pila[-1][0] >= sangria:
                pila.pop()
            pila.append((sangria, set()))
        m = _CLAVE.match(cuerpo)
        if not m:
            continue
        clave = m.group(1)
        while pila and pila[-1][0] > sangria:
            pila.pop()
        if not pila or pila[-1][0] < sangria:
            pila.append((sangria, set()))
        if clave in pila[-1][1]:
            problemas.append((n, clave))
        pila[-1][1].add(clave)
        if _BLOQUE.match(cuerpo[m.end():].strip()):
            bloque_desde = sangria
    return problemas


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
                vacias = [n for n, l in enumerate(t.splitlines(), 1) if re.search(r"\$\{\{\s*\}\}", l)]
                self.assertEqual([], vacias)

    def test_el_detector_detecta_el_caso_de_v2_0_3(self):
        """Una prueba que nunca falla no prueba nada."""
        roto = ("jobs:\n  x:\n    steps:\n      - name: a\n        env:\n"
                "          A: 1\n        env:\n          B: 2\n        run: |\n"
                "          echo 'env: dentro de un bloque no cuenta'\n")
        self.assertEqual([(7, "env")], claves_duplicadas(roto))

    def test_el_detector_no_confunde_pasos_ni_bloques(self):
        sano = ("on:\n  push:\n  pull_request:\n"
                "jobs:\n  x:\n    steps:\n"
                "      - name: a\n        run: |\n          name: repetido\n          name: y otra vez\n"
                "      - name: b\n        with:\n          ref: x\n"
                "      - name: c\n        with:\n          ref: y\n")
        self.assertEqual([], claves_duplicadas(sano))


if __name__ == "__main__":
    unittest.main(verbosity=2)
