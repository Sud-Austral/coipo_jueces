<!-- Fuente del ERS de coipo_jueces. El .docx NO se edita: se genera desde aquí con la herramienta de la fábrica (coipo_master_produccion, clonada al lado), con el anterior como plantilla, y se comprueba al releerlo:
     python ../coipo_master_produccion/herramientas/ers_a_docx.py docs/ERS.md --plantilla documentacion/ERS.docx --salida documentacion/ERS.docx -->

21, noviembre, 2026

CORPORACIÓN NACIONAL FORESTAL (CONAF)

# Especificación de Requerimientos de Software (ERS)

PROYECTO: JUECES COIPO: VERIFICADORES EJECUTABLES DE LOS REPOSITORIOS DE LA FLOTA, DISTRIBUIDOS COMO
WORKFLOW REUSABLE DE GITHUB ACTIONS

| Metadatos del documento | Detalle |
|---|---|
| **Código de documento** | ERS-COIPO_JUECES-2026-V2 |
| **Fecha de emisión** | 21 de noviembre de 2026 (la V1 es del 10 de noviembre de 2026) |
| **Repositorio** | coipo_jueces (rama main, commit 81629c2 del 2026-11-21, leído ese día; publicado el mismo día como `v2.0.20`, con el lock de la semilla resellado) |
| **Elaborado por** | Generado con asistencia de IA (Claude) a partir del código y la documentación del repositorio; puesto al día el 2026-11-21 contra el árbol de ese día; pendiente de revisión humana |
| **Unidad requirente** | No documentado en el repositorio |
| **Alcance** | Herramienta de verificación estática, no una aplicación web: once programas en Python de biblioteca estándar (`jueces/jNN_*.py`), su motor común y sus auxiliares, un orquestador, el workflow reusable que los distribuye (`.github/workflows/verificar.yml`), el catálogo de reglas (`REGLAS.md`), el sello de la semilla (`semilla.lock` y su historial) y la suite de pruebas. No tiene servicio, base de datos, interfaz de usuario ni contenedores. |
| **Carácter del documento** | Especificación funcional y técnica reconstruida desde el código (ingeniería inversa). Fuente: `docs/ERS.md`; este `.docx` se genera con `herramientas/ers_a_docx.py` de `coipo_master_produccion` |

<!-- indice: ÍNDICE DE CONTENIDOS -->

## 1. Resumen ejecutivo y propósito del documento

El presente documento especifica los requerimientos de software del repositorio `coipo_jueces`, que
su `README.md` define como los «verificadores ejecutables de la flota COIPO / CONAF». Cada
verificador, llamado juez, es un programa que recibe la ruta de un repositorio ajeno, lo examina en
modo de sólo lectura y emite hallazgos clasificados en dos severidades (`BLOQUEA` y `AVISA`) junto
con un veredicto de cuatro estados.

El sistema resuelve un problema de propagación: las reglas de despliegue, configuración, seguridad,
interfaz y mantenibilidad de las aplicaciones de la flota estaban escritas en guías que se copiaban
de repositorio en repositorio y divergían. Los jueces no se copian: cada aplicación los invoca por
referencia (`uses: Sud-Austral/coipo_jueces/.github/workflows/verificar.yml@v2`), de modo que una
corrección publicada llega a todas las aplicaciones en su siguiente ejecución de integración
continua.

Los destinatarios son los equipos que mantienen las aplicaciones de la flota (que consumen el
workflow y reciben el resumen de hallazgos), quien mantiene las reglas y publica las versiones, y
los agentes de programación que trabajan sobre el repositorio siguiendo `CLAUDE.md`. La unidad
requirente no está documentada en el repositorio.

Como el repositorio no es una aplicación, en este documento los «módulos» son sus componentes (motor
común, orquestador, jueces, workflows, catálogo) y los «usuarios» son quienes lo operan o lo
consumen. La versión 1 de este ERS (2026-11-10) se reconstruyó leyendo el código al commit
`2084d7b`, sin ejecutar nada. Esta versión 2 lo pone al día al commit `81629c2` (2026-11-21): volvió
a leer lo que cambió entre esas fechas y ejecutó la suite de pruebas (422 pruebas, OK). Lo que no se
volvió a leer conserva la lectura del 2026-11-10 y la sección 8 dice cuál es. Donde una regla está
en `main` pero en ningún tag, se dice «sin tag»: una aplicación que consume `@v2` todavía no la
recibe.

## 2. Antecedentes, diagnóstico y justificación

El repositorio trae su propia ficha de problema y de solución (`insumos/00-PROBLEMA.md` e
`insumos/01-SOLUCION.md`), reconstruidas desde el código y marcadas por sus autores como inferidas:
declaran que «no hay área usuaria en la fuente». Lo que sigue combina esas fichas con lo que afirman
`README.md`, `REGLAS.md`, `docs/VERSIONADO.md` y los comentarios del código. Las mediciones citadas
son afirmaciones del repositorio sobre la flota y no fueron comprobadas para este documento, salvo
las que dicen haberse medido el 2026-11-21.

### 2.1. Problemáticas que resuelve

- **La copia no propaga las correcciones.** `README.md` declara medido que `DOCKER.md` vive en 10
  repositorios con 3 contenidos distintos, que el checklist previo al despliegue (Guía 8) tiene 11
  puntos en el repositorio maestro y 9 en otro, y que la tasa de propagación por copia fue de 2
  sobre 9 (22 %) frente a 8 sobre 8 con `uses:`.
- **Errores de despliegue que se repiten sin que nadie los detecte.** Cada juez nace de un fallo ya
  ocurrido, citado en su cabecera: un archivo `.env` versionado con secretos reales
  (`jueces/j09_secretos.py`), un `/health` que respondía 200 con la base vacía
  (`jueces/j11_salud.py`), un `data/` sin anclar en `.gitignore` que congeló un catálogo en el
  servidor (`.gitignore`, `jueces/j08_rsync.py`).
- **Un verificador que aprueba lo que no miró.** `jueces/comun.py` y `tests/test_tres_estados.py`
  citan un incidente de otro sistema de la organización en que «cero de cero» se leyó como conforme;
  de ahí el veredicto de cuatro estados y la regla de que cero comprobaciones es un fallo.
- **Reglas sin fuente.** `REGLAS.md` y `tests/test_reglas_citadas.py` registran que una versión
  anterior bloqueaba despliegues citando códigos de un documento que no estaba versionado en ningún
  repositorio; de ahí el catálogo con trazabilidad en los dos sentidos.
- **Falsos positivos que enseñan a suprimir el verificador.** `README.md` documenta 68 y 53
  hallazgos falsos en la primera pasada de `j09`; de ahí la «calibración inversa» contra
  repositorios que se saben correctos y el conteo público de supresiones.
- **Reglas nuevas que tumban aplicaciones antiguas.** `README.md` («Los jueces miran hacia
  adelante») establece que una regla nueva bloquea sólo lo sembrado desde su fecha de vigencia y
  avisa en lo anterior.
- **Agotamiento de la cuota de GitHub Actions.** La cuota del plan gratuito se agota y la compuerta
  deja de arrancar; de ahí la entrada `runner` del workflow reusable. El workflow que probaba un
  runner propio, `probar-runner.yml`, se retiró el 2026-11-21 (`f91f5e7`).
- **Un CI roto en `main` que nadie ve.** Desde el 2026-11-14, `.github/workflows/alerta-main.yml`
  abre o comenta un issue cuando `Autotest` falla en `main` y lo cierra al volver a verde: la flota
  entera usa estos jueces al mover `v2`.

> Qué ocurre si no se hace nada, cuántas personas operan el sistema, quién decide que un hallazgo se
> corrige o se suprime y quién decide que el trabajo está terminado figuran como pendientes en
> `insumos/00-PROBLEMA.md`: no documentado en el repositorio.

### 2.2. Fuentes de datos

#### Fuentes de datos del sistema

