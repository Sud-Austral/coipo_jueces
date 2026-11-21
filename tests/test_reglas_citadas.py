"""Ningún juez puede citar una regla que no exista en un documento.

EL DEFECTO QUE ESTAS PRUEBAS CIERRAN se encontró en este mismo repositorio: los
jueces `j01`, `j06` y `j09` bloqueaban despliegues citando códigos `D-06`,
`D-27`, `D-28`, `D-31` y `D-37` de un `DECRETOS.md` que **no estaba versionado en
ningún repositorio cuando empezaron a citarlo**. Los generó un asistente y nadie
los escribió. Hoy el archivo existe en `borradores/` de la fábrica, o sea en
cuarentena y sin mandar: la frase original, que decía «no existe en ningún
repositorio», dejó de ser cierta el 2026-09-05 y se corrigió el 2026-09-09.

Una regla así no se puede discutir, ni corregir, ni derogar: cuando estorba, lo
único que se puede hacer es suprimirla. Y un verificador cuyo único camino de
salida es la supresión se apaga solo en unos meses.

La comprobación va en las DOS direcciones a propósito:
  - un código emitido y no listado es una regla inventada;
  - un código listado y no emitido es una regla fantasma, que hace parecer que
    el gate cubre algo que en realidad no mira. Es el mismo error que el
    incidente de COIPO_PDF_EXCEL, movido al nivel del catálogo.

EL AGUJERO QUE TENÍA HASTA EL 2026-11-21. El extractor buscaba, entre los
argumentos de cada llamada, el PRIMERO con forma de código (`^[A-Z0-9]+-[0-9]+$`) y
se saltaba el resto. `j11` emitía `DOCKER-hc` —minúsculas, sin forma de código—, que
no figuraba en `REGLAS.md`, y la prueba no lo veía: el código no casaba con la
forma, así que el extractor no lo contaba ni como emitido ni como huérfano. Salía de
verdad en dos aplicaciones. Y `j08` emitía `G8-8` a través de un alias
(`anota = r.bloquea if desplegable else r.avisa`), que el extractor tampoco veía.

Desde entonces se mira TODA llamada a `.bloquea(` / `.avisa(` de un juez: su primer
argumento tiene que ser un literal —o una constante de módulo con un literal— con
forma de código y presente en `REGLAS.md`; y un `.bloquea`/`.avisa` que no se llama
en el sitio (un alias) o un `.anota(` directo es un fallo, porque esconden el
código o la severidad a esta prueba. `PruebaDelExtractor` lo hace fallar a propósito
con casos sintéticos: una prueba que no se ha visto fallar no es una prueba.
"""

from __future__ import annotations

import ast
import re
import unittest
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
JUECES = RAIZ / "jueces"
REGLAS = RAIZ / "REGLAS.md"

# La forma de un código: un prefijo de 2 a 4 caracteres que empieza por letra
# (`G8`, `DK`, `SEM`, `COD`, `UI`...) y un número. `G8-4` lleva un dígito en el
# prefijo: por eso no es `[A-Z]{2,4}`.
FORMA = re.compile(r"^[A-Z][A-Z0-9]{1,3}-[0-9]+$")
EN_TABLA = re.compile(r"^\|\s*`(?P<codigo>[A-Z][A-Z0-9]{1,3}-[0-9]+)`\s*\|", re.MULTILINE)

EMISORES = frozenset({"bloquea", "avisa"})
# `anota()` es el método común que hay debajo de los dos: llamarlo directo esconde
# la severidad a `PruebaSeveridad`.
OCULTOS = EMISORES | {"anota"}


@dataclass(frozen=True)
class Emision:
    juez: str
    linea: int
    llamada: str  # `bloquea`, `avisa` o `suprimido`
    codigo: str | None  # None si el argumento no es un literal
    problema: str = ""


def _constantes(arbol: ast.Module) -> dict[str, str]:
    """Constantes de módulo con valor de texto: `REGLA = "G8-4"`."""
    salida: dict[str, str] = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Constant) \
                and isinstance(nodo.value.value, str):
            for destino in nodo.targets:
                if isinstance(destino, ast.Name):
                    salida[destino.id] = nodo.value.value
    return salida


def _literal(nodo: ast.AST | None, constantes: dict[str, str]) -> str | None:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.Name):
        return constantes.get(nodo.id)
    return None


def _argumento(llamada: ast.Call, posicion: int) -> ast.AST | None:
    if len(llamada.args) > posicion:
        return llamada.args[posicion]
    return next((k.value for k in llamada.keywords if k.arg == "regla"), None)


