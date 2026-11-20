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


# ---- which console a disc image is from (3.1.0-rc12), read from the image itself ---------------------
# A loose .iso is GameCube, Wii, PS2, PSP, PS3 or Xbox; until rc11 it was left on the drive. The
# formats' own markers, read without changing anything:
#   GameCube disc        0xC2339F3D at 0x1C          Wii disc        0x5D1C9EA3 at 0x18
#   RVZ / WIA (Dolphin)  "RVZ\x01"/"WIA\x01", then disc type 1 GameCube / 2 Wii (big-endian u32 at 0x48)
#   GCZ (Dolphin)        0xB10BC001 little-endian, sub type 0 GameCube / 1 Wii (u32 at 4)
#   Xbox (XDVDFS)        "MICROSOFT*XBOX*MEDIA" at 0x10000 (or 0x18310000 in a full redump image)
#   ISO 9660 (CD001 at 0x8001): in its root folder SYSTEM.CNF -> PS2, PSP_GAME / UMD_DATA.BIN -> PSP,
#                        PS3_GAME / PS3_DISC.SFB -> PS3
IDENTIFIABLE = (".iso", ".rvz", ".wia", ".gcz")


def _read(f, at, n):
    try:
        f.seek(at)
        return f.read(n)
    except OSError:
        return b""