| N° | Fuente | Descripción | Datos principales |
|---|---|---|---|
| 1 | Repositorio bajo examen | Directorio indicado con `--repo`. Se lee la lista de archivos versionados con `git ls-files -z` y el contenido de los archivos desde el disco, sin modificarlos (`jueces/comun.py`, clase `Repo`). | Compose, `.env.example`, `.gitignore`, `.dockerignore`, configuración de nginx, código Python, hojas de estilo, `tsconfig`, workflows de CI, Dockerfile, `docs/CONSTRUCCION.md`, `ruff.toml`, `.oxlintrc.json`. |
| 2 | Archivo `.semilla` del repositorio examinado | Declaración de alcance que escribe la herramienta de siembra de la fábrica (`jueces/comun_semilla.py`). | Claves `adopta:` (capas `semilla`, `interfaz`), `fabrica:` (fecha de siembra AAAA-MM-DD), `maqueta:` (si nació de una maqueta) y `ajeno:` (carpetas que `j16` no mide). |
| 3 | `semilla.lock` | Generado por `semilla/sellar.py` del repositorio `coipo_master_produccion`; no se edita a mano. Lo consume `j12`. | Huella SHA-256 y ruta de 45 archivos congelados de la semilla (encabezado del archivo, 2026-11-21). Ese día `sellar.py --comprobar` lo da desfasado respecto de la semilla: le faltan las piezas de la auditoría. |
| 4 | `semilla.lock.historial` | Huellas de cada lock publicado antes del vigente, en bloques fechados; sólo crece. | Línea `# vigente_hasta: AAAA-MM-DD` y pares huella–ruta; 17 bloques el 2026-11-21. |
| 5 | `REGLAS.md` | Catálogo de códigos de regla con el documento que respalda cada uno. Los documentos fuente (Guía 8, `DOCKER.md`, estándares de interfaz y de código, `AGENTS.md`) viven en `coipo_master_produccion` y aquí sólo se citan. | Código, juez, qué comprueba, fuente, severidad. |
| 6 | Entradas del workflow y variables del runner | Parámetros de `workflow_call` y variables de GitHub Actions leídas por `jueces/correr.py`. | `modo`, `perfil`, `jueces`, `ref_jueces`, `runner`; `GITHUB_ACTIONS`, `GITHUB_OUTPUT`, `NO_COLOR`. |

## 3. Arquitectura tecnológica, alojamiento y seguridad de accesos

### 3.1. Arquitectura y alojamiento

El sistema es un conjunto de guiones de línea de comandos en Python que usan únicamente la
biblioteca estándar y el ejecutable `git`. No hay servicio, contenedor, base de datos, dominio ni
puerto: el repositorio no contiene `docker-compose`, `Dockerfile`, manifiesto de dependencias ni
archivos `.env`. Se ejecuta en dos lugares: en el runner de GitHub Actions de cada aplicación que lo
invoca, y a mano en el equipo de quien lo corre.

#### Componentes

| Componente | Tecnología y versión | Ubicación en el repo | Función |
|---|---|---|---|
| Motor común | Python 3, biblioteca estándar (versión no fijada: se usa el `python3` del runner) | `jueces/comun.py` | Severidades, `Hallazgo`, `Resultado` con su veredicto, clase `Repo` de sólo lectura, supresiones, informe por consola, anotaciones de GitHub y punto de entrada de cada juez. |
| Lector YAML | Python, biblioteca estándar | `jueces/comun_yaml.py` | Analizador del subconjunto de YAML que usan los compose de la flota (no se instala PyYAML); lanza `YamlNoSoportado`. |
| Lector de `.semilla` | Python, biblioteca estándar | `jueces/comun_semilla.py` | Semántica única de `adopta:`, `fabrica:`, `maqueta:` y `ajeno:` para `j12`, `j13`, `j14` y `j16`. |
| Auxiliares de reglas | Python, biblioteca estándar | `jueces/comun_auditoria.py`, `jueces/comun_zen.py` | Miran la forma de la auditoría (`AUD-1`, la emite `j12`) y del Zen de Python (`COD-5`, la emite `j16`); un auxiliar no emite: lo verifica `tests/test_reglas_citadas.py`. Sin tag. |
| Orquestador | Python, biblioteca estándar | `jueces/correr.py` | Descubre los jueces, los filtra por perfil, los ejecuta, escribe resumen Markdown, JSON y salidas del job, y decide el código de salida. |
| Jueces | Python, biblioteca estándar (módulos `ast`, `re`, `hashlib` entre otros) | `jueces/j01`, `j02`, `j05`, `j06`, `j08`, `j09`, `j11`, `j12`, `j13`, `j14`, `j16` (once archivos) | Cada uno expone `comprobar(repo, resultado)` y puede ejecutarse solo. |
| Workflow reusable | GitHub Actions (`workflow_call`); `actions/checkout` y `actions/upload-artifact` fijados por SHA de 40 caracteres | `.github/workflows/verificar.yml` | Mecanismo de distribución: trae el repositorio llamante y el código de los jueces sin persistir la credencial, corre `correr.py` y publica resumen y artefacto. |
| Autoprueba | GitHub Actions, `ubuntu-latest` | `.github/workflows/autotest.yml` | Suite, importación de cada juez sin dependencias, validación del YAML, el Zen con ruff y actionlint con versión y sha256 fijados (sin tag), jueces sobre el propio repositorio y llamada real al reusable. |
| Alerta de `main` | GitHub Actions (`workflow_run`), `ubuntu-latest` | `.github/workflows/alerta-main.yml` | Abre o comenta un issue cuando `Autotest` falla en `main` y lo cierra al volver a verde; sólo `GITHUB_TOKEN` con `issues: write`. |
| Sello de la semilla | Texto generado fuera del repositorio | `semilla.lock`, `semilla.lock.historial` | Huellas de las piezas congeladas, vigentes e históricas. |
| Catálogo y documentación | Markdown, TOML | `REGLAS.md`, `DEUDA.md`, `docs/VERSIONADO.md`, `docs/archivo/FILAS_REGLAS_UI.md`, `insumos/`, `ruff.toml` | Reglas con su fuente, supresiones activas, política de tags, registro histórico, fichas y las reglas del Zen copiadas de la semilla. |
| Pruebas | Python `unittest` | `tests/` (29 archivos `test_*.py` y `ayuda.py`) | Una prueba por juez más las transversales; operan sobre repositorios git sintéticos temporales. |

**Despliegue.** No hay despliegue a servidor. «Publicar» es crear un tag: `vN.N.N` anotado e
inmutable y `vN` móvil que las aplicaciones consumen (`docs/VERSIONADO.md`). La mayor vigente
declarada es `v2`; en el clon leído existen los tags `v1`, `v1.0.0`, `v1.0.1`, `v1.1.0`, `v2` y
`v2.0.0` a `v2.0.20`. Hasta el 2026-11-21, `v2`, `v2.0.19` y `origin/main` apuntaban al mismo
commit (`26301b9`, del 2026-11-14); ese día se publicó `v2.0.20` con lo que `docs/VERSIONADO.md`
listaba en «Sin publicar», y `v2` pasó a apuntarle. El procedimiento de publicación vive en `coipo_master_produccion` y no en
este repositorio. La organización de GitHub que aparece en el `uses:` es `Sud-Austral`.

### 3.2. Autenticación y matriz de roles

El sistema no tiene autenticación, sesiones ni tabla de permisos propios: `insumos/00-PROBLEMA.md`
lo constata y el código lo confirma. El control de acceso es el de GitHub sobre el repositorio
(quién puede fusionar a `main` y mover tags), que no está descrito en el repositorio. Los workflows
declaran `permissions: contents: read`, salvo `alerta-main.yml`, que pide `issues: write`.
`README.md` y `CLAUDE.md` declaran que el repositorio es público a propósito, para no cablear un
token de organización en cada repositorio llamante. La tabla siguiente recoge los perfiles de uso
que se deducen de los documentos.

#### Perfiles de uso

| Perfil / rol | Ámbito de visibilidad | Facultades y permisos |
|---|---|---|
| Equipo de una aplicación de la flota (consumidor) | Su propio repositorio y el resumen de su ejecución | Invoca el workflow con `uses:`; elige `modo` (`advisory` o `bloqueante`), `perfil`, lista de jueces, `ref_jueces` y `runner`; puede suprimir un hallazgo con marcador y motivo, y debe registrarlo en su `DEUDA.md`. |
| Quien ejecuta a mano | Cualquier repositorio en su disco | Corre `jueces/correr.py` o un juez individual con `--repo`; obtiene salida por consola, `RESUMEN.md` y JSON. |
| Mantenedor de los jueces | Este repositorio | Agrega o corrige jueces, mantiene `REGLAS.md`, resella el lock y publica tags. `docs/VERSIONADO.md` exige autorización explícita de una persona para mover el tag móvil. Identidad y cargo del rol: no documentado en el repositorio, salvo las decisiones atribuidas por nombre en `REGLAS.md` y `docs/VERSIONADO.md`. |
| Fábrica (`coipo_master_produccion`) | Externo a este repositorio | Genera `semilla.lock` y su historial, es dueña de los documentos fuente de las reglas y prueba la paridad de `j14` con su propio instrumento (`jueces/j14_construccion.py`). |
| GitHub Actions | Repositorio llamante, sólo lectura | Ejecuta el job con `contents: read`, con tiempo máximo de 10 minutos. |

## 4. Especificación funcional de los módulos

### 4.1. Módulo 1: Motor común de hallazgos, veredictos y supresiones

`jueces/comun.py` define el contrato que todos los jueces comparten: qué es un hallazgo, cómo se
llega al veredicto, cómo se lee el repositorio examinado y cómo se silencia un hallazgo dejando
rastro.

