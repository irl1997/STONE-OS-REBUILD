"""STONE EMULATION (M14): the person's own games for other consoles, in STONE's library.

Games (ROMs, disc images) and BIOS files are the person's own; STONE never downloads them. They go in

    ~/Emulation/roms/<system>/     e.g. ~/Emulation/roms/ps2/Juego.iso
    ~/Emulation/bios/              BIOS files, for the emulators that ask for them (their own setup)

`folders()` creates that tree (with a README per system). `scan()` lists the games it finds for every
system whose emulator (from the Flathub catalog, emulators.py) is installed. `add_to_library()` turns
them into non-Steam shortcuts that start the emulator with the game, so they appear in STONE Home's
library and start through Steam like any game (Gamescope then puts them in front, the guide button
works): through Steam's interface when it runs, otherwise when the STONE session next starts.

Only standalone emulators are used: each one accepts a game file on its command line. Systems served
only by RetroArch cores are left out (a core is a separate download the person makes in RetroArch).
"""

import os
import re

from . import emulators, shortcuts, vdf

# system -> (folder, name, catalog key, extensions, arguments before the file)
SYSTEMS = {
    "gc": ("gc", "GameCube", "dolphin", (".iso", ".gcm", ".gcz", ".rvz", ".ciso"), ["-b", "-e"]),
    "wii": ("wii", "Wii", "dolphin", (".iso", ".wbfs", ".rvz", ".gcz", ".wad"), ["-b", "-e"]),
    "ps2": ("ps2", "PlayStation 2", "pcsx2", (".iso", ".chd", ".cso", ".bin", ".gz"), ["-batch", "-fullscreen", "--"]),
    "psp": ("psp", "PlayStation Portable", "ppsspp", (".iso", ".cso", ".pbp", ".chd"), ["--fullscreen"]),
    "ps3": ("ps3", "PlayStation 3", "rpcs3", (".pkg", ".iso", "eboot.bin"), ["--no-gui"]),
    "wiiu": ("wiiu", "Wii U", "cemu", (".wud", ".wux", ".rpx", ".wua"), ["-f", "-g"]),
    "3ds": ("3ds", "Nintendo 3DS", "azahar", (".3ds", ".cci", ".cxi", ".3dsx"), []),
    "nds": ("nds", "Nintendo DS", "melonds", (".nds",), []),
    "gba": ("gba", "Game Boy Advance", "mgba", (".gba", ".gb", ".gbc"), ["-f"]),
    "dreamcast": ("dreamcast", "Dreamcast", "flycast", (".gdi", ".chd", ".cdi", ".cue"), []),
    "xbox": ("xbox", "Xbox", "xemu", (".iso", ".xiso"), ["-full-screen", "-dvd_path"]),
    # Nintendo Switch: Eden (-f fullscreen, -g game) [VERIFICAR EN PLACA: T-EMU-03]
    "switch": ("switch", "Nintendo Switch", "eden", (".nsp", ".xci", ".nca", ".nso", ".nro"), ["-f", "-g"]),
}
# Another emulator that also opens a system's games, used when the first one is not installed:
# system -> [(catalog key, arguments before the file)]
ALTERNATES = {
    "switch": [("ryujinx", ["--fullscreen"])],
}
MAX_PER_SYSTEM = 300
# 3.1.0-rc12: games of more than one file. A sheet names the files of one game (cue: its tracks, gdi: a
# Dreamcast disc's tracks, m3u: the discs of a multi-disc game); those files are parts, never games of
# their own. A game may also live in its own folder: its main file is chosen as below.
SHEETS = (".m3u", ".cue", ".gdi")
PART_SUFFIX = ".stone-part"


# Said in the system's LEEME.txt: what the emulator needs from the person's own console.
NOTES = {
    "switch": "Eden y Ryujinx piden las claves (prod.keys) y el firmware de tu propia consola: se indican dentro del emulador.",
}


def _ext_of(name):
    n = name.lower()
    return "eboot.bin" if n == "eboot.bin" else os.path.splitext(n)[1]


