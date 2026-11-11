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

from . import emulators, shortcuts, vdf

# system -> (folder, name, catalog key, extensions, arguments before the file)
SYSTEMS = {
    "gc": ("gc", "GameCube", "dolphin", (".iso", ".gcm", ".gcz", ".rvz", ".ciso"), ["-b", "-e"]),
    "wii": ("wii", "Wii", "dolphin", (".iso", ".wbfs", ".rvz", ".gcz", ".wad"), ["-b", "-e"]),
    "ps2": ("ps2", "PlayStation 2", "pcsx2", (".iso", ".chd", ".cso", ".bin", ".gz"), ["-batch", "-fullscreen", "--"]),
    "psp": ("psp", "PlayStation Portable", "ppsspp", (".iso", ".cso", ".pbp", ".chd"), ["--fullscreen"]),
    "ps3": ("ps3", "PlayStation 3", "rpcs3", (".pkg", ".iso"), ["--no-gui"]),
    "wiiu": ("wiiu", "Wii U", "cemu", (".wud", ".wux", ".rpx", ".wua"), ["-f", "-g"]),
    "3ds": ("3ds", "Nintendo 3DS", "azahar", (".3ds", ".cci", ".cxi", ".3dsx"), []),
    "nds": ("nds", "Nintendo DS", "melonds", (".nds",), []),
    "gba": ("gba", "Game Boy Advance", "mgba", (".gba", ".gb", ".gbc"), ["-f"]),
    "dreamcast": ("dreamcast", "Dreamcast", "flycast", (".gdi", ".cdi", ".chd"), []),
    "xbox": ("xbox", "Xbox", "xemu", (".iso", ".xiso"), ["-full-screen", "-dvd_path"]),
}
MAX_PER_SYSTEM = 300


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
                f.write(f"Juegos de {name} ({', '.join(exts)}). Se abren con {emulators.CATALOG[emu][1]}.\n"
                        "Después: STONE Home → Ajustes → Emuladores → Añadir juegos a la biblioteca.\n")
    os.makedirs(os.path.join(base, "bios"), exist_ok=True)
    return base


def scan(base=None, installed=None):
    """{"systems": [{key, name, emulator, installed, games: [{name, path}]}]} for every system folder."""
    base = base or base_dir()
    installed = installed if installed is not None else {c["key"] for c in emulators.catalog() if c["installed"]}
    out = []
    for key, (folder, name, emu, exts, _) in SYSTEMS.items():
        d = os.path.join(base, "roms", folder)
        games = []
        try:
            names = sorted(os.listdir(d))
        except OSError:
            names = []
        for n in names:
            p = os.path.join(d, n)
            if n.startswith(".") or not n.lower().endswith(exts) or not os.path.isfile(p):
                continue
            games.append({"name": os.path.splitext(n)[0], "path": p})
            if len(games) >= MAX_PER_SYSTEM:
                break
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
        args = SYSTEMS[s["key"]][4]
        for g in s["games"]:
            opts = " ".join(["run", fid, *args, _dq(g["path"])])
            out.append({"name": f"{g['name']} ({s['name']})", "exe": f'"{emulators.FLATPAK}"', "start": '"/"', "options": opts})
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