| ID | Requisito | Regla de negocio / detalle | Estado | Fuente |
|---|---|---|---|---|
| RF-001 | El sistema debe representar cada defecto como un hallazgo con ubicación y consecuencia. | Campos: `regla`, `severidad`, `archivo` (relativo; vacío si es del repositorio entero), `mensaje`, `manifestacion` (cómo se ve el defecto en producción, obligatorio), `linea` y `arreglo` opcionales. | Implementado | `jueces/comun.py` (`Hallazgo`) |
| RF-002 | El sistema debe clasificar los hallazgos en exactamente dos severidades. | `BLOQUEA` y `AVISA`. El código declara deliberada la ausencia de un nivel intermedio. | Implementado | `jueces/comun.py` (`Severidad`) |
| RF-003 | El sistema debe emitir por cada juez un veredicto de cuatro estados. | `HALLAZGOS` si hay algún hallazgo; si no, `OK` si registró al menos una comprobación; si no, `NO_APLICA` si el juez declaró que no corresponde; en otro caso `SIN_EVALUAR`. Los hallazgos mandan sobre lo demás. | Implementado | `jueces/comun.py` (`Resultado.veredicto`); `tests/test_tres_estados.py` |
| RF-004 | El sistema debe registrar por separado lo comprobado, lo no evaluado, lo que no aplica y lo suprimido. | Listas `comprobado`, `no_evaluado`, `no_aplica` y `supresiones` del resultado. Sólo el juez puede declarar `no_aplica`, desde evidencia del código; el repositorio examinado no puede declararse a sí mismo fuera de alcance. | Implementado | `jueces/comun.py` (`Resultado`) |
| RF-005 | El sistema debe leer el repositorio examinado en modo de sólo lectura, a partir de lo versionado. | La lista de archivos sale de `git ls-files -z` decodificado como UTF-8; no se recorre el disco, para que un `.env` local no versionado no sea hallazgo. Los textos se leen con `utf-8-sig` y reemplazo de bytes inválidos. | Implementado | `jueces/comun.py` (`Repo`) |
| RF-006 | El sistema debe distinguir un índice de git ilegible de un repositorio sin archivos. | `indice_roto()` devuelve el motivo si no hay `.git` o si `git ls-files` falla; `sin_indice()` lo anota en `no_evaluado` y el juez no dictamina (`SIN_EVALUAR`), nunca `OK` ni `NO_APLICA`. | Implementado | `jueces/comun.py`; `tests/test_indice_roto.py` |
| RF-007 | El sistema debe reconocer el compose de la raíz con cualquiera de sus cuatro nombres. | `docker-compose.yml`, `docker-compose.yaml`, `compose.yml`, `compose.yaml`, en ese orden. | Implementado | `jueces/comun.py` (`COMPOSE`, `Repo.compose`) |
| RF-008 | El sistema debe permitir suprimir un hallazgo concreto con un marcador y un motivo escrito. | Marcador `coipo-jueces:ignorar(REGLA) motivo` en la misma línea o en la inmediatamente anterior; el motivo debe tener al menos 12 caracteres; sin motivo suficiente no suprime nada. | Implementado | `jueces/comun.py` (`suprimido`); `tests/test_j09_secretos.py` |
| RF-009 | El sistema debe contar y publicar toda supresión activa. | Cada supresión se imprime, se totaliza y, en GitHub, genera un `::warning::` que nombra `DEUDA.md`. La existencia de la fila en `DEUDA.md` no la comprueba ningún código: es una exigencia documental. | Parcial | `jueces/comun.py` (`informar`); `DEUDA.md` |
| RF-010 | El sistema debe permitir ejecutar cada juez por separado desde la línea de comandos. | Argumentos `--repo` (por defecto `.`), `--modo` (`advisory` por defecto, o `bloqueante`), `--json` y `--github`. Sale con 1 sólo en modo bloqueante y con algún hallazgo `BLOQUEA`. | Implementado | `jueces/comun.py` (`ejecutar`) |
| RF-011 | El sistema debe emitir anotaciones de GitHub Actions coherentes con el modo. | `::error` sólo si el modo es bloqueante y la severidad es `BLOQUEA`; en advisory todo baja a `::warning`. `no aplica` y `no evaluado` salen como `::notice`. | Implementado | `jueces/comun.py` (`_anotacion_github`); `tests/test_anotaciones.py` |
| RF-012 | El sistema debe interpretar los archivos compose sin dependencias externas. | Analizador propio del subconjunto de YAML en uso; una forma no soportada lanza `YamlNoSoportado` en vez de leerse mal. | Implementado | `jueces/comun_yaml.py`; `tests/test_yaml_formas.py` |
| RF-013 | El sistema debe leer la declaración de alcance `.semilla` con una semántica única. | Sin `.semilla`: `NO_APLICA`. Sin clave `adopta:`: adopta todo. Lista en línea, en flujo, entre comillas o en bloque: exactamente esas capas. `adopta:` vacía: error de declaración, `SIN_EVALUAR` con la línea citada. Apagar por lista algo que regiría se cuenta como supresión. `maqueta:` deja a `j13` en `NO_APLICA` sin contar supresión y a `j16` sin medir la maqueta; `ajeno:` declara carpetas que `j16` no mide, cada una una supresión publicada (desde `v2.0.15`). | Implementado | `jueces/comun_semilla.py`; `tests/test_adopta_formas.py`, `tests/test_adopta_cruzado.py`; `docs/VERSIONADO.md` |

### 4.2. Módulo 2: Orquestador de jueces

`jueces/correr.py` es lo que invoca el workflow reusable. Concentra la lógica de qué juez aplica a
qué perfil y de cuándo el proceso sale con error.

| ID | Requisito | Regla de negocio / detalle | Estado | Fuente |
|---|---|---|---|---|
| RF-014 | El sistema debe descubrir los jueces dinámicamente desde el directorio. | Carga todo `j*.py`; el nombre debe cumplir `jNN_nombre.py` y el módulo debe definir `comprobar`; en caso contrario lanza `JuezInvalido` en vez de ignorarlo. | Implementado | `jueces/correr.py` (`descubrir`) |
| RF-015 | El sistema debe filtrar los jueces por perfil de ejecución. | Perfiles `aplicacion` y `encuadre_operativo` (software de terceros). Cada juez declara `PERFILES`; `j05`, `j11`, `j13`, `j14` y `j16` sólo corren en `aplicacion`; los demás en ambos (releído el 2026-11-21). | Implementado | `jueces/correr.py`; constante `PERFILES` de cada juez |
| RF-016 | El sistema debe permitir ejecutar un subconjunto de jueces. | `--jueces` acepta ids cortos separados por espacios o comas (`j01 j09`). Un id que no existe para el perfil produce error y salida 1, con la lista de disponibles. | Implementado | `jueces/correr.py` (`main`) |
| RF-017 | El sistema debe salir con error si ningún juez aplica al perfil. | «No corrió ningún juez» nunca se lee como conforme: salida 1. | Implementado | `jueces/correr.py` |
| RF-018 | El sistema debe aislar la falla de un juez sin disimularla. | Una excepción en un juez se registra como no evaluado, los demás siguen, y el proceso sale con 1 en cualquier modo. | Implementado | `jueces/correr.py` |
| RF-019 | El sistema debe generar un resumen en Markdown. | Tabla por juez (veredicto, comprobaciones, bloqueantes, avisos, supresiones) y secciones de hallazgos, supresiones activas, no aplica y no evaluado. Se escribe en la ruta de `--resumen`. | Implementado | `jueces/correr.py` (`resumen_markdown`) |
| RF-020 | El sistema debe exportar el resultado consolidado en JSON. | Repositorio, modo, perfil, totales y, por juez, veredicto, listas y hallazgos. Ruta de `--json`. | Implementado | `jueces/correr.py` |
| RF-021 | El sistema debe escribir las salidas del job de GitHub, con centinela previo. | Antes de correr escribe `estado=no_corrio` y `-1` en `bloqueantes`, `avisos` y `supresiones`; al terminar los sobrescribe con `estado=corrio` y los totales. | Implementado | `jueces/correr.py` |
| RF-022 | El sistema debe detener el proceso en modo bloqueante cuando hay hallazgos bloqueantes. | Salida 1 si el modo es `bloqueante` y hay al menos un `BLOQUEA`. En `advisory` sale 0 y, en GitHub, emite un `::warning::` con el número de bloqueantes. | Implementado | `jueces/correr.py` |
| RF-023 | El sistema debe tratar cero comprobaciones como un fallo. | Si ningún juez comprobó nada, salida 1 en cualquier modo, salvo que todos los jueces que corrieron hayan dicho `NO_APLICA`. | Implementado | `jueces/correr.py`; `tests/test_tres_estados.py` |
| RF-024 | El sistema debe hacer exigible el perfil declarado. | En modo `bloqueante` y perfil `aplicacion`, cualquier juez `SIN_EVALUAR` produce salida 1. En `encuadre_operativo` se tolera. | Implementado | `jueces/correr.py` |

### 4.3. Módulo 3: Jueces de despliegue, identidad y configuración (j01, j02, j06, j08)

Estos jueces verifican el contrato que el pipeline de despliegue de la flota da por supuesto: la
forma del compose, el nombre y el puerto de la aplicación, el archivo de ejemplo de variables y lo
que se ignora o se sincroniza al servidor.

