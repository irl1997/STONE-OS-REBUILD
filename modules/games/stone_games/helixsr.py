"""HelixSR in one press (3.1.0-rc16; the owner, 22-11-2026: "para el HelixSR quiero que el usuario lo
seleccione y solo juegue, stone os debe hacer todo para que HelixSR funcione al seleccionarlo").

HelixSR (github.com/lonewolf0622/HelixSR, made and tested on the BC-250) runs NVIDIA's DLSS network and AMD's FSR 4
network as ordinary shaders. Its release ZIP carries no NVIDIA software: its own setup downloads NVIDIA's DLSS
310.7.0 DLL from NVIDIA's GitHub (under NVIDIA's license) and builds the network on the machine, once. Read from
HelixSR 3.4.1 (helixsr-setup.sh, setup/helixsr_setup.py, setup/helixsr_install.py, setup/helixsr_bridge.py):

  helixsr-setup.sh --yes        builds what is missing (a portable Python with numpy, Microsoft's DXC through Proton,
                                NVIDIA's DLL); with --yes and no game folder it installs into NO game ("the games
                                named install, the rest stay as they are")
  setup/helixsr_bridge.py RELEASE status | install --game DIR --way scaler --scaler PKG --scaler-name winmm.dll
                                | remove --game DIR       one JSON object per call (HelixSR Desktop's own interface)

What STONE does when the person picks HelixSR for a game:
  1. NVIDIA's license is shown on STONE's screen, whole (license_text); only the person's ACEPTO lets the build ask
     for NVIDIA's DLL. STONE never accepts a license for anyone: without that ACEPTO nothing is downloaded from NVIDIA.
  2. The release is downloaded from HelixSR's author (install.fetch: GitHub's SHA-256, unpacked safely).
  3. build_start(): HelixSR's own setup runs in the background, unattended, into no game (minutes, once per release);
     build_state() follows it and its log is kept for the diagnostic report.
  4. install_game(): HelixSR Scaler into THIS game through the bridge, as winmm.dll (so STONE switches it per launch
     with WINEDLLOVERRIDES, like OptiScaler); STONE keeps a record so the game's files are known and removable.
  5. The game's upscaler becomes HelixSR; after every launch STONE checks winmm.dll is really loaded (scaling.py).
Never for games with anti-cheat, online-only or 32-bit (HelixSR's own bridge allows anti-cheat games; STONE does not).
"""

import json
import os
import signal
import subprocess
import time
import urllib.parse
import urllib.request

from . import install

LICENSE_KEY = "nvidia-dlss-310.7.0"
LICENSE_URL = "https://raw.githubusercontent.com/NVIDIA/DLSS/v310.7.0/LICENSE.txt"
LICENSE_PAGE = "https://github.com/NVIDIA/DLSS/blob/v310.7.0/LICENSE.txt"
LICENSE_HOSTS = ("raw.githubusercontent.com",)
SCALER_NAME = "winmm.dll"
BUILD_TIMEOUT_S = 3 * 3600


class HelixError(ValueError):
    pass


def state_path():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "stone", "helixsr.json")


def _state():
    try:
        with open(state_path()) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(d):
    os.makedirs(os.path.dirname(state_path()), exist_ok=True)
    tmp = state_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f)
    os.replace(tmp, state_path())


# ---- the release on the console --------------------------------------------------------------------
def release_dir(comp=None):
    """The extracted release folder (with helixsr-setup.sh and setup/helixsr_bridge.py), or None."""
    comp = comp or install.have("helixsr")
    if not comp:
        return None
    for d, dirs, files in os.walk(comp["path"]):
        if d.count(os.sep) - comp["path"].count(os.sep) > 3:
            dirs[:] = []
        if "helixsr-setup.sh" in files and os.path.isfile(os.path.join(d, "setup", "helixsr_bridge.py")):
            return d
    return None


def python():
    """HelixSR's own portable Python when its setup made one (Bazzite is read-only), else the system's."""
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    p = os.path.join(data, "HelixSR", "python", "bin", "python3")
    return p if os.access(p, os.X_OK) else "python3"


