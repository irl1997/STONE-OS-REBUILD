"""STONE STORAGE and DOWNLOADS (M20, M13): disks, games by size, caches and Steam's downloads.

Read from Steam's own files (no Steam interface needed):

  libraries   every Steam library folder (libraryfolders.vdf), its disk's free and total space
  games       installed games by size on disk (SizeOnDisk), plus their shader cache and Proton
              prefix sizes (steamapps/shadercache/<appid>, steamapps/compatdata/<appid>)
  downloads   games Steam is downloading or updating (appmanifest StateFlags and
              BytesDownloaded / BytesToDownload): name and progress
  alerts      a disk with less than LOW_GB free

Cleaning is limited to what Steam rebuilds by itself: a game's shader cache (it is compiled again
the next time the game starts). Uninstalling a game is Steam's (steam://uninstall/<appid>, which
asks for confirmation in Steam's own dialog). Nothing else is deleted.
"""

import glob
import os
import shutil

from . import library, vdf

LOW_GB = 20


def _du(path, limit=200000):
    """Bytes under path (files only, symlinks not followed); stops counting after `limit` entries."""
    total, n = 0, 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
            n += 1
            if n >= limit:
                return total
    return total


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def libraries(root):
    out = []
    for lib in library.library_paths(root):
        try:
            st = os.statvfs(lib)
            free, total = st.f_bavail * st.f_frsize, st.f_blocks * st.f_frsize
        except OSError:
            free = total = None
        out.append({"path": lib, "free": free, "total": total,
                    "low": free is not None and free < LOW_GB * 2**30})
    return out


def _apps(lib):
    """(appid, AppState) of the games of ONE library folder (Steam's tools left out, as in the library)."""
    for acf in sorted(glob.glob(os.path.join(lib, "steamapps", "appmanifest_*.acf"))):
        try:
            st = vdf.get_ci(vdf.load_file(acf, limit=2**20), "AppState")
        except (OSError, vdf.VDFError):
            continue
        if not isinstance(st, dict):
            continue
        appid, name = str(vdf.get_ci(st, "appid") or ""), vdf.get_ci(st, "name") or ""
        if library.valid_appid(appid) and name and appid not in library.TOOL_APPIDS and not library.TOOL_NAME.search(name):
            yield appid, name, st


def games(root, caches=True):
    out = []
    for lib in library.library_paths(root):
        for appid, name, st in _apps(lib):
            if not _int(vdf.get_ci(st, "StateFlags")) & 4:
                continue
            item = {"appid": appid, "name": name, "library": lib, "size": _int(vdf.get_ci(st, "SizeOnDisk"))}
            if caches:
                item["shader_cache"] = _du(os.path.join(lib, "steamapps", "shadercache", appid))
                item["prefix"] = _du(os.path.join(lib, "steamapps", "compatdata", appid))
            out.append(item)
    out.sort(key=lambda g: -(g["size"] or 0))
    return out


def downloads(root):
    out = []
    for lib in library.library_paths(root):
        for appid, name, st in _apps(lib):
            flags = _int(vdf.get_ci(st, "StateFlags"))
            if not flags & (2 | 1024):
                continue
            done, todo = _int(vdf.get_ci(st, "BytesDownloaded")), _int(vdf.get_ci(st, "BytesToDownload"))
            out.append({"appid": appid, "name": name, "downloaded": done, "total": todo,
                        "progress": round(done / todo, 3) if todo else None, "installed": bool(flags & 4)})
    return out


def status(root):
    libs = libraries(root)
    return {"libraries": libs, "games": games(root), "downloads": downloads(root),
            "alerts": [f"Queda poco espacio en {lib['path']}: {lib['free'] / 2**30:.0f} GB libres" for lib in libs if lib["low"]]}


def clear_shader_cache(root, appid):
    """Delete one game's shader cache (Steam compiles it again). Only inside a Steam library."""
    appid = str(appid)
    if not library.valid_appid(appid):
        return {"error": "Juego no válido"}
    freed = 0
    for lib in library.library_paths(root):
        base = os.path.realpath(os.path.join(lib, "steamapps", "shadercache"))
        p = os.path.realpath(os.path.join(base, appid))
        if not p.startswith(base + os.sep) or not os.path.isdir(p):
            continue
        freed += _du(p)
        shutil.rmtree(p, ignore_errors=True)
    return {"ok": True, "freed": freed}
