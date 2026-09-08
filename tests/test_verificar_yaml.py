"""El `ref_jueces` por defecto no puede quedarse en una mayor anterior.

EL DEFECTO QUE ESTA PRUEBA EXISTE PARA IMPEDIR, medido el 2026-09-08.

`verificar.yml` hace DOS checkouts: el del repositorio que se verifica y el del
código de los jueces. El segundo usa el input `ref_jueces`, cuyo valor por
defecto era `v1` — un tag móvil. Consecuencia: el `uses:@<sha>` de una aplicación
congelaba **el YAML** y no **el código**. `coipo_prensa2` fijaba un SHA creyendo
que fijaba los jueces, y su propio comentario decía que compraba estabilidad de
calibración. No la compraba.

Al publicar `v2` habría sido peor: quien pusiera `@v2` en su `uses:` habría
ejecutado el YAML de v2 con los jueces de v1, en silencio y sin ninguna señal.

SE INTENTÓ DEDUCIRLO DEL CONTEXTO Y NO SE PUEDE. `github.job_workflow_ref` llega
**vacío** en los pasos de un workflow reusable —existe en las reclamaciones del
token OIDC, no en el contexto que ve `run:`—, comprobado en una ejecución real.

Así que el valor por defecto vuelve a ser literal, y esta prueba es lo que impide
que se pudra: el día que se publique `v3` y alguien olvide esta línea, la suite
falla antes del tag. Un valor por defecto que hay que acordarse de subir sin nada
que lo compruebe es la misma clase de deuda que este repositorio existe para
cerrar.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VERIFICAR = RAIZ / ".github" / "workflows" / "verificar.yml"

# `ref_jueces:` … `default: <algo>` dentro de su bloque.
DEFECTO = re.compile(
    r"ref_jueces:.*?^\s*default:\s*(?P<valor>\S+)", re.DOTALL | re.MULTILINE)


class PruebaRefPorDefecto(unittest.TestCase):

    def setUp(self):
        self.texto = VERIFICAR.read_text(encoding="utf-8")

    def _defecto(self) -> str:
        m = DEFECTO.search(self.texto)
        self.assertIsNotNone(m, "no se encontró el default de `ref_jueces`")
        return m.group("valor").strip("'\"")

    def test_el_default_es_una_mayor(self):
        """No un SHA ni una rama: `vN`. Un SHA fijo dejaría a toda la flota
        congelada en un commit sin que nadie lo decidiera."""
        self.assertRegex(self._defecto(), r"^v\d+$",
                         "el default de ref_jueces tiene que ser una mayor `vN`")

    def test_el_default_es_la_mayor_mas_alta_que_existe(self):
        """La comprobación que importa.

        Si hay un tag `v3` y este YAML sigue diciendo `v2`, entonces `@v3`
        ejecutaría el YAML de v3 con los jueces de v2. Es el mismo defecto que
        esta prueba nació para cerrar, una mayor más tarde.

        Se leen los tags LOCALES. Si no hay ninguno —un clon sin tags, que es lo
        normal en un runner con `fetch-depth: 1`— la prueba se salta en vez de
        fallar: no puede distinguir «está mal» de «no hay con qué comprobarlo», y
        cero comprobaciones no es conformidad.
        """
        try:
            salida = subprocess.run(
                ["git", "tag", "-l", "v[0-9]"], cwd=RAIZ,
                capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as e:  # pragma: no cover
            self.skipTest(f"no se pudo listar los tags: {e}")

        mayores = sorted(
            (int(t[1:]) for t in salida.split() if re.fullmatch(r"v\d+", t)),
            reverse=True)
        if not mayores:
            self.skipTest("este clon no tiene tags `vN`: nada que comprobar")

        self.assertEqual(f"v{mayores[0]}", self._defecto(),
                         "el default de `ref_jueces` se quedó en una mayor "
                         "anterior: quien use el tag nuevo ejecutaría este YAML "
                         "con los jueces de la mayor vieja")

    def test_el_paso_falla_si_no_hay_referencia(self):
        """Y si por lo que sea la referencia queda vacía, el paso tiene que
        MORIR, no continuar con un valor inventado. Un gate que no sabe qué
        código está ejecutando no verifica nada — y esto ya salvó una vez, el
        2026-09-08, cuando `job_workflow_ref` llegó vacío."""
        self.assertIn("No se pudo determinar", self.texto)
        self.assertIn("exit 1", self.texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
