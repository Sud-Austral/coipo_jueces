"""Pruebas de j14 — construir con la fábrica: `docs/CONSTRUCCION.md`.

Fixtures SINTÉTICOS: este repositorio es público. El `CONSTRUCCION.md` de abajo
está inventado a mano con la forma de la plantilla de la semilla; los
`correlation_id` no corresponden a ninguna llamada real.

LAS NEGATIVAS VAN PRIMERO, y una por condición de fallo: un juez que sólo se ha
visto en verde no se ha visto funcionar. Después, las fechas límite —2026-10-19
avisa, 2026-10-20 bloquea— y al final el positivo.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j14_construccion as j14  # noqa: E402
from comun import Repo, Resultado  # noqa: E402

VIGENTE = "version: 2026-10-20\nfabrica: 2026-10-20\nadopta: semilla, interfaz\n"
VISPERA = "version: 2026-10-19\nfabrica: 2026-10-19\nadopta: semilla, interfaz\n"
SIN_FECHA = "version: 2026-09-08\nadopta: interfaz\n"

METODOLOGIA = "smb-metodologia-construir-una-aplicacion-coipo-de-prueba"
CORRELACION = "corr-1700000000000-0000abcd"

COMPLETO = f"""# Construcción de esta aplicación con la fábrica

metodologia: {METODOLOGIA}
instancia: conaf
fecha: 2026-10-20

## Objetivos de la metodología aplicados

objetivos:
- 1 Consultar la fábrica antes de escribir: se leyó la metodología y el grafo.

## Consultas: el rastro

consultas:
- 2026-10-20 ver_metodologia {METODOLOGIA} conaf {CORRELACION}
- 2026-10-20 consultar_grafo.py "huerto riego": nada en el grafo

instrumento: no aplica: el encargo no trae formulario ni planilla

registrado: obj-leccion-sintetica-0000 corr-1700000000001-0000beef
"""

PLANTILLA_A_MEDIAS = """# Construcción de esta aplicación con la fábrica

metodologia: [PENDIENTE] sombrero_id de IGNUS
instancia: conaf
fecha: [PENDIENTE] AAAA-MM-DD

objetivos:
- [PENDIENTE] número y nombre

consultas:
- [PENDIENTE] AAAA-MM-DD listar_metodologias conaf corr-…

