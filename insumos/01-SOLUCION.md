# Solucion, leida del codigo

Este es el documento solido del conjunto: aqui el codigo es la solucion y la
evidencia alcanza para describirla casi completa.

## Que hace

Permite revisar un repositorio ajeno y emitir sobre el un veredicto con
hallazgos clasificados por severidad, sin instalar nada y sin modificar el
repositorio revisado [jueces/correr.py] y [jueces/comun.py]. Permite ejecutar
todas las revisiones de una vez o una sola por separado, apuntando a una ruta
de disco [jueces/correr.py]. Permite entregar el resultado de dos maneras: un
resumen escrito en formato de texto marcado [jueces/correr.py] y anotaciones
volcadas al sistema de integracion continua [jueces/comun.py:568],
[jueces/correr.py:193].

Permite tambien que cada repositorio revisado elija cuanto pesa el resultado:
hay un modo que interrumpe el proceso y otro que solo deja constancia
[README.md], y hay un perfil distinto segun si lo revisado es una aplicacion
o el encuadre operativo [tests/test_tres_estados.py]. Y permite suprimir un
hallazgo concreto siempre que se escriba un motivo, comportamiento que esta
fijado por pruebas en al menos cuatro de las nueve revisiones
[tests/test_j01_despliegue.py], [tests/test_j05_cors.py],
[tests/test_j06_config.py], [tests/test_j12_semilla.py].

## Que revisa cada verificacion

- Despliegue: revisa el archivo de composicion de contenedores, los servicios
  declarados y el contexto de construccion, y mira aparte la configuracion
  del servidor web interno [jueces/j01_despliegue.py]. Las pruebas fijan que
  una version obsoleta, dos servicios publicando puerto, ningun puerto o una
  base de datos dentro de la composicion son motivo de bloqueo
  [tests/test_j01_despliegue.py].
- Identidad: revisa el nombre del proyecto y el puerto publicado
  [jueces/j02_identidad.py]. Las pruebas fijan que el nombre en mayusculas
  bloquea y que un puerto escrito a mano en vez de tomado de una variable
  tambien [tests/test_j02_identidad.py].
- Origenes cruzados: analiza el arbol sintactico de los archivos Python en
  busca de la configuracion de origenes permitidos [jueces/j05_cors.py]. Las
  pruebas fijan que el comodin bloquea, que una variable inerte bloquea, y
  que la ausencia de esa configuracion no es un hallazgo sino un no aplica
  [tests/test_j05_cors.py].
- Configuracion: revisa que exista un archivo de ejemplo de variables de
  entorno, que no convivan dos grafias distintas para lo mismo y que la
  version de lenguaje que se prueba coincida con la que se construye
  [jueces/j06_config.py]. Distingue previamente si el repositorio despliega o
  no, para no exigirle a uno que no despliega [jueces/j06_config.py].
- Lo que viaja al servidor: revisa las entradas del archivo de exclusiones y
  que archivos quedarian versionados o sincronizados [jueces/j08_rsync.py].
  Las pruebas fijan que una entrada sin anclar bloquea y que el archivo de
  ejemplo de variables nunca es un hallazgo [tests/test_j08_rsync.py].
- Secretos: calcula entropia, decide si un valor parece generado y si parece
  secreto, revisa archivos de entorno versionados y el contenido del codigo
  [jueces/j09_secretos.py]. Las pruebas fijan que un marcador de relleno no
  es un secreto, que una referencia a una variable tampoco lo es, y que una
  credencial dentro de una cadena de conexion si bloquea
  [tests/test_j09_secretos.py].
- Salud del servicio: busca la funcion y la ruta de salud analizando el arbol
  sintactico, y comprueba que la ruta declarada en el chequeo de la
  composicion sea la misma que expone el codigo [jueces/j11_salud.py].
  Ademas mira si esa ruta queda sin autenticacion, si ejecuta SQL en crudo y
  si hay una captura de excepcion que devuelve exito de todas formas
  [jueces/j11_salud.py], [tests/test_j11_salud.py].