def sheet_files(sheet):
    """The files a .cue / .gdi / .m3u names that exist next to it (never outside its folder)."""
    d = os.path.dirname(os.path.realpath(sheet))
    try:
        with open(sheet, encoding="utf-8", errors="replace") as f:
            lines = f.read(256 * 1024).splitlines()
    except OSError:
        return []
    names = []
    ext = os.path.splitext(sheet)[1].lower()
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ext == ".cue":
            m = re.match(r'FILE\s+"([^"]+)"', ln, re.I) or re.match(r"FILE\s+(\S+)", ln, re.I)
            if m:
                names.append(m.group(1))
        elif ext == ".gdi":
            if i == 0:
                continue                                   # the number of tracks
            m = re.match(r'\d+\s+\d+\s+\d+\s+\d+\s+(?:"([^"]+)"|(\S+))', ln)
            if m:
                names.append(m.group(1) or m.group(2))
        else:
            names.append(ln)
    out = []
    for n in names:
        p = os.path.realpath(os.path.join(d, n.replace("\\", "/")))
        if p.startswith(d + os.sep) and os.path.isfile(p) and p not in out:
            out.append(p)
    return out


# Systems whose games are folders by nature (a Switch game with its updates and DLC, a PS3 or Wii U game):
# a folder is one game, its main file chosen below. For the others, a folder with several games (a
# «Colección» folder) is several games, unless a sheet (.cue/.gdi/.m3u) ties them together.
FOLDER_GAMES = ("switch", "ps3", "wiiu")


def _candidates(folder, system, depth=3):
    exts = SYSTEMS[system][3]
    found = []
    base = folder.count(os.sep)
    for d, dirs, files in os.walk(folder):
        if d.count(os.sep) - base >= depth:
            dirs[:] = []
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for n in files:
            if not n.startswith(".") and not n.endswith(PART_SUFFIX) and _ext_of(n) in exts:
                found.append(os.path.join(d, n))
        if len(found) > 500:
            break
    return found