| ID | Requisito | Regla de negocio / detalle | Estado | Fuente |
|---|---|---|---|---|
| RF-025 | El sistema debe verificar la estructura del compose (`G8-7`). | `BLOQUEA`: clave `version:`, ningún servicio, ningún servicio que publique puerto, más de un servicio que publique puerto. `AVISA`: servicio sin healthcheck o sin `restart:`. | Implementado | `jueces/j01_despliegue.py`; `tests/test_j01_despliegue.py` |
| RF-026 | El sistema debe impedir que el compose levante un motor de base de datos propio (`DK-3`). | `BLOQUEA` por cada servicio que levante un motor de base de datos: la base de la flota es compartida y externa al compose. | Implementado | `jueces/j01_despliegue.py` |
| RF-027 | El sistema debe verificar el `.dockerignore` frente al contexto de build (`DK-4`). | `BLOQUEA` si falta `.dockerignore` y hay builds con `context: .`, o si existe y no excluye `.env`; `AVISA` si falta y los contextos son acotados. | Implementado | `jueces/j01_despliegue.py` |
| RF-028 | El sistema debe advertir sobre `proxy_pass` a un nombre literal sin `resolver` en el nginx interno (`NG-1`) y sobre servicios sin `mem_limit` (`OPS-1`). | Ambas sólo `AVISA`: figuran en «Reglas sin fuente escrita» y una prueba impide que bloqueen. Sin tag: `NG-1` sólo exime el upstream en `$variable`, y un nombre literal con `resolver` también avisa. | Implementado | `jueces/j01_despliegue.py`; `REGLAS.md`; `tests/test_reglas_citadas.py` |
| RF-029 | El sistema debe verificar el nombre del repositorio (`G8-1`). | `BLOQUEA` si el nombre del directorio no está en minúsculas dentro de `[a-z0-9_-]`: ese nombre es el de la carpeta del servidor. | Implementado | `jueces/j02_identidad.py`; `tests/test_j02_identidad.py` |
| RF-030 | El sistema debe verificar que el puerto se publique por variable (`G8-2`). | `BLOQUEA` si el compose cablea un número en vez de `${APP_PORT}`. La unicidad del puerto en la máquina se reporta siempre como no evaluada. Sin tag: el lado del host de `ports:` se lee entero (`127.0.0.1:${APP_PORT:?mensaje}:8000` y valores anidados). | Implementado | `jueces/j02_identidad.py` |
| RF-031 | El sistema debe verificar el archivo `.env.example` (`G8-3`). | `BLOQUEA` si falta en un repositorio desplegable, si no declara las seis variables base (`DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`, `APP_PORT`), si `APP_PORT` lleva comillas o espacios, o si declara `DATABASE_URL`. Sin compose no se exige y se anota no evaluado. | Implementado | `jueces/j06_config.py`; `tests/test_j06_config.py` |
| RF-032 | El sistema debe detectar la convivencia de las grafías `SESSION_` y `SESION_` (`G8-6`). | `BLOQUEA` cuando conviven variables con ambas grafías. | Implementado | `jueces/j06_config.py` |
| RF-033 | El sistema debe advertir divergencias entre la versión de lenguaje del CI y la de los Dockerfile (`CI-1`). | `AVISA` si ningún workflow fija la versión de python o node, si el CI prueba con una versión que ninguna imagen usa, o si las imágenes usan varias versiones. No bloquea (regla sin fuente escrita). | Implementado | `jueces/j06_config.py` |
| RF-034 | El sistema debe verificar el `.gitignore` (`G8-8`). | `BLOQUEA` si `.env` no está ignorado, si un patrón como `data/` no está anclado con barra inicial, o si hay un `.env` versionado pese al `.gitignore`. | Implementado | `jueces/j08_rsync.py`; `tests/test_j08_rsync.py` |
| RF-035 | El sistema debe verificar qué archivos llegan al servidor con la sincronización anclada (`G8-10`). | `BLOQUEA` un `.env` versionado en un subdirectorio; `AVISA` variantes como `.env.production` que viajan en cada despliegue y archivos versionados bajo el `data/` de la raíz, que nunca llegan. Los `.env.example` no son hallazgo. | Implementado | `jueces/j08_rsync.py` |

### 4.4. Módulo 4: Jueces de seguridad y salud del servicio (j05, j09, j11)

| ID | Requisito | Regla de negocio / detalle | Estado | Fuente |
|---|---|---|---|---|
| RF-036 | El sistema debe verificar que CORS se configure por dominio (`G8-5`). | Analiza el árbol sintáctico de los archivos Python. `BLOQUEA` un origen `*`, un origen por IP y una variable `CORS_ORIGINS` declarada que el middleware no usa. Si el repositorio no registra CORS, declara `NO_APLICA`. | Implementado | `jueces/j05_cors.py`; `tests/test_j05_cors.py` |
| RF-037 | El sistema debe detectar archivos `.env` versionados (`G8-4`). | `BLOQUEA` todo `.env` en `git ls-files`, salvo los nombres de ejemplo permitidos (`.env.example`, `.env.sample`, `.env.template`, `.env.dist` y variantes) y los `.env` por modo de Vite bajo `frontend/`, `web/` o `client/`; sin tag, la excepción de Vite exige el sufijo de modo. | Implementado | `jueces/j09_secretos.py` (`comprobar_env_versionados`) |
| RF-038 | El sistema debe detectar claves privadas en el árbol versionado (`G8-4`). | Patrón `-----BEGIN ... PRIVATE KEY-----` (RSA, EC, OPENSSH, PGP, DSA). Se busca también en directorios de prueba. | Implementado | `jueces/j09_secretos.py` |
| RF-039 | El sistema debe detectar credenciales embebidas en una cadena de conexión (`G8-4`). | Esquemas postgres, mysql, mongodb, redis, amqp y http(s) con `usuario:clave@host`. No es hallazgo si la cadena está interpolada desde variables ni si el host es de ejemplo (`localhost`, `127.0.0.1`, `example.`). | Implementado | `jueces/j09_secretos.py`; `tests/test_j09_secretos.py` |
| RF-040 | El sistema debe detectar valores con apariencia de secreto generado (`G8-4`). | Exige a la vez una clave con nombre secreto (`SECRET`, `TOKEN`, `PASSWORD`, `API_KEY`, `HMAC`, etc.) y un literal con forma de credencial; descarta referencias `${VAR}`, marcadores de relleno y sufijos inocentes (`_URL`, `_ALGORITHM`, `_VERSION`…). `*_ACCESS_KEY` se trata como identificador y sólo bloquea si el valor parece generado (hexadecimal o base64 de 32 o más caracteres, o formato `vN:`). Las líneas comentadas se escanean igual. | Implementado | `jueces/j09_secretos.py` (`parece_secreto`, `generado`, `entropia`) |
| RF-041 | El sistema debe limitar el escaneo de secretos a archivos que puedan contenerlos. | Excluye extensiones binarias, archivos de bloqueo de dependencias, directorios como `node_modules/` y `dist/`, y archivos de más de 512 KB. En archivos de prueba sólo se miran claves privadas y `.env`. | Implementado | `jueces/j09_secretos.py` (`escaneable`, `ES_PRUEBA`) |
| RF-042 | El sistema debe verificar que exista un endpoint `/health` utilizable por la sonda de despliegue (`G8-9`). | `BLOQUEA` si no se encuentra `/health` en el backend Python ni en un `location /health` del nginx interno; si exige autenticación; si el nginx devuelve un código de error o redirección; o si ejecuta `execute()` con una cadena cruda sin `text()`. Sin compose en la raíz se anota no evaluado. Sin tag: también ve `Depends()` por defecto, `dependencies=[...]`, `sesion_actual` y `RedirectResponse`. | Implementado | `jueces/j11_salud.py`; `tests/test_j11_salud.py` |
| RF-043 | El sistema debe advertir cuando un fallo de datos se disfraza de aplicación sana (`G8-11`). | `AVISA` si un `except` de `/health` devuelve 200 sin una vía que haga visible el fallo. No exige 503: `REGLAS.md` explica que la guía y `DOCKER.md` se contradicen en este punto. | Implementado | `jueces/j11_salud.py`; `REGLAS.md` (nota sobre `G8-11`) |
| RF-044 | El sistema debe advertir cuando el healthcheck del compose no apunta a `/health` (`DK-5`). | `AVISA`. Hasta el 2026-11-21 se emitía como `DOCKER-hc`, sin fila en `REGLAS.md`; ahora es `DK-5`, con su fuente en `DOCKER.md` (`60d9167`, sin tag). | Implementado | `jueces/j11_salud.py` (`comprobar_coherencia_healthcheck`); `REGLAS.md` |
| RF-069 | El sistema debe verificar que el cuerpo de `/health` lleve la clave `app` (`SEM-4`). | `AVISA` si ni el módulo del handler ni el `return` de `location /health` del nginx interno llevan `app`, que es lo único que delata una colisión de `APP_PORT`. Corre en toda aplicación, sembrada o no. Desde el 2026-11-21, sin tag. | Implementado (sin tag) | `jueces/j11_salud.py`; `REGLAS.md` |

