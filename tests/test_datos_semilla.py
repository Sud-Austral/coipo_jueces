"""Los datos que lee `j12` —`semilla.lock` y `semilla.lock.historial`— están enteros.

POR QUÉ SE VIGILA EL DATO Y NO SÓLO EL LECTOR. Los dos archivos los genera
`semilla/sellar.py` de la fábrica y viajan con el tag que consume toda la flota. Sus
lectores tienen dos huecos, medidos el 2026-11-24 con archivos sintéticos:

  - `j12._lock()` salta en silencio una línea que no casa con `ENTRADA` (una huella en
    mayúsculas, de 63 o de 65 caracteres): esa pieza deja de vigilarse, y un lock cortado
    por la mitad se lee como uno más corto. La cabecera `# N archivos.` no se contrasta.
  - el lector del historial salta igual una línea de entrada mal formada. Eso retrasa la
    primera aparición de la pieza, y con ella su vigencia: la misma aplicación pasa de
    BLOQUEA a AVISA sin ninguna nota. Tampoco comprueba el `# N bloques.` ni el orden.

Arreglar los lectores cambia el veredicto de un juez y va con ese cambio. Mientras
tanto, y también después, lo que se publica se comprueba aquí: si un resellado deja una
línea que el lector descartaría, la suite sale roja ANTES del tag.

Y una cosa más que nadie comprobaba: las piezas que `AUD-1` exige (`comun_auditoria`)
tienen que seguir en el lock. Si la semilla renombra una, `AUD-1` bloquearía a toda
siembra nueva por un archivo que ya no existe.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))

import comun_auditoria as aud  # noqa: E402
import historial_semilla as hs  # noqa: E402

LOCK = RAIZ / "semilla.lock"
HISTORIAL = RAIZ / "semilla.lock.historial"

DECLARA_ARCHIVOS = re.compile(r"^#[ \t]*(\d+) archivos\.[ \t]*$", re.MULTILINE)
DECLARA_BLOQUES = re.compile(r"^#[ \t]*(\d+) bloques\.[ \t]*$", re.MULTILINE)


def lineas_de_datos(texto: str) -> list[tuple[int, str]]:
    """(número, línea) de lo que no es un comentario ni una línea en blanco."""
    return [
        (n, linea.strip())
        for n, linea in enumerate(texto.splitlines(), 1)
        if linea.strip() and not linea.strip().startswith("#")
    ]


def descartadas(texto: str) -> list[tuple[int, str]]:
    """Las líneas de datos que el lector NO reconoce como entrada, y por tanto salta."""
    return [(n, linea) for n, linea in lineas_de_datos(texto) if not hs.ENTRADA.match(linea)]


def rutas(texto: str) -> list[str]:
    return [
        m.group("ruta") for _, linea in lineas_de_datos(texto) if (m := hs.ENTRADA.match(linea))
    ]


class PruebaLock(unittest.TestCase):
    def setUp(self):
        self.texto = LOCK.read_text(encoding="utf-8")

    def test_ninguna_linea_se_descarta(self):
        self.assertEqual([], descartadas(self.texto))

    def test_trae_las_piezas_que_declara_y_ninguna_repetida(self):
        m = DECLARA_ARCHIVOS.search(self.texto)
        self.assertIsNotNone(m, "el lock no declara `# N archivos.`: no hay contra qué contar")
        declaradas = int(m.group(1))
        self.assertGreater(declaradas, 0)
        self.assertEqual(declaradas, len(rutas(self.texto)), "entradas leídas frente a declaradas")
        self.assertEqual(declaradas, len(set(rutas(self.texto))), "hay una ruta repetida")

    def test_las_piezas_que_exige_aud1_siguen_selladas(self):
        self.assertTrue(aud.SELLADAS, "`comun_auditoria.SELLADAS` está vacía: no se compara nada")
        faltan = sorted(set(aud.SELLADAS) - set(rutas(self.texto)))
        self.assertEqual(
            [],
            faltan,
            "AUD-1 exige piezas que el lock ya no sella: bloquearía a toda siembra nueva por "
            "un archivo que la semilla ya no trae",
        )


class PruebaHistorial(unittest.TestCase):
    def setUp(self):
        self.texto = HISTORIAL.read_text(encoding="utf-8")
        self.historial = hs.leer(HISTORIAL)

    def test_se_puede_leer(self):
        self.assertIsNotNone(self.historial, "falta `semilla.lock.historial`")
        self.assertTrue(self.historial.fechas)

    def test_ninguna_linea_se_descarta(self):
        self.assertEqual([], descartadas(self.texto))

    def test_trae_los_bloques_que_declara(self):
        m = DECLARA_BLOQUES.search(self.texto)
        self.assertIsNotNone(m, "el historial no declara `# N bloques.`")
        self.assertEqual(int(m.group(1)), len(self.historial.fechas))

    def test_los_bloques_van_del_mas_antiguo_al_mas_nuevo(self):
        """La primera aparición de una pieza se cuenta por POSICIÓN de bloque: un bloque
        fuera de sitio cambia desde cuándo rige una pieza."""
        fechas = list(self.historial.fechas)
        self.assertEqual(sorted(fechas), fechas)


class PruebaDelDetector(unittest.TestCase):
    """El detector tiene que ver lo que el lector saltaría, sobre texto sintético."""

    def test_ve_una_huella_en_mayusculas_y_una_corta(self):
        buena = "a" * 64 + "  backend/Dockerfile"
        texto = "\n".join(
            [
                "# un comentario",
                buena,
                "A" * 64 + "  frontend/nginx.conf",
                "",
                "a" * 63 + "  backend/requirements.txt",
            ]
        )
        self.assertEqual([3, 5], [n for n, _ in descartadas(texto)])
        self.assertEqual(["backend/Dockerfile"], rutas(texto))


if __name__ == "__main__":
    unittest.main(verbosity=2)
