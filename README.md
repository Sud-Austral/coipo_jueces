# coipo_jueces

Verificadores ejecutables de la flota COIPO / CONAF. Se distribuyen como
**workflow reusable**, nunca por copia.

```yaml
# .github/workflows/ci.yml de cualquier app
jobs:
  jueces:
    uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2
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

Estado de la flota con los **nueve** jueces, medido el **2026-09-08** en modo
advisory sobre los **24** repositorios `coipo_*`/`COIPO_*` del disco. `j13_interfaz`
**BLOQUEA** desde la firma del estándar (2026-09-07) y sólo juzga a quien lo
**declara**: hoy `coipo_atraso_personal` (todo) y `coipo_prensa2` (`adopta:
interfaz`). Tras esta medición se corrigió un falso positivo de `j11` sobre
`coipo_n8n` (software de terceros sin Python propio), que aparecía con 1.

| Repositorio | Bloquea | Avisa | Qué encuentra |
|---|---:|---:|---|
| `coipo_prensa2` | **0** | 9 | **la única aplicación alineada.** `j13` en `OK`. Avisan `OPS-1`, `G8-7` y `NG-1`, los tres declarados en su ficha |
| `coipo_atraso_personal` | **0** | 0 | el único repositorio **sembrado**; patrón de calibración de `j12`/`j13` |
| `coipo_master_produccion` | **0** | 0 | la fábrica. Tuvo 1 bloqueante —una credencial versionada— hasta el 2026-09-07 |
| `coipo_jueces` | **0** | 0 | este repositorio, con 1 supresión declarada en `DEUDA.md` |
| `coipo_n8n` | **0** | 2 | software de terceros: `j11` `NO_APLICA` desde el 2026-09-08 |
| `coipo_sitra` · `coipo_entrega_planta_test` | 1 | 2 · 11 | |
| `COIPO_ENTREGA_PLANTA` | 2 | 11 | sin `.dockerignore` con `context: .`; `proxy_pass` literal; CI node 20 y Dockerfile 22 |
| 8 repositorios más | 2 | 1–8 | `aireadme`, `cabania`, `dendroenergia`, `moodle`, `notebooklm`, `prevencion_incendio`, `seguimiento_madera`, `vista_catastro` |
| `COIPO_CHATBOTNORMATIVA` · `COIPO_LICITACION_IA` · `COIPO_PDF_EXCEL` | 3 | 1–2 | |
| `COIPO_BID_LOSRIOS` | 4 | 2 | |
| `COIPO_DIRECTORIO` | 6 | 3 | |
| `COIPO_USUARIOS` | 9 | 8 | `.env` versionado con `JWT_SECRET` y `RUT_HMAC_SECRETS`; `.dockerignore` que no excluye `.env` |
| `COIPO_SEGUIMIENTO` · `COIPO_SEGUIMIENTOPROYECTO` | **12** | 8 | los dos peores de la flota; `DATABASE_URL` versionada y `5432:5432` publicado |

**Lo que dice la medición completa:** de 24, **cinco** con cero bloqueantes, y
sólo dos son aplicaciones. Los repositorios con 5–7 comprobaciones no están más
sanos que los de 18: son los que el gate apenas puede mirar.

Cada uno de esos 12 bloqueantes es un defecto real y verificable, no una
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
  Guía 8 punto 3). Los otros tres eran valores que los propios repos declaran falsos en
  español (`...-jamas-usar-en-produccion`).
- `j06`: exigía `.env.example` a este mismo repositorio, que no es una
  aplicación. Una regla aplicada fuera de su dominio.

Los falsos positivos no son un detalle de afinación: son el modo de muerte más
probable de un verificador, porque enseñan a la gente a suprimirlo.

## Supresiones

Se silencia un hallazgo con un marcador en el código, con **motivo obligatorio**
de al menos 12 caracteres, en la misma línea o en la anterior:

```python
JWT_SECRET = "..."  # coipo-jueces:ignorar(G8-4) fixture del arnés de pruebas
```

Toda supresión **se cuenta y se publica** en el resumen y en las salidas del
job. Si el número crece respecto de `main`, el verificador se está apagando; esa
es la única señal temprana que existe. Cada supresión exige además una fila en
el `DEUDA.md` de la app.

## Jueces

| Juez | Reglas | Qué mira | Estado |
|---|---|---|---|
| `j01_despliegue` | `G8-7` · `DK-3` · `DK-4` · `NG-1` · `OPS-1` | compose (`version:`, un solo `ports:`, base de datos propia, healthcheck, `restart`), `.dockerignore` frente al contexto de build, y `proxy_pass` literal sin `resolver` en el nginx interno | ✅ |
| `j06_config` | `G8-3` · `G8-6` · `CI-1` | `.env.example` y las seis variables base, `APP_PORT` sin comillas, `DATABASE_URL` prohibida, `SESSION_`/`SESION_` conviviendo, y versiones del CI frente a las del Dockerfile | ✅ |
| `j09_secretos` | `G8-4` | `.env` versionados, claves privadas, credenciales en DSN y valores con pinta de generados | ✅ |
| `j11_salud` | `G8-9` · `G8-11` | `/health` existe, sin auth ni redirección, con `text()`; y que un fallo de datos no se disfrace de app sana | ✅ |
| `j02_identidad` | `G8-1` · `G8-2` | nombre del repositorio en minúsculas y `APP_PORT` declarado y no cableado | ✅ |
| `j05_cors` | `G8-5` | CORS por dominio, nunca `*` ni una IP | ✅ |
| `j08_rsync` | `G8-8` · `G8-10` | `.gitignore` con las rutas **ancladas**, y qué llega al servidor | ✅ |
| `j12_semilla` | `SEM-1` | que las piezas congeladas de la semilla no se editen por aplicación, en los repositorios que **declaran** haberse sembrado (`.semilla`) | ✅ |
| `j13_interfaz` | `UI-3` · `UI-10` · `UI-15` | la interfaz —tokens de color redefinidos en el tema oscuro, `outline:0` con sustituto, y `prefers-reduced-motion` apagando todo el movimiento— en los repositorios que **declaran** seguir el estándar (`.semilla`) | ✅ **BLOQUEA** desde la firma del estándar (2026-09-07) |

**Qué documento respalda cada código está en [`REGLAS.md`](REGLAS.md)**, y una
prueba falla si un juez emite un código que no figura ahí —o si el catálogo
anuncia una regla que ningún juez comprueba.

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
