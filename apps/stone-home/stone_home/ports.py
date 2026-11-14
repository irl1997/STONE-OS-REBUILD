"""Ports of Nintendo Switch 2 games, and Switch 2 emulation (3.1.0-rc6).

The owner, 14-11-2026: "he visto varios proyectos que hacen ports de juegos [de Switch 2]... que stone
os también haga ports". A port is a recompilation: the game's code translated ahead of time into a PC
program, made by each project for one game, which needs the person's own copy of the game (dumped from
their own console). STONE does not make ports: it installs the ones their projects publish for Linux on
x86-64, from each project's own GitHub releases, checks every download against the SHA-256 GitHub
publishes for it, and adds them to the library. No game file, key or dumping tool is ever downloaded:
the port's own start screen takes the person's copy.

Only projects with a Linux x86-64 build are listed (checked 14-11-2026): a Windows-only one (Star Fox's
SpaceAnimalsRecomp) is not. AppImages are unpacked once at install (`--appimage-extract`), so they do not
need FUSE and start without unpacking every time. All of this is experimental: the projects are days or
weeks old; a game may not start, and mkw-recomp says some AMD drivers can hang the GPU. [VERIFICAR EN PLACA]
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request

API = "https://api.github.com/repos/{repo}/releases/latest"
# key -> facts. "asset": the Linux x86-64 file of a release; "needs": what the person brings.
CATALOG = {
    "mkw": {"name": "Mario Kart World", "project": "mkw-recomp", "repo": "adriadam10/mkw-recomp", "kind": "port",
            "asset": r"-x86_64\.AppImage$", "license": "MIT",
            "needs": "Tu copia de Mario Kart World 1.0.0 o 1.8.0 volcada de tu Switch 2 (carpetas exefs y romfs, "
                     "o un archivo .nup o .nx). La primera vez, su pantalla de inicio la prepara: unos 30 GB.",
            "note": "Experimental: algunos menús aún fallan y en algunas GPU AMD la imagen puede colgarse. Sin juego en línea."},
    "eglantine": {"name": "Eglantine", "project": "Eglantine", "repo": "Eglantine-Community/Eglantine", "kind": "emulator",
                  "asset": r"^eglantine-linux-x86_64\.AppImage$", "license": "GPL-3.0",
                  "needs": "Tus juegos de Switch 2 y las claves de tu propia consola, que se indican dentro del emulador.",
                  "note": "Emulador de Switch 2 muy experimental: pocos juegos arrancan y con fallos."},
}
MAX_ASSET = 1024 * 2**20


def base_dir():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "stone", "ports")


def _get(url, limit, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "STONE-OS", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError("too big")
    return data


def _state(key):
    try:
        with open(os.path.join(base_dir(), key, "stone-port.json")) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def exe_of(key):
    st = _state(key)
    p = st.get("exe")
    return p if isinstance(p, str) and os.path.isfile(p) and os.access(p, os.X_OK) else None


def latest(key, get=_get):
    """{"tag", "asset", "url", "size", "sha256"} of the project's latest release for Linux x86-64."""
    c = CATALOG[key]
    rel = json.loads(get(API.format(repo=c["repo"]), 4 * 2**20).decode())
    for a in rel.get("assets") or []:
        if re.search(c["asset"], a.get("name") or ""):
            digest = str(a.get("digest") or "")
            return {"tag": str(rel.get("tag_name") or "")[:40], "asset": a["name"], "url": a.get("browser_download_url"),
                    "size": int(a.get("size") or 0), "sha256": digest[7:] if digest.startswith("sha256:") else None}
    return None


def catalog():
    """Every port with what is installed: [{key, name, project, kind, needs, note, installed, tag}]."""
    out = []
    for k, c in CATALOG.items():
        st = _state(k)
        out.append({"key": k, "name": c["name"], "project": c["project"], "kind": c["kind"], "needs": c["needs"],
                    "note": c["note"], "license": c["license"], "installed": exe_of(k) is not None, "tag": st.get("tag")})
    return out


def install(key, progress, get=_get, run=subprocess.run, steam_ui=None):
    """Download, check, unpack and add one port to the library. progress(state, text) from this thread.
    Returns True on success."""
    if key not in CATALOG:
        progress("error", "Port desconocido")
        return False
    c = CATALOG[key]
    progress("installing", f"Buscando la última versión de {c['project']}…")
    try:
        rel = latest(key, get)
    except Exception as e:  # noqa: BLE001  (no internet, the project moved or was taken down)
        progress("error", f"No se pudo leer {c['project']} en GitHub: {e}")
        return False
    if not rel or not rel["url"] or not rel["sha256"] or not 0 < rel["size"] <= MAX_ASSET:
        progress("error", f"{c['project']} no publica ahora una versión para Linux que STONE pueda comprobar")
        return False
    d = os.path.join(base_dir(), key)
    os.makedirs(d, exist_ok=True)
    if shutil.disk_usage(d).free < rel["size"] * 3 + 2 * 2**30:
        progress("error", "No hay espacio suficiente en el disco")
        return False
    progress("installing", f"Descargando {c['project']} {rel['tag']} ({rel['size'] / 2**20:.0f} MB)…")
    path = os.path.join(d, rel["asset"])
    try:
        data = get(rel["url"], MAX_ASSET, timeout=1800)
    except Exception as e:  # noqa: BLE001
        progress("error", f"No se pudo descargar {c['project']}: {e}")
        return False
    if hashlib.sha256(data).hexdigest() != rel["sha256"]:
        progress("error", f"La descarga de {c['project']} no coincide con la suma que publica GitHub: no se instaló")
        return False
    with open(path + ".part", "wb") as f:
        f.write(data)
    os.chmod(path + ".part", 0o755)
    os.replace(path + ".part", path)
    progress("installing", "Preparando…")
    root = os.path.join(d, "app")
    shutil.rmtree(root, ignore_errors=True)
    try:
        r = run([path, "--appimage-extract"], cwd=d, capture_output=True, timeout=600)
        ok = r.returncode == 0 and os.path.isdir(os.path.join(d, "squashfs-root"))
    except (OSError, subprocess.SubprocessError):
        ok = False
    if ok:
        os.replace(os.path.join(d, "squashfs-root"), root)
        exe = os.path.join(root, "AppRun")
    else:
        exe = path                                   # FUSE is there: the AppImage runs as it is
    with open(os.path.join(d, "stone-port.json"), "w") as f:
        json.dump({"tag": rel["tag"], "asset": rel["asset"], "sha256": rel["sha256"], "exe": exe}, f)
    for old in os.listdir(d):                         # older downloads go
        if old.endswith(".AppImage") and old != rel["asset"]:
            os.remove(os.path.join(d, old))
    name = f"{c['name']} (Switch 2)" if c["kind"] == "port" else f"{c['name']} (emulador de Switch 2)"
    if steam_ui is None:
        from . import steamcef as steam_ui
    if steam_ui.add_shortcut(name, exe, d, "") is not None:
        progress("done", f"{c['name']} instalado. Ya está en tu biblioteca")
    else:
        from . import emulators
        emulators.queue_entries([{"name": name, "exe": f'"{exe}"', "start": f'"{d}"', "options": ""}])
        progress("done", f"{c['name']} instalado. Aparece en tu biblioteca al reiniciar la consola")
    return True
