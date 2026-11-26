#!/usr/bin/env python3
"""Resumen determinista de un repositorio para `repo_resumen_guardar` (IGNUS).

Lo que una sesión nueva necesita para no explorar a ciegas: árbol, comandos, resultado de
los jueces, dependencias y archivos más tocados, con el commit al que corresponde. Sólo
biblioteca estándar y git: sirve en un PC y en un runner de CI.

    python resumen/resumir_repo.py D:/GitHub/coipo_app            # imprime
    python resumen/resumir_repo.py D:/GitHub/coipo_* --registrar   # a Neo4j
    opciones: --jueces D:/GitHub/coipo_jueces (corre los jueces), --instancia conaf

Sin texto de conversaciones ni contenido de archivos fuera de comandos y nombres de
dependencias. Las líneas con forma de credencial se descartan (y IGNUS las rechaza igual).
"""
import argparse
import collections
import json
import pathlib
import re
import subprocess
import sys
import tempfile

# Misma guarda que mcp/ignus/contexto.py de coipo_mcp (IGNUS vuelve a validar al recibir).
_SECRETO = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"      # JWT
    r"|\b(?:ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}"                     # GitHub
    r"|\bsk-[A-Za-z0-9_-]{20,}"                                            # claves sk-
    r"|\bAKIA[0-9A-Z]{16}\b"                                               # AWS
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?i:\bbearer\s+[A-Za-z0-9._~+/-]{20,})"
    r"|(?i:(?:password|passwd|clave|token|secret|api[_-]?key)\s*[=:]\s*['\"]?[^\s'\"]{8,})")

TOPE = {"arbol": 6000, "comandos": 4000, "jueces": 2500, "dependencias": 2500,
        "mas_modificados": 1500}


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def cortar(texto, n):
    texto = texto.strip()
    return texto if len(texto) <= n else texto[:n].rsplit("\n", 1)[0] + "\n…(cortado)"


def limpio(lineas):
    return [l for l in lineas if not _SECRETO.search(l)]


def nombre_repo(repo):
    url = git(repo, "remote", "get-url", "origin").strip()
    m = re.search(r"[/:]([^/:]+?)(?:\.git)?/?$", url)
    return (m.group(1) if m else pathlib.Path(repo).name)[:80]


def arbol(archivos):
    """Carpetas hasta 2 niveles con cuántos archivos tiene cada una, y los de la raíz."""
    raiz = sorted(a for a in archivos if "/" not in a)
    dirs = collections.Counter()
    for a in archivos:
        partes = a.split("/")
        if len(partes) > 1:
            dirs[partes[0] + "/"] += 1
        if len(partes) > 2:
            dirs["/".join(partes[:2]) + "/"] += 1
    lineas = [f"{len(archivos)} archivos versionados", "raíz: " + ", ".join(raiz[:40])]
    lineas += [f"{d} ({n})" for d, n in sorted(dirs.items())
               if d.count("/") == 1 or n >= 3][:150]
    return "\n".join(lineas)


_BLOQUE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
_CMD = re.compile(r"^\s*(python3?|py |pip|npm|npx|node|pnpm|yarn|docker|make|pytest|uv |go |"
                  r"cargo|bash|sh |\./|git |gh |uvicorn|streamlit)")


def comandos(repo):
    """Bloques de código con comandos de CLAUDE.md (primero) y README.md."""
    salida = []
    for nombre in ("CLAUDE.md", "AGENTS.md", "README.md"):
        f = pathlib.Path(repo) / nombre
        if not f.is_file():
            continue
        texto = f.read_text(encoding="utf-8", errors="replace")
        lineas = [l.rstrip() for b in _BLOQUE.findall(texto) for l in b.splitlines()
                  if _CMD.match(l)]
        if lineas:
            salida.append(f"[{nombre}]")
            salida += list(dict.fromkeys(limpio(lineas)))[:40]
    return "\n".join(salida) or "(sin comandos en CLAUDE.md/README.md)"