- Integridad de la semilla: calcula huellas de los archivos sembrados y las
  contrasta contra un archivo de bloqueo [jueces/j12_semilla.py] y
  [semilla.lock]. Las pruebas fijan que un cambio de fin de linea no cuenta
  como diferencia y que un repositorio que nunca se sembro no se juzga
  [tests/test_j12_semilla.py].
- Interfaz: revisa las hojas de estilo en busca de foco visible, tema oscuro
  y respeto por la preferencia de movimiento reducido
  [jueces/j13_interfaz.py]. Las pruebas fijan explicitamente que ninguna
  regla de esta verificacion bloquea [tests/test_j13_interfaz.py].

## Roles: quien ve que

El codigo no impone roles de persona: no hay autenticacion ni permisos en la
evidencia. Lo que si esta impuesto por el codigo es una escala de severidad
—bloquear, avisar, no corresponder— y un veredicto de tres estados
[jueces/comun.py], [tests/test_tres_estados.py]. Las pruebas fijan que un
verificador que no pudo mirar no puede declararse limpio
[tests/test_tres_estados.py]: esa distincion entre haber revisado y no haber
podido revisar es la decision de diseno mas fuerte del repositorio.
[INFERIDO]

Quien puede cambiar el modo de un repositorio de avisar a bloquear:
[PENDIENTE]

## De donde salen los datos

- La entrada de cada revision es un repositorio de disco, indicado por
  parametro al ejecutar [jueces/correr.py]. No hay ninguna conexion de red ni
  ninguna base de datos en la evidencia. [INFERIDO]
- El catalogo de reglas vive en un documento del propio repositorio, y hay
  una prueba que exige que todo codigo de hallazgo emitido este documentado
  ahi y que todo codigo documentado se emita [REGLAS.md],
  [tests/test_reglas_citadas.py]. Es un cierre de trazabilidad poco habitual
  y conviene registrarlo.
- La lista de archivos sembrados y sus huellas sale del archivo de bloqueo
  [semilla.lock]. Quien es dueno de ese contenido y quien autoriza cambiarlo:
  [PENDIENTE]
- Las pruebas no tocan repositorios reales: construyen repositorios
  sinteticos temporales [tests/ayuda.py]. [INFERIDO]

## Que NO hace

Estas ausencias si son afirmables, porque el analizador busco esas categorias
en el repositorio completo:

- No tiene base de datos: la extraccion de tablas devolvio una lista vacia.
- No declara ninguna dependencia externa: la extraccion de manifiestos
  devolvio una lista vacia, y todos los modulos importados por los
  verificadores pertenecen a la biblioteca estandar del lenguaje o al propio
  repositorio [jueces/comun.py], [jueces/correr.py].
- No expone ningun servicio propio. La unica ruta que aparece en la
  extraccion de endpoints esta dentro de una prueba
  [tests/test_j11_salud.py:50], y es la ruta que la prueba escribe en un
  repositorio sintetico para que el verificador de salud la encuentre. No es
  un endpoint que este sistema sirva. [INFERIDO]
- No hay verificadores numerados 3, 4, 7 ni 10: la numeracion de los archivos
  salta esos cuatro numeros y la evidencia no contiene ningun archivo con
  ellos. Si existieron y se retiraron, o si estan reservados, es [PENDIENTE].

## Iteraciones

Hay un documento propio de versionado [docs/VERSIONADO.md] y el README
muestra que el flujo reutilizable se consume con una etiqueta de version
mayor [README.md], lo que indica un esquema de versiones con etiquetas
estables. [INFERIDO] Las versiones concretas publicadas y sus fechas son
[PENDIENTE], porque el contenido de ese documento no esta en la evidencia
extraida.

## Nota sobre exposicion

El README declara que el repositorio se mantiene publico a proposito, para no
tener que distribuir credenciales de organizacion a cada repositorio que lo
consume, y afirma que los verificadores no llevan secretos [README.md]. La
segunda parte es coherente con la evidencia —no hay manifiestos ni variables
de configuracion de servicio— pero que hoy no haya ningun secreto en el
historial completo del repositorio es [VERIFICAR].
