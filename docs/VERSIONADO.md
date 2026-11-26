# Versionado y publicación de `coipo_jueces`

Este repositorio se consume por `uses:`, no por copia. Eso significa que **el
tag es la interfaz pública**: lo que las apps de la flota ejecutan en cada
push es lo que apunte ese tag, y moverlo mal cambia el comportamiento del CI de
toda CONAF a la vez. (Hasta el 2026-11-25 este archivo decía «las 22 apps», «22
repos» y «22 pull requests»: una cifra tecleada sin fecha, que ya no era la de
la flota. Cuántos repositorios hay se mide, con su fecha, en cada entrada de más
abajo.)

## Dos tags, con propósitos opuestos

| Tag | Qué es | ¿Se mueve? | Para qué |
|---|---|---|---|
| `vN.N.N` | anotado, apunta a un commit concreto | **jamás** | poder decir «el 5 de septiembre corría exactamente esto» |
| `vN` | ligero, apunta al último `vN.x` | **sí, en cada publicación de esa mayor** | que un arreglo llegue a las apps sin tocar cada repositorio |

**Hoy la mayor vigente es `v2`.** `v1` sigue existiendo y **congelado** en
`d73d735`: quien no haya migrado ejecuta exactamente lo de entonces, que es
justamente lo que una mayor compra.

Es la convención de las propias actions de GitHub, y se puede comprobar:
`actions/checkout@v7` y `actions/checkout@v7.0.1` resuelven hoy al mismo commit
`3d3c42e5…`, pero mañana `v7` apuntará a `v7.0.2` y `v7.0.1` seguirá donde está.

**Las apps fijan la mayor, `@vN`.** Es deliberado y es toda la tesis del repositorio: la
propagación por copia en esta flota está medida en 22 % y la del `uses:` en
100 %. Fijar cada app a `@v1.0.3` devolvería el problema de la copia con otro
nombre — un pull request por aplicación para un arreglo de una línea, y la certeza de que
alguien se queda atrás.

> El contrapeso: si `v1` se mueve, se mueve para **todos a la vez**. Por eso una
> publicación se hace con la suite en verde y la calibración inversa repetida, y
> por eso un cambio que pueda poner rojo a un repo que hoy está verde no es un
> `v1.x`: es un `v2`, y cada app migra cuando decide.

## Publicar

**Los comandos no viven aquí.** El procedimiento —fusionar a `main`, crear el
tag anotado, reapuntar el móvil, qué comprobar después— está escrito **una sola
vez**, en `docs/publicar-los-jueces.md` de `coipo_master_produccion` (privado: es
la fábrica, no este repositorio). Este archivo conserva la **política**, que es
lo que no cambia aunque cambien los pasos.

> Hasta el 2026-10-12 había aquí una copia del procedimiento, y no coincidía con
> la de la fábrica: sus ejemplos eran de `v1` cuando la mayor vigente es `v2`,
> cableaba una rama de trabajo concreta (`jueces-fase-1`) y presentaba el
> `push -f` como un paso de rutina, mientras la fábrica lo trata como operación
> irreversible. Dos copias del mismo procedimiento es la enfermedad que este
> repositorio existe para curar, así que se quitó la de aquí en vez de
> «sincronizarla»: una copia sincronizada hoy vuelve a separarse mañana.

La política:

1. **Hay dos clases de tag, y ya están en la tabla de arriba.** `vN.N.N` es
   anotado e **inmutable**: no se mueve, no se borra y no se rehace —`v2.0.0` y
   `v2.0.3` salieron rotos y la única salida fue avisar y publicar el siguiente—.
   `vN` es el **móvil** y es el único que se reapunta, siempre al *commit* de un
   `vN.N.N` y nunca al objeto tag, para que `git describe` y las herramientas que
   resuelven tags no se confundan.
2. **Qué número toca** lo decide «Cuándo toca una mayor nueva», más abajo, y se
   **mide antes de publicar**, no se supone. Es `vN.x` sólo si nadie que hoy está
   verde se pone rojo; en cualquier otro caso es la mayor siguiente.
3. **El `push -f` del tag móvil es el único force-push legítimo de este
   repositorio.** Es seguro porque el móvil es un puntero, no historia: no se
   reescribe ningún commit y nadie pierde trabajo. Un `push -f` sobre `main` o
   sobre un `vN.N.N` es otra cosa y no se hace nunca. Y aun siendo legítimo, cambia
   lo que corre en el CI de toda la flota sin que nadie toque una aplicación:
   exige la autorización explícita de una persona, no se hace por inercia. Una
   mayor congelada (`v1`) no se reapunta nunca.
4. **Antes de mover el móvil, tres comprobaciones**, y ninguna se salta:
   - la suite entera en verde, `python -m unittest discover -s tests`: el tag
     publica también los comentarios y los docstrings;
   - la calibración inversa de este repositorio contra sí mismo,
     `python jueces/correr.py --repo . --modo bloqueante --perfil encuadre_operativo`.
     El perfil es `encuadre_operativo` porque este repositorio no despliega: con
     `aplicacion`, `j01` y `j06` salen `SIN_EVALUAR`, que en modo bloqueante es
     exit 1;
   - el run de `Autotest` del commit, con el job `el-reusable-lo-valida-github` en
     verde. **La suite verde no es la validación del YAML de los workflows**: sólo
     GitHub la hace, y sólo al invocar el archivo (ver `v2.0.3` más abajo).
5. **El lock viaja con el tag.** Si `semilla/CONGELADO/` cambió en la fábrica,
   `semilla.lock` se resella **en el mismo tag**; sin eso, `j12` acusa de «editada»
   a toda aplicación sembrada por un archivo que no tocó. Con el lock viaja el
   `semilla.lock.historial` que mantiene `sellar.py`: las huellas de cada lock
   publicado antes, que es lo que le permite a `j12` decir «atrasada» (AVISA,
   siempre) en vez de «editada» (BLOQUEA) (ver la nota sobre `SEM-1` en
   [`REGLAS.md`](../REGLAS.md)). Se publica en el mismo commit que el lock, y no se
   edita a mano: sólo crece. Hasta el 2026-10-24 viajaba en su lugar un
   `semilla.lock.anterior` con una ventana de 30 días (D2); el plazo no tenía
   fuente —lo eligió una IA como valor por omisión— y esa decisión lo eliminó.
   Resellar el lock es una publicación como cualquier otra: tiene su propio `vN.x`
   y su propia medición del radio de explosión, como las de `v2.0.10` y `v2.0.11`.

## Cuándo toca una mayor nueva

- Un juez nuevo en modo bloqueante, o una regla que pasa de `AVISA` a `BLOQUEA`.
- Un cambio en las entradas de `verificar.yml` que rompa a quien no lo actualice.
- Cualquier cosa que pueda poner rojo a un repositorio que hoy está verde.

Todo lo demás —jueces nuevos en advisory, correcciones de falsos positivos,
mensajes más claros— es `vN.x` y viaja solo.

> **ENMIENDA del 2026-10-25: un juez que mira hacia adelante puede ir en `vN.x`.**
>
> El primer criterio de arriba se escribió cuando un juez bloqueante bloqueaba a
> todo el que lo corría. Desde `j16` y `j14` existe otra clase: un juez que sólo
> BLOQUEA lo sembrado **desde su fecha de vigencia** (`fabrica:` de `.semilla`) y
> AVISA en todo lo anterior. Es lo que pide `FILOSOFIA.md` de la fábrica, §4: «las
> reglas miran hacia adelante». Ese juez **no cambia el veredicto de ninguna
> aplicación existente** —ninguna tenía la fecha cuando se escribió la regla—, así
> que no pone rojo a nadie que hoy esté verde, que es lo que el tercer criterio
> protege.
>
> Por eso: **un juez nuevo que sólo BLOQUEA lo sembrado desde su vigencia puede ir
> en `vN.x`**, con su radio de explosión MEDIDO antes de publicar (cero `BLOQUEA`
> nuevos sobre los repositorios del disco). **Si cambia el veredicto de algo que ya
> existe, es mayor nueva**, como siempre. Y la vigencia no puede ser anterior a la
> publicación sin decirlo y medirlo (ver `v2.0.13`).
>
> Esto se escribe DESPUÉS de los hechos: `v2.0.12` (`j16`) y `v2.0.13` (`j14`)
> salieron como `v2.x` sin entrada en este archivo y sin el radio escrito, contra
> la letra del primer criterio. La enmienda pone la regla al día con lo que se hizo
> y lo deja medido abajo; no lo convierte en correcto a posteriori.

