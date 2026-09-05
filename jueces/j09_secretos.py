#!/usr/bin/env python3
"""j09 — secretos en el árbol versionado.  (D-31)

Es el primero de los tres jueces que se encienden en modo bloqueante, porque es
el único cuyo hallazgo no admite discusión: un secreto en git ya salió del
perímetro, y ninguna configuración posterior lo devuelve.

EL CASO QUE FUNDA ESTA REGLA
  `COIPO_USUARIOS/.env` está en `git ls-files` desde el commit 1b475c2 del
  2026-04-20, con `JWT_SECRET` (62 hex) y `RUT_HMAC_SECRETS` (v1:<64 b64url>)
  reales. El `.gitignore` del repo SÍ lista `.env` — pero un archivo ya
  trackeado ignora el `.gitignore`, así que la protección es cosmética. Ese JWT
  es HS256, global de toda la flota y sin claim `aud`: quien lo tenga firma
  tokens válidos para cualquier app de CONAF, incluido `is_admin: true`.

  Y `RUT_HMAC_SECRETS` es peor, porque no se arregla rotando: `core/rut.py` no
  re-hashea lo antiguo (haría falta el RUT en claro, que justamente no se
  guarda), de modo que cada `rut_hmac` escrito con `v1` queda calculado para
  siempre con una clave publicada. La seudonimización de esas filas es nula.

PRUEBA DE CALIBRACIÓN (obligatoria antes de encender la regla)
  Corrido hoy sobre COIPO_USUARIOS este juez debe salir ROJO, y sobre
  coipo_prensa2 y COIPO_ENTREGA_PLANTA debe salir VERDE — sus `.env.example`
  usan placeholders a propósito. Si no reproduce esas tres respuestas, el
  verificador está mal y no se conecta a nada.

POR QUÉ `git ls-files` Y NO UN RECORRIDO DEL DISCO
  Un `.env` en el directorio de trabajo es lo NORMAL y correcto: es como se
  desarrolla. Lo que constituye el incidente es que esté versionado. Un juez
  que mirase el disco daría rojo a todo el mundo el primer día, y un juez que
  da rojo a todo el mundo se desactiva en una semana.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import Repo, Resultado, ejecutar, suprimido  # noqa: E402

REGLA = "D-31"

# --------------------------------------------------------------------------
# Qué archivos se miran
# --------------------------------------------------------------------------

# `.env` versionados que SÍ son legítimos:
#   - los ejemplos, que existen precisamente para llevar placeholders;
#   - los `.env.*` de Vite bajo frontend/, que en esta flota contienen
#     `VITE_API_BASE_URL=` y nada más (COIPO_USUARIOS/frontend/.env.production
#     está VACÍO a propósito, para que las rutas queden relativas).
#
# Estar en la allowlist exime de la regla "no versionar .env", NO del escaneo
# de contenido. Un `.env.example` con un secreto real dentro sigue siendo un
# incidente, y de hecho es la forma más habitual de filtrar uno.
PERMITIDOS_ENV = {
    ".env.example", ".env.sample", ".env.template", ".env.dist",
    ".env.dev.example", ".env.local.example", ".env.prod.example",
}
SUFIJOS_PERMITIDOS = (".env.example", ".env.sample", ".env.template")

# Vite lee estos según el modo; van versionados por diseño.
VITE = re.compile(r"^(frontend|web|client)/\.env(\.(development|production|test))?$")

# Ruido: lo que no se escanea porque no puede contener un secreto escrito a
# mano y sí puede contener basura de alta entropía (hashes, minificados).
EXTENSIONES_BINARIAS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg", ".pdf", ".zip",
    ".gz", ".tar", ".mp4", ".mp3", ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".mbz", ".jar", ".so", ".dll",
    ".pyc", ".whl", ".db", ".sqlite", ".sqlite3",
}
NOMBRES_RUIDO = {
    "package-lock.json", "poetry.lock", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "composer.lock", "go.sum", "requirements.lock",
}
DIRECTORIOS_RUIDO = ("node_modules/", "dist/", "build/", ".venv/", "venv/",
                     "__pycache__/", "site-packages/", "vendor/")
TOPE_BYTES = 512 * 1024

# --------------------------------------------------------------------------
# Qué parece un secreto
# --------------------------------------------------------------------------

CLAVES_SECRETAS = re.compile(
    r"SECRET|TOKEN|PASSWORD|PASSWD|_PWD|APIKEY|API_KEY|ACCESS_KEY|PRIVATE_KEY"
    r"|CREDENTIAL|SALT|HMAC|ENCRYPTION_KEY|SIGNING_KEY",
    re.IGNORECASE,
)

# Sufijos que convierten una clave "secreta" en metadatos inofensivos:
# JWT_ALGORITHM, RUT_KEY_VERSION, SESSION_MAX_AGE_SECONDS, SMTP_PASSWORD_FILE.
SUFIJOS_INOCENTES = re.compile(
    r"_(URL|URI|HOST|PORT|NAME|ALGORITHM|ALGO|EXPIRES|ENABLED|MODE|PATH|FILE"
    r"|ROUNDS|VERSION|TTL|SECONDS|MINUTES|HOURS|DAYS|ANIOS|YEARS|LENGTH|TYPE"
    r"|ID|HINT|LABEL|REQUIRED|POLICY|KEY_VERSION)$",
    re.IGNORECASE,
)

# Un valor que empieza por `$` es una referencia (compose, shell, CI), no un
# secreto: `${JWT_SECRET:?falta}` es exactamente lo que queremos ver.
REFERENCIA = re.compile(r"^\$[\{(]?[A-Za-z_]")

PLACEHOLDER = re.compile(
    r"change|cambiar|example|ejemplo|placeholder|your[_\- ]|tu[_\- ]|poner"
    r"|reemplaz|replace|generar|generate|openssl|sample|dummy|fake|xxxx|todo"
    r"|tbd|aqui|here|<|>|\.\.\.|secreto|password123|admin123"
    r"|^\*+$|^-+$|^_+$|^0+$|^none$|^null$|^empty$|^vacio$"
    # La flota marca sus valores falsos en español, y lo hace bien:
    #   JWT_SECRET: t0-gate-jwt-secret-jamas-usar-en-produccion  (CI del IAM)
    #   SESSION_SECRET=dev-secret-no-usar-en-produccion          (.env.dev.example de EP)
    # Sin estos patrones el juez marcaba como incidente dos valores que el
    # propio repositorio declara falsos en el comentario de al lado.
    r"|no[-_ ]?usar|jamas|jamás|nunca|never|do[-_ ]?not[-_ ]?use"
    r"|en[-_ ]?produccion|en[-_ ]?producción|invalid|invalido|inválido"
    r"|^dev[-_]|[-_]dev$|^local[-_]|[-_]local$|^t0[-_]|^test[-_]|[-_]test$",
    re.IGNORECASE,
)

# Un secreto real es un literal con el juego de caracteres de una credencial.
# Este filtro es lo que separa `JWT_SECRET=a1b2...` de `token = jwt.encode(...)`
# y de `_VARIABLES_SECRETAS = (`: sin el, la primera pasada de este juez emitio
# 68 hallazgos sobre COIPO_USUARIOS y 53 sobre coipo_prensa2 —que tenia que
# salir verde— porque cualquier expresion de codigo entraba como "valor".
LITERAL_CREDENCIAL = re.compile(r"^[A-Za-z0-9_\-+/=:.@]{8,}$")

# Directorios y archivos de prueba. Un `password="hunter2"` en un fixture es
# legitimo y necesario; tratarlo como incidente es la via mas rapida a que
# alguien desactive el juez. En tests solo se miran claves privadas y .env.
ES_PRUEBA = re.compile(
    r"(^|/)(tests?|__tests__|spec|fixtures|grabaciones)(/|$)"
    r"|(^|/)conftest\.py$|(^|/)test_[^/]*$|[^/]*(_test|\.test|\.spec)\.[A-Za-z]+$"
)

HEX_LARGO = re.compile(r"^[0-9a-fA-F]{32,}$")
B64_LARGO = re.compile(r"^[A-Za-z0-9_\-+/]{32,}={0,2}$")
# `v1:<base64url>` — el formato literal de RUT_HMAC_SECRETS.
VERSIONADO = re.compile(r"^v\d+:[A-Za-z0-9_\-+/]{20,}={0,2}$")

CLAVE_PRIVADA = re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----")

# Credencial embebida en un DSN: postgres://<usuario>:<clave>@<host>
#
# Los signos de menor y mayor no son adorno: sin ellos esta línea es un DSN
# válido y el propio juez la marca como hallazgo al correr sobre este repo. Pasó
# en el primer CI verde. Documentar un patrón con un ejemplo que el detector
# reconoce es la forma más rápida de aprender a suprimirlo.
DSN_CON_CLAVE = re.compile(
    r"\b(postgres(?:ql)?|mysql|mongodb|redis|amqp|https?)(?:\+\w+)?://"
    r"(?P<usuario>[^:/\s@]{1,64}):(?P<clave>[^@/\s]{1,128})@"
    r"(?P<host>[^/\s:?]{1,128})",
    re.IGNORECASE,
)

# Interpolación: f-string de Python, plantilla de shell o de compose, formato JS.
#   f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}..."
# en coipo_prensa2/backend/app/config.py:69 NO es una fuga: es exactamente el
# patrón que el decreto D-06 EXIGE —componer la URL desde las cinco variables—
# y marcarlo era señalar como incidente la única forma correcta de hacerlo.
INTERPOLADO = re.compile(r"[{}<>$%]")

HOSTS_DE_EJEMPLO = re.compile(
    r"^(localhost|127\.0\.0\.1|::1|0\.0\.0\.0|ejemplo\.|example\.)", re.IGNORECASE
)

ASIGNACION = re.compile(
    r"""(?P<clave>[A-Za-z_][A-Za-z0-9_]{2,60})\s*[:=]\s*
        (?P<valor>"[^"\n]{0,512}"|'[^'\n]{0,512}'|[^\s\#,;)}\]]{1,512})""",
    re.VERBOSE,
)


