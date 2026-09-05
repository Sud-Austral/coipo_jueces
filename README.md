# coipo_jueces

Verificadores ejecutables de la flota COIPO / CONAF. Se distribuyen como
**workflow reusable**, nunca por copia.

```yaml
# .github/workflows/ci.yml de cualquier app
jobs:
  jueces:
    uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v1
    with:
      modo: advisory        # advisory | bloqueante
      perfil: aplicacion    # aplicacion | encuadre_operativo
```

A mano, sobre cualquier repositorio y sin instalar nada:

```bash
python3 jueces/correr.py --repo /ruta/al/repo --modo advisory --resumen RESUMEN.md
python3 jueces/j09_secretos.py --repo /ruta/al/repo --modo bloqueante
```

## Por qué existe esto

Está medido en esta flota, no supuesto:

- `DOCKER.md` vive en **10 repositorios con 3 contenidos distintos**.
- `guia-8-prompt-checklist-pre-deploy.md` tiene 11 puntos en el repo maestro y
  9 en `COIPO_ENTREGA_PLANTA` — al único repo **sin CI** le faltan justo los dos
  puntos que más caros salieron.
- Tasa de propagación del mecanismo copia: **2 de 9 (22 %)**.
  Tasa del `uses:` a un workflow reusable: **8 de 8 (100 %)**.

De ahí la regla que gobierna este repositorio: **una corrección a un juez llega
a todas las apps en su siguiente push, sin que nadie tenga que acordarse.**

## Por qué es público

Un reusable alojado en un repositorio privado obliga a cablear un PAT de
organización en cada repo llamante. El historial de esta flota con secretos de
larga vida es un `.env` versionado desde abril de 2026: no se añade otro. Los
jueces son Python de biblioteca estándar y no llevan secretos, así que
publicarlos no expone nada.

Los hallazgos, el registro de puertos y los decretos siguen **privados** en
`coipo_master_produccion`.

> **Regla dura, consecuencia de lo anterior:** los fixtures de las pruebas son
> **sintéticos**. Nunca se copia un archivo de un repositorio privado de CONAF a
> este árbol. Un fixture "tomado de COIPO_ENTREGA_PLANTA" publicaría código
> privado en internet — exactamente el tipo de fuga por conveniencia que estos
> jueces existen para evitar.

## Los dos modos

| Modo | Qué hace | Para qué |
|---|---|---|
| `advisory` | informa todo, sale **0** | medir la distancia sin dejar a la flota sin poder desplegar sus arreglos urgentes |
| `bloqueante` | un hallazgo `BLOQUEA` hace salir **1** | la compuerta de verdad |

El paso de uno a otro es **por regla y con fecha escrita en `DECRETOS.md`**, no
por criterio de quien corre el comando. Encender todas las reglas de golpe deja
a la flota sin desplegar, y el desenlace previsible es que alguien apague el
verificador entero.

## Calibración inversa

Un juez nuevo se valida contra el código que **ya se sabe bueno**. Si sale rojo
sobre un repo cuyo comportamiento es correcto, el verificador está mal — no el
código. Cada juez lleva su tabla de calibración en el docstring.

Estado de la flota con los tres jueces, medido el 2026-09-05 en modo advisory:

| Repositorio | Bloquea | Avisa | No evaluado | Qué encuentra |
|---|---:|---:|---:|---|
| `coipo_n8n` | **0** | 0 | 1 | la referencia: `mem_limit` y healthcheck en todos, guards `${VAR:?}`, `resolver` |
| `COIPO_USUARIOS` | 4 | 6 | 0 | `.env` versionado con `JWT_SECRET` y `RUT_HMAC_SECRETS`; `.dockerignore` que no excluye `.env` |
| `coipo_prensa2` | 6 | 9 | 0 | `SESSION_`/`SESION_` conviviendo; CI que prueba python 3.11 y node 22 mientras construye 3.14 y 26; `proxy_pass` literal |
| `COIPO_ENTREGA_PLANTA` | 5 | 7 | 0 | sin `.dockerignore` con `context: .`; `proxy_pass` literal; CI con node 20 y Dockerfile con 22 |
| `coipo_master_produccion` | 0 | 1 | 3 | repo de doctrina: no despliega, no se le exige contrato de `.env` |
| `coipo_jueces` | 0 | 0 | 3 | este mismo repo |

