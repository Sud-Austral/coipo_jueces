# Filas para `REGLAS.md` — las reglas de interfaz (`UI-N`)

> # EJECUTADO EL 2026-09-07. ESTE ARCHIVO YA NO PIDE NADA.
>
> Era un checklist: qué pegar en `REGLAS.md` para que `j13` pudiera viajar. Se
> pegó. **Se conserva como registro de cómo se hizo, no como tarea pendiente**, y
> todo lo que sigue está en pasado aunque su redacción original fuera en futuro.
>
> **Qué pasó de verdad, y difiere de lo que este archivo anticipaba.** La sección
> «Dónde van» dice *«en “Reglas sin fuente escrita”, NO en “Reglas vigentes”»*, y
> eso fue cierto durante unas horas. El **mismo 2026-09-07** se firmó
> `identidad/ESTANDAR_UI.md` (Luis Monsalve, Profesional UIA), la fuente pasó a
> ser escrita, y las tres filas subieron a **«Reglas vigentes» con severidad
> BLOQUEA**. `PruebaSeveridad` no lo impidió porque ya no había nada que impedir:
> impide bloquear **sin** fuente firmada, que es justo lo contrario.
>
> **La suite está en verde** (137 pruebas, 16 subtests). El bloque de abajo que
> dice «LA SUITE ESTÁ EN ROJO HASTA QUE SE PEGUEN ESTAS FILAS» describe el estado
> del 2026-09-07 por la mañana, y ése es su valor: enseña que el mecanismo cazó
> un juez cuyos códigos el catálogo no conocía.
>
> **Lo único de aquí que sigue siendo trabajo pendiente** es la línea final de la
> tabla de calibración, y hay que leerla con el dato nuevo: el 2026-09-08 se
> volvió a medir y `coipo_atraso_personal` —el único repositorio que declara, y
> por tanto el único patrón vivo de `j12` y `j13`— sale con **1 `SEM-1`
> bloqueante**. Su «OK, 1 comprobación» de `j13` sigue siendo cierto, pero ese
> «1» significa que sólo se ejercitó `comprobar_foco`: ese repositorio no tiene
> tema oscuro ni movimiento que apagar, así que **`UI-3` y `UI-15` nunca han
> corrido contra un repositorio real**, sólo contra los fixtures sintéticos de
> `tests/test_j13_interfaz.py`.

**Este archivo no es el catálogo: es lo que hay que pegar en él.** Lo escribió un
asistente de IA el 2026-09-07 y `REGLAS.md` no se toca desde aquí a propósito —
el catálogo lo edita quien lo mantiene, no quien propone una regla.

> ## LA SUITE ESTÁ EN ROJO HASTA QUE SE PEGUEN ESTAS FILAS
>
> Y es correcto que lo esté. Medido ahora mismo:
>
> ```
> FAIL: test_todo_codigo_emitido_esta_documentado
>   {'UI-3': ['j13_interfaz'], 'UI-10': ['j13_interfaz'], 'UI-15': ['j13_interfaz']}
> FAIL: test_cada_codigo_nombra_su_juez_correctamente
>   UI-10 sin fila en REGLAS.md
> ```
>
> `jueces/j13_interfaz.py` emite tres códigos que el catálogo no conoce, y
> `test_reglas_citadas.py` lo caza en las dos direcciones. **Es el mecanismo
> funcionando, no un defecto de la entrega**: un juez cuyos códigos nadie puede
> rastrear hasta un documento es exactamente lo que produjo los `D-NN` de un
> `DECRETOS.md` inexistente. La entrega está completa cuando estas filas están
> pegadas; hasta entonces, `j13` no debería viajar a `main`.

---

## Dónde van: en «Reglas sin fuente escrita», NO en «Reglas vigentes»

**Y no es una cautela: es una consecuencia mecánica.**

El documento que sostiene estos códigos —`identidad/ESTANDAR_UI.md` de
`coipo_master_produccion`— **está en cuarentena y sin firmar**. Un documento
generado por IA y no firmado no es una fuente escrita en el sentido que esa
palabra tiene en este catálogo; darlo por tal repetiría el error que `REGLAS.md`
existe para impedir.

Y la tabla de «sin fuente escrita» promete que sus reglas no bloquean, promesa
que `test_reglas_citadas.py::PruebaSeveridad` hace cumplir: **si una regla de esa
tabla llama a `bloquea()`, la prueba falla**. Poner ahí las `UI-N` convierte la
firma pendiente en algo que el CI vigila solo.

Pegar **al final de la tabla de la sección «Reglas sin fuente escrita»**, después
de la fila de `CI-1`. La cabecera de esa tabla es de **cuatro** columnas:

```
| Código | Juez | Qué comprueba | Qué respalda hoy la regla |
|---|---|---|---|
```

### Las tres filas

```
| `UI-3` | `j13` | un token de color que se usa como texto, borde o anillo de foco está redefinido en el tema oscuro | `identidad/ESTANDAR_UI.md` de `coipo_master_produccion`, **en cuarentena y sin firmar**. Lo que sí está medido: en `coipo_prensa2` seis tokens no se redefinen en `[data-theme=oscuro]`, y el peor da **1,38:1** sobre la tarjeta oscura — texto presente e ilegible. El anillo de foco cae a **2,99:1**, por debajo del 3:1 de WCAG 2.4.11 |
| `UI-10` | `j13` | un `outline:0` va acompañado de un `:focus-visible` que lo sustituya, **en los repositorios que declaran seguir el estándar** (`.semilla` en la raíz) | Ídem, sin firmar. Medido: `coipo_prensa2` tiene **tres recetas distintas** de anillo de foco, **cinco** valores de `outline-offset` (`-3, -2, 1, 2, 3`) y **tres** anchos, ninguno como token. WCAG 2.4.11 sí es norma, pero la regla concreta que este juez comprueba la escribe el estándar |
| `UI-15` | `j13` | el bloque `prefers-reduced-motion` apaga todo el movimiento, no una parte, **en los repositorios que declaran seguir el estándar** (`.semilla` en la raíz) | Ídem, sin firmar. Medido: el bloque de `coipo_prensa2` (`estilos.css:254`) desactiva **una** transición y deja **ocho** vivas. Cumple la letra y no la función |
```