def entropia(s: str) -> float:
    """Shannon, en bits por carácter. `openssl rand -hex 32` ronda 4,0."""
    if not s:
        return 0.0
    total = 0.0
    for c in set(s):
        p = s.count(c) / len(s)
        total -= p * math.log2(p)
    return total


def generado(valor: str) -> bool:
    """El valor tiene pinta de haber salido de un generador de claves."""
    return bool(
        VERSIONADO.match(valor)
        or HEX_LARGO.match(valor)
        or (B64_LARGO.match(valor) and entropia(valor) >= 3.5)
    )


def parece_secreto(clave: str, valor: str, *, en_env: bool) -> bool:
    """Heuristica deliberadamente conservadora, y en DOS niveles.

    La primera version dejaba que la entropia del VALOR disparara sola, sin
    mirar la clave. Resultado medido: 68 hallazgos bloqueantes sobre
    COIPO_USUARIOS y 53 sobre coipo_prensa2, que por diseno tenia que salir
    verde. Cualquier cadena de 32 caracteres —un SHA, un identificador largo,
    una clase CSS— era un "secreto". Ese es el generador de ruido que mata a un
    verificador: la gente aprende a suprimir y en tres meses esta apagado.

    Ahora se exige SIEMPRE que la clave sea de las que guardan secretos, y el
    listen se ajusta al archivo:

      en un .env      -> basta un valor no-placeholder de 8+ caracteres. Es
                         donde viven los secretos de verdad, asi que ahi se
                         mira con lupa.
      en codigo       -> hace falta ademas que el valor este claramente
                         GENERADO (hex de 32+, base64 de 32+ con entropia alta,
                         o el formato `vN:<b64>` de RUT_HMAC_SECRETS). Una
                         contrasena corta escrita a mano en un modulo puede ser
                         un ejemplo de la documentacion; una cadena de 64 hex
                         no lo es nunca.
    """
    v = valor.strip().strip("\"'")
    if not v or REFERENCIA.match(v) or PLACEHOLDER.search(v):
        return False
    if not LITERAL_CREDENCIAL.match(v):
        return False
    if not CLAVES_SECRETAS.search(clave) or SUFIJOS_INOCENTES.search(clave):
        return False
    return True if en_env else generado(v)


