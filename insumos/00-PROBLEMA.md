# Problema, reconstruido desde el codigo

Este documento se deduce de lo que quedo escrito en el repositorio. No hay
area usuaria en la fuente, asi que cada afirmacion lleva su cita o su marca.

## La cadena de inferencia, dicha en voz alta

El repositorio contiene nueve programas que revisan repositorios ajenos y
emiten hallazgos: despliegue [jueces/j01_despliegue.py], identidad
[jueces/j02_identidad.py], origenes cruzados [jueces/j05_cors.py],
configuracion [jueces/j06_config.py], lo que se sincroniza al servidor
[jueces/j08_rsync.py], secretos [jueces/j09_secretos.py], salud del servicio
[jueces/j11_salud.py], integridad de la semilla [jueces/j12_semilla.py] e
interfaz [jueces/j13_interfaz.py].

De ahi la inferencia: si se construyeron verificaciones automaticas
especificas para cada una de esas nueve cosas, es probable que en cada una de
ellas hubiera errores que se repetian de un repositorio a otro y que nadie
detectaba a tiempo. [INFERIDO]

Hay una lectura mas fina, y es la que sostiene todo el diseno del
repositorio. Las verificaciones no se copian: se distribuyen como un flujo
reutilizable al que otros repositorios apuntan
[.github/workflows/verificar.yml]. Eso solo tiene sentido si el problema no
era unicamente "hay errores", sino "las correcciones no llegaban a todos los
repositorios". [INFERIDO]

El propio README del repositorio afirma haber medido esa tasa de propagacion
en la flota y contrastar el mecanismo de copia contra el mecanismo de
referencia [README.md]. Es una afirmacion del repositorio sobre si mismo, no
un dato verificado por este documento: confirmar que la medicion es actual y
como se hizo queda [PENDIENTE].

## Quien sufre el problema

El codigo no impone roles: no hay autenticacion, no hay guardas y no hay
tabla de permisos en la evidencia. Lo que si esta en el codigo es una escala
de severidad y un veredicto, que son las decisiones que el sistema toma sobre
un repositorio ajeno [jueces/comun.py]. Sus funciones distinguen bloquear,
avisar y declarar que algo no corresponde [jueces/comun.py].

Ademas hay dos perfiles de ejecucion nombrados en el flujo reutilizable y
comprobados en las pruebas, uno para aplicaciones y otro para el encuadre
operativo [tests/test_tres_estados.py]. Que ese par de perfiles corresponda a
dos audiencias distintas es [INFERIDO].

- Rol que ejecuta la verificacion en su repositorio: [PENDIENTE]
- Rol que decide si un hallazgo se corrige o se suprime: [PENDIENTE]
- Rol que mantiene las reglas: [PENDIENTE]
- Cuantas personas son: [PENDIENTE]

## Como lo resolvian antes

Hay un indicio concreto en el codigo: existe una verificacion dedicada a
comprobar que un conjunto de archivos sembrados en un repositorio no fue
editado despues, contrastando huellas contra un archivo de bloqueo
[jueces/j12_semilla.py] y [semilla.lock]. Que exista esa verificacion sugiere
que antes los archivos comunes se distribuian por copia y divergian sin que
nadie lo notara. [INFERIDO]

En la misma linea, hay una verificacion que compara la version de lenguaje
que se prueba en integracion continua contra la que efectivamente se
construye [jueces/j06_config.py], y otra que compara el chequeo de salud
declarado en el compose contra la ruta que realmente expone el codigo
[jueces/j11_salud.py]. Ambas son revisiones que una persona podia hacer a
mano, leyendo dos archivos y comparandolos. [INFERIDO]

- Quien hacia esa revision antes: [PENDIENTE]
- Cuanto tardaba por repositorio: [PENDIENTE]
- Con que frecuencia se hacia: [PENDIENTE]

## Que pasa si no se hace nada

[PENDIENTE] Sin excepcion. El codigo no lo responde y no se deduce de que el
sistema exista.

## Volumen

No hay base de datos: la extraccion de tablas devolvio una lista vacia. El
unico orden de magnitud disponible es el del propio repositorio: nueve
verificadores y once pruebas, una por verificador mas dos transversales
[tests/test_reglas_citadas.py] y [tests/test_tres_estados.py]. Eso mide el
tamano de la herramienta, no el del problema.

Cuantos repositorios se verifican hoy y cuantos hallazgos se emiten por
corrida: [PENDIENTE]

## Quien decide que esta terminado

[PENDIENTE] Sin excepcion. Hay dos modos de ejecucion
nombrados en el README, uno que bloquea y otro que solo avisa [README.md], y hay pruebas que fijan cuando un veredicto
es limpio, cuando tiene hallazgos y cuando el verificador no pudo mirar
[tests/test_tres_estados.py]. Pero elegir el modo en el que corre cada
repositorio es una decision de una persona, y esa persona no esta en el
codigo.