def _nombre(func: ast.AST) -> str | None:
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else None


def emisiones_de(texto: str, juez: str) -> list[Emision]:
    """Cada llamada que emite o suprime un código en el fuente de un juez."""
    arbol = ast.parse(texto)
    constantes = _constantes(arbol)
    llamados = {id(n.func) for n in ast.walk(arbol) if isinstance(n, ast.Call)}
    salida: list[Emision] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Attribute) and nodo.attr in OCULTOS and id(nodo) not in llamados:
            salida.append(Emision(juez, nodo.lineno, nodo.attr, None,
                                  f"`.{nodo.attr}` usado sin llamarlo (un alias): el código y "
                                  "la severidad quedan fuera del alcance de esta prueba"))
        if not isinstance(nodo, ast.Call):
            continue
        nombre = _nombre(nodo.func)
        if nombre == "anota" and isinstance(nodo.func, ast.Attribute):
            salida.append(Emision(juez, nodo.lineno, nombre, None,
                                  "`.anota(` directo: se emite con `bloquea()` o `avisa()`"))
        elif nombre in EMISORES and isinstance(nodo.func, ast.Attribute):
            salida.append(_emision(juez, nodo, nombre, _argumento(nodo, 0), constantes))
        elif nombre == "suprimido":
            # El código es el tercer argumento. Una variable (un auxiliar que recibe la
            # regla) no es una emisión: suprime lo que otra llamada emite.
            codigo = _literal(_argumento(nodo, 2), constantes)
            if codigo is not None:
                salida.append(_emision(juez, nodo, nombre, _argumento(nodo, 2), constantes))
    return salida


def _emision(juez: str, nodo: ast.Call, llamada: str, arg: ast.AST | None,
             constantes: dict[str, str]) -> Emision:
    codigo = _literal(arg, constantes)
    if codigo is None:
        return Emision(juez, nodo.lineno, llamada, None,
                       "el código no es un literal ni una constante de módulo con uno")
    if not FORMA.match(codigo):
        return Emision(juez, nodo.lineno, llamada, codigo,
                       f"`{codigo}` no tiene forma de código (`{FORMA.pattern}`)")
    return Emision(juez, nodo.lineno, llamada, codigo)


def emisiones() -> list[Emision]:
    salida: list[Emision] = []
    for archivo in sorted(JUECES.glob("j*.py")):
        salida += emisiones_de(archivo.read_text(encoding="utf-8"), archivo.stem)
    return salida


def codigos_emitidos() -> dict[str, set[str]]:
    """codigo -> conjunto de jueces que lo EMITEN (con `bloquea` o `avisa`)."""
    salida: dict[str, set[str]] = {}
    for e in emisiones():
        if e.codigo and e.llamada in EMISORES:
            salida.setdefault(e.codigo, set()).add(e.juez)
    return salida


def codigos_documentados() -> set[str]:
    return {m.group("codigo") for m in EN_TABLA.finditer(REGLAS.read_text(encoding="utf-8"))}


class PruebaTrazabilidad(unittest.TestCase):
    def test_existe_el_catalogo(self):
        self.assertTrue(REGLAS.exists(), "falta REGLAS.md: sin él no hay forma de "
                                         "saber qué documento respalda cada regla")

    def test_toda_emision_es_un_codigo_literal(self):
        """Sin alias, sin `.anota(` directo y con un literal con forma de código."""
        problemas = [f"{e.juez}:{e.linea} {e.problema}" for e in emisiones() if e.problema]
        self.assertEqual([], problemas,
                         "estas emisiones esconden su código o su severidad a esta prueba")

    def test_todo_codigo_emitido_esta_documentado(self):
        documentados = codigos_documentados()
        huerfanos = sorted(f"{e.juez}:{e.linea} {e.codigo}" for e in emisiones()
                           if e.codigo and e.codigo not in documentados)
        self.assertTrue(codigos_emitidos(), "ningún juez emite códigos: el extractor está roto")
        self.assertEqual(
            [], huerfanos,
            f"estos códigos bloquean, avisan o se suprimen sin figurar en REGLAS.md, así "
            f"que nadie puede saber qué documento los respalda: {huerfanos}")

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
            fila = next((linea for linea in texto.splitlines()
                         if linea.startswith(f"| `{codigo}`")), None)
            self.assertIsNotNone(fila, f"{codigo} sin fila en REGLAS.md")
            for corto in {j.split("_")[0] for j in jueces}:
                self.assertIn(f"`{corto}`", fila,
                              f"{codigo} lo emite {corto}, pero su fila en REGLAS.md "
                              f"no lo nombra: {fila}")


