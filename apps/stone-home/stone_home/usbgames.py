"""Games for the emulators from a USB drive (3.1.0-rc6).

The owner, 14-11-2026: "conectarle un pendrive con los juegos y que el emulador los lea". A console
installs from a disc and keeps the game; STONE does the same with a USB drive: it finds the games on it
and copies them to ~/Emulation/roms/<system>/ (roms.py), where the emulators read them and from where
they are added to the library. A copy keeps working when the drive is unplugged; a game played from the
drive would not.

Drives: Bazzite mounts them under /run/media (SteamOS's own automount rules, jupiter-hw-support). A
removable partition that is not mounted is mounted with `udisksctl mount` (polkit: rules.d/50-stone.rules
allows the console administrator to mount removable drives, nothing else).

What counts as a game: a file with an extension of a system (roms.SYSTEMS) inside a folder named after
that system (ps2, "PlayStation 2", gba...), at the top of the drive, in roms/ or in Emulation/roms/
(EmuDeck's, RetroDECK's and STONE's own layout); a loose file only when its extension belongs to one
system alone (.gba, .nds, .xci...). Nothing on the drive is changed or run.
"""

import json
import os
import re
import shutil
import subprocess

from . import roms

MEDIA = "/run/media"
CHUNK = 4 * 2**20
# Folder names people and other tools use for each system (lower case, compared without " - " etc.)
ALIASES = {
    "gc": ("gc", "gamecube", "ngc", "nintendo gamecube"), "wii": ("wii", "nintendo wii"),
    "ps2": ("ps2", "playstation 2", "playstation2", "sony playstation 2"),
    "psp": ("psp", "playstation portable", "sony playstation portable"), "ps3": ("ps3", "playstation 3", "playstation3"),
    "wiiu": ("wiiu", "wii u", "nintendo wii u"), "3ds": ("3ds", "n3ds", "nintendo 3ds"), "nds": ("nds", "ds", "nintendo ds"),
    "gba": ("gba", "game boy advance", "gameboy advance", "gb", "gbc"), "dreamcast": ("dreamcast", "dc", "sega dreamcast"),
    "xbox": ("xbox", "microsoft xbox"), "switch": ("switch", "nintendo switch", "ns"),
}
# Extensions that belong to one system only: such a file is a game of that system wherever it is
UNIQUE = {".gba": "gba", ".gbc": "gba", ".gb": "gba", ".nds": "nds", ".3ds": "3ds", ".cci": "3ds", ".cxi": "3ds",
          ".nsp": "switch", ".xci": "switch", ".wbfs": "wii", ".gcm": "gc", ".gdi": "dreamcast", ".cdi": "dreamcast",
          ".wud": "wiiu", ".wux": "wiiu", ".wua": "wiiu", ".pbp": "psp", ".xiso": "xbox"}
MAX_GAMES = 2000


def _key(name):
    return " ".join(re.sub(r"[^0-9a-z]+", " ", name.lower()).split())


SYSTEM_OF = {_key(a): k for k, names in ALIASES.items() for a in names}


def _run(argv, timeout=30):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return None, ""


def mount_removable(run=_run):
    """Mount every removable partition with a file system that nobody mounted (udisksctl, as the
    console administrator). Returns the devices mounted now."""
    rc, out = run(["lsblk", "-J", "-o", "PATH,FSTYPE,MOUNTPOINT,HOTPLUG,RM,TYPE"])
    if rc != 0:
        return []
    try:
        devs = json.loads(out).get("blockdevices") or []
    except ValueError:
        return []
    flat = []

    def walk(ds):
        for d in ds:
            flat.append(d)
            walk(d.get("children") or [])
    walk(devs)
    done = []
    for d in flat:
        removable = d.get("hotplug") in (True, "1", 1) or d.get("rm") in (True, "1", 1)
        path = str(d.get("path") or "")
        if (removable and d.get("type") == "part" and d.get("fstype") and not d.get("mountpoint")
                and re.fullmatch(r"/dev/(sd[a-z]+[0-9]+|mmcblk[0-9]+p[0-9]+|nvme[0-9]+n[0-9]+p[0-9]+)", path)
                and d.get("fstype") in ("vfat", "exfat", "ntfs", "ntfs3", "ext4", "btrfs", "xfs", "f2fs")):
            rc, _ = run(["udisksctl", "mount", "-b", path, "--no-user-interaction"], timeout=60)
            if rc == 0:
                done.append(path)
    return done


