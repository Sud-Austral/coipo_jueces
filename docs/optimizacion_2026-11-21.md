# Informe de optimización 2026-11-21

## 1. Resumen
- Aplicación: coipo_jueces, verificadores ejecutables (Python, biblioteca estándar) de la flota COIPO, distribuidos como workflow reusable.
- Rama: `optimizacion/2026-11-21`; commit base `7c9180c`. Un solo componente (jueces + tests unittest).
- Comandos: `py -3.11 -m unittest discover -s tests -v` (comando del CI `autotest.yml`), `ruff check .` y `ruff check --select F --isolated jueces tests` con ruff 0.17.4 instalado fuera del repo.
- Veredicto: APTO PARA REVISIÓN, con 0 optimizaciones aplicadas. Ruff F no da hallazgos, el lint del repo está limpio y el código no procesa volumen; los candidatos de rendimiento (por ejemplo, cachear llamadas a `git` en `Repo`) son de riesgo alto (caché) y quedan como propuesta.

## 2. Antes y después
| Métrica | Línea base | Después |
|---|---|---|
| Tests (corrida 1) | 422 ejecutados, 19 errores | sin cambios de código: no se repitió |
| Tests (corridas 2 y 3) | 422 ejecutados, 0 fallas, 0 omitidos | ídem |
| `ruff check .` | All checks passed | ídem |
| Build | no hay | — |
Evidencias: `base_1.txt`, `base_2.txt`, `base_3.txt`, `ruff_base.txt` en `D:/optimizacion_evidencias/coipo_jueces/2026-11-21/`.

Inestables: los 19 errores de la corrida 1 (`test_j14_construccion`, `test_j14_mirado`) son `git init -q` con salida 128 dentro de `tests/ayuda.py:51`; pasaron en las corridas 2 y 3. Coinciden con el disco temporal del sistema casi lleno (64 MB libres) y otros agentes en paralelo; tratados como inestables de entorno (no comprobé la causa exacta).

## 3. Optimizaciones aplicadas
Ninguna.

## 4. Descartadas
Ninguna intentada.

## 5. Propuestas no aplicadas
- Memoizar las consultas a `git` de `Repo` en `jueces/comun.py` (riesgo alto: caché; requiere tests que fijen el resultado con repos que cambian durante la corrida).

## 6. Hallazgos fuera de alcance
- La copia del usuario tiene cambios sin commitear en `jueces/j12_semilla.py`, `semilla.lock`, `semilla.lock.historial`, `tests/test_j12_semilla.py` y un `docs/preguntas_usuario.xlsx` sin versionar (no abierto).
- `main` va 31 commits por delante de `origin/main` (sin publicar).
- `tests/ayuda.py` falla con un error crudo `CalledProcessError` si `git init` no puede crear el repositorio temporal; un mensaje más claro ayudaría a distinguir fallas de entorno.

## 7. Tests agregados
Ninguno.

## 8. Partes no revisadas
- Análisis de rendimiento fino por juez (no se perfiló; no hay volumen de datos que lo justifique).
- Sin vulture/radon: no se instalaron.

## 9. Cómo revisar y revertir
- `git log --oneline 7c9180c..optimizacion/2026-11-21`
- `git diff 7c9180c...optimizacion/2026-11-21`
- Borrar: `git worktree remove .claude/worktrees/optimizacion-2026-11-21` y `git branch -D optimizacion/2026-11-21`.
- Línea agregada a `.git/info/exclude`: `.claude/worktrees/`.
