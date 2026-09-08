"""Pruebas de j12 — las piezas congeladas de la semilla no se editan.

La prueba que más importa de este archivo es
`test_un_repo_que_no_se_sembro_no_se_juzga`. La primera versión de este juez
comparaba por RUTA, sin exigir declaración, y puso rojos a cuatro repositorios
de la flota por tener su propio `backend/Dockerfile` y su propio
`frontend/nginx.conf`. **Ninguno se sembró jamás con esta semilla.**

Es la misma lección que ya costó una vez aquí al intentar deducir las
capacidades de un repositorio leyendo su código: hay cosas que hay que declarar.
"""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j12_semilla as j12  # noqa: E402

CONGELADO = "frontend/nginx.conf"
CONTENIDO = "server {\n    listen 8000;\n}\n"


def huella(texto: str) -> str:
    return hashlib.sha256(texto.replace("\r\n", "\n").encode("utf-8")).hexdigest()


class PruebaSemilla(CasoConRepo):
    MODULO = j12

    def setUp(self):
        super().setUp()
        # Un lock sintético, sin tocar el real. El repositorio es público: no se
        # copia nada de un repositorio privado de CONAF, ni siquiera un hash.
        self.lock = Path(self.repo.dir) / "semilla.lock.prueba"
        self.lock.write_text(f"{huella(CONTENIDO)}  {CONGELADO}\n", encoding="utf-8")
        self._real, j12.LOCK = j12.LOCK, self.lock
        self.addCleanup(lambda: setattr(j12, "LOCK", self._real))

    def _sembrado(self, contenido: str = CONTENIDO):
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe(CONGELADO, contenido)

    def test_intacto_no_bloquea(self):
        self._sembrado()
        self.assertSinBloqueos()

    def test_editado_bloquea(self):
        self._sembrado(CONTENIDO + "# un cambio inocente de una app con prisa\n")
        self.assertBloquea("pieza CONGELADA de la semilla y está editada")

    def test_un_repo_que_no_se_sembro_no_se_juzga(self):
        """El falso positivo que puso rojos a cuatro repositorios de la flota.

        Este repositorio tiene un `frontend/nginx.conf` que NO viene de la
        semilla: se llama igual porque toda aplicación web tiene uno.
        """
        self.repo.escribe(CONGELADO, "server { listen 9999; }\n")   # sin `.semilla`
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertEqual("NO_APLICA", r.veredicto)

    def test_el_fin_de_linea_no_es_una_diferencia(self):
        """293 archivos de `coipo_prensa2` tienen CRLF en el árbol de trabajo.

        Un juez que fallara por eso pondría rojo medio Windows por un motivo que
        no tiene nada que ver con el contenido, y se suprimiría en una semana.
        """
        self._sembrado(CONTENIDO.replace("\n", "\r\n"))
        self.assertSinBloqueos()

    def test_que_falte_una_pieza_no_es_un_hallazgo(self):
        """No toda aplicación sembrada usa todas las piezas."""
        self.repo.escribe(".semilla", "version: 2026-09-05\n")
        self.repo.escribe("README.md", "# sin frontend\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos)

    def test_supresion_con_motivo(self):
        self._sembrado("# coipo-jueces:ignorar(SEM-1) cabecera exigida por seguridad\n"
                       + CONTENIDO)
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_sin_lock_no_se_declara_conforme(self):
        """Un juez cuyo catálogo no está no aprueba: se declara incapaz de mirar."""
        self._sembrado()
        self.lock.unlink()
        r = self.repo.juzga()
        self.assertEqual([], r.comprobado)
        self.assertTrue(r.no_evaluado, "tiene que decir que no pudo evaluar")
        self.assertEqual("SIN_EVALUAR", r.veredicto)


class PruebaAdopcion(PruebaSemilla):
    """La clave `adopta:` de `.semilla`, en las dos direcciones.

    Estas pruebas se escribieron porque al implementar `adopta:` NINGUNA de las
    existentes se rompió. Cero pruebas rotas es cero cobertura: se podía
    implementar la clave entera, romperla, y la suite salía verde con sus 137.
    Es el mismo patrón que `comun.py` denuncia —cero hallazgos con cero
    comprobaciones no es conformidad— aplicado a la propia suite.
    """

    def _con_adopta(self, valor, contenido=CONTENIDO):
        self.repo.escribe(".semilla", "version: 2026-09-05\nadopta: " + valor + "\n")
        self.repo.escribe(CONGELADO, contenido)

    def test_sin_clave_adopta_se_juzga_todo(self):
        """La retrocompatibilidad, fijada como contrato y no como accidente.

        Los `.semilla` que `sembrar.py` escribió antes de existir esta clave no
        la llevan. Que la ausencia signifique «adopta todo» es lo que hace que
        ningún veredicto de la flota cambie al desplegar esto.
        """
        self._sembrado(CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_sin_semilla_es_no_aplica_y_dice_por_que(self):
        """Y la razón tiene que NOMBRAR la línea que la produjo.

        Un `no_aplica` autodeclarado que no se puede leer es indistinguible de
        uno honesto. La pieza congelada está EDITADA a propósito: sin la clave
        esto sería un bloqueante.
        """
        self._con_adopta("interfaz", CONTENIDO + "# editado\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.hallazgos)
        self.assertTrue(r.no_aplica, "tiene que decir por qué")
        self.assertIn(".semilla:2", r.no_aplica[0])
        self.assertIn("adopta: interfaz", r.no_aplica[0])

    def test_adopta_sin_semilla_se_cuenta_como_supresion(self):
        """Se paga. Es la única vía por la que un repositorio se apaga un juez a
        sí mismo, y `comun.py` explica por qué esa puerta no puede salir gratis:
        sale con `::warning::` y exige su fila en DEUDA.md."""
        self._con_adopta("interfaz", CONTENIDO + "# editado\n")
        r = self.repo.juzga()
        self.assertEqual(1, len(r.supresiones), r.supresiones)

    def test_adopta_con_semilla_sigue_bloqueando(self):
        """Declararlo explícitamente no relaja nada."""
        self._con_adopta("semilla, interfaz", CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_comentado_no_declara_nada(self):
        """El peor caso posible si el patrón se copiara mal.

        Un `# adopta: interfaz` dentro de un comentario que apagara j12 sería una
        puerta trasera invisible en un diff. La expresión exige que la clave
        empiece la línea tras espacios, y `#` no es espacio en blanco.
        """
        self.repo.escribe(".semilla", "# adopta: interfaz\nversion: 2026-09-05\n")
        self.repo.escribe(CONGELADO, CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_en_mayusculas_y_sin_espacio(self):
        """`adopta:SEMILLA` cuenta igual: nadie debería perder o ganar un juez
        por un espacio o una mayúscula."""
        self.repo.escribe(".semilla", "version: 2026-09-05\nadopta:SEMILLA\n")
        self.repo.escribe(CONGELADO, CONTENIDO + "# editado\n")
        self.assertBloquea("pieza CONGELADA")

    def test_adopta_desconocido_no_apaga_este_juez_en_silencio(self):
        """Un typo —`adopta: semila`— no puede apagar el juez sin decirlo.

        Sale NO_APLICA, que es lo correcto porque la lista no incluye la capa,
        pero la razón cita la línea literal: quien lea el resumen ve el typo.
        """
        self._con_adopta("semila", CONTENIDO + "# editado\n")
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertIn("semila", r.no_aplica[0])
        self.assertEqual(1, len(r.supresiones), "y se cuenta, no sale gratis")


if __name__ == "__main__":
    unittest.main(verbosity=2)