class PruebaDelExtractor(unittest.TestCase):
    """El extractor tiene que ver los defectos que dice ver, sobre fuentes sintéticos."""

    def _problemas(self, fuente: str) -> list[str]:
        return [e.problema for e in emisiones_de(fuente, "jXX") if e.problema]

    def test_un_codigo_sin_forma_es_un_problema(self):
        self.assertTrue(self._problemas('def f(r):\n    r.avisa("DOCKER-hc", "", "m", "p")\n'))

    def test_un_alias_es_un_problema(self):
        fuente = ("def f(r, x):\n"
                  "    anota = r.bloquea if x else r.avisa\n"
                  '    anota("G8-8", "", "m", "p")\n')
        self.assertEqual(2, len(self._problemas(fuente)), self._problemas(fuente))

    def test_un_codigo_en_una_variable_es_un_problema(self):
        self.assertTrue(self._problemas('def f(r, regla):\n    r.bloquea(regla, "", "m", "p")\n'))

    def test_anota_directo_es_un_problema(self):
        self.assertTrue(self._problemas('def f(r):\n    r.anota("G8-1", 1, "", "m", "p")\n'))

    def test_un_literal_y_una_constante_valen(self):
        fuente = ('REGLA = "G8-4"\n'
                  "def f(r):\n"
                  '    r.bloquea(REGLA, "", "m", "p")\n'
                  '    r.avisa(regla="SEM-1", archivo="", mensaje="m", manifestacion="p")\n')
        emitidas = emisiones_de(fuente, "jXX")
        self.assertEqual([], [e.problema for e in emitidas if e.problema])
        self.assertEqual({"G8-4", "SEM-1"}, {e.codigo for e in emitidas})


SECCION_SIN_FUENTE = "## Reglas sin fuente escrita"


def severidades_emitidas() -> dict[str, set[str]]:
    """código -> con qué llamadas se emite: `bloquea`, `avisa`."""
    salida: dict[str, set[str]] = {}
    for e in emisiones():
        if e.codigo and e.llamada in EMISORES:
            salida.setdefault(e.codigo, set()).add(e.llamada)
    return salida


def codigos_sin_fuente_escrita() -> set[str]:
    """Los códigos de la tabla «Reglas sin fuente escrita» de REGLAS.md."""
    texto = REGLAS.read_text(encoding="utf-8")
    i = texto.find(SECCION_SIN_FUENTE)
    if i < 0:
        return set()
    resto = texto[i + len(SECCION_SIN_FUENTE):]
    fin = resto.find("\n## ")
    return {m.group("codigo")
            for m in EN_TABLA.finditer(resto if fin < 0 else resto[:fin])}


class PruebaSeveridad(unittest.TestCase):
    """REGLAS.md promete que las reglas sin fuente escrita no bloquean.

    Hasta el 2026-09-05 eso era solo una frase. `NG-1`, `CI-1` y `SEM-1` estaban
    en esa tabla y llamaban a `bloquea()`. Se descubrió al correr el gate sobre
    `coipo_prensa2`, donde 5 de los 6 bloqueantes salían de ahí: el repositorio
    más maduro de la flota, detenido por reglas que el propio catálogo declaraba
    inofensivas. Una promesa que nada ejecuta se rompe sola.
    """

    def test_la_seccion_sin_fuente_existe_y_tiene_reglas(self):
        self.assertTrue(
            codigos_sin_fuente_escrita(),
            f"no se encontró ninguna regla bajo «{SECCION_SIN_FUENTE}» en "
            f"REGLAS.md. O se renombró la sección y esta prueba dejó de mirar "
            f"nada —cero de cero leído como conformidad—, o ya no quedan reglas "
            f"sin fuente y hay que borrar esta prueba a propósito, no dejarla "
            f"pasando en vacío")

    def test_ninguna_regla_sin_fuente_escrita_bloquea(self):
        severidades = severidades_emitidas()
        infractoras = sorted(c for c in codigos_sin_fuente_escrita()
                             if "bloquea" in severidades.get(c, set()))
        self.assertEqual(
            [], infractoras,
            f"REGLAS.md las lista como «sin fuente escrita» y promete que no "
            f"bloquean, pero llaman a bloquea(): {infractoras}. O se les escribe "
            f"la fuente y suben a la tabla de reglas vigentes, o pasan a avisa(). "
            f"Bloquear un despliegue citando un documento que no existe es "
            f"exactamente lo que este catálogo existe para impedir")


if __name__ == "__main__":
    unittest.main(verbosity=2)