### 4.5. Módulo 5: Jueces de semilla, interfaz, construcción y código (j12, j13, j14, j16)

Estos cuatro jueces sólo actúan sobre repositorios que declaran su alcance con un archivo `.semilla`
en la raíz. `j12`, `j13`, `j14` y `j16` gradúan la severidad de sus reglas más nuevas por la fecha
de siembra: bloquean en lo sembrado desde su vigencia y avisan en lo anterior.

| ID | Requisito | Regla de negocio / detalle | Estado | Fuente |
|---|---|---|---|---|
| RF-045 | El sistema debe detectar piezas congeladas de la semilla editadas por la aplicación (`SEM-1`). | Calcula la huella SHA-256 de cada archivo del lock presente en la aplicación, con `\r\n` normalizado a `\n`. Si no coincide con el lock vigente ni con el historial, `BLOQUEA` como «editada». Que el archivo no exista no es hallazgo. Requiere `adopta:` con `semilla` o sin la clave. | Implementado | `jueces/j12_semilla.py`; `semilla.lock`; `tests/test_j12_semilla.py` |
| RF-046 | El sistema debe distinguir una pieza atrasada de una editada (`SEM-1`). | Si la huella coincide con algún bloque de `semilla.lock.historial`, `AVISA` siempre, sin plazo, indicando la fecha hasta la que esa versión fue vigente. Si el historial falta, se comporta como «editada» y lo anota no evaluado; si no se entiende, se ignora entero y se anota. | Implementado | `jueces/j12_semilla.py`; `semilla.lock.historial`; `REGLAS.md` |
| RF-047 | El sistema debe verificar que un `outline:0` tenga sustituto de foco (`UI-9`). | `BLOQUEA` si una hoja de estilo quita el contorno sin un `:focus-visible` que lo sustituya; los comentarios CSS no se leen. Requiere `adopta:` con `interfaz` o sin la clave. | Implementado | `jueces/j13_interfaz.py`; `tests/test_j13_interfaz.py` |
| RF-048 | El sistema debe verificar que los tokens de color usados se redefinan en el tema oscuro (`UI-3`). | `BLOQUEA` un token usado como texto, borde o anillo de foco que no se redefine en el bloque del tema oscuro. Sin tag: sin ningún bloque de tema oscuro también es `UI-3` (antes se anotaba «no evaluado» y el juez salía OK), y ese caso bloquea sólo en lo sembrado desde el 2026-11-22 y avisa en lo anterior. | Implementado | `jueces/j13_interfaz.py`; `REGLAS.md` |
| RF-049 | El sistema debe verificar que `prefers-reduced-motion` apague todo el movimiento (`UI-15`). | `BLOQUEA` si queda movimiento fuera del bloque de movimiento reducido. | Implementado | `jueces/j13_interfaz.py` |
| RF-050 | El sistema debe verificar el rastro de construcción con la fábrica (`FAB-8`). | `docs/CONSTRUCCION.md` debe existir (versionado si hay git), sin `[PENDIENTE]` ni `[VERIFICAR]`, con `metodologia:`, `instancia:`, `objetivos:` y `consultas:`, una metodología `smb-metodologia-…` y al menos un `correlation_id` con forma válida; sin `registrado:` sólo avisa. Sólo comprueba la forma: no llama a ningún servicio y lo anota como no evaluado en cada ejecución. | Implementado | `jueces/j14_construccion.py`; `tests/test_j14_construccion.py` |
| RF-051 | El sistema debe limitar el tamaño de los archivos de código (`COD-1`). | Más de 1000 líneas es hallazgo de la severidad que corresponda por fecha; entre 801 y 1000 siempre `AVISA`. No se mide lo que `.semilla` declara `ajeno:` ni, con `maqueta:`, la maqueta validada. | Implementado | `jueces/j16_codigo.py`; `tests/test_j16_codigo.py` |
| RF-052 | El sistema debe verificar que el frontend sea TypeScript estricto (`COD-2`). | Ningún `.js` o `.jsx` en `frontend/src/` y un `frontend/tsconfig*.json` con `"strict": true`. | Implementado | `jueces/j16_codigo.py` |
| RF-053 | El sistema debe verificar la independencia del dominio (`COD-3`). | El dominio (`frontend/src/dominio/`, `backend/app/dominio/` y la carpeta `dominio/` de servicios hermanos) no importa interfaz, adaptadores, red, base de datos ni el sistema (`os` en Python; `fs`, `http`, `pg`, `process.env` en Node); en lo nuevo `frontend/src/dominio/` debe existir. | Implementado | `jueces/j16_codigo.py` |
| RF-054 | El sistema debe graduar la severidad de las reglas nuevas por la fecha de siembra. | `BLOQUEA` si `fabrica:` de `.semilla` es igual o posterior a la vigencia de la regla y adopta `semilla`; `AVISA` si es anterior, si falta o si sólo adopta otro estándar (con fecha vigente se cuenta como supresión); sin `.semilla`, `NO_APLICA`. Vigencias: `FAB-8` 2026-10-20, `COD-N` 2026-10-24, `FAB-9` 2026-11-13, y, sin tag, `UI-3` sin tema oscuro y `AUD-1` 2026-11-22. | Implementado | `jueces/j14_construccion.py`, `jueces/j16_codigo.py`, `jueces/j13_interfaz.py`, `jueces/j12_semilla.py`; `REGLAS.md` |
| RF-065 | El sistema debe vigilar la lista de paquetes del sistema de la imagen (`SEM-2`). | `AVISA` si una línea de `backend/paquetes-sistema.txt` no lleva motivo de 12 caracteres o más, o si el paquete es para compilar (`gcc`, `make`, `build-essential`, `*-dev`). Regla nueva sin fecha desde la que bloquee. Del 2026-11-20, sin tag. | Implementado (sin tag) | `jueces/j12_semilla.py`; `REGLAS.md` |
| RF-066 | El sistema debe detectar pruebas selladas que faltan (`SEM-3`). | `AVISA` por cada pieza sellada de `backend/tests/` (pruebas de contrato, de arquitectura y su arnés) que falta en una aplicación que adopta `semilla` y tiene backend: borrarla no rompe nada, la calla. Se suprime en `.semilla` con el marcador y la ruta. Desde el 2026-11-21, sin tag. | Implementado (sin tag) | `jueces/j12_semilla.py`; `REGLAS.md` |
| RF-067 | El sistema debe verificar que la auditoría esté siempre, con el último ingreso de cada persona (`AUD-1`). | En lo que adopta `semilla` y tiene `backend/app/`: las cuatro piezas selladas de la auditoría, `composicion/acceso.py`, `main.py` que llama a `montar_acceso(`, la ruta de actividad que sirve `ultimos-ingresos` y, con frontend, las vistas `Actividad` y `UltimosIngresos`. Mira la forma; que se escriban filas lo prueban los contratos sellados de la aplicación. `BLOQUEA` en lo sembrado desde el 2026-11-22. Sin tag. | Implementado (sin tag) | `jueces/j12_semilla.py`, `jueces/comun_auditoria.py`; `REGLAS.md` |
| RF-068 | El sistema debe vigilar que no se edite la maqueta que validó el cliente (`MAQ-1`). | Con `maqueta:` en `.semilla`, `AVISA` si un archivo de `frontend/src/maqueta/` no coincide con su sha256 de `maqueta/PROCEDENCIA.md`, si falta o si falta la procedencia. Desde `v2.0.15` (2026-11-12). | Implementado | `jueces/j12_semilla.py`; `REGLAS.md`; `docs/VERSIONADO.md` |
| RF-070 | El sistema debe exigir que se diga qué se miró de la interfaz (`FAB-9`). | Con `frontend/package.json`, `docs/CONSTRUCCION.md` lleva `mirado:` con qué se miró y qué se vio, de 12 caracteres o más y sin `[PENDIENTE]`; sólo la forma. `BLOQUEA` en lo sembrado desde el 2026-11-13. Desde `v2.0.15`. | Implementado | `jueces/j14_construccion.py`; `REGLAS.md` |
| RF-071 | El sistema debe exigir una prueba por caso de uso (`COD-4`). | `AVISA` si un caso de uso (`app/aplicacion/casos/*.py`, `frontend/src/aplicacion/*.ts` fuera de `puertos/`) no es nombrado por ninguna prueba versionada; sólo que exista, no si es buena. Desde `v2.0.16` (2026-11-14). | Implementado | `jueces/j16_codigo.py`; `REGLAS.md` |
| RF-072 | El sistema debe exigir el Zen de Python con chequeos en el CI de la aplicación (`COD-5`). | `AVISA` si, con backend en Python, no hay `backend/ruff.toml` y un workflow que corra `ruff check` y `ruff format --check`, o si, con frontend, `.oxlintrc.json` no tiene las reglas del Zen y un workflow no corre `npm run lint`. No ejecuta ruff ni oxlint: mira que la aplicación los tenga y los corra. Desde el 2026-11-21, sin tag. | Implementado (sin tag) | `jueces/j16_codigo.py`, `jueces/comun_zen.py`; `REGLAS.md` |

