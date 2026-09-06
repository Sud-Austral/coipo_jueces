# Reglas: qué comprueba cada código y qué documento lo respalda

Este archivo es el **contrato de trazabilidad** de los jueces: cada código que
un juez emite tiene que aparecer aquí con el documento que lo sostiene, y cada
código listado aquí tiene que emitirlo algún juez. Lo verifica
`tests/test_reglas_citadas.py`, y falla en las dos direcciones.

**Por qué existe.** La versión anterior de estos jueces citaba códigos `D-NN` de
un `DECRETOS.md` que no existe en ningún repositorio. Una regla que bloquea un
despliegue citando un documento inexistente no se puede discutir, ni corregir,
ni derogar: solo se puede suprimir. Un código que no puede nombrar su fuente es
una regla que alguien se inventó, y este archivo es lo que lo hace visible.

## Documentos fuente

| Prefijo | Documento | Dónde vive |
|---|---|---|
| `G8-N` | Guía 8 — checklist pre-deploy, punto N | `INSUMO_PRODUCCION2/guia-8-prompt-checklist-pre-deploy.md` |
| `DK-N` | `DOCKER.md` — arquitectura de contenedores | `INSUMO_PRODUCCION2/DOCKER.md` |
| `H-N` | Hallazgo N del estado real del servidor | `INSUMO_PRODUCCION2/00-HALLAZGOS-Y-ESTADO-REAL.md` |
| otros | **sin fuente escrita todavía** | ver la columna «fuente» |

Los dos primeros documentos son privados (viven en `coipo_master_produccion`).
Este repositorio es público y por eso los **cita**, no los copia.

## Reglas vigentes

| Código | Juez | Qué comprueba | Fuente | Severidad |
|---|---|---|---|---|
| `G8-1` | `j02` | el nombre del repositorio está en minúsculas y dentro de `[a-z0-9_-]` | Guía 8, punto 1 | BLOQUEA |
| `G8-2` | `j02` | el compose publica por `${APP_PORT}` y no cablea un número. **La unicidad en la VM no se puede comprobar desde un repositorio: se reporta como no evaluada** | Guía 8, punto 2 | BLOQUEA |
| `G8-3` | `j06` | `.env.example` existe y declara las seis variables base; `APP_PORT` sin comillas; `DATABASE_URL` única prohibida | Guía 8, punto 3 | BLOQUEA |
| `G8-4` | `j09` | secretos reales en el árbol versionado: `.env` commiteado, claves privadas, credenciales en un DSN, valores con pinta de generados | Guía 8, punto 4 | BLOQUEA |
| `G8-5` | `j05` | CORS por dominio: ni `*` ni una IP; y `CORS_ORIGINS` no puede ser una variable inerte que el middleware ignora | Guía 8, punto 5 | BLOQUEA |
| `G8-6` | `j06` | `SESSION_` y `SESION_` conviviendo: con una sola S la cookie viaja sin `Secure` y la app arranca igual | Guía 8, punto 6 | BLOQUEA |
| `G8-7` | `j01` | estructura del compose: sin `version:`, al menos un servicio, **un solo** `ports:`, healthcheck y `restart:` | Guía 8, punto 7 | BLOQUEA / AVISA |
| `G8-8` | `j08` | `.gitignore` existe, ignora `.env`, y sus rutas van **ancladas**: `data/` sin barra inicial ignora cualquier `data` a cualquier profundidad. Además, un `.env` ya versionado no lo salva el `.gitignore` | Guía 8, punto 8 | BLOQUEA |
| `G8-9` | `j11` | `GET /health` existe, sin autenticación, sin redirección, y con `text()` si usa SQLAlchemy 2.x | Guía 8, punto 9 | BLOQUEA |
| `G8-11` | `j11` | un fallo de datos no se disfraza de aplicación sana | Guía 8, punto 11 | AVISA (ver nota) |
| `G8-10` | `j08` | qué llega al servidor con el `rsync` anclado: un `.env` en un subdirectorio **sí** viaja; lo versionado bajo el `data/` de la raíz **nunca** llega | Guía 8, punto 10 | BLOQUEA / AVISA |
| `DK-3` | `j01` | ningún servicio del compose levanta un motor de base de datos | `DOCKER.md`, «La base de datos no está en el `docker-compose.yml`» | BLOQUEA |
| `DK-4` | `j01` | hay `.dockerignore` en la raíz cuando se construye con `context: .`, y excluye `.env` | `DOCKER.md`, «conviene un `.dockerignore` en la raíz» | BLOQUEA / AVISA |