def dependencias(repo, archivos):
    salida = []
    for a in archivos:
        base = a.rsplit("/", 1)[-1]
        if a.count("/") > 2 or "node_modules" in a:
            continue
        f = pathlib.Path(repo) / a
        try:
            if base.startswith("requirements") and base.endswith(".txt"):
                nombres = [re.split(r"[<>=~!\[; ]", l.strip())[0] for l in
                           f.read_text(encoding="utf-8", errors="replace").splitlines()
                           if l.strip() and not l.lstrip().startswith(("#", "-"))]
                salida.append(f"{a}: " + ", ".join(nombres[:60]))
            elif base == "package.json":
                d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                for k in ("dependencies", "devDependencies"):
                    if d.get(k):
                        salida.append(f"{a} {k}: " + ", ".join(list(d[k])[:60]))
            elif base == "pyproject.toml":
                m = re.search(r"dependencies\s*=\s*\[(.*?)\]", f.read_text(
                    encoding="utf-8", errors="replace"), re.S)
                if m:
                    salida.append(f"{a}: " + ", ".join(re.findall(r'"([A-Za-z0-9_.-]+)', m.group(1))))
        except (OSError, ValueError):
            continue
    return "\n".join(limpio(salida)) or "(sin requirements/package.json/pyproject)"


def mas_modificados(repo):
    salida = git(repo, "log", "--since=120.days", "--name-only", "--format=")
    c = collections.Counter(l for l in salida.splitlines() if l.strip())
    return "\n".join(f"{n:4d} {a}" for a, n in c.most_common(20)) or "(sin commits en 120 días)"


def jueces(repo, ruta_jueces):
    if not ruta_jueces:
        ci = [p for p in (pathlib.Path(repo) / ".github" / "workflows").glob("*.y*ml")]
        usa = [p.name for p in ci if "coipo_jueces" in p.read_text(encoding="utf-8",
                                                                    errors="replace")]
        return (f"usa coipo_jueces en {', '.join(usa)}" if usa
                else "no llama a coipo_jueces en su CI") + " (jueces no ejecutados aquí)"
    with tempfile.TemporaryDirectory() as t:
        salida = pathlib.Path(t) / "h.json"
        subprocess.run([sys.executable, str(pathlib.Path(ruta_jueces) / "jueces" / "correr.py"),
                        "--repo", str(repo), "--json", str(salida)],
                       capture_output=True, timeout=300)
        if not salida.is_file():
            return "los jueces no terminaron"
        d = json.loads(salida.read_text(encoding="utf-8"))
    lineas = [f"bloqueantes={d.get('bloqueantes')} avisos={d.get('avisos')} "
              f"supresiones={d.get('supresiones')}"]
    for r in d.get("resultados") or []:
        if r.get("veredicto") != "OK":
            h = (r.get("hallazgos") or [{}])[0]
            msg = str(h.get("mensaje") or h.get("detalle") or h)[:160]
            lineas.append(f"{r.get('juez')} {r.get('veredicto')}: {msg}")
    return "\n".join(limpio(lineas))


def resumir(repo, ruta_jueces=None):
    repo = pathlib.Path(repo)
    commit = git(repo, "rev-parse", "HEAD").strip()
    if not commit:
        raise ValueError(f"{repo} no es un repositorio git con commits")
    archivos = [a for a in git(repo, "ls-files").splitlines() if a]
    datos = {"arbol": arbol(archivos), "comandos": comandos(repo),
             "jueces": jueces(repo, ruta_jueces),
             "dependencias": dependencias(repo, archivos),
             "mas_modificados": mas_modificados(repo)}
    datos = {k: cortar(v, TOPE[k]) for k, v in datos.items()}
    return {"repo": nombre_repo(repo), "commit": commit,
            "rama": git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()[:80], **datos}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("repos", nargs="+")
    p.add_argument("--registrar", action="store_true")
    p.add_argument("--jueces", default=None, help="ruta a un clon de coipo_jueces")
    p.add_argument("--instancia", default="conaf")
    a = p.parse_args()
    if a.registrar:
        from ignus import herramientas
    fallos = 0
    for ruta in a.repos:
        try:
            r = resumir(ruta, a.jueces)
        except (ValueError, OSError, subprocess.SubprocessError) as e:
            print(f"SALTA {ruta}: {e}")
            continue
        tam = len(json.dumps(r, ensure_ascii=False))
        if not a.registrar:
            print(json.dumps(r, ensure_ascii=False, indent=1))
            continue
        res = herramientas.ejecutar("repo_resumen_guardar",
                                    {**r, "neo4j_instance": a.instancia})[0]
        if res.get("success"):
            print(f"ok    {r['repo']:40s} {r['commit'][:7]} {tam:6d} B")
        else:
            fallos += 1
            print(f"FALLA {r['repo']:40s} {json.dumps(res.get('error'), ensure_ascii=False)[:300]}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
