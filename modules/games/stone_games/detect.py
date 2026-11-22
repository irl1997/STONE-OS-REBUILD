"""Facts about an installed game, read from disk (no game is started, nothing is changed).

  install_dir    <library>/steamapps/common/<installdir> from the game's appmanifest
  build          Steam's buildid (game version) from the appmanifest
  anti_cheat     EasyAntiCheat / BattlEye / other kernel-level anti-cheat files in the game folder
  injected       upscaler injections already installed by the person in the game folder:
                   helixsr     HelixSR (HelixSR/helixsr.dll next to OptiScaler's proxy DLL)
                   optiscaler  OptiScaler (OptiScaler.ini + proxy DLL), without HelixSR
                 with the proxy DLL name (dxgi, winmm, version, ...) and a fingerprint of the
                 files (size + mtime) so an update of HelixSR/OptiScaler invalidates measurements
  proton         the compatibility tool Steam uses for this game (config.vdf), or None (default)
  exe_bits       32 or 64: the game's executable (the largest .exe that is not an installer or a
                 launcher), from its PE header. OptiScaler and HelixSR are 64-bit DLLs: a 32-bit game
                 can never load them (3.1.0-rc16; board, 22-11-2026: Batman Arkham City, 32-bit, was
                 offered FSR 3.1 and STONE then saw it was not loaded). None: unknown

STONE bundles neither. On the person's request only (install.py) it downloads them from their authors
and installs OptiScaler in a game; this module just reads what is there, whoever installed it.
"""

import glob
import hashlib
import os
import re
import struct
import time

from stone_home import library, vdf

PROXIES = ("dxgi.dll", "winmm.dll", "version.dll", "d3d12.dll", "dbghelp.dll", "wininet.dll", "winhttp.dll")
ANTI_CHEAT = (("EasyAntiCheat", "EasyAntiCheat"), ("EasyAntiCheat_EOS.sys", "EasyAntiCheat"),
              ("BattlEye", "BattlEye"), ("BEService_x64.exe", "BattlEye"), ("vgk.sys", "Vanguard"),
              ("mhyprot2.sys", "mhyprot"), ("xigncode", "XIGNCODE"), ("nProtect", "nProtect"),
              ("EAAntiCheat.GameServiceLauncher.exe", "EA Anti-Cheat"))
MAX_DEPTH = 4
# not the game: installers, redistributables, launchers, crash reporters (as install.SKIP_EXE)
NOT_GAME_EXE = re.compile(r"(unins|crash|launcher|redist|setup|install|dxsetup|vc_|dotnet|ue4prereq|epicweb|eac|battleye|updater|"
                          r"helper|report|physx)", re.I)
NOT_GAME_DIR = re.compile(r"^(_?commonredist|redist|redistributables?|directx|dxsetup|vcredist.*|physx.*|support|installers?|"
                          r"__installer|_installer|prereq.*|dotnet.*|easyanticheat|battleye|eac)$", re.I)


def pe_bits(path):
    """32 or 64 from a Windows executable's PE header (machine i386 / AMD64), else None."""
    try:
        with open(path, "rb") as f:
            head = f.read(64)
            if len(head) < 64 or head[:2] != b"MZ":
                return None
            off = struct.unpack_from("<I", head, 0x3C)[0]
            if not 0 < off < 64 * 1024:
                return None
            f.seek(off)
            pe = f.read(6)
    except OSError:
        return None
    if len(pe) < 6 or pe[:4] != b"PE\0\0":
        return None
    machine = struct.unpack_from("<H", pe, 4)[0]
    return 64 if machine in (0x8664, 0xAA64) else 32 if machine == 0x14C else None


def manifest(root, appid):
    for lib in library.library_paths(root):
        acf = os.path.join(lib, "steamapps", f"appmanifest_{appid}.acf")
        try:
            st = vdf.get_ci(vdf.load_file(acf, limit=2**20), "AppState")
        except (OSError, vdf.VDFError):
            continue
        if isinstance(st, dict):
            d = vdf.get_ci(st, "installdir")
            return {"library": lib, "installdir": d if isinstance(d, str) else None,
                    "build": str(vdf.get_ci(st, "buildid") or "") or None, "name": vdf.get_ci(st, "name")}
    return None


def _walk(top, depth=MAX_DEPTH):
    top = os.path.realpath(top)
    base = top.count(os.sep)
    for d, dirs, files in os.walk(top):
        if d.count(os.sep) - base >= depth:
            dirs[:] = []
        yield d, dirs, files


def _fp(paths):
    h = hashlib.sha1()
    for p in sorted(paths):
        try:
            s = os.stat(p)
            h.update(f"{os.path.basename(p)}:{s.st_size}:{int(s.st_mtime)}".encode())
        except OSError:
            pass
    return h.hexdigest()[:12]


