"""Pruebas de j08 — `.gitignore` anclado y qué llega al servidor (puntos 8 y 10).

Fixtures SINTÉTICOS: este repositorio es público, y varias de estas pruebas
tratan justamente sobre archivos con credenciales.

Se usa git de verdad —no un doble— porque el hallazgo que más importa aquí sólo
existe dentro de git: un `.env` que figura en el `.gitignore` y aun así está
versionado, porque `.gitignore` no se aplica a lo que ya está trackeado. Un
doble que devolviera listas de rutas no reproduciría esa asimetría.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j08_rsync as j08  # noqa: E402

GITIGNORE_CORRECTO = "/.env\n/data/\nnode_modules/\n"


class PruebaGitignore(CasoConRepo):
    """Guía 8, punto 8."""

    MODULO = j08

    def test_anclado_no_bloquea(self):
        self.repo.escribe(".gitignore", GITIGNORE_CORRECTO)
        self.repo.escribe("README.md", "# app\n")
        self.assertSinBloqueos()

    def test_data_sin_anclar_bloquea(self):
        """El error que la guía dice que ya ocurrió y hubo que corregir."""
        self.repo.escribe(".gitignore", "/.env\ndata/\n")
        self.repo.escribe("README.md", "# app\n")
        self.assertBloquea("no está anclado con barra inicial")

    def test_el_hallazgo_nombra_el_data_anidado_que_ya_existe(self):
        """Un hallazgo con la ruta concreta se arregla; uno genérico se discute."""
        self.repo.escribe(".gitignore", "/.env\ndata/\n")
        self.repo.escribe("frontend/src/data/comunas.json", "[]\n")
        r = self.repo.juzga()
        manifestaciones = [h.manifestacion for h in r.bloqueantes]
        self.assertTrue(any("frontend/src/data" in m for m in manifestaciones),
                        manifestaciones)

    def test_env_no_ignorado_bloquea(self):
        self.repo.escribe(".gitignore", "node_modules/\n")
        self.repo.escribe("README.md", "# app\n")
        self.assertBloquea("`.env` no está ignorado")

    def test_sin_gitignore_avisa_si_no_despliega(self):
        """La severidad la fija lo que hay en juego, no la regla."""
        self.repo.escribe("README.md", "# solo documentación\n")
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertTrue(any("no hay `.gitignore`" in h.mensaje for h in r.hallazgos))

    def test_sin_gitignore_bloquea_si_hay_compose(self):
        self.repo.escribe("README.md", "# app\n")
        self.repo.escribe("docker-compose.yml", "services:\n  app:\n    image: x\n")
        self.assertBloquea("no hay `.gitignore`")


class PruebaLoQueViaja(CasoConRepo):
    """Guía 8, punto 10 — el rsync está ANCLADO a la raíz."""

    MODULO = j08

    def setUp(self):
        super().setUp()
        self.repo.escribe(".gitignore", GITIGNORE_CORRECTO)

    def test_env_en_subdirectorio_bloquea(self):
        """Desde agosto de 2026 SÍ llega al servidor. Antes no llegaba."""
        self.repo.escribe("frontend/.env", "VITE_TOKEN=x\n")
        self.assertBloquea("es un `.env` en un subdirectorio")

    def test_env_en_la_raiz_bloquea_por_estar_versionado(self):
        """No por llegar al servidor —el rsync lo excluye— sino por estar en git.

        Y el arreglo tiene que decir que hay que ROTAR: `git rm --cached` saca el
        archivo del próximo commit, no del historial ni de los clones que ya
        existen. Un arreglo que se quede en el `git rm` deja el secreto vivo.
        """
        self.repo.escribe(".env", "JWT_SECRET=x\n")
        r = self.repo.juzga()
        self.assertBloquea("`.env` está versionado", r)
        arreglos = [h.arreglo for h in r.bloqueantes]
        self.assertTrue(any("rotar" in a.lower() for a in arreglos), arreglos)

    def test_env_example_nunca_es_hallazgo(self):
        """Es el archivo que la Guía 8 EXIGE en su punto 3."""
        self.repo.escribe(".env.example", "APP_PORT=8080\n")
        self.repo.escribe("frontend/.env.sample", "VITE_API=/api\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_variante_de_vite_avisa_pero_no_bloquea(self):
        """`.env.production` suele llevar configuración de build, no secretos."""
        self.repo.escribe("frontend/.env.production", "VITE_API_URL=/api\n")
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes, [h.mensaje for h in r.bloqueantes])
        self.assertAvisa("viaja al servidor en cada despliegue", r)

    def test_versionado_dentro_de_data_avisa(self):
        """El rsync excluye `/data/`: ese archivo NUNCA existe en el servidor."""
        self.repo.escribe("data/catalogo.xlsx", "no importa\n")
        self.assertAvisa("versionado dentro del `data/` de la raíz")

    def test_data_anidado_no_es_hallazgo(self):
        """`frontend/src/data/` sí se sincroniza: no hay nada que reportar."""
        self.repo.escribe("frontend/src/data/comunas.json", "[]\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])


if __name__ == "__main__":
    unittest.main(verbosity=2)
