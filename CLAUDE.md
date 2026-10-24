# coipo_jueces — guía para agentes

## Qué es
Verificadores ejecutables (Python, solo biblioteca estándar) de la flota COIPO / CONAF. Se distribuyen como **workflow reusable** (`.github/workflows/verificar.yml`, consumido con `uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2`), nunca por copia. Repositorio **público a propósito**. Más contexto: [`README.md`](README.md), [`insumos/`](insumos/).

## Estructura
- `jueces/`: `comun.py` (severidades, veredicto de tres estados, supresiones), `correr.py` (orquestador) y `jNN_*.py` (j01, j02, j05, j06, j08, j09, j11, j12, j13).
- `tests/`: una prueba por juez más transversales (`test_reglas_citadas.py`, `test_tres_estados.py`, `test_verificar_yaml.py`, `test_workflows_yaml.py`); `ayuda.py` arma repositorios sintéticos.
- `REGLAS.md` (catálogo de reglas), `DEUDA.md` (supresiones activas), `semilla.lock`, `docs/VERSIONADO.md`.
- `.github/workflows/`: `verificar.yml` (reusable), `autotest.yml` (los jueces se prueban a sí mismos), `probar-runner.yml` (manual).

## Comandos (VERIFICADOS el 2026-10-24)
```bash
python3 -m unittest discover -s tests -v            # 181 pruebas OK, 1 omitida
python3 jueces/correr.py --repo . --modo bloqueante --perfil encuadre_operativo   # según docs/VERSIONADO.md
```
No hay build ni lint. Sin `pip install`.

## Convenciones
- Un juez nuevo: archivo `jNN_nombre.py` con `comprobar(repo, resultado)`; `correr.py` lo descubre solo. Todo código de hallazgo debe figurar en `REGLAS.md` y viceversa (lo comprueba una prueba).
- Solo lectura sobre el repo revisado; todo hallazgo lleva `manifestacion`; «no pude evaluar» se reporta aparte de «OK».
- Supresión: `# coipo-jueces:ignorar(REGLA) motivo` (motivo de al menos 12 caracteres) y una fila en `DEUDA.md`.
- Un `skip` en pruebas debe tratarse como fallo (README).

## Trampas
- **Fixtures sintéticos siempre**: nunca copiar archivos de repos privados de CONAF aquí (el repo es público).
- `v2` es un tag móvil que consumen las apps de la flota; `vN.N.N` no se mueve jamás. Un cambio que pueda poner rojo a un repo hoy verde es una mayor nueva (`docs/VERSIONADO.md`). No muevas tags sin seguir ese documento.
- Si cambias `verificar.yml` o archivos sembrados, `semilla.lock` debe resellarse (varios commits lo corrigen a posteriori) y la ref por defecto de `ref_jueces` debe seguir la mayor (la comprueba `test_verificar_yaml.py`).
- No hay secretos ni `.env`; no agregues ninguno.