def scan_folder(folder):
    out = {"anti_cheat": [], "injected": None, "exe_bits": None}
    if not folder or not os.path.isdir(folder):
        return out
    found_ac = set()
    biggest = None
    top = os.path.realpath(folder)
    for d, dirs, files in _walk(folder):
        # every folder is still looked at for anti-cheat; only the executable search skips installer folders
        in_installer = any(NOT_GAME_DIR.match(x) for x in os.path.relpath(d, top).split(os.sep) if x != ".")
        for f in files if not in_installer else ():
            if f.lower().endswith(".exe") and not NOT_GAME_EXE.search(f):
                try:
                    sz = os.path.getsize(os.path.join(d, f))
                except OSError:
                    continue
                if biggest is None or sz > biggest[0]:
                    biggest = (sz, os.path.join(d, f))
        names = set(dirs) | set(files)
        for marker, name in ANTI_CHEAT:
            if any(n.lower() == marker.lower() or (marker.lower() in n.lower() and len(marker) > 8) for n in names):
                found_ac.add(name)
        lower = {f.lower(): f for f in files}
        if "optiscaler.ini" in lower and out["injected"] is None:
            proxy = next((p for p in PROXIES if p in lower), None)
            # HelixSR: its DLL next to OptiScaler (up to 2.x), or HelixSR Scaler's own install record (3.x, the bridge)
            helix = os.path.isfile(os.path.join(d, "HelixSR", "helixsr.dll")) or os.path.isfile(os.path.join(d, "helixsr", "helixsr.dll")) \
                or "helixsr-scaler.files" in lower
            files_fp = [os.path.join(d, lower["optiscaler.ini"])] + ([os.path.join(d, lower[proxy])] if proxy else []) + \
                glob.glob(os.path.join(d, "[Hh]elix[Ss][Rr]", "*.dll"))
            out["injected"] = {"kind": "helixsr" if helix else "optiscaler", "dir": d, "proxy": proxy[:-4] if proxy else None,
                               "fingerprint": _fp(files_fp)}
    out["anti_cheat"] = sorted(found_ac)
    out["exe_bits"] = pe_bits(biggest[1]) if biggest else None
    return out


def proton_tool(root, appid):
    try:
        d = vdf.load_file(os.path.join(root, "config", "config.vdf"), limit=8 * 2**20)
    except (OSError, vdf.VDFError):
        return None
    m = vdf.get_ci(d, "InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping") or {}
    e = m.get(str(appid)) if isinstance(m, dict) else None
    if isinstance(e, dict):
        name = vdf.get_ci(e, "name")
        return name if isinstance(name, str) and name else None
    return None


# 3.1.0-rc12: the folder walk (anti-cheat, injected upscalers: up to MAX_DEPTH levels of a game that can
# hold tens of thousands of files) was done again for every launch and every look at a game's page. Its
# result is kept per game for CACHE_S, for the same folder and build; install.py forgets it when STONE
# installs or removes files in the game.
CACHE_S = float(os.environ.get("STONE_DETECT_CACHE_S", "120"))
NO_INJECT_S = min(CACHE_S, 30.0)
_SCANS = {}


def _still_valid(hit, now):
    """The cached result still holds for upscaler files: the folder they were in is unchanged (the
    person's own installer, HelixSR's, writes there); with none found it is kept only NO_INJECT_S, so a
    HelixSR installed by its author's installer shows up within that time."""
    inj = hit[2].get("injected")
    if not inj:
        return now - hit[1] < NO_INJECT_S
    try:
        return int(os.stat(inj["dir"]).st_mtime) == hit[3]
    except OSError:
        return False


def forget(appid=None):
    if appid is None:
        _SCANS.clear()
    else:
        _SCANS.pop(str(appid), None)


def facts(root, appid):
    """Everything above for one Steam game; None fields are unknown."""
    m = manifest(root, appid)
    folder = os.path.join(m["library"], "steamapps", "common", m["installdir"]) if m and m.get("installdir") else None
    key, now = (folder, m.get("build") if m else None), time.monotonic()
    hit = _SCANS.get(str(appid))
    if hit and hit[0] == key and now - hit[1] < CACHE_S and _still_valid(hit, now):
        scan = hit[2]
    else:
        scan = scan_folder(folder)
        try:
            mt = int(os.stat(scan["injected"]["dir"]).st_mtime) if scan.get("injected") else None
        except OSError:
            mt = None
        _SCANS[str(appid)] = (key, now, scan, mt)
    return {"appid": str(appid), "installed": bool(folder and os.path.isdir(folder)), "install_dir": folder,
            "build": m.get("build") if m else None, "anti_cheat": scan["anti_cheat"], "injected": scan["injected"],
            "exe_bits": scan.get("exe_bits"),
            "proton": proton_tool(root, appid)}