### 4.6. Módulo 6: Distribución por workflow reusable y autoprueba

| ID | Requisito | Regla de negocio / detalle | Estado | Fuente |
|---|---|---|---|---|
| RF-055 | El sistema debe ofrecerse como workflow reusable invocable desde el CI de cada aplicación. | Disparador `workflow_call` con entradas `modo` (por defecto `advisory`), `perfil` (`aplicacion`), `jueces` (vacío: todos), `ref_jueces` (`v2`) y `runner` (`ubuntu-latest`); salidas `bloqueantes` y `supresiones`, y en `main`, sin tag, también `estado` y `avisos`. | Implementado | `.github/workflows/verificar.yml`; `docs/VERSIONADO.md` |
| RF-056 | El sistema debe verificar el repositorio llamante con una versión determinada del motor. | Dos checkouts: el repositorio llamante (profundidad 1) y `coipo_jueces` en `.coipo_jueces` con la referencia de `ref_jueces`, los dos con `persist-credentials: false`. Si no se puede determinar la referencia, el paso falla con error. | Implementado | `.github/workflows/verificar.yml` (paso `motor`) |
| RF-057 | El sistema debe publicar el resumen y conservar los hallazgos aunque el job falle. | Con `if: always()`, agrega `RESUMEN.md` al resumen del paso y sube `RESUMEN.md` y `hallazgos.json` como artefacto con nombre único por invocación y retención de 30 días. | Implementado | `.github/workflows/verificar.yml` |
| RF-058 | El sistema debe probarse a sí mismo en cada cambio. | En `push` a `main`, en `pull_request` y a mano: suite `unittest`, importación de cada juez con el intérprete sin paquetes, comprobación de que todo `uses:` del reusable lleva SHA de 40 caracteres, jueces sobre el propio repositorio en modo bloqueante con perfil `encuadre_operativo`, y un job que invoca el reusable de la rama. En `main`, sin tag: el Zen con ruff y actionlint con versión y sha256 fijados. | Implementado | `.github/workflows/autotest.yml` |
| RF-059 | El sistema debe permitir probar un runner propio antes de usarlo como compuerta. | `probar-runner.yml` (disparo manual con la etiqueta del runner) se retiró el 2026-11-21 (`f91f5e7`). La entrada `runner` del reusable sigue. | Retirado | historial de git (`f91f5e7`); `docs/VERSIONADO.md` |
| RF-073 | El sistema debe avisar cuando su propia autoprueba falla en `main`. | `alerta-main.yml` (`workflow_run` de `Autotest` en `main`) abre o comenta un issue «main en rojo» y lo cierra al volver a verde; sólo `GITHUB_TOKEN` con `issues: write`. Desde el 2026-11-14 (`0c56216`, en `v2.0.17`). | Implementado | `.github/workflows/alerta-main.yml` |

### 4.7. Módulo 7: Catálogo de reglas, deuda y versionado

| ID | Requisito | Regla de negocio / detalle | Estado | Fuente |
|---|---|---|---|---|
| RF-060 | El sistema debe mantener trazabilidad en los dos sentidos entre los códigos emitidos y el catálogo. | Una prueba recorre el árbol sintáctico de los jueces y falla si un código emitido no tiene fila en `REGLAS.md`, si una fila no la emite ningún juez o si la columna «Juez» no coincide. Desde el 2026-11-21 (`60d9167`, sin tag) lee el primer argumento de toda llamada a `bloquea` o `avisa` y falla ante un alias, y un `comun_*.py` no puede emitir; antes sólo reconocía códigos con la forma `LETRAS-NÚMERO`. | Implementado (sin tag) | `tests/test_reglas_citadas.py`; `REGLAS.md` |
| RF-061 | El sistema debe impedir que una regla sin fuente escrita bloquee. | Si una regla de la tabla «Reglas sin fuente escrita» llama a `bloquea()`, la prueba `PruebaSeveridad` falla. | Implementado | `tests/test_reglas_citadas.py`; `REGLAS.md` |
| RF-062 | El sistema debe mantener un registro de las supresiones activas del propio repositorio. | `DEUDA.md` lleva una fila por supresión (regla, dónde, por qué, qué la cerraría); declara una supresión activa (`G8-4`), nombrada por su prueba (`test_clave_privada_en_un_test_si_bloquea`) y no por un número de línea (`88b6afb`). | Implementado | `DEUDA.md` |
| RF-063 | El sistema debe publicarse con dos clases de tag. | `vN.N.N` anotado e inmutable; `vN` móvil que se reapunta al commit del último `vN.x`. Un cambio que pueda poner rojo a un repositorio hoy verde es una mayor nueva; un juez que sólo bloquea lo sembrado desde su vigencia puede ir en `vN.x` con su radio medido. Lo que hay en `main` sin tag se lista en «Sin publicar». Es política escrita; el procedimiento vive fuera del repositorio. | Parcial | `docs/VERSIONADO.md` |
| RF-064 | El sistema debe impedir que la referencia por defecto del motor quede en una mayor anterior. | Una prueba compara el `default` de `ref_jueces` con los tags (en CI) o con la mayor vigente que declara `docs/VERSIONADO.md`. Otra detecta claves duplicadas en un mismo mapa de los workflows. | Implementado | `tests/test_verificar_yaml.py`; `tests/test_workflows_yaml.py` |

## 5. Funcionalidades complementarias e integraciones

#### Integraciones y salidas

| Elemento | Tipo | Detalle | Fuente |
|---|---|---|---|
| GitHub Actions | Integración | Único canal de distribución. Los jueces leen `GITHUB_ACTIONS` y escriben en `GITHUB_OUTPUT`; el workflow escribe en `GITHUB_STEP_SUMMARY` y sube un artefacto. | `.github/workflows/verificar.yml`; `jueces/correr.py` |
| `git` | Dependencia de ejecución | Se invoca `git ls-files -z` sobre el repositorio examinado. Es el único proceso externo. | `jueces/comun.py` |
| Fábrica `coipo_master_produccion` | Integración por archivos | Provee `semilla.lock` y `semilla.lock.historial` (generados por `semilla/sellar.py`), los documentos fuente de las reglas, el procedimiento de publicación y la herramienta que genera este ERS. No hay conexión de red: los archivos se traen al repositorio y se publican con el tag. | `semilla.lock`; `docs/VERSIONADO.md`; `REGLAS.md` |
| Paridad de `j14` con el instrumento de la fábrica | Prueba externa | La fábrica prueba que su instrumento y `j14` coincidan cuando este repositorio está clonado al lado; esa prueba no está en este repositorio. | `jueces/j14_construccion.py` (cabecera) |
| Resumen `RESUMEN.md` | Reporte | Markdown con tabla por juez y detalle de hallazgos, supresiones, no aplica y no evaluado. | `jueces/correr.py` |
| `hallazgos.json` | Exportación | Resultado consolidado; también por juez con `--json`. | `jueces/correr.py`; `jueces/comun.py` |
| Anotaciones en el pull request | Notificación | `::error`, `::warning` y `::notice` con archivo y línea. | `jueces/comun.py` |
| Issue «main en rojo» | Notificación | Lo abre, comenta y cierra `alerta-main.yml` según el resultado de `Autotest` en `main`. | `.github/workflows/alerta-main.yml` |
| Salida por consola | Reporte | Con color si la salida es un terminal y `NO_COLOR` no está definida. | `jueces/comun.py` |

**Tareas programadas.** No hay: ningún workflow usa `schedule` (buscado el 2026-11-21). Los
disparadores son `workflow_call`, `push` a `main`, `pull_request`, `workflow_dispatch` y
`workflow_run`.

**Notificaciones por correo, importaciones masivas y conexiones a servicios externos.** No existen
en el código. `j14` declara expresamente que no llama al servicio de metodologías y que no debe
tener clave ni red hacia él.

## 6. Diccionario de datos

El repositorio no tiene base de datos. Se describen las estructuras en memoria, de archivo y de
mensaje que el sistema maneja.

