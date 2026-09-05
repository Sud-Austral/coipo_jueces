# Versionado y publicación de `coipo_jueces`

Este repositorio se consume por `uses:`, no por copia. Eso significa que **el
tag es la interfaz pública**: lo que las 22 apps de la flota ejecutan en cada
push es lo que apunte ese tag, y moverlo mal cambia el comportamiento del CI de
toda CONAF a la vez.

## Dos tags, con propósitos opuestos

| Tag | Qué es | ¿Se mueve? | Para qué |
|---|---|---|---|
| `v1.0.0` | anotado, apunta a un commit concreto | **jamás** | poder decir «el 5 de septiembre corría exactamente esto» |
| `v1` | ligero, apunta al último `v1.x` | **sí, en cada publicación** | que un arreglo llegue a las 22 apps sin tocar 22 repos |

Es la convención de las propias actions de GitHub, y se puede comprobar:
`actions/checkout@v7` y `actions/checkout@v7.0.1` resuelven hoy al mismo commit
`3d3c42e5…`, pero mañana `v7` apuntará a `v7.0.2` y `v7.0.1` seguirá donde está.

**Las apps fijan `@v1`.** Es deliberado y es toda la tesis del repositorio: la
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
python3 jueces/correr.py --repo . --modo bloqueante

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

## Cuándo toca `v2`

- Un juez nuevo en modo bloqueante, o una regla que pasa de `AVISA` a `BLOQUEA`.
- Un cambio en las entradas de `verificar.yml` que rompa a quien no lo actualice.
- Cualquier cosa que pueda poner rojo a un repositorio que hoy está verde.

Todo lo demás —jueces nuevos en advisory, correcciones de falsos positivos,
mensajes más claros— es `v1.x` y viaja solo.

## Comprobar qué está publicado de verdad

```bash
git ls-remote --tags origin          # los tags que existen en GitHub
git ls-remote --heads origin         # las ramas
git rev-parse v1 v1.0.0              # a qué commit apunta cada uno, en local
```

`git tag -l` solo enseña lo **local**. Que un tag exista en tu máquina no
significa que las apps lo puedan usar; hasta el `git push origin <tag>` no
existe para nadie más.
