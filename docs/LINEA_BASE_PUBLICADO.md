# Línea base de lo publicado — coipo_jueces

> Generado el 2026-10-26 con la metodología «Mejorar una app ya publicada» (objetivo 527, versión con banda de ruido
> y hallazgos preexistentes). Solo lectura sobre lo publicado (GET). **Archivo nuevo, sin commit.**

## 1. Identificación
| | |
|---|---|
| Repositorio | coipo_jueces |
| Rama local / commit local | main / a814f5c |
| Árbol de trabajo | LIMPIO (antes de crear este informe) |
| Sembrada (`.semilla`) | no (tiene `semilla.lock` y `semilla.lock.historial`) |
| Qué es | Verificadores ejecutables de la flota COIPO / CONAF, distribuidos como workflow reusable (README.md:1-4) |

## 2. Entorno y evidencia del dominio
| Entorno | Dominio | Evidencia (archivo:línea) |
|---|---|---|
| ninguno | sin dominio detectable | `iam.conaf.cl` aparece solo como dato de prueba (jueces/j05_cors.py:15, tests/test_j05_cors.py:81); no es un servicio del repo |

## 3. CI y despliegue (gh run list)
Autotest · push · main · success · a814f5c (= HEAD local); Autotest · pull_request · arreglos-auditoria-2026-10-25 · success (6924c44, d80eea9); Autotest · push · main · success · 1a2d589; Autotest · pull_request · j14-construccion · success · e084850.
Commit publicado: no aplica (se consume como workflow reusable por rama/etiqueta, no hay /health).

## 4. Funcionalidad medida
No se midió: sin dominio.

## 5. Hallazgos preexistentes
| Hallazgo | ¿Por diseño? | Fuente |
|---|---|---|
| Sin servicio en ejecución | sí, es una librería de jueces + workflows | README.md:1-4 |

## 6. Interfaz
No medida en esta pasada.

## 7. Defectos simples corregidos (sin commit)
| Archivo | Antes | Después | Cómo se verificó |
|---|---|---|---|
| (ninguno) | | | Barrido de enlaces relativos en `.md`: salida vacía. No se tocó código ni reglas |

Defectos vistos y NO corregidos: ninguno.

## 8. No lo comprobé
- Qué repos consumen el workflow reusable ni con qué versión.
- Los otros workflows (probar-runner.yml, verificar.yml) no los ejecuté.