Cada uno de esos 15 bloqueantes es un defecto real y verificable, no una
preferencia de estilo. Y `coipo_n8n` en verde es tan importante como los rojos:
es la prueba de que el juez no dispara sobre el repositorio que hizo las cosas
bien.

Tres correcciones al verificador —no al código— hicieron falta para llegar aquí:

- `j09`, primera pasada: **68** hallazgos sobre `COIPO_USUARIOS` y **53** sobre
  `coipo_prensa2`, que debía salir verde. Dejaba que la entropía del *valor*
  disparara sola sin mirar la clave, así que cualquier cadena de 32 caracteres
  —un SHA, un identificador— era un secreto.
- `j09`, segunda pasada: cuatro falsos positivos, y uno señalaba el patrón
  **correcto** (componer la URL desde las cinco variables, que es lo que exige
  D-06). Los otros tres eran valores que los propios repos declaran falsos en
  español (`...-jamas-usar-en-produccion`).
- `j06`: exigía `.env.example` a este mismo repositorio, que no es una
  aplicación. Una regla aplicada fuera de su dominio.

Los falsos positivos no son un detalle de afinación: son el modo de muerte más
probable de un verificador, porque enseñan a la gente a suprimirlo.

## Supresiones

Se silencia un hallazgo con un marcador en el código, con **motivo obligatorio**
de al menos 12 caracteres, en la misma línea o en la anterior:

```python
JWT_SECRET = "..."  # coipo-jueces:ignorar(D-31) fixture del arnés de pruebas
```

Toda supresión **se cuenta y se publica** en el resumen y en las salidas del
job. Si el número crece respecto de `main`, el verificador se está apagando; esa
es la única señal temprana que existe. Cada supresión exige además una fila en
el `DEUDA.md` de la app.

## Jueces

| Juez | Reglas | Qué mira | Estado |
|---|---|---|---|
| `j01_despliegue` | D-37 · D-27 | compose (`version:`, un solo `ports:`, base de datos propia, healthcheck, `mem_limit`, `restart`), `.dockerignore` frente al contexto de build, y `proxy_pass` literal sin `resolver` en el nginx interno | ✅ |
| `j06_config` | D-06 · D-08 · D-28 | `.env.example` y las seis variables base, `APP_PORT` sin comillas, `DATABASE_URL` prohibida, `SESSION_`/`SESION_` conviviendo, y versiones del CI frente a las del Dockerfile | ✅ |
| `j09_secretos` | D-31 | `.env` versionados, claves privadas, credenciales en DSN y valores con pinta de generados | ✅ |
| `j02_capas` | D-25 | el dominio no importa infraestructura (AST, no grep) | pendiente |
| `j03_iam_bff` | — | `IAM_JWT_SECRET` inexistente, sin token en `localStorage`, `state` de un solo uso | pendiente |
| `j10_rat` | D-23 | ficha ↔ `COMMENT ON COLUMN` ↔ anonimizador | pendiente |

Añadir un juez es añadir un archivo `jNN_nombre.py` que exponga
`comprobar(repo, resultado)`. `correr.py` los descubre solo; un archivo con
nombre de juez que no cumpla el contrato es un **error ruidoso**, no un archivo
que se ignora en silencio.

## Contrato de un juez

- Solo biblioteca estándar. Sin `pip install` en el CI de las apps.
- Solo lectura. Un juez jamás modifica el repositorio que examina.
- Todo hallazgo lleva `manifestacion`: cómo se ve ese defecto **en producción**.
  Si no se puede escribir, el hallazgo no debería existir.
- «No pude evaluar» se reporta aparte de «evalué y está bien». Confundirlos es
  cómo un control se apaga durante meses sin que nadie se entere.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Un `skip` es un fallo: una dependencia ausente falla con instrucciones, nunca se
salta. Un test permanentemente saltado tiene el mismo color que uno que pasa.
