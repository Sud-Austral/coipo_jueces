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

import os
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

    def _mayores_publicadas(self) -> list[int]:
        """Las mayores `vN` que existen como tag, de mayor a menor.

        El glob es `v[0-9]*` y no `v[0-9]`. La primera versión usaba el segundo, y
        un glob —no una regex— hace que `v[0-9]` case «v» más UN dígito: el día que
        existiera `v10` la prueba no lo habría visto y habría pasado en VERDE con el
        default retrasado. El mismo defecto que esta prueba nació para cerrar, una
        decena más tarde. El `fullmatch` de abajo es el que descarta `v1.0.0`.
        """
        try:
            salida = subprocess.run(
                ["git", "tag", "-l", "v[0-9]*"], cwd=RAIZ,
                capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as e:  # pragma: no cover
            return []
        return sorted((int(x[1:]) for x in salida.split()
                       if re.fullmatch(r"v\d+", x)), reverse=True)

    def test_hay_tags_con_los_que_comprobar(self):
        """En CI, no haber tags NO es una excusa: es el fallo.

        La comprobación de abajo se salta si el clon no tiene tags, y eso es
        correcto en la máquina de alguien. Pero medido el 2026-09-08, el checkout
        de `autotest.yml` era superficial y sin tags, así que se saltaba SIEMPRE y
        sólo allí: el único guardián del valor por defecto no se ejecutaba en el
        único sitio donde la suite corre sola.

        Esta prueba convierte esa condición en un fallo ruidoso cuando corre en
        GitHub Actions. Si vuelve a rojo, el arreglo es `fetch-depth: 0` en el
        checkout, no relajar esto.
        """
        if not os.environ.get("GITHUB_ACTIONS"):
            self.skipTest("fuera de CI: un clon local puede no tener tags")
        self.assertTrue(self._mayores_publicadas(),
                        "el checkout de CI no trae tags, así que la comprobación "
                        "del default se salta. Añade `fetch-depth: 0`.")

    def test_el_default_no_se_queda_en_una_mayor_anterior(self):
        """La comprobación que importa.

        Si existe un tag `v3` y este YAML sigue diciendo `v2`, entonces `@v3`
        ejecutaría el YAML de v3 con los jueces de v2 — el mismo defecto que esta
        prueba nació para cerrar, una mayor más tarde.

        Es «no se quedó atrás» y NO una igualdad, a propósito. Con igualdad, el
        procedimiento de publicar era imposible de cumplir: para sacar `v3` hay que
        commitear el YAML con `default: v3` ANTES de que el tag exista, y ahí la
        mayor más alta publicada sigue siendo v2. `VERSIONADO.md` manda correr la
        suite antes de tagear, así que la prueba habría bloqueado justo el paso que
        protege, y `main` habría quedado en rojo entre el push y el tag.

        Adelantarse es legítimo. Quedarse atrás es el defecto.
        """
        mayores = self._mayores_publicadas()
        if not mayores:
            self.skipTest("este clon no tiene tags `vN`: nada que comprobar")

        declarada = int(self._defecto()[1:])
        self.assertGreaterEqual(
            declarada, mayores[0],
            f"el default de `ref_jueces` es v{declarada} y ya existe "
            f"v{mayores[0]}: quien use el tag nuevo ejecutaría este YAML con los "
            "jueces de la mayor vieja, sin ningún error")

    def test_los_ejemplos_de_enganche_usan_la_mayor_vigente(self):
        """Los `@vN` de copiar-y-pegar tienen que ser el default, no otro.

        Es la vía por la que un repositorio se engancha al gate: alguien copia el
        bloque del README o de la cabecera del propio reusable. Medido el
        2026-09-08, los dos decían `@v1` mientras la mayor vigente era `v2` — o
        sea que copiarlos enganchaba al motor CONGELADO, sin `j13` y con las
        reglas de interfaz en AVISA. Y funciona: no falla, no avisa, y el
        repositorio cuenta como «con gate» en cualquier recuento sin tenerlo.
        """
        esperado = self._defecto()
        for ruta in (RAIZ / "README.md", VERIFICAR):
            texto = ruta.read_text(encoding="utf-8")
            for cita in re.findall(r"verificar\.yml@(v\d+)", texto):
                self.assertEqual(
                    esperado, cita,
                    f"{ruta.name} ofrece `@{cita}` como ejemplo de enganche y la "
                    f"mayor vigente es `{esperado}`: quien lo copie se engancha "
                    "al motor equivocado")

    def test_el_paso_falla_si_no_hay_referencia(self):
        """Y si por lo que sea la referencia queda vacía, el paso tiene que
        MORIR, no continuar con un valor inventado. Un gate que no sabe qué
        código está ejecutando no verifica nada — y esto ya salvó una vez, el
        2026-09-08, cuando `job_workflow_ref` llegó vacío."""
        self.assertIn("No se pudo determinar", self.texto)
        self.assertIn("exit 1", self.texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
