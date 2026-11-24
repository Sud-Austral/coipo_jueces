# coipo_jueces — guía para agentes

## Qué es
Verificadores ejecutables (Python, solo biblioteca estándar) de la flota COIPO / CONAF. Se distribuyen como **workflow reusable** (`.github/workflows/verificar.yml`, consumido con `uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2`), nunca por copia. Repositorio **público a propósito**. Más contexto: [`README.md`](README.md), [`insumos/`](insumos/).

## Estructura
- `jueces/`: `comun.py` (severidades, veredicto de cuatro estados, supresiones, `Repo` con `indice_roto()` y `sin_indice()`), `comun_yaml.py` (el parser YAML de los compose), `comun_semilla.py` (`adopta:` y `fabrica:` de `.semilla`, con su semántica única), `comun_auditoria.py` (AUD-1, desde el 2026-11-21), `comun_zen.py` (COD-5, el Zen de Python en el CI de la app), `historial_semilla.py` (lee `semilla.lock.historial` para `j12`; separado el 2026-11-22 por COD-1), `correr.py` (orquestador) y once `jNN_*.py` (j01, j02, j05, j06, j08, j09, j11, j12, j13, j14, j16). Se cuentan con `ls jueces/j*.py`.
- `tests/`: una prueba por juez más transversales (`test_reglas_citadas.py`, `test_tres_estados.py`, `test_verificar_yaml.py`, `test_workflows_yaml.py`, `test_adopta_cruzado.py`, `test_adopta_formas.py`, `test_indice_roto.py`, `test_anotaciones.py`, `test_yaml_formas.py`, `test_aud1_auditoria.py`, `test_cod5_zen.py`, `test_maqueta.py`, `test_semilla_claves.py`, `test_paquetes_sistema.py`, entre otras: `ls tests/`); `ayuda.py` arma repositorios sintéticos.
- `REGLAS.md` (catálogo de reglas), `DEUDA.md` (supresiones activas), `semilla.lock`, `docs/VERSIONADO.md`.
- `.github/workflows/`: `verificar.yml` (reusable), `autotest.yml` (los jueces se prueban a sí mismos, con actionlint sobre el reusable y ruff) y `alerta-main.yml` (abre un issue si `Autotest` falla en main). `probar-runner.yml` se retiró el 2026-11-21: pedía un runner self-hosted desde un repositorio público y quedaba encolado para siempre.

## Comandos (VERIFICADOS el 2026-10-25; la suite, de nuevo el 2026-11-24: `Ran 486 tests`, OK, ~7 min en Windows)
```bash
python3 -m unittest discover -s tests -v            # imprime «Ran N tests»: 0 omitidas desde el 2026-10-25
python3 jueces/correr.py --repo . --modo bloqueante --perfil encuadre_operativo   # según docs/VERSIONADO.md
```
No hay build. Lint con ruff 0.17.4 (`ruff check .`), con las reglas de `ruff.toml`, copia del sellado de la semilla (el Zen de Python con chequeos, decisión de Luis Monsalve del 2026-11-21); corre en `autotest.yml`. Ojo: con otra versión de ruff el conteo cambia (el 2026-11-24, ruff 0.12.0 local dio 4 hallazgos; no se comprobó con 0.17.4). Es una herramienta de este CI y del desarrollo, no una dependencia: los jueces siguen siendo de biblioteca estándar y el CI de las apps no instala nada. Una excepción de lint va en su línea con el código y el motivo (`# noqa: UP042 <motivo>`).

## Convenciones
- Un juez nuevo: archivo `jNN_nombre.py` con `comprobar(repo, resultado)`; `correr.py` lo descubre solo. Todo código de hallazgo debe figurar en `REGLAS.md` y viceversa (lo comprueba una prueba).
- Solo lectura sobre el repo revisado; todo hallazgo lleva `manifestacion`; «no pude evaluar» se reporta aparte de «OK».
- Supresión: `# coipo-jueces:ignorar(REGLA) motivo` (motivo de al menos 12 caracteres) y una fila en `DEUDA.md`.
- Un `skip` en pruebas debe tratarse como fallo (README). Desde el 2026-10-25 la suite no tiene ninguno.

## Trampas
- **Fixtures sintéticos siempre**: nunca copiar archivos de repos privados de CONAF aquí (el repo es público).
- `v2` es un tag móvil que consumen las apps de la flota; `vN.N.N` no se mueve jamás. Un cambio que pueda poner rojo a un repo hoy verde es una mayor nueva (`docs/VERSIONADO.md`). No muevas tags sin seguir ese documento.
- Si cambias `verificar.yml` o archivos sembrados, `semilla.lock` debe resellarse (varios commits lo corrigen a posteriori) y la ref por defecto de `ref_jueces` debe seguir la mayor (la comprueba `test_verificar_yaml.py`).
- No hay secretos ni `.env`; no agregues ninguno.
