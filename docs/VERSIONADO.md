# Versionado y publicación de `coipo_jueces`

Este repositorio se consume por `uses:`, no por copia. Eso significa que **el
tag es la interfaz pública**: lo que las 22 apps de la flota ejecutan en cada
push es lo que apunte ese tag, y moverlo mal cambia el comportamiento del CI de
toda CONAF a la vez.

## Dos tags, con propósitos opuestos

| Tag | Qué es | ¿Se mueve? | Para qué |
|---|---|---|---|
| `vN.N.N` | anotado, apunta a un commit concreto | **jamás** | poder decir «el 5 de septiembre corría exactamente esto» |
| `vN` | ligero, apunta al último `vN.x` | **sí, en cada publicación de esa mayor** | que un arreglo llegue a las apps sin tocar 22 repos |

**Hoy la mayor vigente es `v2`.** `v1` sigue existiendo y **congelado** en
`d73d735`: quien no haya migrado ejecuta exactamente lo de entonces, que es
justamente lo que una mayor compra.

Es la convención de las propias actions de GitHub, y se puede comprobar:
`actions/checkout@v7` y `actions/checkout@v7.0.1` resuelven hoy al mismo commit
`3d3c42e5…`, pero mañana `v7` apuntará a `v7.0.2` y `v7.0.1` seguirá donde está.

**Las apps fijan la mayor, `@vN`.** Es deliberado y es toda la tesis del repositorio: la
propagación por copia en esta flota está medida en 22 % y la del `uses:` en
100 %. Fijar cada app a `@v1.0.3` devolvería el problema de la copia con otro
nombre — 22 pull requests para un arreglo de una línea, y la certeza de que
alguien se queda atrás.

> El contrapeso: si `v1` se mueve, se mueve para **todos a la vez**. Por eso una
> publicación se hace con la suite en verde y la calibración inversa repetida, y
> por eso un cambio que pueda poner rojo a un repo que hoy está verde no es un
> `v1.x`: es un `v2`, y cada app migra cuando decide.

## Publicar

```bash
# 0. la suite y la calibración, antes de nada
python3 -m unittest discover -s tests
# perfil encuadre_operativo: este repo no despliega, y con 'aplicacion'
# j01 y j06 salen SIN_EVALUAR, que en modo bloqueante es exit 1
python3 jueces/correr.py --repo . --modo bloqueante --perfil encuadre_operativo

# 1. la rama entra en main
git checkout main
git merge --ff-only jueces-fase-1
git push origin main

# 2. el tag inmutable. `-a` = anotado: lleva autor, fecha y mensaje propios.
#    Un tag ligero (`git tag v1.0.0` a secas) es solo un puntero sin autoría,
#    y para una interfaz pública eso es perder la única traza de quién publicó
#    qué y cuándo — que es exactamente lo que Contraloría pregunta.
git tag -a v1.0.0 -m "j09 (secretos versionados) + infraestructura de jueces"
git push origin v1.0.0

# 3. el tag móvil de la serie. `-f` porque ya existe y hay que reapuntarlo.
git tag -f v1 v1.0.0^{commit}
git push -f origin v1
```

`v1.0.0^{commit}` no es adorno: sin eso, `v1` apuntaría al **objeto tag**
`v1.0.0` en vez de al commit, y quedaría un tag que apunta a otro tag. GitHub
Actions lo resuelve igual, pero `git describe` y media herramienta se
confunden.

## Publicaciones siguientes

Repetir solo los pasos 2 y 3 con el número nuevo:

```bash
git tag -a v1.0.1 -m "j01: falso positivo con context: ./backend"
git push origin v1.0.1
git tag -f v1 v1.0.1^{commit}
git push -f origin v1
```

**El `push -f` sobre `v1` es el único force-push legítimo de este repositorio.**
Es seguro porque `v1` es un puntero, no historia: no se reescribe ningún commit
y nadie pierde trabajo. Un `push -f` sobre `main` o sobre un `vN.N.N` es otra
cosa y no se hace nunca.

## Cuándo toca una mayor nueva

- Un juez nuevo en modo bloqueante, o una regla que pasa de `AVISA` a `BLOQUEA`.
- Un cambio en las entradas de `verificar.yml` que rompa a quien no lo actualice.
- Cualquier cosa que pueda poner rojo a un repositorio que hoy está verde.

Todo lo demás —jueces nuevos en advisory, correcciones de falsos positivos,
mensajes más claros— es `vN.x` y viaja solo.

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
> sin log y sin pasos. La causa: el paso `correr` de `verificar.yml` llevaba
> **dos claves `env:`**. PyYAML se queda con la última sin avisar —por eso la
> suite y el paso «El YAML del reusable parsea» salieron verdes— y GitHub no
> tolera claves repetidas. La misma clase de desastre que `v2.0.0`: un tag
> anotado no se arregla, sólo se avisa.
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
> versión es `v2.0.0` y está rota; ver abajo.

## Comprobar qué está publicado de verdad

```bash
git ls-remote --tags origin          # los tags que existen en GitHub
git ls-remote --heads origin         # las ramas
git rev-parse v1 v1.0.0              # a qué commit apunta cada uno, en local
```

`git tag -l` solo enseña lo **local**. Que un tag exista en tu máquina no
significa que las apps lo puedan usar; hasta el `git push origin <tag>` no
existe para nadie más.
