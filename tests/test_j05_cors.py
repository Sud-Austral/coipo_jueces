"""Pruebas de j05 — CORS por dominio (Guía 8, punto 5).

Fixtures SINTÉTICOS: este repositorio es público.

La prueba que más importa de este archivo es `test_sin_cors_es_no_aplica`. Un
juez que tratara «esta app no usa CORS» como un defecto pondría rojos a
`coipo_prensa2` y `COIPO_ENTREGA_PLANTA`, que sirven frontend y API bajo el
MISMO origen y por tanto no necesitan CORS. Ese falso positivo no se arregla
discutiéndolo: se arregla suprimiendo el juez, y a los tres meses el gate está
apagado.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ayuda import CasoConRepo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
import j05_cors as j05  # noqa: E402


def main_con(origenes: str, extra: str = "") -> str:
    return (
        "from fastapi import FastAPI\n"
        "from fastapi.middleware.cors import CORSMiddleware\n"
        "from .config import settings\n"
        "\n"
        "app = FastAPI()\n"
        "app.add_middleware(\n"
        "    CORSMiddleware,\n"
        f"    allow_origins={origenes},\n"
        f"{extra}"
        "    allow_methods=[\"GET\"],\n"
        ")\n"
    )


class PruebaCors(CasoConRepo):
    MODULO = j05

    def test_origenes_desde_la_configuracion_no_bloquea(self):
        """La forma correcta: el valor real vive en el `.env` del servidor."""
        self.repo.escribe("backend/main.py", main_con("settings.cors_origins"))
        self.assertSinBloqueos()

    def test_comodin_bloquea(self):
        self.repo.escribe("backend/main.py", main_con('["*"]'))
        self.assertBloquea("acepta `*`")

    def test_el_mensaje_distingue_si_hay_credenciales(self):
        """`allow_credentials=False` limita el daño, y el hallazgo debe decirlo.

        Si el texto fuera el mismo en los dos casos, quien lo lea no puede saber
        si tiene una fuga de datos autenticados o una molestia de configuración,
        y va a tratar los dos igual: ignorándolos.
        """
        self.repo.escribe("backend/main.py",
                          main_con('["*"]', "    allow_credentials=False,\n"))
        sin = [h.manifestacion for h in self.repo.juzga().bloqueantes]

        otro = CasoConRepo.__new__(type(self))
        self.repo.escribe("backend/main.py",
                          main_con('["*"]', "    allow_credentials=True,\n"))
        con = [h.manifestacion for h in self.repo.juzga().bloqueantes]
        del otro

        self.assertTrue(any("no adjunta la cookie" in m for m in sin), sin)
        self.assertTrue(any("respuestas autenticadas" in m for m in con), con)

    def test_origen_por_ip_bloquea(self):
        """Una IP en allow_origins no casa NUNCA con una petición real."""
        self.repo.escribe("backend/main.py", main_con('["http://172.31.2.41:8111"]'))
        self.assertBloquea("incluye la IP")

    def test_dominio_literal_no_bloquea_por_si_solo(self):
        self.repo.escribe("backend/main.py", main_con('["https://iam.conaf.cl"]'))
        self.assertSinBloqueos()

    def test_variable_inerte_bloquea(self):
        """El defecto peor: la variable existe, se documenta, y no la usa nadie.

        Quien despliegue va a escribir CORS_ORIGINS en el `.env` del servidor y
        va a dar el asunto por cerrado. No pasa nada. Una variable que miente es
        peor que una ausente, porque la ausente se nota.
        """
        self.repo.escribe("backend/main.py", main_con('["https://iam.conaf.cl"]'))
        self.repo.escribe(".env.example", "CORS_ORIGINS=https://iam.conaf.cl\n")
        self.assertBloquea("está cableado en el código")

    def test_sin_cors_es_no_aplica_y_no_un_hallazgo(self):
        self.repo.escribe("backend/main.py",
                          "from fastapi import FastAPI\napp = FastAPI()\n")
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])
        self.assertEqual("NO_APLICA", r.veredicto)
        self.assertTrue(any("mismo origen" in n for n in r.no_aplica), r.no_aplica)

    def test_los_tests_del_repo_juzgado_no_cuentan(self):
        """Un `["*"]` dentro de tests/ es un fixture, no una configuración."""
        self.repo.escribe("backend/tests/test_cors.py", main_con('["*"]'))
        r = self.repo.juzga()
        self.assertEqual([], r.hallazgos, [h.mensaje for h in r.hallazgos])

    def test_marcador_de_supresion_con_motivo(self):
        # El marcador va en la línea de ARRIBA: un comentario a la derecha de
        # `allow_origins=[...]` se comería la coma que separa los argumentos.
        self.repo.escribe("backend/main.py", main_con('["*"]').replace(
            "    allow_origins=",
            "    # coipo-jueces:ignorar(G8-5) API pública de solo lectura, sin datos\n"
            "    allow_origins="))
        r = self.repo.juzga()
        self.assertEqual([], r.bloqueantes)
        self.assertEqual(1, len(r.supresiones), r.supresiones)


if __name__ == "__main__":
    unittest.main(verbosity=2)