| Entidad / tabla | Clave primaria | Claves foráneas | Atributos principales |
|---|---|---|---|
| `Hallazgo` (dataclass inmutable) | No tiene | `regla` → código de `REGLAS.md` | `regla`, `severidad` (`BLOQUEA` o `AVISA`), `archivo`, `mensaje`, `manifestacion`, `linea`, `arreglo`. |
| `Resultado` (dataclass) | `juez` | Contiene `Hallazgo` | `juez`, `descripcion`, `hallazgos`, `no_evaluado`, `supresiones`, `comprobado`, `no_aplica`; propiedades derivadas `bloqueantes` y `veredicto`. |
| `Adopcion` (dataclass) | No tiene | Archivo `.semilla` del repositorio examinado | Capas adoptadas y línea citada de la declaración; estructura definida en `jueces/comun_semilla.py`. |
| JSON por juez (`--json` de un juez) | `juez` | No tiene | `juez`, `modo`, `no_evaluado`, `no_aplica`, `supresiones`, `veredicto`, `comprobado`, `hallazgos`. |
| JSON consolidado (`hallazgos.json`) | `repo` | `resultados[].juez` | `repo`, `modo`, `perfil`, `bloqueantes`, `avisos`, `supresiones`, `resultados` (por juez: `veredicto`, `comprobado`, `no_evaluado`, `no_aplica`, `supresiones`, `hallazgos`). |
| Salidas del job (`GITHUB_OUTPUT`) | No tiene | No tiene | `estado` (`no_corrio` o `corrio`), `bloqueantes`, `avisos`, `supresiones`; además `ref` y `artefacto` del paso `motor`. |
| `semilla.lock` | Ruta del archivo | No tiene | Una línea por archivo: huella SHA-256 (64 hexadecimales), dos espacios, ruta relativa. Comentarios con `#`. 45 piezas el 2026-11-21. |
| `semilla.lock.historial` | Bloque (`# vigente_hasta: AAAA-MM-DD`) y ruta | Rutas de `semilla.lock` | Encabezado `# formato: 1`; por bloque, pares huella–ruta del lock que dejó de ser vigente en esa fecha. |
| `.semilla` (en el repositorio examinado) | No tiene | No tiene | `version:`, `gerencia:`, `adopta:` (`semilla`, `interfaz`), `fabrica:` (AAAA-MM-DD), `maqueta:`, `ajeno:`. Las cuatro últimas son las que lee este repositorio. |
| Marcador de supresión | Regla y línea | `regla` → código de `REGLAS.md` | `coipo-jueces:ignorar(REGLA) motivo`, motivo de 12 caracteres o más. Para `SEM-3` va en `.semilla`, con la ruta de la pieza en la misma línea. |
| `REGLAS.md` (tabla «Reglas vigentes») | `Código` | `Juez` → archivo `jNN_*.py` | `Código`, `Juez`, `Qué comprueba`, `Fuente`, `Severidad`. La tabla «Reglas sin fuente escrita» reemplaza las dos últimas por «Qué respalda hoy la regla». |
| `DEUDA.md` (tabla «Supresiones activas») | No tiene | `Regla` → código de `REGLAS.md` | `Regla`, `Dónde`, `Por qué`, `Qué la cerraría`. |
| `insumos/MANIFIESTO.yaml` | `ruta` | No tiene | Por archivo: `ruta`, `sha256`, `origen`, `contiene_pii`, `puede_versionarse`, `uso`; lista `notas`. |

## 7. Requerimientos no funcionales y puesta en marcha

| ID | Categoría | Requisito | Estado | Fuente |
|---|---|---|---|---|
| RNF-001 | Compatibilidad | Los jueces deben usar únicamente la biblioteca estándar de Python; no se instala ningún paquete en el CI de las aplicaciones. Un paso de la autoprueba importa cada juez con el intérprete sin paquetes. | Implementado | `.github/workflows/autotest.yml`; `README.md` |
| RNF-002 | Seguridad | Un juez no debe modificar el repositorio que examina: sólo lectura. | Implementado | `jueces/comun.py` (`Repo`); `README.md` |
| RNF-003 | Seguridad | Los workflows deben correr con permisos mínimos (`contents: read`; `issues: write` sólo en `alerta-main.yml`), con las acciones de terceros fijadas por SHA de 40 caracteres y sin persistir la credencial del checkout. | Implementado | `.github/workflows/verificar.yml`; `.github/workflows/autotest.yml`; `.github/workflows/alerta-main.yml` |
| RNF-004 | Seguridad | Las entradas del workflow deben llegar al guion por variables de entorno y no interpoladas en el shell, para evitar la ejecución de su contenido. | Implementado | `.github/workflows/verificar.yml` (paso `correr`) |
| RNF-005 | Seguridad | El repositorio no debe contener secretos ni archivos `.env`, y los datos de prueba deben ser sintéticos: nunca se copia un archivo de un repositorio privado. Como es público, tampoco debe describir secretos de otras aplicaciones ni direcciones de la red interna: las pruebas usan IP de documentación (192.0.2.x, RFC 5737) desde `c347f53`. | Implementado | `CLAUDE.md`; `tests/ayuda.py`; `.gitignore`; `c347f53` |
| RNF-006 | Disponibilidad | El job de verificación debe tener tiempo máximo de 10 minutos para no encolar los despliegues siguientes. | Implementado | `.github/workflows/verificar.yml` |
| RNF-007 | Disponibilidad | La verificación debe poder correr en un runner propio que tenga `git` y `python3`, para no depender de la cuota de Actions. | Implementado | `.github/workflows/verificar.yml` (entrada `runner`) |
| RNF-008 | Rendimiento | El repositorio examinado se clona con profundidad 1 y no se instala Python: se usa el del runner. | Implementado | `.github/workflows/verificar.yml` |
| RNF-009 | Compatibilidad | Los jueces deben operar igual en Windows y en Linux: decodificación UTF-8 explícita, tolerancia a BOM, normalización de fin de línea en las huellas y fin de línea LF forzado en el repositorio. | Implementado | `jueces/comun.py`; `jueces/j12_semilla.py`; `.gitattributes` |
| RNF-010 | Auditoría | Toda supresión y todo «no aplica» deben quedar visibles en el resumen y en las salidas del job. | Implementado | `jueces/comun.py`; `jueces/correr.py` |
| RNF-011 | Fiabilidad | Un juez nuevo debe calibrarse contra repositorios que se saben correctos antes de encenderse; cada juez documenta su calibración en la cabecera y cada publicación su radio en `docs/VERSIONADO.md`. Las mediciones no son reproducibles desde este repositorio. | Parcial | `README.md`; cabeceras de `jueces/j*.py`; `docs/VERSIONADO.md` |
| RNF-012 | Pruebas | Debe existir una prueba por juez y pruebas transversales, sobre repositorios git reales y temporales; una prueba omitida se considera fallo. El 2026-11-21 hay 29 archivos de prueba con 418 funciones `test_` contadas en el código, y la suite ejecutada sobre `81629c2` corrió 422 pruebas en OK (72,6 s). | Implementado | `tests/`; `README.md` |
| RNF-013 | CI/CD | La suite, la autoverificación y la invocación real del reusable deben correr en cada `push` a `main` y en cada pull request. | Implementado | `.github/workflows/autotest.yml` |
| RNF-014 | Mantenibilidad | Ningún archivo del motor debe superar las 800 líneas; por ello el lector YAML, el de `.semilla` y los auxiliares de `AUD-1` y `COD-5` se separaron de `comun.py`. El 2026-11-21 el más largo es `jueces/j12_semilla.py`, con 736. El código propio sigue el Zen de Python con el `ruff.toml` de la semilla (sin tag). | Implementado | `jueces/comun_*.py`; `ruff.toml` |
| RNF-015 | Respaldo | No documentado en el repositorio. El artefacto de cada ejecución se conserva 30 días. | No determinado | `.github/workflows/verificar.yml` |

### 7.1. Estado de implementación y puesta en marcha

- **Ambientes.** No hay ambientes de despliegue. El sistema corre en runners de GitHub Actions
  (`ubuntu-latest` por defecto o uno propio) y en equipos locales.
- **Versión publicada.** `docs/VERSIONADO.md` describe hasta `v2.0.20` (2026-11-21), con `v2` como
  mayor vigente y `v1` congelada. El `main` leído (28 commits después de `v2.0.19`) se publicó ese
  mismo día como `v2.0.20`, con su radio medido el 2026-11-21
  sobre 88 clones (`BLOQUEA` 180 → 182 y `AVISA` 555 → 613, una vez corregida la vigencia de
  `UI-3`). Antes de publicarlos se reselló `semilla.lock` y se vio `Autotest` en verde con los pasos
  nuevos de actionlint y ruff, como pide ese documento.
- **Adopción.** Según `docs/ESTADO.md` de la fábrica (medido el 2026-11-21 con su
  `flota/consumidores.py`), 32 repositorios de la organización llaman a `verificar.yml` (2 en
  bloqueante, 31 con el motor en `v2`) y 19 despliegan sin llamarlo. Desde el 2026-11-21 las
  aplicaciones nuevas nacen con el gate en `modo: bloqueante`.
- **Para ejecutar.** `python3 jueces/correr.py --repo <ruta> --modo advisory --resumen RESUMEN.md`;
  pruebas con `python3 -m unittest discover -s tests -v` (`CLAUDE.md`).
- **Qué falta, según el propio repositorio.** `UI-16` a `UI-20` del estándar de interfaz no tienen
  juez (`REGLAS.md`); queda pendiente corregir en la fábrica la severidad de `UI-9` del estándar
  (`REGLAS.md`, lectura del 2026-11-10 no repetida); publicar lo que está en `main` sin tag, con el
  lock resellado.

