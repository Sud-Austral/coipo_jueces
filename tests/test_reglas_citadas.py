"""Ningún juez puede citar una regla que no exista en un documento.

EL DEFECTO QUE ESTAS PRUEBAS CIERRAN se encontró en este mismo repositorio: los
jueces `j01`, `j06` y `j09` bloqueaban despliegues citando códigos `D-06`,
`D-27`, `D-28`, `D-31` y `D-37` de un `DECRETOS.md` que **no existe en ningún
repositorio de la organización**. Los generó un asistente y nadie los escribió.

Una regla así no se puede discutir, ni corregir, ni derogar: cuando estorba, lo
único que se puede hacer es suprimirla. Y un verificador cuyo único camino de
salida es la supresión se apaga solo en unos meses.

La comprobación va en las DOS direcciones a propósito:
  - un código emitido y no listado es una regla inventada;
  - un código listado y no emitido es una regla fantasma, que hace parecer que
    el gate cubre algo que en realidad no mira. Es el mismo error que el
    incidente de COIPO_PDF_EXCEL, movido al nivel del catálogo.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
JUECES = RAIZ / "jueces"
REGLAS = RAIZ / "REGLAS.md"

CODIGO = re.compile(r"^[A-Z0-9]+-[0-9]+$")
EN_TABLA = re.compile(r"^\|\s*`(?P<codigo>[A-Z0-9]+-[0-9]+)`\s*\|", re.MULTILINE)

# Se recorre el AST y no el texto. Un extractor por regex no ve
# `r.bloquea(REGLA, ...)` —la forma que usa j09— y daria por no emitida una
# regla que si bloquea: exactamente el falso verde que estas pruebas existen
# para impedir.
LLAMADAS = {"bloquea", "avisa", "suprimido"}


def _constantes(arbol: ast.Module) -> dict[str, str]:
    """Constantes de modulo con valor de texto: `REGLA = "G8-4"`."""
    salida: dict[str, str] = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Constant)                 and isinstance(nodo.value.value, str):
            for destino in nodo.targets:
                if isinstance(destino, ast.Name):
                    salida[destino.id] = nodo.value.value
    return salida


def codigos_emitidos() -> dict[str, set[str]]:
    """codigo -> conjunto de jueces que lo emiten."""
    salida: dict[str, set[str]] = {}
    for archivo in sorted(JUECES.glob("j*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        constantes = _constantes(arbol)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            f = nodo.func
            nombre = f.attr if isinstance(f, ast.Attribute) else                 f.id if isinstance(f, ast.Name) else None
            if nombre not in LLAMADAS:
                continue
            for arg in nodo.args:
                valor = arg.value if isinstance(arg, ast.Constant) else                     constantes.get(arg.id) if isinstance(arg, ast.Name) else None
                if isinstance(valor, str) and CODIGO.match(valor):
                    salida.setdefault(valor, set()).add(archivo.stem)
                    break
    return salida


def codigos_documentados() -> set[str]:
    return {m.group("codigo") for m in EN_TABLA.finditer(REGLAS.read_text(encoding="utf-8"))}


class PruebaTrazabilidad(unittest.TestCase):
    def test_existe_el_catalogo(self):
        self.assertTrue(REGLAS.exists(), "falta REGLAS.md: sin él no hay forma de "
                                         "saber qué documento respalda cada regla")

    def test_todo_codigo_emitido_esta_documentado(self):
        emitidos, documentados = codigos_emitidos(), codigos_documentados()
        self.assertTrue(emitidos, "ningún juez emite códigos: el extractor está roto")
        huerfanos = {c: sorted(j) for c, j in emitidos.items() if c not in documentados}
        self.assertEqual(
            {}, huerfanos,
            f"estos códigos bloquean o avisan sin figurar en REGLAS.md, así que "
            f"nadie puede saber qué documento los respalda: {huerfanos}")

    def test_todo_codigo_documentado_se_emite(self):
        emitidos, documentados = codigos_emitidos(), codigos_documentados()
        fantasmas = sorted(documentados - set(emitidos))
        self.assertEqual(
            [], fantasmas,
            f"REGLAS.md anuncia estas reglas y ningún juez las comprueba. El "
            f"catálogo dice que el gate cubre algo que no mira: {fantasmas}")

    def test_cada_codigo_nombra_su_juez_correctamente(self):
        """La columna «Juez» de REGLAS.md no puede mentir sobre quién comprueba qué."""
        texto = REGLAS.read_text(encoding="utf-8")
        for codigo, jueces in sorted(codigos_emitidos().items()):
            fila = next((l for l in texto.splitlines()
                         if l.startswith(f"| `{codigo}`")), None)
            self.assertIsNotNone(fila, f"{codigo} sin fila en REGLAS.md")
            cortos = {j.split("_")[0] for j in jueces}
            for corto in cortos:
                self.assertIn(f"`{corto}`", fila,
                              f"{codigo} lo emite {corto}, pero su fila en REGLAS.md "
                              f"no lo nombra: {fila}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