### `v2`, publicada el 2026-09-08

Cumple **dos** de los tres criterios de arriba, así que no hizo falta ninguna
excepción:

1. **`UI-3`, `UI-10` y `UI-15` pasaron de `AVISA` a `BLOQUEA`** al firmarse
   `identidad/ESTANDAR_UI.md` el 2026-09-07. Es literalmente el primer criterio.
2. **`ref_jueces` cambió de semántica.** Su valor por defecto dejó de ser `v1`.
   Es un cambio en las entradas de `verificar.yml`.

Y trae `j13` (interfaz), la clave `adopta:` de `.semilla`, y los cuatro textos
del gate que describían un estado ya superado.

**Radio de explosión, medido antes de publicar:** los cuatro `uses:` de la flota
—`coipo_atraso_personal` (`ci.yml` y `deploy.yml`) y la plantilla de
`semilla/ESQUELETO`— iban en `modo: advisory`, así que `v2` no puede poner rojo
el despliegue de nadie. `coipo_prensa2` fija un SHA y no se ve afectada.

### `v2.0.1`, 2026-09-08 — y `v2.0.0` está ROTA

**`v2` apunta a `v2.0.1` (`7b4b2632`).** Si usas `@v2`, ya tienes esto.

> ## ⚠ NO USES `@v2.0.0`
>
> `v2.0.0` (`69d50046`) **falla siempre**, en cualquier repositorio, incluso en
> `modo: advisory`. Su `ref_jueces` tiene `default: ""` y el paso que intentaba
> deducir la referencia del contexto muere con:
>
> ```
> ##[error]No se pudo determinar con que version de los jueces verificar.
>   job_workflow_ref=''  ref_jueces=''
> ```
>
> `advisory` no salva: el fallo es del paso, no de `correr.py`, así que el job
> sale rojo entero. **Es un tag anotado e inmutable: no se puede arreglar, sólo
> avisar.** La salida es subir a `@v2` o `@v2.0.1`; o, si de verdad hay que
> quedarse en ese commit, pasar `ref_jueces` explícito.
>
> Estuvo publicado unas horas y `v2` lo apuntó durante ese rato. Si algún
> repositorio quedó rojo por esto, el síntoma es el de arriba.

Qué arregla `v2.0.1`: el `default` de `ref_jueces` vuelve a ser la mayor literal
(`v2`), y `tests/test_verificar_yaml.py` impide que se quede atrás — con
`fetch-depth: 0` en `autotest.yml`, porque sin tags esa prueba se saltaba sola y
**justo en el CI**, que era el único sitio donde corre sin que nadie la invoque.

### `v2.0.2` y `v2.0.3`, 2026-09-08 — la revisión adversaria

**`v2` apunta a `v2.0.3`** (`git rev-list -n1 v2.0.3` da el commit). `v2.0.2`
(`84006329`) arregló que el guardián del `default` no corriera en el CI y tres
defectos suyos; `v2.0.3` cierra lo que salió de una revisión adversaria de 40
hallazgos sobre el motor entero. Todo compatible: ningún repositorio cambia de
veredicto, salvo dos casos que estaban mal:

- `coipo_n8n` pasa de rojo a `NO_APLICA` en `j11`: software de terceros —compose
  sin `build:` y ni una línea de Python— no tiene que escribir un `/health`; lo
  expone la imagen y lo vigila el healthcheck. Las tres condiciones a la vez: un
  repositorio vacío sigue sin ser N/A.
- Un juez con hallazgos **nunca** sale `SIN_EVALUAR`: los hallazgos mandan en la
  etiqueta y lo no evaluado sigue en su lista. Antes el informe decía «no comprobó
  nada» y a la vez emitía `::error::` y exit 1. El exit no cambia.

Qué más arregla, por si algún síntoma le suena:

- `carga_yaml` ya no revienta con `command: --5`, y rechaza anclas y alias en
  posición de valor (`x: &a`, `<<: *a`, `- *a`) con `YamlNoSoportado` en vez de
  colgarlos de la raíz en silencio. Un BOM al inicio de `.env.example` ya no
  produce cinco bloqueantes falsos.
- `adopta:` **vacío** en `.semilla` es `SIN_EVALUAR` con motivo, no un
  `NO_APLICA` gratis.
- `j13` deja de leer comentarios CSS: ni un `/* prefers-reduced-motion */` de
  cabecera hace de bloque, ni tapa un bloque selectivo; y en el `@media` oscuro
  ve **todas** las reglas, no sólo la primera.
- `correr.py`: un juez mal nombrado (`j7_x.py`) o que revienta sale con exit 1 y
  lo dice; y las salidas del job llevan centinela (`estado=no_corrio`,
  `bloqueantes=-1`) para que el workflow no lea vacío como cero.
- `verificar.yml`: el artefacto lleva modo, perfil, etiqueta e intento en el
  nombre —dos jobs del mismo run ya no chocan— y `autotest.yml` fija todos sus
  `uses:` a SHA.
- `semilla.lock` resellado: `verify-banner.mjs` cambió en la fábrica (filete
  por gerencia). Hasta que la fábrica fusione esa rama, su `main` y este lock no
  coinciden — el paso «lock de la mayor vigente» de `coherencia.yml` lo dice.

Doce pruebas nuevas en `tests/test_revision_2026_09_08.py`, una por defecto
reproducido; 175 verdes.

### `v2.0.4`, 2026-09-08 — y `v2.0.3` está ROTA

**`v2` apunta a `v2.0.4`.** Si usas `@v2`, ya tienes esto.

> ## ⚠ NO USES `@v2.0.3`
>
> `v2.0.3` (`e26a0014`) **falla siempre**, en cualquier repositorio y en
> cualquier modo, y ni siquiera llega a tener jobs: GitHub rechaza el archivo.
> El síntoma, en el run del llamante:
>
> ```
> X This run likely failed because of a workflow file issue.
> ```
>
> sin log y sin pasos. Dos causas, las dos en `verificar.yml` y las dos
> invisibles para la suite: el paso `correr` llevaba **dos claves `env:`**
> (PyYAML se queda con la última sin avisar) y un comentario del `run:` tenía
> una **expresión vacía `${{ }}`** — GitHub evalúa las expresiones también
> dentro de los comentarios del shell. La misma clase de desastre que
> `v2.0.0`: un tag anotado no se arregla, sólo se avisa. `actionlint` señala
> las dos; conviene pasarlo en local antes de publicar.
>
> `v2` apuntó a `v2.0.3` durante unos doce minutos (20:46–20:58 del
> 2026-09-08) y volvió a `v2.0.2` de forma provisional hasta `v2.0.4`. Un run
> de `coipo_atraso_personal` cayó en esa ventana; el resto de la flota fija
> SHA o no llama todavía.

Lo que protege desde `v2.0.4`, y por qué dos cosas:

- `tests/test_workflows_yaml.py`: un escáner de claves repetidas, sin PyYAML
  (aquí no hay), que caza el archivo de `v2.0.3` tal cual. Es barato y corre en
  local antes del push.
- **`autotest.yml` llama al reusable** (`uses: ./.github/workflows/verificar.yml`)
  con `ref_jueces: ${{ github.sha }}`. La única validación que cuenta es la de
  GitHub, y sólo la hace al invocar el archivo. Antes ninguna prueba lo
  invocaba: el reusable que juzga a 24 repositorios nunca se había ejecutado a
  sí mismo en su propio CI.

Lección para `Publicar`, arriba: **la suite verde no es la validación del
YAML**. Antes de mover `v2`, mirar que el run de `Autotest` del commit incluya
el job `el-reusable-lo-valida-github` en verde.

### `v2.0.5`, 2026-09-09 — el lock, tras arreglar lo que hacía nacer roja a cada aplicación

> Esta entrada y la de `v2.0.6` se escribieron el 2026-11-21: los dos tags existían
> (`git tag -l`) y este archivo saltaba de `v2.0.4` a `v2.0.7`. Lo de abajo sale de los
> mensajes de sus commits y de `git diff v2.0.4 v2.0.5`, no de memoria.

