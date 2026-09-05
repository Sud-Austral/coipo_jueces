"""Pruebas de j09 — secretos en el árbol versionado.

FIXTURES SINTÉTICOS, SIEMPRE. `coipo_jueces` es un repositorio PÚBLICO: un
fixture "tomado de COIPO_ENTREGA_PLANTA" publicaría código privado de CONAF en
internet, que es exactamente el tipo de fuga por conveniencia que estos jueces
existen para evitar. Todo lo de aquí abajo está escrito a mano y no reproduce
ningún archivo real.

Los secretos de mentira que aparecen en este archivo son eso: de mentira. Son
hexadecimal generado en el momento de escribir la prueba, y el propio j09 no
los mira porque `tests/` casa con ES_PRUEBA.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))

import j09_secretos as j09  # noqa: E402
from comun import Repo, Resultado, suprimido  # noqa: E402

# 64 caracteres hexadecimales. No abre nada: es literalmente el sha256 de la
# cadena "fixture sintetico de coipo_jueces, no es un secreto".
HEX_FALSO = "3f1b8c2e9a47d05e6b83f2c1a09d47be15c3082fa6d94e7b1c250af38d69e4a7"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, encoding="utf-8", errors="replace")


class RepoSintetico:
    """Un repositorio git de verdad, en un directorio temporal.

    Se usa git de verdad y no un doble porque la regla que se está probando ES
    "qué devuelve `git ls-files`". Un doble que devolviera una lista de rutas
    probaría el filtro, no el comportamiento, y el fallo que importa —un `.env`
    trackeado pese al .gitignore— solo existe dentro de git.
    """

    def __init__(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="coipo_jueces_"))
        _git(self.dir, "init", "-q")
        _git(self.dir, "config", "user.email", "prueba@ejemplo.invalid")
        _git(self.dir, "config", "user.name", "prueba")

    def escribe(self, ruta: str, contenido: str, *, versionar: bool = True) -> None:
        p = self.dir / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")
        if versionar:
            _git(self.dir, "add", "-f", ruta)

    def juzga(self) -> Resultado:
        r = Resultado(juez="j09", descripcion="prueba")
        j09.comprobar(Repo(self.dir), r)
        return r

    def cierra(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class PruebaHeuristica(unittest.TestCase):
    """`parece_secreto` en aislamiento. Es donde vive el riesgo de ruido."""

    def test_hex_largo_en_clave_secreta_es_secreto(self):
        self.assertTrue(j09.parece_secreto("JWT_SECRET", HEX_FALSO, en_env=True))
        self.assertTrue(j09.parece_secreto("JWT_SECRET", HEX_FALSO, en_env=False))

    def test_formato_versionado_del_hmac_es_secreto(self):
        valor = "v1:" + "QUFCQkNDRERFRUZGR0dISElJSktLTExNTU5OT08"
        self.assertTrue(j09.parece_secreto("RUT_HMAC_SECRETS", valor, en_env=True))

    def test_placeholder_no_es_secreto(self):
        for v in ("change_this_password", "<generar: openssl rand -hex 32>",
                  "tu_clave_aqui", "xxxxxxxxxxxx", "REEMPLAZAR"):
            with self.subTest(v=v):
                self.assertFalse(j09.parece_secreto("JWT_SECRET", v, en_env=True))

    def test_valor_falso_declarado_en_espanol_no_es_secreto(self):
        """El caso real que hacía rojo al CI del IAM y al .env.dev.example de EP.

        Los dos repos marcan sus valores de mentira en español, con un
        comentario al lado que lo dice. Un juez que no entiende eso convierte
        buena práctica en incidente.
        """
        for v in ("t0-gate-jwt-secret-jamas-usar-en-produccion",
                  "dev-secret-no-usar-en-produccion",
                  "local-nunca-en-produccion"):
            with self.subTest(v=v):
                self.assertFalse(j09.parece_secreto("SESSION_SECRET", v, en_env=True))

    def test_expresion_de_codigo_no_es_valor(self):
        """`token = jwt.encode(...)` y `_VARIABLES_SECRETAS = (` no son valores.

        Dejar pasar expresiones es lo que produjo 68 hallazgos falsos sobre
        COIPO_USUARIOS en la primera versión de este juez.
        """
        for v in ("jwt.encode(payload", "(", "os.environ[", "getenv('X')"):
            with self.subTest(v=v):
                self.assertFalse(j09.parece_secreto("JWT_SECRET", v, en_env=True))

    def test_referencia_a_variable_no_es_secreto(self):
        self.assertFalse(j09.parece_secreto("JWT_SECRET", "${JWT_SECRET:?falta}", en_env=True))

    def test_sufijo_inocente_desactiva_la_clave(self):
        for clave in ("JWT_ALGORITHM", "RUT_KEY_VERSION", "SMTP_PASSWORD_FILE",
                      "SESSION_MAX_AGE_SECONDS"):
            with self.subTest(clave=clave):
                self.assertFalse(j09.parece_secreto(clave, HEX_FALSO[:40], en_env=True))

    def test_clave_no_secreta_nunca_dispara(self):
        """El sesgo del juez: sin clave secreta no hay hallazgo, pase lo que pase.

        Es lo que impide que un sha256 en un lock, un identificador largo o una
        clase CSS entren como "secreto".
        """
        self.assertFalse(j09.parece_secreto("commit_sha", HEX_FALSO, en_env=False))
        self.assertFalse(j09.parece_secreto("event_type", HEX_FALSO, en_env=False))

    def test_en_codigo_hace_falta_que_parezca_generado(self):
        """En un .env basta un valor real; en código hace falta más.

        Una contraseña corta escrita en un módulo puede ser un ejemplo de la
        documentación; una cadena de 64 hex no lo es nunca.
        """
        self.assertTrue(j09.parece_secreto("DATABASE_PASSWORD", "Zx9kLm2Qp", en_env=True))
        self.assertFalse(j09.parece_secreto("DATABASE_PASSWORD", "Zx9kLm2Qp", en_env=False))

    def test_entropia(self):
        self.assertAlmostEqual(j09.entropia(""), 0.0)
        self.assertAlmostEqual(j09.entropia("aaaaaaaa"), 0.0)
        self.assertGreater(j09.entropia(HEX_FALSO), 3.5)


class PruebaDsn(unittest.TestCase):
    def _hallazgos(self, linea: str) -> list:
        repo = RepoSintetico()
        try:
            repo.escribe("app/config.py", linea + "\n")
            return repo.juzga().bloqueantes
        finally:
            repo.cierra()

    def test_credencial_real_en_dsn_bloquea(self):
        h = self._hallazgos('URL = "postgresql://coipo_admin:Zk28vQr91xTn@db:5432/app"')
        self.assertEqual(len(h), 1)
        self.assertIn("URL de conexión", h[0].mensaje)

    def test_fstring_de_las_cinco_variables_no_bloquea(self):
        """El patrón que D-06 EXIGE no puede ser un hallazgo.

        Marcarlo era señalar como incidente la única forma correcta de componer
        la URL, que es justo lo que enseña a la gente a suprimir al juez.
        """
        self.assertEqual(
            self._hallazgos(
                'URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}'
                '@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"'
            ), [])

    def test_ejemplo_de_documentacion_no_bloquea(self):
        self.assertEqual(
            self._hallazgos("# postgresql+psycopg2://coipo:coipo@localhost:5432/dev"), [])

    def test_usuario_igual_a_clave_no_bloquea(self):
        self.assertEqual(
            self._hallazgos('URL = "postgresql://demo:demo@servidor:5432/app"'), [])


class PruebaArchivosDeEntorno(unittest.TestCase):
    def setUp(self):
        self.repo = RepoSintetico()
        self.addCleanup(self.repo.cierra)

    def test_env_versionado_bloquea(self):
        self.repo.escribe(".env", f"JWT_SECRET={HEX_FALSO}\n")
        h = self.repo.juzga().bloqueantes
        self.assertEqual(len(h), 2)  # el archivo versionado + el valor
        self.assertTrue(any("versionado en git" in x.mensaje for x in h))

    def test_gitignore_no_salva_a_un_archivo_ya_trackeado(self):
        """El corazón del incidente de COIPO_USUARIOS.

        Su .gitignore SÍ lista `.env`, y el archivo lleva versionado desde
        abril: un archivo ya trackeado ignora el .gitignore. Un juez que mirase
        el .gitignore en vez de `git ls-files` daría verde sobre el peor caso
        real de la flota.
        """
        self.repo.escribe(".gitignore", "/.env\n", versionar=True)
        self.repo.escribe(".env", f"JWT_SECRET={HEX_FALSO}\n", versionar=True)
        self.assertTrue(self.repo.juzga().bloqueantes)

    def test_env_example_con_placeholders_es_verde(self):
        self.repo.escribe(".gitignore", "/.env\n")
        self.repo.escribe(
            ".env.example",
            "DATABASE_PASSWORD=<generar: openssl rand -hex 32>\n"
            "JWT_SECRET=<generar: openssl rand -hex 32>\n"
            "APP_PORT=8104\n",
        )
        r = self.repo.juzga()
        self.assertEqual(r.bloqueantes, [], [h.mensaje for h in r.hallazgos])

    def test_env_example_con_secreto_real_dentro_si_bloquea(self):
        """Estar en la allowlist exime de "no versionar .env", no del escaneo.

        Es la forma más habitual de filtrar un secreto: pegarlo en el ejemplo
        "solo para probar" y olvidarlo.
        """
        self.repo.escribe(".env.example", f"JWT_SECRET={HEX_FALSO}\n")
        self.assertTrue(self.repo.juzga().bloqueantes)

    def test_env_de_vite_versionado_es_legitimo(self):
        self.repo.escribe(".gitignore", "/.env\n")
        self.repo.escribe("frontend/.env.production", "VITE_API_BASE_URL=\n")
        self.assertEqual(self.repo.juzga().bloqueantes, [])

    def test_gitignore_sin_anclar_avisa(self):
        self.repo.escribe(".gitignore", ".env\n")
        self.repo.escribe("README.md", "# x\n")
        avisos = [h for h in self.repo.juzga().hallazgos if h not in self.repo.juzga().bloqueantes]
        self.assertTrue(any("sin barra inicial" in h.mensaje for h in avisos))


class PruebaFixturesDePrueba(unittest.TestCase):
    def setUp(self):
        self.repo = RepoSintetico()
        self.addCleanup(self.repo.cierra)

    def test_credencial_falsa_en_un_test_no_bloquea(self):
        self.repo.escribe("tests/test_login.py",
                          'def test_x():\n    password = "Zk28vQr91xTn"\n')
        self.assertEqual(self.repo.juzga().bloqueantes, [])

    def test_clave_privada_en_un_test_si_bloquea(self):
        """Los fixtures pueden llevar contraseñas de mentira; nunca una clave.

        Una clave privada es material criptográfico real aunque quien la
        commiteó dijera que era "solo para el test".
        """
        self.repo.escribe("tests/fixtures/id_rsa",
                          "-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----\n")
        self.assertTrue(self.repo.juzga().bloqueantes)


class PruebaSupresion(unittest.TestCase):
    def test_marcador_con_motivo_suprime(self):
        lineas = ["JWT_SECRET=abc  # coipo-jueces:ignorar(D-31) fixture del arnés de pruebas"]
        self.assertIsNotNone(suprimido(lineas, 0, "D-31"))

    def test_marcador_sin_motivo_no_suprime(self):
        """Si silenciar cuesta menos que arreglar, se silencia."""
        self.assertIsNone(suprimido(["X=1  # coipo-jueces:ignorar(D-31)"], 0, "D-31"))
        self.assertIsNone(suprimido(["X=1  # coipo-jueces:ignorar(D-31) porque si"], 0, "D-31"))

    def test_marcador_de_otra_regla_no_suprime(self):
        lineas = ["X=1  # coipo-jueces:ignorar(D-08) motivo suficientemente largo"]
        self.assertIsNone(suprimido(lineas, 0, "D-31"))

    def test_marcador_en_la_linea_anterior_suprime(self):
        lineas = ["# coipo-jueces:ignorar(D-31) motivo suficientemente largo", "JWT_SECRET=abc"]
        self.assertIsNotNone(suprimido(lineas, 1, "D-31"))

    def test_la_supresion_se_cuenta_y_se_publica(self):
        """Una supresión invisible es un juez apagado que parece encendido."""
        repo = RepoSintetico()
        try:
            repo.escribe(
                "app/ajustes.py",
                f'JWT_SECRET = "{HEX_FALSO}"  '
                "# coipo-jueces:ignorar(D-31) valor de prueba del arnés\n",
            )
            r = repo.juzga()
            self.assertEqual(r.bloqueantes, [])
            self.assertEqual(len(r.supresiones), 1)
        finally:
            repo.cierra()


class PruebaDelPropioJuez(unittest.TestCase):
    """Tests del test: sin esto, un juez roto pasa por el motivo equivocado."""

    def test_un_repo_sin_git_no_se_declara_limpio(self):
        """"No pude mirar" y "miré y está bien" no son lo mismo.

        Confundirlos es exactamente cómo un control se apaga sin que nadie se
        entere: el job sale verde durante meses porque nunca llegó a evaluar.
        """
        d = Path(tempfile.mkdtemp(prefix="coipo_jueces_sin_git_"))
        try:
            (d / "archivo.txt").write_text("x", encoding="utf-8")
            r = Resultado(juez="j09", descripcion="prueba")
            j09.comprobar(Repo(d), r)
            self.assertEqual(r.hallazgos, [])
            self.assertTrue(r.no_evaluado, "un repo no evaluable debe decirlo")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_el_juez_detecta_lo_que_dice_detectar(self):
        """Se planta la violación y se exige que el verificador la vea.

        Sin esta prueba, borrar el cuerpo de `comprobar_env_versionados` deja la
        suite en verde.
        """
        repo = RepoSintetico()
        try:
            repo.escribe(".env", f"JWT_SECRET={HEX_FALSO}\n")
            self.assertTrue(repo.juzga().bloqueantes,
                            "el juez dejó pasar un .env versionado con un secreto")
        finally:
            repo.cierra()


if __name__ == "__main__":
    if shutil.which("git") is None:
        # Falla con instrucciones; nunca hace skip. Un test saltado es un test
        # que no protege nada, y su estado permanente "verde" es indistinguible
        # de un test que pasa.
        raise SystemExit("[j09] falta `git` en el PATH: estas pruebas lo necesitan de verdad")
    unittest.main(verbosity=2)
