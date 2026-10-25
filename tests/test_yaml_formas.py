"""El parser de los compose entiende la sintaxis legítima que la flota ya usa.

EL DEFECTO (auditoría del 2026-10-25). `carga_yaml` lanzaba `YamlNoSoportado` ante
tres construcciones de YAML corriente, y el juez que lo leía anotaba «el compose no
se pudo verificar»: un repositorio sano quedaba SIN_EVALUAR por su sintaxis, no
por sus defectos. Fallaban así los compose de tres repositorios del disco:

  - `coipo_cron_master`: ancla y alias (`build: &imagen` … `build: *imagen`);
  - `coipo_neo4j`: un escalar en bloque `>-` como ÍTEM de una lista (el `test:` de
    su healthcheck);
  - `coipo_seguimiento_madera`: `command: >` con el comando en varias líneas.

Y una cuarta que no tumbaba pero leía MAL en silencio: un mapa de varias claves
dentro de una lista (`- type: bind` / `  source: ...`) perdía las claves
siguientes. Cada fragmento de aquí es mínimo e inventado.

Lo que sigue sin soportarse lo dice con `YamlNoSoportado` —etiquetas (`!reset`),
varios documentos, un alias a un ancla que no existe— y queda probado abajo.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "jueces"))
from comun import YamlNoSoportado, carga_yaml  # noqa: E402


class PruebaFormasLegitimas(unittest.TestCase):

    def test_mapa_de_varias_claves_dentro_de_una_lista(self):
        y = carga_yaml(
            "services:\n"
            "  app:\n"
            "    volumes:\n"
            "      - type: bind\n"
            "        source: ./datos\n"
            "        target: /datos\n"
            "      - ./otro:/otro\n"
            "    ports:\n"
            "      - 8080:80\n")
        app = y["services"]["app"]
        self.assertEqual([{"type": "bind", "source": "./datos", "target": "/datos"}, "./otro:/otro"],
                         app["volumes"])
        # `- 8080:80` es un escalar, no un mapa `{8080: 80}`: no hay `: ` con espacio.
        self.assertEqual(["8080:80"], app["ports"])

    def test_escalar_en_bloque_como_valor(self):
        y = carga_yaml(
            "services:\n"
            "  migrar:\n"
            "    command: >\n"
            "      -url=jdbc:postgresql://${DATABASE_HOST}/x\n"
            "      -user=${DATABASE_USER}\n"
            "      migrate\n"
            "    entrypoint: |\n"
            "      #!/bin/sh\n"
            "      echo hola  # no es un comentario de YAML\n"
            "    restart: \"no\"\n")
        m = y["services"]["migrar"]
        self.assertEqual("-url=jdbc:postgresql://${DATABASE_HOST}/x -user=${DATABASE_USER} migrate\n",
                         m["command"])
        self.assertEqual("#!/bin/sh\necho hola  # no es un comentario de YAML\n", m["entrypoint"])
        self.assertEqual("no", m["restart"])

    def test_escalar_en_bloque_como_item_de_lista(self):
        y = carga_yaml(
            "services:\n"
            "  base:\n"
            "    healthcheck:\n"
            "      test:\n"
            "        - CMD-SHELL\n"
            "        - >-\n"
            "          wget -q -O - http://localhost:7474/db/x\n"
            "          | grep -qF ok\n"
            "      interval: 30s\n")
        hc = y["services"]["base"]["healthcheck"]
        self.assertEqual(["CMD-SHELL", "wget -q -O - http://localhost:7474/db/x | grep -qF ok"],
                         hc["test"])
        self.assertEqual("30s", hc["interval"])

    def test_anclas_alias_y_fusion(self):
        y = carga_yaml(
            "x-comun: &comun\n"
            "  restart: unless-stopped\n"
            "  logging:\n"
            "    driver: json-file\n"
            "services:\n"
            "  colector:\n"
            "    <<: *comun\n"
            "    build: &imagen\n"
            "      context: .\n"
            "      dockerfile: collector/Dockerfile\n"
            "  estado:\n"
            "    <<: *comun\n"
            "    restart: always\n"
            "    build: *imagen\n"
            "    ports:\n"
            "      - &puerto \"${APP_PORT:-8080}:8000\"\n"
            "      - *puerto\n")
        s = y["services"]
        self.assertEqual("unless-stopped", s["colector"]["restart"])
        self.assertEqual({"driver": "json-file"}, s["colector"]["logging"])
        self.assertEqual("always", s["estado"]["restart"], "la clave propia gana a la fusionada")
        self.assertEqual({"context": ".", "dockerfile": "collector/Dockerfile"}, s["estado"]["build"])
        self.assertEqual(["${APP_PORT:-8080}:8000"] * 2, s["estado"]["ports"])

    def test_secuencia_en_linea_en_varias_lineas_y_mapa_en_linea(self):
        y = carga_yaml(
            "services:\n"
            "  app:\n"
            "    healthcheck:\n"
            "      test: [\"CMD\", \"curl\",\n"
            "             \"-sf\", \"http://localhost:8000/health\"]\n"
            "    labels: {a: \"1\", b: dos}\n")
        app = y["services"]["app"]
        self.assertEqual(["CMD", "curl", "-sf", "http://localhost:8000/health"], app["healthcheck"]["test"])
        self.assertEqual({"a": "1", "b": "dos"}, app["labels"])

    def test_un_documento_con_marcador_inicial(self):
        self.assertEqual({"services": {"a": {"image": "x"}}},
                         carga_yaml("---\nservices:\n  a:\n    image: x\n"))


class PruebaLoQueNoSeSoporta(unittest.TestCase):
    """Lo que no se entiende se dice: un verde por el motivo equivocado es peor."""

    def test_rechaza_explicitamente(self):
        for texto in ("services:\n  a:\n    ports: !reset []\n",
                      "a: 1\n---\nb: 2\n",
                      "services:\n  a:\n    build: *nadie\n",
                      "a:\n\tb: 1\n"):
            with self.subTest(texto=texto), self.assertRaises(YamlNoSoportado):
                carga_yaml(texto)

    def test_un_asterisco_que_no_es_alias_sigue_siendo_valor(self):
        self.assertEqual("*", carga_yaml('a: "*"\n')["a"])
        self.assertEqual("a*b", carga_yaml("a: a*b\n")["a"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