def bridge(release, args, run=None, timeout=300):
    """One call of HelixSR's bridge: its JSON answer. Raises HelixError with its message when it says no."""
    argv = [python(), os.path.join(release, "setup", "helixsr_bridge.py"), release, *args]
    try:
        r = (run or subprocess.run)(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        raise HelixError(f"HelixSR no respondió ({e.__class__.__name__})") from e
    line = (r.stdout or "").strip().splitlines()[-1:] or [""]
    try:
        out = json.loads(line[0])
    except ValueError as e:
        raise HelixError("HelixSR respondió algo que STONE no entiende") from e
    if not isinstance(out, dict) or not out.get("ok"):
        raise HelixError((out or {}).get("error") or "HelixSR dijo que no")
    return out


# ---- NVIDIA's license: shown whole, accepted only by the person --------------------------------------
def license_text(get=None):
    """NVIDIA's license text (cached once fetched) and its page, for STONE's screen."""
    cache = os.path.join(install.components_dir(), "helixsr-nvidia-license.txt")
    try:
        with open(cache, encoding="utf-8") as f:
            return {"key": LICENSE_KEY, "text": f.read(), "page": LICENSE_PAGE}
    except OSError:
        pass
    u = urllib.parse.urlparse(LICENSE_URL)
    if u.scheme != "https" or u.hostname not in LICENSE_HOSTS:
        raise HelixError("dirección no permitida")
    if get:
        text = get(LICENSE_URL)
    else:
        req = urllib.request.Request(LICENSE_URL, headers={"User-Agent": "stone-os"})
        with urllib.request.urlopen(req, timeout=20) as r:
            text = r.read(512 * 1024).decode("utf-8", "replace")
    if len(text) < 200:
        raise HelixError("La licencia de NVIDIA no se pudo leer")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(text)
    return {"key": LICENSE_KEY, "text": text, "page": LICENSE_PAGE}


def accepted():
    return bool((_state().get("accepted") or {}).get(LICENSE_KEY))


def accept(by_person, now=None):
    """Recorded only from the person's own ACEPTO on STONE's screen (host: game.helixsrAccept)."""
    if by_person is not True:
        raise HelixError("solo la persona acepta una licencia")
    d = _state()
    d.setdefault("accepted", {})[LICENSE_KEY] = int(now or time.time())
    _save(d)


# ---- the build: HelixSR's own setup, unattended, into no game ---------------------------------------
def log_path():
    return os.path.join(os.path.dirname(state_path()), "helixsr-setup.log")


def build_start(release, popen=None, now=None):
    if not accepted():
        raise HelixError("Falta aceptar la licencia de NVIDIA")
    d = _state()
    b = d.get("build") or {}
    if b.get("pid") and _alive(b["pid"]):
        return b
    os.makedirs(os.path.dirname(log_path()), exist_ok=True)
    log = open(log_path(), "w")
    try:
        p = (popen or subprocess.Popen)(["bash", os.path.join(release, "helixsr-setup.sh"), "--yes"], cwd=release,
                                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                        start_new_session=True)
    finally:
        log.close()
    b = {"pid": p.pid, "release": release, "started": int(now or time.time()), "state": "building"}
    d["build"] = b
    _save(d)
    return b


def _alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    try:                                       # a finished child not yet reaped is a zombie: not alive
        with open(f"/proc/{int(pid)}/stat") as f:
            return f.read().split(") ", 1)[1][:1] != "Z"
    except (OSError, IndexError):
        return True


def _tail(n=12):
    try:
        with open(log_path(), encoding="utf-8", errors="replace") as f:
            return [ln.rstrip() for ln in f.readlines()[-n:]]
    except OSError:
        return []


def build_state(run=None, now=None):
    """{"state": "none" | "building" | "ready" | "failed", "step": last line, "why": ...}."""
    d = _state()
    b = d.get("build") or {}
    release = b.get("release") or release_dir()
    if b.get("state") == "building":
        if b.get("pid") and _alive(b["pid"]):
            if (now or time.time()) - b.get("started", 0) > BUILD_TIMEOUT_S:
                try:
                    os.killpg(int(b["pid"]), signal.SIGTERM)
                except (OSError, ValueError):
                    pass
            else:
                last = [ln for ln in _tail() if ln.strip()]
                return {"state": "building", "step": last[-1][:160] if last else None, "since": b.get("started")}
        ok = False
        try:
            ok = bool(release and bridge(release, ["status"], run=run).get("network_ready"))
        except HelixError:
            ok = False
        b["state"] = "ready" if ok else "failed"
        b["ended"] = int(now or time.time())
        d["build"] = b
        _save(d)
    if b.get("state") == "ready":
        return {"state": "ready", "release": release}
    if b.get("state") == "failed":
        last = [ln for ln in _tail() if ln.strip()]
        return {"state": "failed", "why": last[-1][:200] if last else "la preparación de HelixSR se detuvo"}
    return {"state": "none"}


def pending():
    return _state().get("pending")


def set_pending(appid):
    d = _state()
    d["pending"] = str(appid) if appid else None
    _save(d)


def ready():
    b = _state().get("build") or {}
    return b.get("state") == "ready" and bool(b.get("release")) and os.path.isdir(b["release"])


# ---- one game ----------------------------------------------------------------------------------------
def install_game(appid, facts, run=None):
    """HelixSR Scaler into this game, as winmm.dll, through HelixSR's bridge; STONE keeps the record."""
    b = _state().get("build") or {}
    release = b.get("release")
    if not ready():
        raise HelixError("HelixSR todavía no está preparado en la consola")
    if not facts.get("install_dir"):
        raise HelixError("El juego no está instalado")
    out = bridge(release, ["install", "--game", facts["install_dir"], "--way", "scaler",
                           "--scaler", os.path.join(release, "helixsr-scaler"), "--scaler-name", SCALER_NAME,
                           "--fg", "off"], run=run)
    g = out.get("game") or {}
    exe_dir = g.get("exe_folder")
    if g.get("installed") != "scaler" or not exe_dir:
        raise HelixError("HelixSR no quedó instalado en el juego")
    if (g.get("scaler_dll") or SCALER_NAME).lower() != SCALER_NAME:
        raise HelixError(f"HelixSR quedó como {g.get('scaler_dll')}: STONE necesita winmm.dll para activarlo por partida")
    rec = {"appid": str(appid), "kind": "helixsr", "tag": g.get("version"), "exe_dir": exe_dir, "files": [],
           "via": "helixsr_bridge", "game_folder": facts["install_dir"], "time": int(time.time())}
    os.makedirs(install.installs_dir(), exist_ok=True)
    with open(install._install_path(appid), "w") as f:
        json.dump(rec, f)
    install._forget(appid)
    return rec


def remove_game(appid, run=None):
    rec = install.installed_by_stone(appid)
    if not rec or rec.get("kind") != "helixsr":
        raise HelixError("STONE no instaló HelixSR en este juego")
    b = _state().get("build") or {}
    bridge(b.get("release") or release_dir(), ["remove", "--game", rec["game_folder"]], run=run)
    try:
        os.remove(install._install_path(appid))
    except OSError:
        pass
    install._forget(appid)
    return {"ok": True}