## 8. Trazabilidad, supuestos y limitaciones

#### Documentos y archivos consultados

| Archivo | Qué aportó |
|---|---|
| `REGLAS.md` (códigos y filas nuevas, nota sobre `UI-16` a `UI-20`) | `DK-5`, `SEM-2` a `SEM-4`, `AUD-1`, `MAQ-1`, `UI-3`, `COD-4`, `COD-5`, `FAB-9`, y las reglas sin fuente escrita. |
| `docs/VERSIONADO.md` (desde `v2.0.15` y «Sin publicar») | Qué entró en cada tag, qué está sólo en `main`, el radio medido y lo que falta para publicar. |
| `README.md` (búsquedas), `DEUDA.md`, `CLAUDE.md` | Explicación de la numeración de jueces, cifras de la flota, supresión activa, convenciones. |
| `.github/workflows/verificar.yml`, `autotest.yml`, `alerta-main.yml` | Entradas, salidas, pasos, permisos, tiempos, retención y disparadores; el retiro de `probar-runner.yml`. |
| `jueces/` (listado, `PERFILES` de cada juez, largo de cada archivo) | Once jueces, dos auxiliares nuevos y el tamaño del motor. |
| `semilla.lock` (encabezado), `semilla.lock.historial` (bloques), y `sellar.py --comprobar` de la fábrica | 45 piezas, 17 bloques y el lock desfasado. |
| `tests/` (listado y conteo), y la suite ejecutada el 2026-11-21 | 29 archivos, 418 funciones `test_`, 422 pruebas en OK. |
| Historial de git y tags | Los commits que resolvieron cada punto de la sección siguiente; desde el 2026-11-21, `v2` = `v2.0.20`. |
| `docs/ESTADO.md` de `coipo_master_produccion` | Adopción del gate en la flota y los pendientes de la fábrica que tocan a este repositorio. |
| Lectura del 2026-11-10, no repetida: `insumos/00-PROBLEMA.md`, `insumos/MANIFIESTO.yaml`, `jueces/comun.py`, `comun_yaml.py`, `comun_semilla.py`, `correr.py`, las cabeceras de los once jueces y las llamadas a `bloquea` y `avisa` de `j01`, `j06`, `j08`, `j09` y `j11`, `tests/ayuda.py` y las pruebas transversales, `.gitignore`, `.gitattributes` | Lo que esta versión conserva de la V1 sin volver a leerlo. |

### Supuestos

- Se asume que el repositorio es público porque así lo declaran `README.md`, `CLAUDE.md` y
  `verificar.yml`; su visibilidad real en GitHub no fue comprobada.
- Los «usuarios» del sistema se dedujeron de los documentos; el repositorio no nombra una unidad
  requirente ni define roles.
- Las cifras de la flota (repositorios, hallazgos, tasas de propagación, radios) son las que informa
  el repositorio o la fábrica en sus fechas; no fueron verificadas para este documento.
- Los requisitos de las reglas nuevas se redactaron desde `REGLAS.md` y `docs/VERSIONADO.md`, no
  desde la lectura línea a línea del código de los jueces; la suite completa sí se ejecutó.
- Lo que esta actualización no volvió a leer conserva la lectura del 2026-11-10 (ver la tabla
  anterior).
- Este documento no reproduce nombres de personas ni detalles de secretos de otras aplicaciones: el
  repositorio es público.

### Contradicciones y vacíos encontrados

Cada punto de la V1 (2026-11-10) dice si quedó **resuelto**, con su commit, o **abierto**, con su
referencia en `docs/ESTADO.md` de la fábrica cuando la tiene. «Sin tag» quiere decir que el arreglo
está en `main` y todavía no llega a quien consume `@v2`.

- **Código de regla fuera del catálogo. Resuelto el 2026-11-21, sin tag** (`60d9167`): `DOCKER-hc`
  pasa a `DK-5`, con fila en `REGLAS.md`, y `tests/test_reglas_citadas.py` lee el primer argumento
  de toda llamada a `bloquea` y `avisa`.
- **Exposición de información de otros sistemas en un repositorio público. Resuelto en parte el
  2026-11-21, sin tag** (`c347f53`): `j09`, `j08`, `j01`, `comun.py` y `README.md` ya no nombran la
  aplicación, el commit ni las variables de aquel `.env`, y las IP internas de `.gitattributes`,
  `j05` y su prueba se cambiaron por IP de documentación. Sigue abierto: una fila de la tabla de
  mediciones de `README.md` todavía asocia el nombre de otro repositorio de la organización con
  «secretos versionados», y el historial conserva lo anterior; el riesgo de fondo se cierra rotando
  esas credenciales, y lo registra el documento de estado de la fábrica.
- **Datos personales. Abierto.** El 2026-11-21 un nombre de persona, como quien decidió, firmó o
  autorizó reglas y publicaciones, aparece en 16 archivos versionados (entre ellos `REGLAS.md`,
  `docs/VERSIONADO.md`, `CLAUDE.md`, `ruff.toml`, `autotest.yml`, cabeceras de jueces y pruebas). No
  hay otros datos personales ni secretos versionados a la vista en lo leído. `docs/ESTADO.md` no lo
  registra.
- **`insumos/01-SOLUCION.md` contradice al código. Abierto.** Sigue citando `jueces/comun.py:568`
  (línea 14) y un veredicto de tres estados (línea 78); el código y `REGLAS.md` establecen cuatro
  veredictos y que `UI-3`, `UI-9` y `UI-15` bloquean. `insumos/` se regenera a mano con
  `coipo_aireadme`; su último cambio es del 2026-10-25 (`d80eea9`). `docs/ESTADO.md` no lo registra.
- **`DEUDA.md` citaba un archivo que no está en el árbol. Resuelto el 2026-11-21, sin tag**
  (`88b6afb`): la supresión se nombra por su prueba, sin el fixture inexistente ni un número de
  línea que se pudra.
- **`j14` sólo comprueba la forma. Abierto, por diseño.** Un `correlation_id` inventado con la forma
  correcta pasa; el juez lo declara y que los identificadores existan en IGNUS lo mira sólo la
  herramienta de la fábrica con la clave. Referencia: `D8-5 (resto)` de `docs/ESTADO.md`.
- **Cifras de pruebas. Resuelto por medición el 2026-11-21:** la suite corrió 422 pruebas en OK
  sobre `81629c2`, con 418 funciones `test_` en el texto de 29 archivos. Las cifras de los
  documentos (301 el 2026-10-25, 322 en `v2.0.15`, 327 en `v2.0.16`, 137 en `FILAS_REGLAS_UI.md`)
  son de sus fechas.
- **Tamaño de la flota inconsistente entre documentos. Abierto en parte.** `jueces/comun.py` ya no
  habla de 22 aplicaciones; `docs/VERSIONADO.md` (línea 4) todavía dice «las 22 apps de la flota»,
  mientras sus radios se miden sobre 84, 88 o 91 repositorios con fecha y `README.md` da 24 como
  «los de entonces». Referencia: `T6` de `docs/ESTADO.md` (el denominador de la flota tecleado en
  documentos).
- **Numeración de jueces con saltos. Resuelto el 2026-11-21, sin tag** (`0e564c0`): `README.md`
  explica que `j03`, `j04`, `j07` y `j10` vienen de un diseño en cuarentena que nunca se escribió, y
  que `j15` existe sólo en una rama de rescate y nunca se publicó.
- **Procedimiento de publicación y documentos fuente fuera del repositorio. Abierto, por diseño.**
  Siguen en `coipo_master_produccion` (`docs/publicar-los-jueces.md`, citado en el «Aviso
  permanente» de `docs/ESTADO.md`); desde aquí no se puede verificar que las reglas citadas digan lo
  que el catálogo afirma.
- **Estado posterior a `v2.0.14` sin entrada en el versionado. Resuelto:** `docs/VERSIONADO.md`
  documenta `v2.0.15` a `v2.0.20`; la sección «Sin publicar» (desde `8ce32f8`) lista lo que hay en
  `main` después del último tag, y se vació al publicar `v2.0.20` el 2026-11-21.
- **Unidad requirente, responsables, respaldo y nivel de adopción actual. Abierto en parte.** La
  adopción ya está medida, por la fábrica (sección 7.1); la unidad requirente, los responsables y el
  respaldo siguen sin documentar en el repositorio.
- **Nuevo: el lock no tiene las piezas de la auditoría. Abierto.** El 2026-11-21, `semilla/sellar.py --comprobar`
  de la fábrica da este `semilla.lock` por DESFASADO respecto de la semilla, mientras `AUD-1` (sin
  tag) ya exige esas piezas. `docs/VERSIONADO.md` deja el resellado para antes de publicar.

Este documento se elaboró leyendo el código y la documentación del repositorio en las fechas
indicadas, sin entrevistar a la unidad requirente. Los requisitos marcados como Implementado indican
que existe código que los realiza, no que su funcionamiento haya sido probado más allá de la suite.
Debe ser validado por el equipo responsable antes de usarse como especificación oficial.