---

## Y una fila más, sólo cuando alguien firme el documento

Al firmarse `identidad/ESTANDAR_UI.md` por un responsable humano —vía 3 de
`borradores/README.md`; para lo operativo, quien opera las VM— hay que hacer
**cuatro cosas, y en este orden**:

**1.** Añadir el prefijo a la tabla «Documentos fuente», después de la fila de
`SEM-N`:

```
| `UI-N` | El estándar de interfaz: color derivado de los banners medidos, escalas, estados y accesibilidad | `identidad/ESTANDAR_UI.md` |
```

**2.** Mover las tres filas de arriba a «Reglas vigentes», que tiene **cinco**
columnas —la quinta es la severidad—:

```
| `UI-3` | `j13` | un token de color usado como texto, borde o anillo de foco está redefinido en el tema oscuro, **en los repositorios que declaran seguir el estándar** (`.semilla` en la raíz) | `ESTANDAR_UI.md`, UI-3 | BLOQUEA |
| `UI-10` | `j13` | un `outline:0` va acompañado de un `:focus-visible` que lo sustituya, **en los repositorios que declaran seguir el estándar** (`.semilla` en la raíz) | `ESTANDAR_UI.md`, UI-10 | BLOQUEA |
| `UI-15` | `j13` | el bloque `prefers-reduced-motion` apaga todo el movimiento, no una parte, **en los repositorios que declaran seguir el estándar** (`.semilla` en la raíz) | `ESTANDAR_UI.md`, UI-15 | BLOQUEA |
```

**3.** Sólo entonces subir las llamadas de `j13_interfaz.py` de `r.avisa(` a
`r.bloquea(`. Antes de mover las filas, `PruebaSeveridad` lo impide — y hace
bien.

**4.** Borrar de `tests/test_j13_interfaz.py` la prueba
`test_ninguna_regla_de_este_juez_bloquea`, que existe precisamente para vigilar
el paso 3. Borrarla es parte del trámite, no un descuido: dejarla puesta haría
fallar la suite en cuanto el juez empiece a bloquear legítimamente.

**Antes de subir a BLOQUEA, repetir la calibración inversa.** Desde que el alcance se declara, `coipo_prensa2` y `COIPO_USUARIOS` salen `NO_APLICA` y no se verían afectados. Los que sí: **todo proyecto sembrado**, que es exactamente a quien va dirigido el estándar. Antes de encender, correrla sobre TODOS los repositorios con `.semilla` — hoy uno, mañana más.

---

## Calibración inversa de `j13`, ejecutada el 2026-09-07

El estándar es para **proyectos nuevos**, y eso no se deja en manos del modo
advisory: `j13` sólo juzga a quien lo **declara** con `.semilla` en la raíz —el
mismo marcador que exige `j12`, y por la misma lección—. `sembrar.py` ya lo
escribe en todo proyecto sembrado, así que el corte no cuesta editar un archivo.

| Repositorio | ¿Declara? | Veredicto |
|---|---|---|
| `coipo_atraso_personal` | **sí** | **OK**, 1 comprobación |
| `coipo_prensa2` | no | NO_APLICA |
| `COIPO_USUARIOS` | no | NO_APLICA |
| `COIPO_ENTREGA_PLANTA` | no | NO_APLICA |
| `coipo_n8n` | no | NO_APLICA |
| `coipo_jueces` | no | NO_APLICA |

**La dirección de la bandera es lo que la hace segura.** Una que dijera «soy
legado, exígeme menos» la pondría cualquiera con prisa, y sería el repositorio
declarándose a sí mismo N/A — la puerta que `comun.py` cierra a propósito:
*«si pudiera, ésta sería la puerta por la que todo se pone verde»*. Ésta reclama
**más** obligación, así que nadie la pone para escapar.

**Y lo que se pierde hay que decirlo.** `coipo_prensa2` SÍ tiene los tres
defectos: `--verde` y `--verde-oscuro` sin redefinir en oscuro —el anillo de foco
a **2,99:1**, bajo el 3:1 de WCAG 2.4.11— y un bloque de movimiento reducido que
apaga una de nueve transiciones. Son ciertos y afectan a alguien hoy. No se
juzgan en su CI porque son anteriores al estándar; su sitio es la ficha de
alineación del repositorio, donde se decide qué se arregla y cuándo.

Antes de declarar el alcance, `j13` daba HALLAZGOS sobre prensa2 y USUARIOS.
Encender 32 frontends heredados con cada regla nueva enseña una sola cosa: a
ignorar la salida del gate.

**Si un día `j13` juzga a un repositorio sin `.semilla`, el error está en el
juez: no debería ni haberlo mirado.**

La calibración se corrió sobre los **seis** repositorios que están en este disco,
no sobre los 57 de la organización. Para los otros el resultado es DESCONOCIDO.
