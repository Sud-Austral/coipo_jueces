# coipo_jueces — guía para agentes

## Qué es
Verificadores ejecutables (Python, solo biblioteca estándar) de la flota COIPO / CONAF. Se distribuyen como **workflow reusable** (`.github/workflows/verificar.yml`, consumido con `uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2`), nunca por copia. Repositorio **público a propósito**. Más contexto: [`README.md`](README.md), [`insumos/`](insumos/).

## Estructura
- `jueces/`: `comun.py` (severidades, veredicto de cuatro estados, supresiones, `Repo` con `indice_roto()` y `sin_indice()`), `comun_yaml.py` (el parser YAML de los compose), `comun_semilla.py` (`adopta:` y `fabrica:` de `.semilla`, con su semántica única), `correr.py` (orquestador) y once `jNN_*.py` (j01, j02, j05, j06, j08, j09, j11, j12, j13, j14, j16). Se cuentan con `ls jueces/j*.py`.
- `tests/`: una prueba por juez más transversales (`test_reglas_citadas.py`, `test_tres_estados.py`, `test_verificar_yaml.py`, `test_workflows_yaml.py`, `test_adopta_cruzado.py`, `test_adopta_formas.py`, `test_indice_roto.py`, `test_anotaciones.py`, `test_yaml_formas.py`); `ayuda.py` arma repositorios sintéticos.
- `REGLAS.md` (catálogo de reglas), `DEUDA.md` (supresiones activas), `semilla.lock`, `docs/VERSIONADO.md`.
- `.github/workflows/`: `verificar.yml` (reusable), `autotest.yml` (los jueces se prueban a sí mismos), `probar-runner.yml` (manual).

## Comandos (VERIFICADOS el 2026-10-25)
```bash
python3 -m unittest discover -s tests -v            # imprime «Ran N tests»: 0 omitidas desde el 2026-10-25
python3 jueces/correr.py --repo . --modo bloqueante --perfil encuadre_operativo   # según docs/VERSIONADO.md
```
No hay build ni lint. Sin `pip install`.

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
