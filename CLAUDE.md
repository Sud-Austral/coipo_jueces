# coipo_jueces — guía para agentes

## Qué es
Verificadores ejecutables (Python, solo biblioteca estándar) de la flota COIPO / CONAF. Se distribuyen como **workflow reusable** (`.github/workflows/verificar.yml`, consumido con `uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2`), nunca por copia. Repositorio **público a propósito**. Más contexto: [`README.md`](README.md), [`docs/ERS.md`](docs/ERS.md).

## Estructura
- `jueces/`: `comun.py` (severidades, veredicto de cuatro estados, supresiones, `Repo` con `indice_roto()` y `sin_indice()`), `comun_yaml.py` (el parser YAML de los compose), `comun_semilla.py` (las claves `adopta:`, `fabrica:`, `maqueta:` y `ajeno:` de `.semilla`, con su semántica única), `comun_auditoria.py` (lo que mira `AUD-1`), `comun_zen.py` (lo que mira `COD-5`), `historial_semilla.py` (lee `semilla.lock.historial` y dice desde cuándo rige cada pieza), `correr.py` (orquestador) y los jueces `jNN_*.py` (j01, j02, j05, j06, j08, j09, j11, j12, j13, j14, j16). Se cuentan con `ls jueces/j*.py`.
- `tests/`: una prueba por juez (`test_jNN_*.py`) más las transversales. Del propio repositorio: `test_reglas_citadas.py` (catálogo ⇔ código), `test_coherencia_documentos.py` (lo que dicen `README.md`, este archivo, `DEUDA.md`, `REGLAS.md` y `docs/VERSIONADO.md` frente a lo que hay), `test_solo_biblioteca_estandar.py`, `test_datos_semilla.py` (el lock y su historial), `test_verificar_yaml.py`, `test_workflows_yaml.py` y `test_arnes.py`. Del motor: `test_tres_estados.py`, `test_nada_que_mirar.py`, `test_indice_roto.py`, `test_anotaciones.py`, `test_yaml_formas.py`, `test_ignora_env.py` y `test_revision_2026_09_08.py`. De `.semilla` y la semilla: `test_adopta_cruzado.py`, `test_adopta_formas.py`, `test_semilla_claves.py`, `test_aud1_auditoria.py`, `test_maqueta.py`, `test_paquetes_sistema.py` y `test_cod5_zen.py`. `ayuda.py` arma repositorios sintéticos y los borra.
- `REGLAS.md` (catálogo de reglas), `DEUDA.md` (supresiones activas), `semilla.lock` y `semilla.lock.historial` (los genera `sellar.py` de la fábrica: no se editan a mano), `ruff.toml` (copia sellada de la semilla: tampoco), `docs/VERSIONADO.md`, `docs/ERS.md`.
- `.github/workflows/`: `verificar.yml` (reusable), `autotest.yml` (los jueces se prueban a sí mismos, con el `python3` del runner y con Python 3.10, más actionlint sobre el reusable y ruff) y `alerta-main.yml` (abre un issue si `Autotest` falla en main). `probar-runner.yml` se retiró el 2026-11-21: pedía un runner self-hosted desde un repositorio público y quedaba encolado para siempre.

Las listas de jueces, módulos y pruebas de esta sección las comprueba `tests/test_coherencia_documentos.py`: si añades un archivo y no lo nombras aquí, la suite falla.

## Comandos (VERIFICADOS el 2026-11-25, en Windows con `python`)
```bash
python3 -m unittest discover -s tests -v            # imprime «Ran N tests»: 0 omitidas desde el 2026-10-25
python3 jueces/correr.py --repo . --modo bloqueante --perfil encuadre_operativo   # según docs/VERSIONADO.md
python3 -m ruff check --target-version py310 . && python3 -m ruff format --check .   # ruff 0.17.4
```
No hay build. **Python mínimo: 3.10** (decisión de Luis Monsalve del 2026-11-25): `autotest.yml` corre la suite también en `ubuntu-22.04`. Lint con ruff 0.17.4 y las reglas de `ruff.toml`, copia del sellado de la semilla (el Zen de Python con chequeos, decisión de Luis Monsalve del 2026-11-21); esa copia apunta a 3.11 y no se edita aquí, por eso el piso se pasa por línea de comandos. Ruff es una herramienta de este CI y del desarrollo, no una dependencia: los jueces siguen siendo de biblioteca estándar y el CI de las apps no instala nada. Una excepción de lint va en su línea con el código y el motivo (`# noqa: UP042 <motivo>`).

## Convenciones
- Un juez nuevo: archivo `jNN_nombre.py` con `comprobar(repo, resultado)`; `correr.py` lo descubre solo. Todo código de hallazgo debe figurar en `REGLAS.md` y viceversa (lo comprueba una prueba).
- Sólo un juez emite. Un módulo auxiliar (`comun_*.py`, `historial_semilla.py`) devuelve datos y el juez llama a `bloquea()` o `avisa()` (lo comprueba `test_reglas_citadas.py`).
- Solo lectura sobre el repo revisado; todo hallazgo lleva `manifestacion`; «no pude evaluar» se reporta aparte de «OK».
- Un juez que lee `repo.versionados()`, él o un auxiliar suyo, llama antes a `sin_indice()` (lo comprueba `test_indice_roto.py`).
- Supresión: `# coipo-jueces:ignorar(REGLA) motivo` (motivo de al menos 12 caracteres) y una fila en `DEUDA.md`.
- Un `skip` en pruebas debe tratarse como fallo (README). Desde el 2026-10-25 la suite no tiene ninguno.
- Una prueba nueva se ve fallar una vez antes de darla por buena.

## Trampas
- **Fixtures sintéticos siempre**: nunca copiar archivos de repos privados de CONAF aquí (el repo es público). Tampoco binarios de ofimática: una prueba los rechaza.
- `v2` es un tag móvil que consumen las apps de la flota; `vN.N.N` no se mueve jamás. Un cambio que pueda poner rojo a un repo hoy verde es una mayor nueva (`docs/VERSIONADO.md`). No muevas tags sin seguir ese documento.
- Toda publicación lleva su entrada en `docs/VERSIONADO.md` en el mismo commit: una prueba falla si un tag de la mayor vigente no tiene su encabezado.
- `semilla.lock` y su historial viajan con el tag: si `semilla/CONGELADO/` cambió en la fábrica, se resellan aquí en el mismo tag (`docs/VERSIONADO.md`, punto 5). El lock no nombra ningún archivo de este repositorio.
- Si cambias `verificar.yml`, sólo GitHub lo valida, al llamarlo (job `el-reusable-lo-valida-github`), y la ref por defecto de `ref_jueces` debe seguir la mayor (la comprueba `test_verificar_yaml.py`).
- No hay secretos ni `.env`; no agregues ninguno.