def _iso9660_root(f):
    pvd = _read(f, 0x8000, 2048)
    if pvd[1:6] != b"CD001":
        return []
    rec = pvd[156:156 + 34]
    lba, size = int.from_bytes(rec[2:6], "little"), int.from_bytes(rec[10:14], "little")
    data = _read(f, lba * 2048, min(size, 64 * 1024))
    names, i = [], 0
    while i < len(data):
        n = data[i]
        if n == 0:
            i = (i // 2048 + 1) * 2048                      # records never cross a sector
            continue
        nl = data[i + 32]
        names.append(data[i + 33:i + 33 + nl].split(b";")[0].decode("ascii", "replace").upper())
        i += n
    return names


def identify(path):
    """The system of a disc image by its content, or None."""
    try:
        with open(path, "rb") as f:
            head = _read(f, 0, 0x60)
            if head[:4] in (b"RVZ\x01", b"WIA\x01"):
                t = int.from_bytes(_read(f, 0x48, 4), "big")
                return {1: "gc", 2: "wii"}.get(t)
            if int.from_bytes(head[:4], "little") == 0xB10BC001:
                return {0: "gc", 1: "wii"}.get(int.from_bytes(head[4:8], "little"))
            if head[0x1C:0x20] == b"\xc2\x33\x9f\x3d":
                return "gc"
            if head[0x18:0x1C] == b"\x5d\x1c\x9e\xa3":
                return "wii"
            for at in (0x10000, 0x18310000):
                if _read(f, at, 20) == b"MICROSOFT*XBOX*MEDIA":
                    return "xbox"
            root = _iso9660_root(f)
    except OSError:
        return None
    if "SYSTEM.CNF" in root:
        return "ps2"
    if "PSP_GAME" in root or "UMD_DATA.BIN" in root:
        return "psp"
    if "PS3_GAME" in root or "PS3_DISC.SFB" in root:
        return "ps3"
    return None


def _game(system, name, main, files):
    """A game to copy: its main file, and every file with where it goes under roms/<system>/."""
    size = 0
    for src, _rel in files:
        try:
            size += os.path.getsize(src)
        except OSError:
            pass
    return {"system": system, "system_name": roms.SYSTEMS[system][1], "name": roms.clean_title(name), "src": main,
            "files": files, "size": size}


def _system_folder(d, system):
    """The games of a system's folder on the drive: loose files, sheets with their tracks, and games in
    their own folder (copied whole, so their extra files go with them)."""
    out = []
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return out
    parts = set()
    exts = roms.SYSTEMS[system][3]
    for n in names:
        if n.startswith(".") or os.path.splitext(n)[1].lower() not in roms.SHEETS:
            continue
        sheet = os.path.join(d, n)
        refs = roms.sheet_files(sheet)
        parts.update(refs)
        main = sheet if roms._ext_of(n) in exts else next((r for r in refs if roms._ext_of(os.path.basename(r)) in exts), None)
        if main:
            out.append(_game(system, os.path.splitext(n)[0], main,
                             [(sheet, n)] + [(r, os.path.relpath(r, os.path.realpath(d))) for r in refs]))
    for n in names:
        p = os.path.join(d, n)
        if n.startswith(".") or os.path.splitext(n)[1].lower() in roms.SHEETS:
            continue
        if os.path.isdir(p):
            main = roms.main_file(p, system)
            if not main:
                continue
            files = []
            for dd, dirs, fs in os.walk(p):
                dirs[:] = [x for x in dirs if not x.startswith(".")]
                files += [(os.path.join(dd, f), os.path.relpath(os.path.join(dd, f), d)) for f in fs if not f.startswith(".")]
                if len(files) > 2000:
                    break
            out.append(_game(system, n, main, files))
        elif os.path.isfile(p) and roms._ext_of(n) in exts and os.path.realpath(p) not in parts:
            out.append(_game(system, os.path.splitext(n)[0], p, [(p, n)]))
    return out


def scan_volume(path):
    """{"path", "label", "games": [{"system", "system_name", "name", "src", "files", "size"}], "bytes"}."""
    found, bases = [], set()
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
            ext = os.path.splitext(n)[1].lower()
            if os.path.isdir(p) and _key(n) in SYSTEM_OF:
                found += _system_folder(p, SYSTEM_OF[_key(n)])
            elif os.path.isfile(p) and ext in UNIQUE:
                found.append(_game(UNIQUE[ext], os.path.splitext(n)[0], p, [(p, n)]))
            elif os.path.isfile(p) and ext in IDENTIFIABLE:
                system = identify(p)                     # a loose disc image: which console, from inside it
                if system and ext in roms.SYSTEMS[system][3]:
                    found.append(_game(system, os.path.splitext(n)[0], p, [(p, n)]))
    games, seen, total = [], set(), 0
    for g in found:
        try:
            st = os.stat(g["src"])
        except OSError:
            continue
        if (st.st_dev, st.st_ino) in seen or len(games) >= MAX_GAMES:
            continue
        seen.add((st.st_dev, st.st_ino))
        games.append(g)
        total += g["size"]
    return {"path": path, "label": os.path.basename(path), "games": games, "bytes": total}


def scan(media=MEDIA, run=_run, mount=True):
    """Every drive with games on it."""
    if mount:
        mount_removable(run)
    return [v for v in (scan_volume(p) for p in volumes(media)) if v["games"]]


def _safe_rel(rel):
    """A path under roms/<system>/ taken from the drive: no absolute paths, no "..", no hidden parts."""
    parts = [x for x in rel.replace("\x00", "").replace("\\", "/").split("/") if x not in ("", ".")]
    if not parts or any(x == ".." or x.startswith(".") for x in parts):
        return None
    return os.path.join(*parts)


def plan(volume, base=None):
    """What a copy would do: [(src, dst, size)] for the files not already on the console (a game of
    several files is copied whole), and the bytes it needs."""
    base = base or roms.base_dir()
    todo = []
    for g in volume["games"]:
        for src, rel in g.get("files") or [(g["src"], os.path.basename(g["src"]))]:
            rel = _safe_rel(rel)
            if not rel:
                continue
            dst = os.path.join(base, "roms", roms.SYSTEMS[g["system"]][0], rel)
            try:
                size = os.path.getsize(src)
            except OSError:
                continue
            try:
                if os.path.getsize(dst) == size:
                    continue                                # already copied
            except OSError:
                pass
            todo.append((src, dst, size))
    return todo, sum(s for _a, _b, s in todo)


def leftovers(base):
    """Remove half-copied files a power cut or an unplugged drive left (.stone-part)."""
    gone = 0
    for d, _dirs, files in os.walk(os.path.join(base, "roms")):
        for f in files:
            if f.endswith(roms.PART_SUFFIX):
                try:
                    os.remove(os.path.join(d, f))
                    gone += 1
                except OSError:
                    pass
    return gone


def copy(volume, progress, base=None, cancel=lambda: False):
    """Copy a drive's games to the console. progress(done_bytes, total_bytes, game_name) from this
    thread. Returns {"copied", "skipped", "bytes", "error"}; "copied" counts games, all of whose files
    arrived and were checked (size, written to disk) before taking their final name."""
    base = roms.folders(base)
    leftovers(base)
    todo, need = plan(volume, base)
    left = {d for _s, d, _z in todo}
    games_todo = [g for g in volume["games"] if any(os.path.join(base, "roms", roms.SYSTEMS[g["system"]][0], _safe_rel(r) or "") in left
                                                     for _s, r in (g.get("files") or [(g["src"], os.path.basename(g["src"]))]))]
    skipped = len(volume["games"]) - len(games_todo)
    free = shutil.disk_usage(base).free
    if need > free - 2 * 2**30:                             # 2 GB are always left free
        return {"copied": 0, "skipped": skipped, "bytes": 0,
                "error": f"No hay espacio: hacen falta {need / 2**30:.1f} GB y quedan {free / 2**30:.1f} GB libres"}
    done, ok_files = 0, set()
    for src, dst, size in todo:
        if cancel():
            break
        part = dst + roms.PART_SUFFIX
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
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
                fo.flush()
                os.fsync(fo.fileno())
            if cancel():
                os.remove(part)
                break
            if os.path.getsize(part) != size:
                raise OSError(0, "el archivo copiado no tiene el tamaño del original (¿se desconectó el USB?)")
            os.replace(part, dst)
            ok_files.add(dst)
        except OSError as e:
            try:
                os.remove(part)
            except OSError:
                pass
            return {"copied": _whole(games_todo, ok_files, base), "skipped": skipped, "bytes": done,
                    "error": f"No se pudo copiar {os.path.basename(src)}: {e.strerror or e}"}
    return {"copied": _whole(games_todo, ok_files, base), "skipped": skipped, "bytes": done, "error": None}


def _whole(games, ok_files, base):
    """Games all of whose files are on the console now."""
    n = 0
    for g in games:
        dsts = [os.path.join(base, "roms", roms.SYSTEMS[g["system"]][0], _safe_rel(r) or "")
                for _s, r in (g.get("files") or [(g["src"], os.path.basename(g["src"]))])]
        if all(d in ok_files or os.path.exists(d) for d in dsts):
            n += 1
    return n