Tag sobre `8b9e74f` (PR #3, commit `7c68159`). **Ningún juez cambia**: cambian
`semilla.lock`, dos filas de `REGLAS.md`, `FILAS_REGLAS_UI.md` y un docstring de
`tests/test_reglas_citadas.py`. El lock pasa de **21 a 20 archivos**, porque la fábrica
arregló tres defectos que llegaban tal cual a cada aplicación nueva:

- `backend/tests/contrato/test_health.py` (sellada): su expresión rechazaba
  `http://127.0.0.1:8000/health`, el healthcheck que escribe el propio esqueleto, y la
  compuerta `t0` de toda aplicación sembrada salía roja sin poder arreglarlo.
- `backend/Dockerfile` y `frontend/Dockerfile`: el backend copia `requirements.txt` (de
  la aplicación) y `requirements-base.txt` (sellado); el frontend usa `npm ci` con el
  lock que el esqueleto ya versiona. `requirements.txt` y `requirements-dev.txt` salen
  del lock; entran `requirements-base.txt` y `requirements-dev-base.txt`.
- `.dockerignore` sale del lock (`NO_SE_SELLA`): cada aplicación lo amplía.

Medido entonces con la semilla materializada: nueve jueces, 21 comprobaciones, 0
bloqueantes.

### `v2.0.6`, 2026-09-09 — el arnés del verificador de banner

Tag sobre `64803f8` (PR #4, commit `dc4a01e`). Sólo cambia una huella de
`semilla.lock`: `frontend/scripts/verify-banner.mjs` pedía los banners en una ruta que la
semilla no siembra (`src/assets/`, heredada de `COIPO_USUARIOS`), así que
`npm run verificar:banner` no podía pasar en ninguna aplicación recién sembrada. Ahora
pide `/banner.jpg` y `/banner-corto.jpg`, como el componente real. Ningún juez cambia.

### `v2.0.7`, 2026-09-15 — el lock, tras arreglar la semilla

**`v2` apunta a `v2.0.7`.** No cambia ni un juez: lo único que cambia es
`semilla.lock`, porque `semilla/CONGELADO/` de la fábrica se corrigió en tres
piezas y ganó una cuarta.

| Pieza sellada | Por qué cambió |
|---|---|
| `backend/app/core/auditoria/clasificacion.py` | `log_acceso.ip_red` y `ua_familia` no declaraban `accion_al_vencer`; el módulo **reventaba al importarse**. Pasan a `ELIMINAR` |
| `backend/tests/conftest.py` | el guard metía el `DATABASE_HOST` del `.env` local en la denylist de producción: desarrollar con Postgres en `localhost` abortaba la suite con código 2 |
| `frontend/scripts/verify-banner.mjs` | su ayuda decía `npm run verify:banner` —el script es `verificar:banner`— y el arnés enlazaba `componentes.css`, que no existe |
| **nueva** `backend/tests/contrato/test_todo_importa.py` | importa cada módulo de `app/` y falla nombrando cuál. Va sellada para correr en la compuerta `t0` de **cada** aplicación: el defecto de la primera fila llevaba meses llegando a cada aplicación nueva porque el CI sólo importaba `app.main` |

**Por qué es `v2.x` y no una mayor**, medido antes de publicar y no deducido —
los tres criterios de «Cuándo toca una mayor nueva», uno por uno:

1. Ningún juez nuevo y ninguna regla cambia de severidad. `jueces/` no se toca.
2. `verificar.yml` no cambia: ninguna entrada nueva, ninguna semántica distinta.
3. **Nadie que hoy esté verde se pone rojo.** Corriendo el gate con este lock:

   | Repositorio | Qué le llega | Resultado |
   |---|---|---|
   | `coipo_atraso_personal` | `@v2` móvil, `modo: advisory` en `ci.yml` y `deploy.yml`; su `.semilla` no declara `adopta:`, así que `j12` sí lo juzga | 19 comprobaciones, **3 bloqueantes**, `exit 0`: advisory los publica y no rompe el build. Se cierran pasándole `sembrar.py --destino . --actualizar`, que reescribe sólo lo sellado |
   | `coipo_prensa2` | nada: fija el SHA `84006329` (v2.0.2) en el `uses:` **y** en `ref_jueces`, las dos mitades | 22 comprobaciones, 0 bloqueantes, 9 avisos, 1 supresión — idéntico a antes |
   | `coipo_n8n` | no llama al reusable | 11 comprobaciones, 0 bloqueantes |
   | la plantilla de `semilla/ESQUELETO` | `@v2` móvil, advisory | sembrada de cero: 21 comprobaciones, **0 bloqueantes, 0 avisos** |

   Es el mismo razonamiento con el que se publicó `v2`, con los números de hoy.

Antes de mover el tag: `python -m unittest discover -s tests` → **181 OK** (1 skip),
y el run de `Autotest` de `3866d7e` con `el-reusable-lo-valida-github` en verde —
la lección de `v2.0.3`, que la suite verde no valida el YAML.

### `v2.0.8`, 2026-09-15 — un backtick dentro de una plantilla

**`v2` apunta a `v2.0.8`.** Una sola pieza sellada cambia,
`frontend/scripts/verify-banner.mjs`, y por un defecto que se publicó en
`v2.0.7`: el comentario que se le añadió llevaba rutas **entre backticks**, y ese
arnés HTML vive dentro de una plantilla de JavaScript. Un backtick la termina, así
que el archivo entero dejaba de parsear:

```
SyntaxError: Unexpected identifier 'estilos'
```

`npm run verificar:banner` moría ahí, en cualquier aplicación que lo corriera.

**Radio de explosión de `v2.0.7`, que es lo que importa aquí:** el tag estuvo
vigente unos veinte minutos y ningún repositorio de la flota corrió
`verificar:banner` en esa ventana —`coipo_atraso_personal` no llegó a ese paso y
`coipo_prensa2` fija SHA—. El único que lo ejecutó fue el CI de la propia fábrica,
que es exactamente donde tenía que aparecer: el job `semilla-materializada`
siembra un proyecto y le corre lo que correrá su aplicación.

**La lección, que ya estaba escrita una vez para `v2.0.3`:** la suite verde no
valida lo que no ejecuta. `tests/` no toca ese `.mjs` y el gate tampoco; lo único
que lo prueba es correrlo. En local se comprueba con `node --check`.

### `v2.0.9`, 2026-09-26 — el runner se puede elegir

La organizacion agoto los 2000 min/mes de Actions del plan Free y eso bloqueo
despliegues a produccion: siete repositorios tienen su `deploy` con `needs:`
hacia este reusable, asi que sin cuota la compuerta no arranca y el despliegue
—que corre en un runner self-hosted y es GRATIS— nunca llega a ejecutarse.

Se anade el input `runner`, que por defecto vale `ubuntu-latest`. Apuntandolo a
la etiqueta de un runner self-hosted, la compuerta deja de consumir cuota sin
perder ni una comprobacion. Los jueces son de biblioteca estandar, asi que a la
maquina solo se le piden `git` y `python3`.

**Por que es `v2.x` y no `v3`:** el input es opcional y su valor por defecto
reproduce el comportamiento anterior. Quien no lo pase no nota nada, que es
justamente el criterio de esta casa para no forzar una mayor.

**Radio de explosion:** ninguno. Con el default, `runs-on` resuelve a
`ubuntu-latest` igual que antes. Solo cambia el comportamiento de quien pase
`runner:` explicitamente.

### `v2.0.10`, 2026-09-27 — el lock, otra vez, y esta vez el rojo lo cazo el propio j12

**`v2` apunta a `v2.0.10`.** Ni un juez cambia. Lo unico que cambia es una linea de
`semilla.lock`: el hash de `backend/requirements-base.txt`.

Qué pasó, en orden, porque la secuencia es la lección:

1. El 2026-09-26 se le puso techo de mayor a `sqlalchemy` en la semilla
   (`>=2.0.52,<2.2` en vez de un rango abierto), tras dos averías de producción en la
   misma semana causadas por SQLAlchemy 2.1.
2. Se actualizó el fichero en `semilla/CONGELADO/` **y** en las dos aplicaciones que lo
   usan, `coipo_api` y `coipo_atraso_personal`. Los tres quedaron byte a byte idénticos.
3. **No se volvió a sellar.** Así que el lock publicado seguía describiendo el contenido
   anterior.
4. `j12` hizo exactamente su trabajo: `[BLOQUEA] SEM-1 backend/requirements-base.txt`,
   «es una pieza CONGELADA de la semilla y está editada». En `coipo_atraso_personal`,
   que corre los jueces en **bloqueante**, eso puso el CI en rojo.

Y la parte incómoda: durante unas horas pareció un falso positivo. Los tres ficheros
eran idénticos, así que «está editada» sonaba a error del juez. No lo era. **El juez no
compara la app contra la semilla: la compara contra el lock**, que es lo único que viaja
al CI de cada aplicación. La semilla y las apps se habían movido juntas y el lock se
había quedado atrás — que es literalmente el fallo que el paso «El semilla.lock publicado
esta al dia» de `coipo_master_produccion` existe para cazar, y lo cazó.

Nota para quien busque el lock: **no está en `coipo_master_produccion`.** Vive aquí,
porque tiene que ser público para que lo lea el CI de cada app. Buscarlo en la fábrica y
no encontrarlo hizo perder tiempo.

**Por qué es `v2.x` y no una mayor** — los tres criterios, medidos:

1. Ningún juez nuevo y ninguna regla cambia de severidad. `jueces/` no se toca.
2. `verificar.yml` no cambia: ninguna entrada nueva, ninguna semántica distinta.
3. **Nadie que hoy esté verde se pone rojo.** Corrido antes de mover el tag, con el lock
   viejo y con el nuevo:

   | Repositorio | Con el lock de `v2.0.9` | Con este lock |
   |---|---|---|
   | `coipo_atraso_personal` (`@v2`, **bloqueante**) | **1 bloqueante**: `SEM-1` sobre `requirements-base.txt` | 22 comprobaciones, **0 bloqueantes**, 0 avisos |
   | `coipo_api` (`@v2`, advisory) | 0 bloqueantes, 6 avisos | 0 bloqueantes, los mismos 6 avisos |
   | `coipo_prensa2` | no le llega: fija el SHA `0c6e8b6d` en el `uses:` **y** en `ref_jueces` | idéntico |

   Es el único caso hasta hoy en que mover el lock **quita** un bloqueante en vez de
   arriesgar uno nuevo: el rojo lo estaba causando el lock viejo.

Antes de mover el tag: `python -m unittest discover -s tests` → **181 OK** (1 skip), y la
calibración de este repositorio contra sí mismo en `--modo bloqueante --perfil
encuadre_operativo` → 6 jueces, 6 comprobaciones, **0 bloqueantes**, 1 supresión.

### `v2.0.11`, 2026-09-30 — el lock, por tercera vez: resellado en local y no publicado

**`v2` apunta a `v2.0.11`.** Ni un juez cambia. Cambia `semilla.lock` (23 archivos): cinco
entradas, tres con hash nuevo y dos nuevas.

| Pieza sellada | Qué pasó |
|---|---|
| `backend/app/dominio/modelo/identidad.py` | cambió (la fábrica, commit `f1d776a`, 2026-09-29: la clase `Identidad` estaba definida dos veces) |
| `backend/app/adaptadores/salida/iam/cliente_iam.py` | cambió |
| `backend/tests/arquitectura/test_capas.py` | cambió |
| **nueva** `backend/app/adaptadores/salida/iam/mapeo_claims.py` | `conftest.py` la pedía y no existía |
| **nueva** `backend/tests/contrato/test_la_semilla_importa.py` | importa todo `app/` y ejecuta el mapeo de claims |

La secuencia, que es la lección repetida de `v2.0.10`: `semilla/CONGELADO/` cambió el
2026-09-29; el lock se resello **en local** ese mismo día y **no se commiteó ni se publicó**.
El lock publicado (`v2.0.10`, sellado el 2026-09-26) seguía describiendo la semilla anterior,
y el CI de la fábrica (`coherencia.yml`) quedó rojo en `coherencia` (pasos «lock al día» de
`main` y de la mayor) y en `semilla-materializada` (`j12`: `SEM-1` sobre los tres archivos que
cambiaron). Se reprodujo en local paso a paso; no se leyeron los logs de GitHub.

**Por qué es `v2.x` y no una mayor** — los tres criterios, uno por uno:

1. Ningún juez nuevo y ninguna regla cambia de severidad. `jueces/` no se toca.
2. `verificar.yml` no cambia.
3. **Nadie que hoy esté verde en su build se pone rojo.** Medido sobre las seis aplicaciones con
   `.semilla` que había en un disco local (no son las 24 de la flota), comparando cada archivo
   sellado contra el lock viejo y el nuevo:

   | Repositorio | `modo:` | Con este lock |
   |---|---|---|
   | `coipo_visor_saff`, `coipo_visor_sidco` | advisory | **3 hallazgos `SEM-1` nuevos** (`identidad.py`, `cliente_iam.py`, `test_capas.py`: aún tienen la versión anterior). `advisory` los publica y no rompe el build. Se cierran con `sembrar.py --destino . --actualizar` |
   | `coipo_avisete`, `coipo_api` | advisory | dejan de tener 3 hallazgos `SEM-1`: sus archivos ya eran los nuevos |
   | `coipo_prevension_ministerial`, `COIPO_PRENSA2` | no medido | ningún archivo que cambió en este lock les difiere de él; sus diferencias (`Dockerfile`, `nginx.conf`, `pytest.ini`, `conftest.py`) ya existían con el lock viejo |

   Quien tenga la versión anterior de `identidad.py` tiene el defecto de la clase duplicada:
   `cliente_iam.py` construye la primera y la segunda la pisa, y el callback del primer login
   falla con `TypeError`. Ese es el motivo de que el hallazgo convenga, no sólo moleste.

Antes de mover el tag: `python -m unittest discover -s tests` → **181 OK** (1 skip), y la
calibración de este repositorio contra sí mismo en `--modo bloqueante --perfil
encuadre_operativo` → 6 jueces, 6 comprobaciones, **0 bloqueantes**, 1 supresión.

### `v2.0.12`, 2026-10-24 — `j16` (código mantenible) y el historial de locks

**`v2.0.12` es `02d9dd18`.** Trae `j16_codigo` (`COD-1` tamaño, `COD-2` TypeScript,
`COD-3` capas; regla 9 de `AGENTS.md` de la fábrica), `j12` con
`semilla.lock.historial` (una pieza atrasada AVISA siempre; sólo la editada
BLOQUEA) y el lock de 42 piezas.

**Por qué `v2.x` y no `v3`**, con lo que se midió (tablas de calibración de
`jueces/j16_codigo.py` y `jueces/j12_semilla.py`, y la medición del 2026-10-25 de
abajo):

- `j16` BLOQUEA sólo con `fabrica:` del 2026-10-24 o posterior. Ninguna aplicación
  del disco lo tenía al publicar (la más reciente, `coipo_firms`, 2026-10-23): CERO
  `BLOQUEA` nuevos. El resto AVISA o sale `NO_APLICA`.
- `j12` con historial QUITA bloqueos: de 79 `BLOQUEA` en diez aplicaciones
  sembradas a 5 en tres, y los 5 son ediciones de verdad.
- `coipo_atraso_personal`, la única `@v2` en modo bloqueante, ya estaba en rojo
  antes, por `j12` (`SEM-1` sobre `mapeo_claims.py`, una edición real del
  2026-09-25); `j16` no le añade ningún `BLOQUEA`.

Fue, en la práctica, la primera publicación bajo la enmienda de arriba, escrita un
día después.

### `v2.0.13`, 2026-10-25 — `j14` (construir con la fábrica)

**`v2.0.13` es `1a2d589a`, y `v2` apunta ahí.** Trae `j14_construccion` (`FAB-8`:
`docs/CONSTRUCCION.md` con el rastro de IGNUS), `COD-3` en los servicios hermanos
(`collector/`) y el lock resellado (`requiere_db` exige base).

**Radio de explosión, medido el 2026-10-25** sobre los 88 repositorios `coipo*` con
git de `D:\GitHub`, perfil `aplicacion`, modo bloqueante: `j14` y `j16` emiten
**cero `BLOQUEA`** en los 88. `j14` juzga a los 12 que llevan `.semilla`: once
AVISAN y `coipo_firms` sale OK; los 76 restantes, `NO_APLICA`.

**La vigencia de `j14` es ANTERIOR a su publicación, y se dice.** `VIGENCIA =
"2026-10-20"` (la fecha de `AGENTS.md`, §3.8), y el juez se publicó el 2026-10-25.
Cualquier aplicación sembrada entre esas dos fechas nació ya bajo una regla que
ningún CI le comprobaba, y BLOQUEA desde el primer push tras mover `v2`. En el
disco hay UNA: `coipo_firms` (`fabrica: 2026-10-23`), y pasa (`OK`, seis
`correlation_id`). Fuera del disco: DESCONOCIDO.

Entró por error `HUSKY_AUDIT.md` en la raíz (`3ba3775`), la salida de una
auditoría ajena; se quitó en la rama `arreglos-auditoria-2026-10-25`.

### `v2.0.14`, 2026-10-25 — los arreglos de la auditoría

Arreglos de una auditoría del 2026-10-25 (cada uno con su prueba, escrita antes y
vista fallar, y su mutación), rama `arreglos-auditoria-2026-10-25`, PR #10. Lo que
sigue es el radio medido antes de decidir su número.

Medido sobre los mismos 88 repositorios, `main` (`1a2d589`) contra la rama,
perfil `aplicacion`, modo bloqueante:

- **63 `BLOQUEA` desaparecen, todos explicados:** 13 `G8-4` de
  `# MINIO_ACCESS_KEY=<usuario>` (un identificador, no un secreto: `coipo_n8n` y
  `coipo_prensa2` quedan en verde); 50 `G8-9` «no se encontró `/health`»: 3 porque
  el `/health` lo responde el nginx interno con `return 200` (`coipo_tv`,
  `coipo_boton_rojo`, `coipo_prevension_ministerial`), 2 porque un
  `location /health` del nginx interno hace de proxy y se anota como no verificado
  (`coipo_pgbackrest`, `coipo_seguimiento_madera`), y 45 porque el repositorio no
  tiene compose y pasa a «no evaluado», como en `j01` y `j06` (SIN_EVALUAR, que en
  perfil `aplicacion` bloqueante sigue saliendo 1).
- **1 `BLOQUEA` nuevo:** `UI-3` en `coipo_prevension_ministerial`. Su `.semilla`
  declara `adopta:` como lista YAML en bloque (`- interfaz`), que `main` leía VACÍA
  y dejaba a `j13` en SIN_EVALUAR; leída bien, `j13` juzga lo que el repositorio
  declara. Su `exit` no cambia (1 → 1) y su `deploy.yml` corre en `advisory`.
- `coipo_atraso_personal` no cambia: 1 `BLOQUEA` (`j12`) antes y después.
- Avisos nuevos (`G8-7`, `OPS-1`) en `coipo_cron_master` y
  `coipo_seguimiento_madera`, cuyos compose el parser ahora entiende.

Por la letra de «Cuándo toca una mayor nueva», ese `BLOQUEA` nuevo hace de esto
una mayor; por la enmienda, es un veredicto que cambia en una aplicación que no
estaba en verde.

**Decidido por Luis Monsalve el 2026-10-25: `v2.0.14`, no `v3`.** Es el arreglo de
un lector que ocultaba un juez (el `adopta:` en bloque se leía vacío), no una regla
nueva: lo que `j13` exige a ese repositorio es lo que su propio `.semilla` declaró
adoptar. Ningún `exit` pasa de 0 a 1 en los 88 repositorios medidos. Queda como
precedente de la enmienda: arreglar una lectura que dejaba sin juzgar a quien sí
pidió ser juzgado es `vN.x`.

### `v2.0.15`, 2026-11-12 — la maqueta validada, `FAB-9` y `ajeno:`

Decidido por Luis Monsalve el 2026-11-12, tras ver que la fábrica destruía las maquetas
que el cliente ya había validado (`coipo_catastro_equipo`, `coipo_gobernanza_curso`):

- **`maqueta:` en `.semilla`** (la escribe `sembrar.py --maqueta` de la fábrica): `j13`
  sale `NO_APLICA` **sin** contar supresión, `j16` no mide `maqueta/` ni
  `frontend/src/maqueta/`, y `j12` avisa con **`MAQ-1`** si la cara copiada no coincide
  con su sha256 de `maqueta/PROCEDENCIA.md` (con `\r\n` normalizado).
- **`ajeno:` en `.semilla`**: carpetas que `j16` no mide; cada una, una supresión publicada.
- **`FAB-9`** (`j14`): `mirado:` en `CONSTRUCCION.md`. BLOQUEA lo sembrado desde el
  **2026-11-13** —el día siguiente a la publicación— y AVISA en lo anterior.

Radio medido sobre los 84 repositorios `coipo*` del disco, `v2` (`a814f5c`) contra la
rama, perfil `aplicacion`, con `j12`, `j13`, `j14` y `j16`, sin ninguno sin medir:

- **Primera medición, con vigencia del 2026-11-12: 2 `BLOQUEA` nuevos**, en
  `coipo_catastro_equipo` y `coipo_catastro_equipos`, sembradas ese mismo día antes de
  que la regla existiera. Eso es mayor nueva; se corrigió la vigencia, no el número.
- **Segunda medición, con vigencia del 2026-11-13: 0 `BLOQUEA` nuevos.** Cambian 8
  veredictos de `j14` de `OK` a `HALLAZGOS`, todos por avisos de `FAB-9`
  (`coipo_catastro_equipo`, `coipo_catastro_equipos`, `coipo_catastro_incendio`,
  `coipo_firms`, `coipo_gobernanza_curso2`, `coipo_pee_visor`, `coipo_presupuesto_erp`,
  `coipo_silvicultura`); la cuenta de bloqueantes de cada uno es la misma antes y después.

Por la enmienda del 2026-10-25, un juez que sólo bloquea lo sembrado desde su vigencia y
no cambia el veredicto bloqueante de nada que exista va en `vN.x`. Suite: 322 pruebas.

### `v2.0.16`, 2026-11-14 — `COD-4` y el log inmutable probado en Postgres

Entra a partir de la pregunta de Luis Monsalve del 2026-11-14, «¿son suficientes los
tests que se siembran?». Él autorizó la publicación ese mismo día.

- **`COD-4`** (`j16`, **sólo AVISA**): cada caso de uso tiene una prueba versionada que
  lo nombra, buscada con límites de palabra. Los auxiliares que empiezan con `_` no
  cuentan. Fuente: `docs/ESTANDAR_CODIGO.md` de la fábrica, COD-4.
- **`semilla.lock`**: pasa de 42 a 43 piezas. Entra
  `backend/tests/contrato/test_log_inmutable.py`, que se marca `requiere_db`. `j12` sólo
  juzga las piezas presentes, así que una aplicación sembrada antes sin ella no recibe
  ningún hallazgo.

Radio medido con `flota/consumidores.py --lock-candidato`, comparando el lock de `v2`
(`47677eb`) con el candidato. El resultado es idéntico: 4 en rojo y 1 que frenaría el
despliegue, los mismos de hoy (`coipo_api`, `coipo_atraso_personal`, `coipo_avisete`,
`coipo_visor_saff`, por piezas editadas). Hay **0 `BLOQUEA` nuevos**.

`COD-4` se calibró sobre los 91 repositorios `coipo*` del disco y dio 2 avisos, los dos
reales (`coipo_atraso_personal`, `coipo_avisete`). Suite: 327 pruebas.

### `v2.0.17`, 2026-11-14 — `test_guards.py` en el lock

Luis Monsalve autorizó esta publicación el mismo día. Lo único que cambia es `semilla.lock`,
que pasa de 43 a 44 piezas: entra `backend/tests/contrato/test_guards.py`, la prueba de
contrato de `exigir_rol`, el ámbito y el 404 sin oráculo. El docstring de `guards.py` ya la
citaba, pero la semilla no la traía. `j12` sólo juzga las piezas presentes, así que una
aplicación sembrada antes no recibe ningún hallazgo nuevo.

El radio, medido con `consumidores.py --lock-candidato`, da lo mismo con el lock de `v2`
(`v2.0.16`) que con el candidato. Siguen los 4 rojos de antes (`coipo_api`,
`coipo_atraso_personal`, `coipo_avisete`, `coipo_visor_saff`), con PR abierto o con una
decisión pendiente. **0 `BLOQUEA` nuevos.**

### `v2.0.18`, 2026-11-14 — conservación permanente

Decisión de Luis Monsalve del 2026-11-14: en la flota no se purga ni se desidentifica nada.
Él mismo autorizó esta publicación. `semilla.lock` pasa a 45 piezas:

- **Nueva** `db/0000_10_conservacion_permanente.sql`. Retira las tres `fn_purgar_*` y deja
  el DELETE prohibido siempre en los tres logs.
- **Cambia** `clasificacion_catalogo.py`. Todo queda `permanente`, y las 10 columnas que
  estaban en ELIMINAR pasan a CONSERVAR_JUSTIFICADO con su firma.
- **Cambia** `test_log_inmutable.py`. Comprueba que ya no exista ninguna purga y que un
  DELETE se rechace aunque esté puesto el antiguo flag.

Radio medido con `consumidores.py --lock-candidato`: hay **0 `BLOQUEA` nuevos** (siguen los
mismos 4). Los avisos por piezas atrasadas pasan de 9 a 15: son las aplicaciones cuyo
catálogo de clasificación es el anterior, y `j12` los marca como atrasados, no como
editados. Una aplicación desplegada deja de poder purgar sólo cuando corre
`sembrar.py --actualizar` y su arranque aplica la `0000_10`. La base legal sigue marcada
[VERIFICAR con Fiscalía].

### `v2.0.19`, 2026-11-14 — `test_log_inmutable.py` con cualquier runner de migraciones

Autorizada por Luis Monsalve el mismo día. El lock sigue con 45 piezas, pero cambia la huella
de `backend/tests/contrato/test_log_inmutable.py`.

Esa prueba sellada llamaba a `migraciones.aplicar(..., esquema=)`, y el parámetro `esquema`
sólo existe en el ESQUELETO desde el 2026-10-29. En `coipo_visor_saff`, sembrada antes, el CI
reventaba con `TypeError`.

La versión nueva:
- crea el esquema y lo fija en el `search_path` de la URL (`postgresql+psycopg://`);
- pasa `esquema=` sólo si el runner de la app lo acepta.

Se probó con los dos runners. **0 `BLOQUEA` nuevos:** la pieza anterior queda en el historial,
así que una app que la tenga sólo recibe un aviso de atrasada.

### `v2.0.20`, 2026-11-21 — el gate que no miente, la auditoría siempre (`AUD-1`), el Zen (`COD-5`) y el lock con la auditoría

Autorizada por Luis Monsalve el 2026-11-21: en el plan aprobado ese día («Publicación, al
final y en este orden») y, con el radio de abajo a la vista, al elegir que `j12` avisara antes
de publicar. **Reversión:** antes de este tag `v2` apuntaba a
`26301b98ef588b84e41bcd43c70e8c5b4dc0ca91` (`v2.0.19`). El tag se crea sólo con `Autotest` en
verde sobre su commit, en GitHub (`docs/publicar-los-jueces.md` de la fábrica).

Lo que entra, después de `v2.0.19`:

Commits anteriores a esta tanda:

- `5c84057` — `j12`: `SEM-2` para `backend/paquetes-sistema.txt`, y el lock de la semilla
  del 2026-11-20.
- `c73a20c` — `semilla.lock`: `test_guards` y `test_log_inmutable` desde
  `coipo_informe_sapif`.
- `c347f53` — repositorio público: sin el detalle de secretos de otra aplicación ni IPs
  internas (la redacción de P0; no se deshace).

La tanda «P1a — que el gate no mienta» (2026-11-21), un commit por tema:

| Tema | Qué cambia en lo que el gate dice |
|---|---|
| Trazabilidad | `DOCKER-hc` pasa a `DK-5`; `test_reglas_citadas` lee el primer argumento de TODA llamada a `bloquea`/`avisa` y falla ante un alias |
| `j02` | el lado del host de `ports:` se lee entero (`127.0.0.1:${APP_PORT:?msg}:8000`, valores anidados) |
| `j11` | `G8-9` ve `Depends()` por defecto, `dependencies=[...]`, `sesion_actual` y `RedirectResponse`; **`SEM-4`** (AVISA): el cuerpo de `/health` lleva `app` |
| `j13` | sin ningún tema oscuro, `UI-3` es un hallazgo (antes «no evaluado» y OK): BLOQUEA en lo sembrado desde el 2026-11-22, AVISA en lo anterior |
| `j16` | **`COD-5`** (AVISA): el CI corre `ruff check`/`ruff format --check` y `npm run lint` con las reglas del Zen, no más blandas que las de la semilla (lo mira `comun_zen.py`, lo emite `j16`). Calibrado: una siembra de hoy, 0; `coipo_app`, 4 |
| `j12` | **`AUD-1`**: la auditoría siempre y el último ingreso de cada persona (piezas selladas, `montar_acceso(` en `main.py`, ruta `ultimos-ingresos`, vistas `Actividad` y `UltimosIngresos`). BLOQUEA en lo sembrado desde el 2026-11-22, AVISA en lo anterior. Calibrado: una siembra de hoy, 0; `coipo_informe_sapif` (2026-11-19), 9 avisos |
| Trazabilidad | un `comun_*.py` no puede emitir: la prueba sólo lee `jueces/j*.py`, y `COD-5` escrito en un auxiliar pasaba sin fila en REGLAS.md (visto en rojo) |
| `.env` | un solo `ignora_env()` para `j01` y `j08`; `j09` deja el `.gitignore` a `G8-8`; la lista de Vite exige el sufijo de modo |
| `j01` | `NG-1` sólo exime el upstream en `$variable`: un nombre literal con `resolver` avisa |
| `j12` | **`SEM-3`** (AVISA): falta una pieza sellada de `backend/tests/` |
| Motor | la consola dice la severidad real en advisory; lo que no se miró es N/A y no una comprobación; un solo lector de claves de `.semilla`; `Repo.compose()`, `alcance_semilla`, `no_adopta` y `Siembra` en vez de cuatro copias |
| Workflows | `verificar.yml` expone `estado` y `avisos` y no persiste la credencial; `autotest.yml` con actionlint (versión y sha256 fijados) y ruff; fuera `probar-runner.yml` |
| Zen de Python | `ruff.toml` copiado de la semilla; `ruff check` en cero, y `ruff format` en el último commit de la tanda, solo |

**Radio medido** (2026-11-21), el gate en advisory sobre los mismos 88 clones de
`D:\GitHub` que la línea base del 2026-11-20, más la siembra fresca `coipo_prueba3` y una
copia suya con los archivos en el índice; `main` antes de la tanda (`c347f53`) contra el
final. **BLOQUEA: 180 → 183** (sobre los 88 de la línea base: 141 → 144); **AVISA: 555 →
613**. Los tres `BLOQUEA` nuevos, uno por uno:

- `coipo_app`, **0 → 1**: `UI-3` sin tema oscuro. Declara `adopta: semilla, interfaz` y su
  CSS no tiene ni una regla de tema oscuro. **Es un repositorio verde que pasa a rojo**
  (consume `@v2` en advisory en sus tres workflows, así que su build no se rompe). Por la
  letra de «Cuándo toca una mayor nueva», eso es mayor nueva; el precedente de `v2.0.14`
  —«arreglar una lectura que dejaba sin juzgar a quien sí pidió ser juzgado es `vN.x`»—
  se escribió con la condición de que ningún `exit` pasara de 0 a 1, y aquí en
  bloqueante pasaría. **Resuelto el mismo día sin mayor nueva** (6bd55bb): como FAB-9,
  «sin tema oscuro» bloquea sólo en lo sembrado desde el 2026-11-22 y avisa en lo
  anterior (FILOSOFIA.md §4 de la fábrica). `coipo_app` queda con un AVISA y sin
  bloqueantes (medido: 0 BLOQUEA, UI-3 en AVISA); el radio de esta tanda baja a
  **BLOQUEA 182** (141 → 143 sobre los 88), contado restando ese caso.
- Un repositorio que ya tenía cuatro: `G8-2`. Una línea `IP:${VARIABLE:?mensaje}:puerto`
  se leía cortada dentro de la guarda y no se juzgaba; publica un puerto por una
  variable que no es `APP_PORT`.
- Otro que ya tenía cinco: `G8-4`, por un `.env` versionado bajo `frontend/` sin sufijo
  de modo, que la lista de Vite dejaba pasar (`j08` ya lo bloqueaba como `G8-10`).

(Este repositorio es público: los dos se nombran en el informe de la tanda, no aquí.)

Ningún `BLOQUEA` nuevo en `coipo_n8n` (0 → 0) ni en la siembra fresca (sus 18 son los de
`docs/CONSTRUCCION.md` sin rellenar, antes y después). Los avisos: −62 `G8-4` (el
duplicado del `.gitignore`), +107 `SEM-3` en 13 aplicaciones sembradas (casi todos el
arnés de `backend/tests/arnes/` y `test_guards`/`test_log_inmutable`, sellados después de
sembrarlas), +11 `SEM-4`, +2 `NG-1` en una aplicación (nombre literal con `resolver`),
y `DOCKER-hc` → `DK-5` en dos repositorios (3 avisos). Los refactores del
motor y de ruff se comprobaron aparte: la misma salida, JSON y consola, en los 90.

Después de medir ese radio entraron:

- `2b9f201` — ERS: `docs/ERS.md` es la fuente y `documentacion/ERS.docx` se genera.
- `af329f8` — `ruff.toml`: la copia al día con el sellado (`[lint.isort]`), y la fábrica la
  compara desde ese día (`herramientas/coherencia.py ruff-de-los-jueces`).
- `7c9180c` — `j14`: el docstring apunta a donde viven hoy la lógica y la prueba de paridad.
- `dd6b779` — **`j12`: una ruta recién sellada no es una pieza editada.** Una pieza que ningún
  bloque del historial nombra es nueva en el lock vigente: AVISA en lo sembrado antes del día
  siguiente al último `vigente_hasta` (o sin `fabrica:`), BLOQUEA en lo sembrado después, y
  sin historial BLOQUEA como siempre. Seis pruebas nuevas y tres mutaciones vistas en rojo.
- `565f1ff` — `semilla.lock` resellado desde `semilla/CONGELADO/` de la fábrica en `5296662`:
  **45 → 54 piezas** (la auditoría siempre, el `ruff.toml` del Zen y lo demás de la tanda); el
  lock anterior entra al historial (18 bloques).
- y este commit: esta entrada y el ERS al día con la publicación.

**Radio del lock**, `flota/consumidores.py --lock-candidato` de la fábrica contra la
organización (2026-11-21; 104 repositorios con el prefijo leídos): 32 consumidores del gate
(2 en `bloqueante`), 20 aplicaciones que `j12` juzga. Con el lock nuevo, antes del cambio de
`j12`, **5** quedaban con un `SEM-1 BLOQUEA`, y 4 de ellas por la misma razón: tenían un
archivo PROPIO en una ruta que el lock sellaba por primera vez (`middleware_acceso.py` y
`backend/ruff.toml` en una, `postgres/auditor.py` en otra, y `rutas/autenticacion.py` —su
login con el IAM— en dos). Con `dd6b779`: **2** con `SEM-1 BLOQUEA`, las dos por piezas que
YA estaban selladas en `v2` y ya bloqueaban (una pieza de pruebas editada en una aplicación
y un `Dockerfile` editado en otra, que su rama `uat` corrige); 18 sólo avisan (atrasadas, o
las 5 rutas propias); **frenarían el despliegue: 0** (las dos van en `advisory`). Ningún
`BLOQUEA` nuevo. Las aplicaciones no se nombran aquí, que es público: van en el informe de la
tanda, en la fábrica.

Verificado en local antes del tag: la suite (449 pruebas, OK), el autojuicio (0 bloqueantes),
`ruff check`/`ruff format --check` y `actionlint` 1.7.12 sobre los tres workflows (visto en
rojo con un `${{ }}` vacío); en la fábrica, una siembra nueva juzgada en `bloqueante` con este
lock sale con 0 bloqueantes y 0 avisos (con el `CONSTRUCCION.md` de prueba de su CI).

### `v2.0.21`, 2026-11-22 — los hooks de Claude Code en el lock, y una ruta sellada que no pierde su gracia al resellar

Autorizada por Luis Monsalve el 2026-11-22 («puedes hacer todo eso»), con el radio de abajo a
la vista. **Reversión:** antes de este tag `v2` apuntaba a
`e04937083fb3b2830554dcbbe24f3d138260f72c` (`v2.0.20`). El tag se crea sólo con `Autotest` en
verde sobre su commit, en GitHub (`docs/publicar-los-jueces.md` de la fábrica).

Lo que entra, después de `v2.0.20`:

- `c6f8ad6` — `REGLAS.md` y `j11` citan el `AGENTS.md` del ESQUELETO, que su `CLAUDE.md`
  importa desde el 2026-11-21 (sólo texto).
- `856c050` — `semilla.lock` resellado desde `semilla/CONGELADO/` de la fábrica en `b8cae41`:
  **54 → 69 piezas**. Las 15 nuevas son los hooks de Claude Code que la semilla siembra desde el
  2026-11-22 a pedido de Luis Monsalve: `.claude/settings.json`, los scripts de
  `.claude/hooks/` (no editar una pieza sellada, el gate antes del push y el inicio de
  sesión), su manifiesto `selladas.json` y el `pre-push` de `.githooks/`. El lock de `v2.0.20`
  entra al historial (19 bloques).
- `b6f00bf` — **`j12`: la vigencia de una ruta sellada es por pieza.** Con la vara de
  `dd6b779` sólo tenían gracia las rutas que ningún bloque del historial nombraba; al resellar,
  el lock anterior entra al historial y sus rutas recién selladas la perdían. Ahora cada pieza
  rige desde el día siguiente al último bloque que todavía no la nombraba, contado por posición
  (dos resellados del mismo día dan dos bloques con la misma fecha), y lo sellado antes de
  `GRACIA_DESDE` (2026-11-22) se juzga como siempre. La lectura del historial pasa a
  `jueces/historial_semilla.py`: `j12` tenía 794 líneas. Cuatro pruebas nuevas y tres mutaciones
  vistas en rojo; la misma vara en `flota/consumidores_lectura.py` de la fábrica (`9d8f59b`).
- y este commit: esta entrada y el ERS al día con la publicación.

**Radio del lock**, `flota/consumidores.py --lock-candidato` de la fábrica contra la
organización (2026-11-22). Con el lock nuevo y el `j12` de `v2.0.20`, **5** aplicaciones
sumaban un `SEM-1 BLOQUEA`: las rutas que `v2.0.20` selló por primera vez y que perdían la
gracia al entrar su lock al historial. Lo encontró esta medición, antes de publicar. Con
`b6f00bf`: **2** con `SEM-1 BLOQUEA`, las mismas dos y por las mismas piezas que con el lock
publicado; 17 sólo avisan; **frenarían el despliegue: 0**. Las 15 piezas nuevas no están en
ninguna aplicación ya sembrada, y una pieza ausente no es un hallazgo: la reciben con
`sembrar.py --actualizar --reponer`. Ningún `BLOQUEA` nuevo. Las aplicaciones no se nombran
aquí, que es público.

Verificado en local antes del tag: la suite (480 pruebas, OK), el autojuicio (0 bloqueantes),
`ruff check`/`ruff format --check`; en la fábrica, una siembra nueva juzgada en `bloqueante`
con este lock y este `j12` sale con 0 bloqueantes y 0 avisos (con el `CONSTRUCCION.md` de
prueba de su CI).

### `v2.0.22`, 2026-11-22 — tres falsos positivos que aparecieron al alinear el IAM

Autorizada por Luis Monsalve el 2026-11-22, en el plan aprobado ese día para llevar
`coipo_usuarios` (el IAM) al estándar de la fábrica («el tag v2.0.21 y mover v2»: la otra
publicación del día tomó ese número y esta pasa a `v2.0.22`). **Reversión:** antes de este tag
`v2` apuntaba a `1e395cc57e8e27282c5670131b280d3442595440` (`v2.0.21`). El tag se crea sólo con
`Autotest` en verde sobre su commit.

Lo que entra, después de `v2.0.21`: `8fdafe5` y este commit. Sin resellado: el lock no cambia.

| Juez | Qué estaba mal | Qué hace ahora |
|---|---|---|
| `j02` (`G8-1`) | `Repo.nombre` era la carpeta local. Un clon de `coipo_usuarios` en una carpeta `COIPO_USUARIOS` salía bloqueado sin nada que arreglar: el repositorio se llama en minúsculas en GitHub | el nombre sale del remoto `origin` (el que usa el despliegue, `github.event.repository.name`); sin remoto, la carpeta. En el CI no cambia nada: el checkout se llama como el repositorio |
| `j13` (`UI-15`) | miraba solo el PRIMER `@media prefers-reduced-motion` de cada hoja. Un `.x:hover { @media (prefers-reduced-motion: no-preference) {…} }` anidado antes del bloque universal lo tapaba: «apaga 0 de 14» sobre un CSS correcto | se miran todos los bloques `reduce`; un `no-preference` (que ENCIENDE movimiento, no lo apaga) no cuenta como bloque. El hueco de un repositorio con SOLO bloques `no-preference` (que hoy sale «completo») no se toca: cerrarlo puede poner rojo a uno verde, y eso es mayor nueva |
| `j16` (`COD-3`) | el arreglo proponía `src/puertos/` y `src/interfaz/`, que no existen en la semilla ni en `ESTANDAR_CODIGO.md` | nombra `src/aplicacion/puertos/`, `src/adaptadores/`, `src/composicion.ts`, `src/componentes/` y `src/vistas/` |

Seis pruebas nuevas, vistas en rojo antes del arreglo (la de `UI-15` reproduce el «apaga 0 de 1»).

**Radio medido** (2026-11-22), `correr.py --jueces "j02 j13 j16"` en advisory sobre los **163
clones** de `D:\GitHub`, la versión anterior contra la nueva: **BLOQUEA 84 → 83, AVISA 207 →
207**. El único cambio es el `G8-1` falso de un clon del IAM. Ningún repositorio pasa de verde a
rojo. Se midió sobre `c6f8ad6`; `v2.0.21` no tocó `comun.py`, `j02`, `j13` ni `j16`
(`git diff c6f8ad6 1e395cc` vacío para esos archivos), así que el radio vale igual.

Verificado en local antes del tag: la suite (OK), el autojuicio (0 bloqueantes), `ruff check` y
`ruff format --check`.

### `v2.0.23`, 2026-11-24 — el lock, con `ARG BASE_PATH` en `frontend/Dockerfile`

> **Entrada reconstruida el 2026-11-25 desde git.** El tag se publicó sin ella. Es la
> tercera vez, después de `v2.0.12` y `v2.0.13` (ver la enmienda del 2026-10-25, más
> arriba). Desde el 2026-11-25 `tests/test_coherencia_documentos.py` falla si un tag de la
> mayor vigente no tiene aquí su encabezado: la regla dejó de depender de que alguien se
> acuerde.

Tag anotado del 2026-11-24 sobre `1f3d69616a0238ef0934b2cb07782297021e550e`. El tag anterior
es `v2.0.22` (`81c485ba67341a676bd7b098218ed81478d78381`). Quién la autorizó no consta en
este repositorio.

Lo que entra, después de `v2.0.22`: `db3e9ae` (el informe de optimización del 2026-11-21),
`0b46df2` (`docs/preguntas_usuario.xlsx`), su merge `a596e39` y `1f3d696`, que es el
resellado. En el lock cambia una sola huella, la de `frontend/Dockerfile` (mensaje del tag:
«con ARG BASE_PATH (LOCK-LAB, 81deb0e de la fabrica)»), y el lock anterior entra al
historial como bloque `vigente_hasta: 2026-11-24`, que pasa de 19 a 20 bloques. No toca
ningún juez.

**Radio: no quedó escrito**, y la política de arriba lo pide en cada resellado. Lo que
dicen las reglas, sin haberlo medido para esta entrada: una aplicación que conserva el
`frontend/Dockerfile` anterior coincide con el historial y sale «atrasada» —`SEM-1` AVISA—,
no «editada».

### `v2.0.24`, 2026-11-24 — el MCP es recomendado, no obligatorio

Autorizada por Luis Monsalve el 2026-11-24 («puedes hacerlo todo»), después de que un
colega quedara obligado a conectarse al MCP sólo para pasar `FAB-8`. **Reversión:** antes
de este tag `v2` apuntaba a `1f3d69616a0238ef0934b2cb07782297021e550e`. Sin resellado: el
lock está al día (`sellar.py --comprobar`).

Lo que entra: `d20a29e` y este commit. `j14` (`FAB-8`) acepta, en vez de un
`correlation_id` de IGNUS, la línea `copia-local metodologia_coipo.json <fecha>
sha256:<64 hex>` de quien consultó la copia versionada de la fábrica, y la anota como
AVISA. Sin ningún rastro sigue bloqueando. **Sólo relaja**: ningún repositorio verde
puede ponerse rojo, por eso es `v2.x` y no se midió con `consumidores.py` (que mide
`SEM-1`, no `FAB-8`).

### `v2.0.25`, 2026-11-26 — `resumen.yml` (el resumen del repo para IGNUS) y la tanda «coherencia y barreras»

Autorizada por Luis Monsalve el 2026-11-26 («autorizo todo»). **Reversión:** antes de este
tag `v2` apuntaba al commit de `v2.0.24`. Sin resellado: `verificar.yml` y el lock no se tocan.

Lo que entra: la tanda de abajo (antes «Sin publicar») y `83f85ce`, que agrega
`.github/workflows/resumen.yml`, un reusable **aparte** (pide `id-token: write`) que corre
`resumen/resumir_repo.py` y manda el resumen a `POST /repo-resumen` de IGNUS con el token
OIDC de GitHub Actions, sin secretos. Probado de punta a punta el 2026-11-26 desde
`Sud-Austral/test-actions` (HTTP 200). **Radio: cero** para quien no lo llame: es un archivo
nuevo y sólo corre en las apps que agreguen el job `resumen`.

Tanda «coherencia y barreras» (2026-11-25), tras una auditoría del repositorio entero. Un
commit por tema:

- `23af159` — el arnés borra de verdad sus repositorios temporales. En Windows no lo hacía:
  22.651 directorios en `%TEMP%`, medidos el 2026-11-24.
- `873b4bc` — documentos al día: la entrada de `v2.0.23`, que se publicó sin ella; la tabla
  de fuentes y las filas `FAB-8` y `SEM-1` de `REGLAS.md`; `CLAUDE.md` y `README.md`; Python
  mínimo 3.10. Salen `insumos/` y dos binarios de ofimática.
- `42421ab` — barreras: `tests/test_coherencia_documentos.py`,
  `tests/test_solo_biblioteca_estandar.py` y `tests/test_datos_semilla.py`; la trazabilidad
  cubre todo `jueces/*.py`; la lista de jueces que leen el índice sale del código. En
  `autotest.yml`, una pierna con Python 3.10.
- `634f046` — dos pruebas que no podían fallar, y las vigencias de `j13` y `j16` fijadas por
  debajo.
- `2cc7ee4` — pruebas de `j12` y `AUD-1`: mueren 19 mutantes que sobrevivían con la suite en
  verde. `test_j12_semilla.py` pasa de 106 pruebas a 58: 55 eran repeticiones por herencia.

**Radio: cero, por construcción.** No cambia ninguna línea ejecutable de `jueces/`: el árbol
sintáctico de sus 18 módulos, sin docstrings, es idéntico al de `d04babf` (`v2.0.24`).
Cambian documentos, pruebas, el arnés y el CI de este repositorio. `verificar.yml` y el lock
no se tocan, así que no hay nada que resellar.

Verificado en local el 2026-11-25: la suite (511 pruebas, OK, 0 omitidas) con Python 3.12.3 y
3.11.9; `ruff check` y `ruff format --check` con `--target-version py310`; el autojuicio
(exit 0, 1 supresión). Cada prueba nueva se vio en rojo una vez, sobre una copia. **Lo que
sólo corre en GitHub** —la suite en Linux, con el `python3` de `ubuntu-latest` y con Python
3.10, y el job `el-reusable-lo-valida-github`— no se copia aquí: es el resultado de
`Autotest` sobre el commit que entró en `main`.

Lo que la auditoría encontró y esta tanda NO arregla, porque cambia veredictos: los falsos
rojos y las caídas van en una tanda `v2.x` propia; los falsos verdes entran primero como
AVISA, con su radio medido, y pasan a BLOQUEA en `v3` (decisión de Luis Monsalve del
2026-11-25).

### Migrar a una mayor nueva

Se cambia el `@vN` de cada `uses:` **a propósito**, uno a uno. No hay prisa: la
mayor anterior sigue apuntando donde apuntaba, y eso es exactamente lo que se
compra al no moverla.

> **Las dos mitades se pueden separar, y sigue siendo posible.** El `uses:` fija
> **el YAML**; `ref_jueces` fija **el código de los jueces**. Un `uses:@<sha>` sin
> `ref_jueces` congela el YAML y deja el motor siguiendo el `vN` móvil — que es lo
> que le pasaba a `coipo_prensa2`, fijando un SHA y creyendo que congelaba los
> jueces.
>
> **La única forma de congelar las dos es pasar `ref_jueces` con el mismo SHA del
> `uses:`**, y hay que mover las dos líneas a la vez. Es lo que hace hoy
> `coipo_prensa2`.
>
> Se intentó cerrarlo del todo haciendo que el motor se dedujera de
> `github.job_workflow_ref`. **No se puede:** ese campo llega **vacío** en los
> pasos de un workflow reusable —existe en las reclamaciones del token OIDC, no en
> el contexto que ve `run:`—, medido en una ejecución real el 2026-09-08. Esa
> versión es `v2.0.0` y está rota; ver arriba.

## Comprobar qué está publicado de verdad

```bash
git ls-remote --tags origin          # los tags que existen en GitHub
git ls-remote --heads origin         # las ramas
git rev-parse v1 v1.0.0              # a qué commit apunta cada uno, en local
```

`git tag -l` solo enseña lo **local**. Que un tag exista en tu máquina no
significa que las apps lo puedan usar; hasta el `git push origin <tag>` no
existe para nadie más.