# --------------------------------------------------------------------------
# Comprobaciones
# --------------------------------------------------------------------------


def escaneable(repo: Repo, ruta: str) -> bool:
    if any(d in ruta for d in DIRECTORIOS_RUIDO):
        return False
    p = Path(ruta)
    if p.name in NOMBRES_RUIDO or p.suffix.lower() in EXTENSIONES_BINARIAS:
        return False
    try:
        if repo.ruta(ruta).stat().st_size > TOPE_BYTES:
            return False
    except OSError:
        return False
    return True


def env_permitido(ruta: str) -> bool:
    nombre = Path(ruta).name
    return (
        nombre in PERMITIDOS_ENV
        or nombre.endswith(SUFIJOS_PERMITIDOS)
        or bool(VITE.match(ruta))
    )


def comprobar_env_versionados(repo: Repo, r: Resultado) -> None:
    """`**/.env` en el árbol versionado.

    Se mira tanto la raíz como los subdirectorios a propósito. Desde que los
    `--exclude` del rsync del despliegue quedaron ANCLADOS (`--exclude='/.env'`),
    un `.env` anidado ya NO se excluye: sí llega al servidor. Antes era solo una
    fuga por git; ahora además se despliega.
    """
    for ruta in repo.versionados():
        nombre = Path(ruta).name
        if not (nombre == ".env" or nombre.startswith(".env.")):
            continue
        if env_permitido(ruta):
            continue
        r.bloquea(
            REGLA, ruta,
            "archivo de entorno versionado en git",
            "cualquiera con acceso al repositorio —y a todo su historial— tiene "
            "las credenciales de producción; el .gitignore no protege un archivo "
            "que ya está trackeado",
            arreglo="git rm --cached <archivo>, rotar TODO lo que contenga y "
                    "purgar el historial. Rotar sin purgar deja el secreto viejo "
                    "accesible en cualquier clon anterior.",
        )