def _size(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return -1


def main_file(folder, system, depth=3):
    """The file an emulator opens for a game kept in its own folder: a sheet the system opens first,
    then the formats in the system's order (the largest file of the first one found). None if none."""
    exts = SYSTEMS[system][3]
    found = _candidates(folder, system, depth)
    for e in exts:
        cand = [p for p in found if _ext_of(os.path.basename(p)) == e and _size(p) >= 0]
        if cand:
            return max(cand, key=lambda p: (_size(p), p))
    return None


def folder_games(folder, system):
    """[(name, main file)] of a folder under a system: one game (a sheet in it, a single game file, or a
    system whose games are folders), or each game file on its own (a folder of several games)."""
    name = os.path.basename(folder.rstrip(os.sep))
    try:
        has_sheet = any(os.path.splitext(n)[1].lower() in SHEETS for n in os.listdir(folder))
    except OSError:
        return []
    found = _candidates(folder, system)
    if system in FOLDER_GAMES or has_sheet or len(found) <= 1:
        m = main_file(folder, system)
        return [(name, m)] if m else []
    return [(os.path.splitext(os.path.basename(p))[0], p) for p in sorted(found)]


_TAGS = re.compile(r"\s*(\[[^\]]*\]|\((?:USA|Europe|Japan|World|En|Es|Fr|De|It|NTSC|PAL|Rev|v\d)[^)]*\))", re.I)


def clean_title(name):
    """«God of War (USA) (En,Fr) [!]» -> «God of War»: region and dump tags off; «Disc 1» kept."""
    t = _TAGS.sub("", name or "").strip()
    return re.sub(r"\s{2,}", " ", t) or name


def games_in(d, system):
    """[{"name", "path"}] of one system's folder: loose files, sheets with their parts, and games in
    their own folder. A sheet's parts are never games of their own; a sheet the emulator does not open
    (a PS2 .cue) gives its first part as the game."""
    exts = SYSTEMS[system][3]
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return []
    parts, out = set(), []
    for n in names:
        if n.startswith(".") or os.path.splitext(n)[1].lower() not in SHEETS:
            continue
        sheet = os.path.join(d, n)
        refs = sheet_files(sheet)
        parts.update(refs)
        main = sheet if _ext_of(n) in exts else next((r for r in refs if _ext_of(os.path.basename(r)) in exts), None)
        if main:
            out.append({"name": clean_title(os.path.splitext(n)[0]), "path": main})
    for n in names:
        p = os.path.join(d, n)
        if n.startswith(".") or n.endswith(PART_SUFFIX) or n == "LEEME.txt" or os.path.splitext(n)[1].lower() in SHEETS:
            continue
        if os.path.isdir(p):
            out += [{"name": clean_title(nm), "path": m} for nm, m in folder_games(p, system)]
        elif _ext_of(n) in exts and os.path.realpath(p) not in parts and os.path.isfile(p):
            out.append({"name": clean_title(os.path.splitext(n)[0]), "path": p})
        if len(out) >= MAX_PER_SYSTEM:
            break
    return sorted(out, key=lambda g: g["name"].lower())


def launch_args(system, emulator):
    """The arguments before the game file for this system with this emulator."""
    if emulator != SYSTEMS[system][2]:
        return dict(ALTERNATES.get(system, [])).get(emulator, SYSTEMS[system][4])
    return SYSTEMS[system][4]


def base_dir():
    return os.path.join(os.path.expanduser("~"), "Emulation")


def folders(base=None):
    """Create ~/Emulation/roms/<system> and ~/Emulation/bios with a short README. Returns the base."""
    base = base or base_dir()
    for folder, name, emu, exts, _ in SYSTEMS.values():
        d = os.path.join(base, "roms", folder)
        os.makedirs(d, exist_ok=True)
        readme = os.path.join(d, "LEEME.txt")
        if not os.path.exists(readme):
            with open(readme, "w") as f:
                others = "".join(f" o {emulators.CATALOG[alt][1]}" for alt, _a in ALTERNATES.get(folder, []))
                f.write(f"Juegos de {name} ({', '.join(exts)}). Se abren con {emulators.CATALOG[emu][1]}{others}.\n"
                        + (NOTES[folder] + "\n" if folder in NOTES else "")
                        + "Después: STONE Home → Ajustes → Emuladores → Añadir juegos a la biblioteca.\n")
    os.makedirs(os.path.join(base, "bios"), exist_ok=True)
    return base


def scan(base=None, installed=None):
    """{"systems": [{key, name, emulator, installed, games: [{name, path}]}]} for every system folder."""
    base = base or base_dir()
    installed = installed if installed is not None else {c["key"] for c in emulators.catalog() if c["installed"]}
    out = []
    for key, (folder, name, emu, _exts, _) in SYSTEMS.items():
        if emu not in installed:                     # the other emulator for this system, if it is the one installed
            emu = next((alt for alt, _args in ALTERNATES.get(key, []) if alt in installed), emu)
        games = games_in(os.path.join(base, "roms", folder), key)
        out.append({"key": key, "name": name, "emulator": emulators.CATALOG[emu][1], "emulator_key": emu,
                    "installed": emu in installed, "games": games})
    return {"base": base, "systems": out}


def _dq(s):
    """A double-quoted argument as Steam ROM Manager writes them in launch options."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`") + '"'


def existing(root=None):
    """(Exe, LaunchOptions) of every non-Steam shortcut already in Steam (read only)."""
    have = set()
    for acct in shortcuts.accounts(root or shortcuts.steam_root()):
        try:
            with open(os.path.join(acct, "config", "shortcuts.vdf"), "rb") as f:
                items = (vdf.binary_loads(f.read()).get("shortcuts") or {}).values()
        except (OSError, vdf.VDFError, AttributeError):
            continue
        have |= {(str(vdf.get_ci(v, "Exe") or ""), str(vdf.get_ci(v, "LaunchOptions") or "")) for v in items if isinstance(v, dict)}
    return have


def entries(scanned):
    """Steam shortcut entries for the games whose emulator is installed."""
    out = []
    for s in scanned["systems"]:
        if not s["installed"] or not s["games"]:
            continue
        fid = emulators.CATALOG[s["emulator_key"]][0]
        args = launch_args(s["key"], s["emulator_key"])
        for g in s["games"]:
            opts = " ".join(["run", fid, *args, _dq(g["path"])])
            out.append({"name": f"{g['name']} ({s['name']})", "exe": f'"{emulators.FLATPAK}"', "start": '"/"', "options": opts})
    return out


def game_files(path, base=None):
    """What uninstalling an emulator game deletes (rc12): its own folder when it has one under
    roms/<system>/, else the file with the sheets that name it and their parts. Only paths inside
    ~/Emulation/roms; [] for anything else."""
    base = os.path.realpath(os.path.join(base or base_dir(), "roms"))
    p = os.path.realpath(path)
    if not p.startswith(base + os.sep):
        return []
    rel = os.path.relpath(p, base).split(os.sep)
    if len(rel) < 2 or rel[0] not in {v[0] for v in SYSTEMS.values()}:
        return []
    sysdir = os.path.join(base, rel[0])
    if len(rel) > 2:                                   # roms/<system>/<game folder>/...
        return [os.path.join(sysdir, rel[1])]
    out = [p]
    try:
        names = os.listdir(sysdir)
    except OSError:
        names = []
    for n in names:                                    # sheets naming it, and their other parts
        if os.path.splitext(n)[1].lower() in SHEETS:
            sheet = os.path.join(sysdir, n)
            refs = sheet_files(sheet)
            if p == sheet or p in refs:
                out += [sheet] + refs
    return sorted(set(out))


def remove_game(path, base=None):
    """Delete an emulator game's files (game_files). {"ok", "removed", "bytes"}."""
    import shutil as _sh
    files = game_files(path, base)
    if not files:
        return {"ok": False, "error": "No es un juego de la carpeta de emuladores de STONE"}
    n = size = 0
    for f in files:
        try:
            if os.path.isdir(f):
                for d, _ds, fs in os.walk(f):
                    size += sum(os.path.getsize(os.path.join(d, x)) for x in fs if os.path.isfile(os.path.join(d, x)))
                _sh.rmtree(f)
            else:
                size += os.path.getsize(f)
                os.remove(f)
            n += 1
        except OSError:
            pass
    return {"ok": n > 0, "removed": n, "bytes": size}


def signature(base=None):
    """What changes when games are added or removed in ~/Emulation/roms (cheap: the folders' times and
    names, no reading of files). Compared by the host to add new games by themselves (rc12)."""
    base = base or base_dir()
    out = []
    for folder, *_rest in SYSTEMS.values():
        d = os.path.join(base, "roms", folder)
        try:
            st = os.stat(d)
            names = sorted(n for n in os.listdir(d) if not n.endswith(PART_SUFFIX))
        except OSError:
            continue
        out.append((folder, int(st.st_mtime), len(names), hash(tuple(names))))
    return tuple(out)


def waiting(base=None, installed=None):
    """{system name: emulator name} of the systems with games whose emulator is not installed."""
    out = {}
    for s in scan(base, installed)["systems"]:
        if s["games"] and not s["installed"]:
            out[s["name"]] = s["emulator"]
    return out


def add_to_library(base=None, steam_ui=None, installed=None, root=None):
    """Add every found game not yet in Steam: now through Steam's interface when it runs (and the
    fields are safe to pass to it), else queued for the next STONE session start.
    Returns {"found", "new", "added", "queued"}."""
    es = entries(scan(base, installed))
    have = existing(root)
    new = [e for e in es if (e["exe"], e["options"]) not in have]
    if steam_ui is None:
        from . import steamcef as steam_ui
    added, queued = 0, []
    for e in new:
        try:
            ok = steam_ui.add_shortcut(e["name"], e["exe"].strip('"'), e["start"].strip('"'), e["options"]) is not None
        except ValueError:                       # quotes in the path: written by file at session start
            ok = False
        if ok:
            added += 1
        else:
            queued.append(e)
    if queued:
        emulators.queue_entries(queued)
    return {"found": len(es), "new": len(new), "added": added, "queued": len(queued)}