registrado: [PENDIENTE] objetivo_id
"""


class Base(CasoConRepo):
    MODULO = j14

    def sembrado(self, semilla: str = VIGENTE, construccion: str | None = COMPLETO) -> Resultado:
        self.repo.escribe(".semilla", semilla)
        if construccion is not None:
            self.repo.escribe("docs/CONSTRUCCION.md", construccion)
        return self.repo.juzga()


# ── Negativas: cada condición de fallo, en lo sembrado desde la vigencia ───────

class PruebaNegativas(Base):
    def test_sin_archivo_bloquea(self):
        self.assertBloquea("no existe `docs/CONSTRUCCION.md`", self.sembrado(construccion=None))

    def test_un_pendiente_bloquea_con_su_linea(self):
        r = self.sembrado(construccion=COMPLETO.replace("instancia: conaf", "instancia: [PENDIENTE]"))
        self.assertBloquea("`[PENDIENTE]`", r)
        pendiente = next(h for h in r.bloqueantes if "[PENDIENTE]" in h.mensaje)
        self.assertEqual(4, pendiente.linea)

    def test_un_verificar_tambien_bloquea(self):
        r = self.sembrado(construccion=COMPLETO + "\n- [VERIFICAR] el colector en uat\n")
        self.assertBloquea("`[VERIFICAR]`", r)

    def test_la_plantilla_a_medias_bloquea_una_vez_por_pendiente(self):
        r = self.sembrado(construccion=PLANTILLA_A_MEDIAS)
        pendientes = [h for h in r.bloqueantes if "[PENDIENTE]" in h.mensaje]
        self.assertEqual(5, len(pendientes), [h.linea for h in pendientes])
        self.assertEqual([3, 5, 8, 11, 13], [h.linea for h in pendientes])

    def test_cada_campo_que_falta_bloquea(self):
        # Escritos aquí y no leídos de `j14.CAMPOS`: si el juez dejara de exigir uno,
        # la prueba tiene que ponerse roja, no encogerse con él. Pasó en la mutación.
        for campo in ("metodologia", "instancia", "objetivos", "consultas"):
            with self.subTest(campo=campo):
                self.setUp()
                r = self.sembrado(construccion=COMPLETO.replace(f"{campo}:", f"{campo.upper()}_X ="))
                self.assertBloquea(f"falta el campo `{campo}:`", r)

    def test_sin_metodologia_bloquea(self):
        r = self.sembrado(construccion=COMPLETO.replace(METODOLOGIA, "la de la fábrica"))
        self.assertBloquea("no cita ninguna metodología", r)

    def test_sin_correlation_id_bloquea(self):
        texto = (COMPLETO.replace(CORRELACION, "ok")
                 .replace("corr-1700000000001-0000beef", ""))
        self.assertBloquea("ningún `correlation_id`", self.sembrado(construccion=texto))

    def test_un_correlation_id_con_forma_invalida_no_cuenta(self):
        """`corr-…` de la plantilla, o uno con pocos dígitos, no es rastro."""
        for falso in ("corr-…", "corr-123-abcdef", "corr-1700000000000-xyz", "CORR-1700000000000-0000abcd"):
            with self.subTest(falso=falso):
                self.setUp()
                texto = (COMPLETO.replace(CORRELACION, falso)
                         .replace("corr-1700000000001-0000beef", ""))
                self.assertBloquea("ningún `correlation_id`", self.sembrado(construccion=texto))

    def test_existe_en_el_disco_pero_no_versionado_bloquea(self):
        self.repo.escribe(".semilla", VIGENTE)
        self.repo.escribe("docs/CONSTRUCCION.md", COMPLETO, versionar=False)
        self.assertBloquea("no está versionado")

    def test_texto_basura_bloquea(self):
        self.assertBloquea("falta el campo", self.sembrado(construccion="jkl\x00\x01 ::: {{}}\n"))


# ── Las fechas límite: mira hacia adelante ─────────────────────────────────────

class PruebaFechas(Base):
    def test_sembrado_el_19_solo_avisa(self):
        r = self.sembrado(VISPERA, construccion=None)
        self.assertSinBloqueos(r)
        self.assertAvisa("no existe `docs/CONSTRUCCION.md`", r)
        self.assertAvisa("antes de la regla del 2026-10-20", r)

    def test_sembrado_el_20_bloquea(self):
        self.assertBloquea("con la regla ya vigente desde el 2026-10-20",
                           self.sembrado(VIGENTE, construccion=None))

    def test_la_plantilla_a_medias_del_19_solo_avisa(self):
        r = self.sembrado(VISPERA, construccion=PLANTILLA_A_MEDIAS)
        self.assertSinBloqueos(r)
        self.assertAvisa("`[PENDIENTE]`", r)

    def test_sin_fabrica_solo_avisa(self):
        """Como coipo_prensa2 o coipo_atraso_personal: `.semilla` anterior a la clave."""
        r = self.sembrado(SIN_FECHA, construccion=None)
        self.assertSinBloqueos(r)
        self.assertAvisa("sin `fabrica:`", r)

    def test_fabrica_comentada_no_declara_nada(self):
        r = self.sembrado("# fabrica: 2026-10-25\nadopta: semilla\n", construccion=None)
        self.assertSinBloqueos(r)
        self.assertAvisa("sin `fabrica:`", r)

    def test_vigente_sin_semilla_en_adopta_avisa_y_se_cuenta_como_supresion(self):
        r = self.sembrado("fabrica: 2026-10-25\nadopta: interfaz\n", construccion=None)
        self.assertSinBloqueos(r)
        self.assertAvisa("declara no adoptar `semilla`", r)
        self.assertEqual(1, len(r.supresiones))

    def test_vigente_con_adopta_vacia_bloquea_y_lo_anota(self):
        """Una clave mal escrita —o la lista YAML en varias líneas— no relaja la regla."""
        r = self.sembrado("fabrica: 2026-10-25\nadopta:\n  - interfaz\n", construccion=None)
        self.assertBloquea("no existe `docs/CONSTRUCCION.md`", r)
        self.assertTrue(any("VACÍA" in n for n in r.no_evaluado), r.no_evaluado)


# ── Alcance ────────────────────────────────────────────────────────────────────

class PruebaAlcance(Base):
    def test_sin_semilla_es_no_aplica(self):
        self.repo.escribe("docs/CONSTRUCCION.md", PLANTILLA_A_MEDIAS)
        r = self.repo.juzga()
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertEqual([], r.hallazgos)

    def test_no_corre_en_encuadre_operativo(self):
        self.assertEqual(("aplicacion",), j14.PERFILES)


# ── El positivo ───────────────────────────────────────────────────────────────

class PruebaPositivo(Base):
    def test_completo_sale_ok_y_dice_que_no_miro_ignus(self):
        r = self.sembrado()
        self.assertEqual("OK", r.veredicto, [h.mensaje for h in r.hallazgos])
        self.assertTrue(any("2 `correlation_id`" in c for c in r.comprobado), r.comprobado)
        self.assertTrue(any("IGNUS" in n for n in r.no_evaluado), r.no_evaluado)

    def test_sin_registrado_solo_avisa(self):
        r = self.sembrado(construccion=COMPLETO.replace("registrado:", "cierre:"))
        self.assertSinBloqueos(r)
        self.assertAvisa("`registrado:`", r)

    def test_lee_el_disco_sin_git(self):
        """La prueba de paridad de la fábrica crea la aplicación SIN git."""
        for texto, bloquea in ((COMPLETO, False), (PLANTILLA_A_MEDIAS, True)):
            with self.subTest(bloquea=bloquea):
                tmp = Path(tempfile.mkdtemp(prefix="coipo_jueces_sin_git_"))
                self.addCleanup(shutil.rmtree, tmp, True)
                (tmp / "docs").mkdir()
                (tmp / ".semilla").write_text(VIGENTE, encoding="utf-8")
                (tmp / "docs" / "CONSTRUCCION.md").write_text(texto, encoding="utf-8")
                r = Resultado(juez="j14", descripcion="sin git")
                j14.comprobar(Repo(tmp), r)
                self.assertEqual(bloquea, bool(r.bloqueantes), [h.mensaje for h in r.hallazgos])


if __name__ == "__main__":
    unittest.main(verbosity=2)
