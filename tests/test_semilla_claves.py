"""Un solo lector para las claves de `.semilla`: `adopta:`, `fabrica:`, `maqueta:` y `ajeno:`.

Hasta el 2026-11-21 cada clave tenía su expresión: `adopta:` y `fabrica:` aceptaban
sangría, `maqueta:` y `ajeno:` no; `adopta:` leía la lista YAML en bloque y `ajeno:` la
leía VACÍA —una carpeta declarada ajena se medía igual, sin aviso—, y `maqueta:` se
quedaba con las comillas del valor. Ahora las cuatro pasan por `leer_clave()`.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
from comun_semilla import leer_adopcion, leer_ajeno, leer_clave, leer_fabrica, leer_maqueta  # noqa: E402


class PruebaAjeno(unittest.TestCase):
    def test_lista_en_bloque(self):
        texto = (
            "version: 1\najeno:\n  - vendor/visor\n  - frontend/public/libs/  # copiada\nfin: x\n"
        )
        self.assertEqual(["vendor/visor/", "frontend/public/libs/"], leer_ajeno(texto))

    def test_en_linea_y_en_flujo(self):
        self.assertEqual(["a/", "b/"], leer_ajeno("ajeno: a/, b\n"))
        self.assertEqual(["a/", "b/"], leer_ajeno("ajeno: [a/, 'b']\n"))

    def test_con_sangria(self):
        self.assertEqual(["vendor/"], leer_ajeno("  ajeno: vendor/\n"))

    def test_comentada_no_declara(self):
        self.assertEqual([], leer_ajeno("# ajeno: vendor/\n"))

    def test_la_raiz_no_se_puede_declarar_ajena(self):
        self.assertEqual([], leer_ajeno("ajeno: /, ./\n"))


class PruebaMaqueta(unittest.TestCase):
    def test_con_sangria(self):
        self.assertEqual(
            (2, "origen@abc123"), leer_maqueta("version: 1\n  maqueta: origen@abc123\n")
        )

    def test_sin_comillas_ni_comentario(self):
        self.assertEqual(
            (1, "origen@abc123"),
            leer_maqueta('maqueta: "origen@abc123"  # validada el 2026-11-12\n'),
        )

    def test_vacia_o_comentada_no_declara(self):
        self.assertIsNone(leer_maqueta("maqueta:\n"))
        self.assertIsNone(leer_maqueta("# maqueta: origen@abc\n"))


class PruebaFabrica(unittest.TestCase):
    def test_formas(self):
        self.assertEqual("2026-10-24", leer_fabrica("fabrica: 2026-10-24\n"))
        self.assertEqual("2026-10-24", leer_fabrica("  fabrica: 2026-10-24  # sembrado\n"))
        self.assertEqual("2026-10-24", leer_fabrica("fabrica: '2026-10-24'\n"))
        self.assertIsNone(leer_fabrica("# fabrica: 2026-10-24\n"))
        self.assertIsNone(leer_fabrica("fabrica: pronto\n"))

    def test_el_mes_y_el_dia_van_con_dos_cifras(self):
        """`fabrica:` se compara con las vigencias como CADENA, y eso sólo ordena bien con
        `AAAA-MM-DD`: `2026-11-3` quedaría DESPUÉS de `2026-11-22`. Por eso una fecha con el
        mes o el día de una sola cifra no se lee como fecha. Aflojar la expresión a una o
        dos cifras no rompía ninguna prueba (mutación del 2026-11-24)."""
        for texto in ("fabrica: 2026-11-3\n", "fabrica: 2026-1-22\n", "fabrica: 26-11-22\n"):
            with self.subTest(texto=texto):
                self.assertIsNone(leer_fabrica(texto))


class PruebaLeerClave(unittest.TestCase):
    def test_la_misma_lectura_para_adopta(self):
        """`adopta:` sigue leyéndose igual: en línea, en flujo y en bloque."""
        texto = "version: 1\nadopta:\n  - semilla\n  - interfaz\n"
        clave = leer_clave(texto, "adopta")
        self.assertEqual((2, 4), (clave.numero, clave.hasta))
        self.assertEqual(("semilla", "interfaz"), clave.items)
        self.assertEqual(frozenset({"semilla", "interfaz"}), leer_adopcion(texto).declarado)

    def test_una_clave_que_empieza_igual_no_es_la_clave(self):
        self.assertIsNone(leer_clave("ajenos: x/\n", "ajeno"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