## Reglas sin fuente escrita

Estas comprueban algo real, pero **ningún documento de la flota las dice**. O se
escriben en la guía que corresponda, o se derogan. Mientras tanto no bloquean.

| Código | Juez | Qué comprueba | Qué respalda hoy la regla |
|---|---|---|---|
| `SEM-1` | `j12` | un archivo declarado congelado por `semilla.lock` está editado en una aplicación que declara haberse sembrado (`.semilla` en la raíz) | Ninguno todavía. La regla nace de la medición que funda toda la arquitectura: `DOCKER.md` en 10 repositorios con 3 contenidos distintos, propagación por copia 22 % frente a 100 % del `uses:`. **La mitad de la semilla no puede distribuirse de otra forma** —Docker lee el `Dockerfile` del disco—, así que lo único posible es que la deriva no sea silenciosa. |
| `NG-1` | `j01` | `proxy_pass` a un nombre literal sin `resolver` en el nginx **interno** | Ningún documento. Lo implementan por su cuenta `COIPO_USUARIOS`, `coipo_n8n` y `coipo_seguimiento_madera`; siete repos más no. El comportamiento de nginx (resolución única al arrancar) sí es verificable. **La versión anterior de este juez justificaba la regla con un «despliegue a uat roto con exit 22» que no consta en ningún sitio.** |
| `OPS-1` | `j01` | los servicios declaran `mem_limit` | Ningún documento. Solo `coipo_n8n` lo hace, en sus cuatro servicios. El arreglo exige medir la RAM de la VM antes, así que la regla no puede bloquear. |
| `CI-1` | `j06` | la versión de python/node del CI coincide con la que construyen los Dockerfile | Ningún documento. Divergencia real medida en `coipo_prensa2` (CI 3.11, imágenes 3.13/3.14) y `COIPO_ENTREGA_PLANTA` (CI node 20, Dockerfile node 22): el CI prueba sobre un runtime que no es el que se despliega. |

### Nota sobre `G8-11`

La Guía 8 pide 503 cuando `/health` no puede hablar con la base. `DOCKER.md`
pide que `app` dependa del backend con `condition: service_healthy`. **Juntas,
cualquier fallo del backend tumba el sitio entero en vez de degradarlo**, así que
tres implementaciones independientes —`coipo_prensa2`, `COIPO_ENTREGA_PLANTA` y
`coipo_dendroenergia`— eligieron 200 con el estado en el cuerpo, y las tres lo
dejaron escrito. El estándar va perdiendo 3 a 0 contra el código de producción.

Por eso `G8-11` **avisa y no bloquea**: el hueco real es que el smoke test
(`curl -sf .../health`) solo mira el código HTTP, y ese smoke test vive en
`infra-docker-base`, que por contrato no se edita por app. Ninguna aplicación
puede cerrarlo sola, y bloquear el despliegue de alguien por algo que no está en
su mano es la forma más rápida de que aprenda a suprimir al juez.

## Reglas de la Guía 8 todavía sin juez

Los once puntos de la Guía 8 tienen juez. Lo que queda fuera del alcance de un
verificador por repositorio está declarado como tal: la unicidad de `APP_PORT`
(punto 2) es una propiedad de la VM, y el punto 3 solo comprueba las variables
base, no las que cada backend exige sin default.

## Los cuatro veredictos

Un juez no responde sí o no. La Guía 8 pide su checklist en `[OK] / [FALTA] /
[N/A]`, y aquí eso son cuatro estados porque «no pude mirarlo» tiene que verse
distinto de «no corresponde»:

| Veredicto | Significa | ¿Detiene el despliegue? |
|---|---|---|
| `OK` | comprobó y no encontró nada | no |
| `HALLAZGOS` | comprobó y encontró | sí, si alguno es BLOQUEA |
| `NO_APLICA` | lo miró y aquí no corresponde (el `[N/A]` de la guía) | no |
| `SIN_EVALUAR` | **no pudo** comprobar nada | sí, en perfil `aplicacion` |

`NO_APLICA` lo declara el **juez**, desde evidencia que encontró en el código.
Un repositorio no puede declararse N/A a sí mismo: si pudiera, esa sería la
puerta por la que todo se pone verde sin arreglar nada.
