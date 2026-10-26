"""`adopta:` de `.semilla`: tres formas de escribirla, UNA semántica en cuatro jueces.

EL DEFECTO (auditoría del 2026-10-25). `leer_adopcion` sólo leía la línea de la
clave, partiendo por comas y espacios:

  - la lista YAML en bloque (`adopta:` y debajo `  - interfaz`) se leía VACÍA. Es
    el caso real de `coipo_prevension_ministerial/.semilla`: j12 y j13 salían
    SIN_EVALUAR con un mensaje que decía «está VACÍA» de una lista que no lo está;
  - en línea, `[semilla, interfaz]` daba las capas `[semilla` e `interfaz]`, y
    entre comillas, `"semilla"` con comillas: ninguna casaba y el repositorio
    «no adoptaba nada»;
  - y cada juez la interpretaba distinto: j16 no la leía, j14 trataba la vacía
    como «todo» y j12/j13 como SIN_EVALUAR.

LA SEMÁNTICA ÚNICA (comun_semilla.py y REGLAS.md, «Nota sobre el alcance»):

  sin `.semilla`             -> NO_APLICA en j12, j13, j14 y j16.
  `.semilla` sin `adopta:`   -> adopta todo (`semilla` e `interfaz`).
  `adopta:` con una lista    -> exactamente esas capas, en cualquiera de las tres
                                formas. Lo que no adopta su capa: j12/j13 NO_APLICA
                                y j14/j16 AVISAN; en los cuatro, contado como
                                supresión cuando apaga algo que regiría.
  `adopta:` vacía            -> error de declaración: los cuatro lo anotan en
                                `no_evaluado` y no dictaminan (SIN_EVALUAR).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import RepoSintetico, hay_git  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j12_semilla as j12  # noqa: E402
import j13_interfaz as j13  # noqa: E402
import j14_construccion as j14  # noqa: E402
import j16_codigo as j16  # noqa: E402
from comun import leer_adopcion  # noqa: E402

AMBAS = frozenset({"semilla", "interfaz"})

FORMAS_AMBAS = {
    "línea": "adopta: semilla, interfaz\n",
    "línea sin coma": "adopta: semilla interfaz\n",
    "flujo": "adopta: [semilla, interfaz]\n",
    "flujo con comillas": "adopta: [\"semilla\", 'interfaz']  # comentario\n",
    "entre comillas": "adopta: \"semilla, interfaz\"\n",
    "bloque": "adopta:\n  - semilla\n  - interfaz\n",
    "bloque sin sangría y con comentario": "adopta:\n# la capa de la semilla\n- semilla   # sembrada\n- 'interfaz'\n",
}
FORMAS_VACIAS = {
    "sin nada": "adopta:\n",
    "flujo vacío": "adopta: []\n",
    "comillas vacías": "adopta: \"\"\n",
    "sólo coma": "adopta: ,\n",
}


class PruebaLectura(unittest.TestCase):

    def test_las_tres_formas_dan_las_mismas_capas(self):
        for nombre, adopta in FORMAS_AMBAS.items():
            with self.subTest(forma=nombre):
                a = leer_adopcion("version: 2026-10-25\n" + adopta + "gerencia: 1_SECOM\n")
                self.assertEqual(AMBAS, a.declarado)
                self.assertFalse(a.vacia)
                self.assertEqual(2, a.numero)

    def test_las_vacias_son_vacias(self):
        for nombre, adopta in FORMAS_VACIAS.items():
            with self.subTest(forma=nombre):
                a = leer_adopcion("version: 2026-10-25\n" + adopta)
                self.assertTrue(a.vacia, a.declarado)

    def test_la_lista_en_bloque_se_corta_en_la_siguiente_clave(self):
        a = leer_adopcion("adopta:\n  - interfaz\ngerencia: 1_SECOM\n  - semilla\n")
        self.assertEqual(frozenset({"interfaz"}), a.declarado)

    def test_ausente_y_comentada_adoptan_todo(self):
        for texto in ("version: 2026-10-25\n", "# adopta: interfaz\nversion: 2026-10-25\n"):
            with self.subTest(texto=texto):
                a = leer_adopcion(texto)
                self.assertIsNone(a.declarado)
                self.assertTrue(a.adopta("semilla") and a.adopta("interfaz"))

    def test_la_cita_de_una_lista_en_bloque_no_dice_vacia(self):
        cita = leer_adopcion("adopta:\n  - interfaz\n").cita()
        self.assertIn("interfaz", cita)
        self.assertNotIn("VAC", cita.upper())


# Un repositorio sembrado DESPUÉS de las dos vigencias (j14: 2026-10-20, j16:
# 2026-10-24), con defectos que cada juez sabe ver: un archivo de 1200 líneas,
# sin `docs/CONSTRUCCION.md`, un CSS que incumple y una pieza «congelada» editada.
CSS_MALO = ":root { --v: #064928; }\n.t { color: var(--v); transition: all .2s; }\n.t:focus { outline: 0; }\n"


class PruebaCuatroJueces(unittest.TestCase):

    def setUp(self):
        if not hay_git():
            self.fail("falta `git` en el PATH: esta prueba lo necesita de verdad")

    def _repo(self, adopta: str) -> RepoSintetico:
        repo = RepoSintetico(j16)
        self.addCleanup(repo.cierra)
        repo.escribe(".semilla", "version: 2026-10-25\nfabrica: 2026-10-25\n" + adopta)
        repo.escribe("src/grande.py", "x = 1\n" * 1200)
        repo.escribe("src/estilos.css", CSS_MALO)
        repo.escribe("frontend/nginx.conf", "server {\n    listen 1;\n}\n")
        return repo

    def _juzga(self, repo: RepoSintetico, modulo):
        repo.modulo = modulo
        return repo.juzga()

    def test_solo_interfaz_en_las_tres_formas_dice_lo_mismo_en_los_cuatro(self):
        formas = {"línea": "adopta: interfaz\n", "flujo": "adopta: [interfaz]\n",
                  "comillas": "adopta: \"interfaz\"\n", "bloque": "adopta:\n  - interfaz\n"}
        for nombre, adopta in formas.items():
            with self.subTest(forma=nombre):
                repo = self._repo(adopta)
                r12, r13 = self._juzga(repo, j12), self._juzga(repo, j13)
                r14, r16 = self._juzga(repo, j14), self._juzga(repo, j16)
                self.assertEqual("NO_APLICA", r12.veredicto, r12.no_evaluado)
                self.assertEqual(1, len(r12.supresiones))
                self.assertEqual("HALLAZGOS", r13.veredicto, r13.no_evaluado)
                for r in (r14, r16):
                    self.assertEqual([], r.bloqueantes, [h.mensaje for h in r.bloqueantes])
                    self.assertTrue(r.hallazgos, "no adopta `semilla`: AVISA, no calla")
                    self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_ambas_en_bloque_bloquea_lo_nuevo(self):
        """La lista en bloque cuenta igual que la de una línea: lo sembrado tras la
        vigencia BLOQUEA en j14 y j16."""
        repo = self._repo("adopta:\n  - semilla\n  - interfaz\n")
        self.assertTrue(self._juzga(repo, j14).bloqueantes)
        self.assertTrue(self._juzga(repo, j16).bloqueantes)

    def test_vacia_es_sin_evaluar_en_los_cuatro_y_lo_dice(self):
        for nombre, adopta in FORMAS_VACIAS.items():
            repo = self._repo(adopta)
            for modulo in (j12, j13, j14, j16):
                with self.subTest(forma=nombre, juez=modulo.__name__):
                    r = self._juzga(repo, modulo)
                    self.assertEqual("SIN_EVALUAR", r.veredicto,
                                     f"{[h.mensaje for h in r.hallazgos]} {r.no_aplica}")
                    self.assertTrue(any("VACÍA" in n for n in r.no_evaluado), r.no_evaluado)
                    self.assertFalse(r.supresiones, "vacía no declara nada que suprimir")


if __name__ == "__main__":
    unittest.main(verbosity=2)