def volumes(media=MEDIA, ismount=os.path.ismount):
    """Mounted drives under /run/media (/run/media/<user>/<label> or /run/media/<label>)."""
    out = []
    try:
        top = sorted(os.listdir(media))
    except OSError:
        return out
    for a in top:
        p = os.path.join(media, a)
        if ismount(p):
            out.append(p)
            continue
        try:
            subs = sorted(os.listdir(p))
        except OSError:
            continue
        out += [os.path.join(p, b) for b in subs if ismount(os.path.join(p, b))]
    return out


def _games_in(d, system, depth=1):
    exts = roms.SYSTEMS[system][3]
    out = []
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return out
    for n in names:
        p = os.path.join(d, n)
        if n.startswith("."):
            continue
        if os.path.isfile(p) and n.lower().endswith(exts):
            out.append((system, p))
        elif depth > 0 and os.path.isdir(p):
            out += _games_in(p, system, depth - 1)          # a game in its own folder
    return out


def scan_volume(path):
    """{"path", "label", "games": [{"system", "system_name", "name", "src", "size"}], "bytes"}."""
    found, seen, bases = [], set(), set()
    for base in (path, os.path.join(path, "roms"), os.path.join(path, "ROMs"), os.path.join(path, "Emulation", "roms")):
        try:
            st = os.stat(base)
            names = sorted(os.listdir(base))
        except OSError:
            continue
        if (st.st_dev, st.st_ino) in bases:              # roms and ROMs are one folder on FAT and exFAT drives
            continue
        bases.add((st.st_dev, st.st_ino))
        for n in names:
            p = os.path.join(base, n)
            if n.startswith("."):
                continue
            if os.path.isdir(p) and _key(n) in SYSTEM_OF:
                found += _games_in(p, SYSTEM_OF[_key(n)])
            elif os.path.isfile(p) and os.path.splitext(n)[1].lower() in UNIQUE:
                found.append((UNIQUE[os.path.splitext(n)[1].lower()], p))
    games, total = [], 0
    for system, src in found:
        try:
            st = os.stat(src)
        except OSError:
            continue
        if (st.st_dev, st.st_ino) in seen or len(games) >= MAX_GAMES:
            continue
        seen.add((st.st_dev, st.st_ino))
        size = st.st_size
        games.append({"system": system, "system_name": roms.SYSTEMS[system][1],
                      "name": os.path.splitext(os.path.basename(src))[0], "src": src, "size": size})
        total += size
    return {"path": path, "label": os.path.basename(path), "games": games, "bytes": total}


def scan(media=MEDIA, run=_run, mount=True):
    """Every drive with games on it."""
    if mount:
        mount_removable(run)
    return [v for v in (scan_volume(p) for p in volumes(media)) if v["games"]]


def _safe_name(n):
    n = os.path.basename(n).replace("\x00", "")
    return n if n and not n.startswith(".") else None


def plan(volume, base=None):
    """What a copy would do: [(src, dst, size)] for the games not already on the console, and the
    bytes it needs."""
    base = base or roms.base_dir()
    todo = []
    for g in volume["games"]:
        name = _safe_name(g["src"])
        if not name:
            continue
        dst = os.path.join(base, "roms", roms.SYSTEMS[g["system"]][0], name)
        try:
            if os.path.getsize(dst) == g["size"]:
                continue                                    # already copied
        except OSError:
            pass
        todo.append((g["src"], dst, g["size"]))
    return todo, sum(s for _a, _b, s in todo)


def copy(volume, progress, base=None, cancel=lambda: False):
    """Copy a drive's games to the console. progress(done_bytes, total_bytes, game_name) from this
    thread. Returns {"copied", "skipped", "bytes", "error"}."""
    base = roms.folders(base)
    todo, need = plan(volume, base)
    skipped = len(volume["games"]) - len(todo)
    free = shutil.disk_usage(base).free
    if need > free - 2 * 2**30:                             # 2 GB are always left free
        return {"copied": 0, "skipped": skipped, "bytes": 0,
                "error": f"No hay espacio: hacen falta {need / 2**30:.1f} GB y quedan {free / 2**30:.1f} GB libres"}
    done, copied = 0, 0
    for src, dst, _size in todo:
        if cancel():
            break
        part = dst + ".stone-part"
        try:
            with open(src, "rb") as fi, open(part, "wb") as fo:
                while True:
                    if cancel():
                        break
                    b = fi.read(CHUNK)
                    if not b:
                        break
                    fo.write(b)
                    done += len(b)
                    progress(done, need, os.path.basename(dst))
            if cancel():
                os.remove(part)
                break
            os.replace(part, dst)
            copied += 1
        except OSError as e:
            try:
                os.remove(part)
            except OSError:
                pass
            return {"copied": copied, "skipped": skipped, "bytes": done,
                    "error": f"No se pudo copiar {os.path.basename(src)}: {e.strerror or e}"}
    return {"copied": copied, "skipped": skipped, "bytes": done, "error": None}
