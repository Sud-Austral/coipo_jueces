# Deuda declarada

Una fila por cada supresión activa del gate. Lo exige `comun.py`, que emite un
`::warning::` por cada una y nombra este archivo: **el contador de supresiones es
la única señal temprana de que un gate se está apagando solo.**

> Este archivo no existía en **ningún** repositorio de la flota —tampoco en éste,
> que es quien lo exige— hasta el 2026-09-08. El dogfood de `autotest.yml` emitía
> en cada ejecución un aviso pidiendo una fila en un archivo que no estaba.

## Supresiones activas

| Regla | Dónde | Por qué | Qué la cerraría |
|---|---|---|---|
| `G8-4` | `tests/test_j09_secretos.py` (fixture `tests/fixtures/id_rsa`) | Es la **prueba** de que `j09` detecta una clave privada: el fixture tiene que parecer una clave para que el detector la vea. Se suprime con motivo escrito en vez de evadir el detector, porque una evasión no deja rastro y la supresión sí | Nada: es deuda **por diseño** y se queda. El día que `j09` distinga `tests/fixtures/` por su cuenta, la fila sobra |

**1 supresión activa.** Si sube, la pregunta no es cuál cerrar: es por qué el
gate dejó de servir.