def comprobar_contenido(repo: Repo, r: Resultado) -> None:
    """Escaneo del contenido, con el listón ajustado al tipo de archivo.

    En un archivo de prueba solo se busca una clave privada: los fixtures
    llevan credenciales falsas por necesidad, y tratarlas como incidente es la
    vía más rápida a que alguien apague el juez.
    """
    for ruta in repo.versionados():
        if not escaneable(repo, ruta):
            continue
        texto = repo.texto(ruta)
        if texto is None or chr(0) in texto[:8192]:
            continue

        nombre = Path(ruta).name
        en_env = nombre == ".env" or nombre.startswith(".env.")
        es_prueba = bool(ES_PRUEBA.search(ruta)) and not en_env
        lineas = texto.splitlines()

        for i, linea in enumerate(lineas):
            if len(linea) > 2048:
                continue

            if CLAVE_PRIVADA.search(linea):
                motivo = suprimido(lineas, i, REGLA)
                if motivo:
                    r.supresiones.append(f"{ruta}:{i + 1} clave privada — {motivo}")
                else:
                    r.bloquea(
                        REGLA, ruta, "bloque de clave privada versionado",
                        "la clave sirve para suplantar al servicio; rotarla "
                        "obliga a reconfigurar a cada consumidor",
                        linea=i + 1,
                        arreglo="retirar del historial y emitir un par nuevo",
                    )
                continue

            if es_prueba:
                continue

            for m in DSN_CON_CLAVE.finditer(linea):
                clave, usuario, host = m.group("clave", "usuario", "host")
                if REFERENCIA.match(clave) or PLACEHOLDER.search(clave):
                    continue
                if INTERPOLADO.search(clave) or INTERPOLADO.search(usuario):
                    continue
                # `coipo:coipo@localhost` en un .md es un ejemplo de la
                # documentación, no una credencial. Usuario igual a contraseña
                # es la convención universal del dato de juguete.
                if HOSTS_DE_EJEMPLO.match(host) or clave == usuario:
                    continue
                motivo = suprimido(lineas, i, REGLA)
                if motivo:
                    r.supresiones.append(f"{ruta}:{i + 1} DSN con credencial — {motivo}")
                    continue
                r.bloquea(
                    REGLA, ruta,
                    "credencial embebida en una URL de conexión "
                    f"(usuario '{m.group('usuario')}')",
                    "la contraseña de la base viaja en el código, en los logs de "
                    "la aplicación y en cualquier traza que imprima la URL",
                    linea=i + 1,
                    arreglo="componer la URL desde las cinco variables "
                            "DATABASE_HOST/PORT/USER/PASSWORD/NAME (D-06); nunca "
                            "desde una DATABASE_URL del entorno",
                )

            for m in ASIGNACION.finditer(linea):
                clave, valor = m.group("clave"), m.group("valor")
                if not parece_secreto(clave, valor, en_env=en_env):
                    continue
                motivo = suprimido(lineas, i, REGLA)
                if motivo:
                    r.supresiones.append(f"{ruta}:{i + 1} {clave} — {motivo}")
                    continue
                r.bloquea(
                    REGLA, ruta,
                    f"'{clave}' parece llevar un valor real, no un placeholder",
                    "el secreto está publicado para todo el que tenga acceso al "
                    "repositorio; si es el JWT_SECRET de la flota, permite firmar "
                    "tokens de cualquier app de CONAF",
                    linea=i + 1,
                    arreglo="sustituir por un placeholder que diga cómo generarlo "
                            "(p. ej. '<generar: openssl rand -hex 32>'), rotar el "
                            "valor real y purgar el historial",
                )


def comprobar_gitignore(repo: Repo, r: Resultado) -> None:
    """`/.env` anclado con barra inicial.

    Sin la barra, el patrón casa a cualquier profundidad. `guia-8 §8` documenta
    el caso real: un `data/` sin anclar dejó congelado un catálogo en el
    servidor durante meses, porque `rsync --delete` no borra lo excluido y el
    directorio versionado nunca llegaba a actualizarse. Nadie lo vio: `/health`
    respondió 200 todo ese tiempo.
    """
    if not repo.existe(".gitignore"):
        r.avisa(REGLA, "", "el repositorio no tiene .gitignore",
                "nada impide que el próximo `git add -A` versione un .env",
                arreglo="añadir un .gitignore con /.env y /data/ anclados")
        return

    lineas = repo.lineas(".gitignore")
    patrones = [l.strip() for l in lineas if l.strip() and not l.startswith("#")]
    if any(p in ("/.env", "/.env*") for p in patrones):
        return

    sin_anclar = next((i + 1 for i, l in enumerate(lineas)
                       if l.strip() in (".env", ".env*")), None)
    if sin_anclar:
        r.avisa(REGLA, ".gitignore",
                "'.env' sin barra inicial: casa a cualquier profundidad",
                "un .env anidado queda excluido del rsync y se congela en el "
                "servidor sin que nada avise",
                linea=sin_anclar, arreglo="anclarlo como /.env")
    else:
        r.avisa(REGLA, ".gitignore", "el .gitignore no excluye .env",
                "el próximo `git add -A` versiona las credenciales locales",
                arreglo="añadir /.env")


def comprobar(repo: Repo, r: Resultado) -> None:
    if not repo.tiene_git():
        r.no_evaluado.append(
            f"{repo.raiz} no es un repositorio git: no se puede afirmar qué está "
            "versionado, y mirar el disco daría el veredicto contrario al correcto"
        )
        return
    if not repo.versionados():
        r.no_evaluado.append("`git ls-files` no devolvió nada (¿repo vacío, o git ausente?)")
        return
    comprobar_env_versionados(repo, r)
    comprobar_contenido(repo, r)
    comprobar_gitignore(repo, r)


if __name__ == "__main__":
    ejecutar("j09", "secretos en el árbol versionado (D-31)", comprobar)
