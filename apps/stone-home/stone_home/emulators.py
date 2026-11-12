"""Emulators for other consoles, installed from Flathub and added to Steam as shortcuts.

A fixed catalog (Flathub ids checked against Flathub's Emulator category, 25-10-2026). Nothing
else can be installed from STONE Home: the page sends a catalog key, never a package name.

  install    `flatpak install --user flathub <id>` (no root, no password; the user's own
             Flatpak installation), then the emulator is added to Steam as a non-Steam
             shortcut so it appears in STONE's library and launches like a game:
             while Steam runs, through Steam's interface (steamcef.add_shortcut); otherwise
             it is queued and written by `stone-home-session register` before Steam starts.
  installed  which catalog entries are installed (user or system Flatpak), and their version.
  updates    which installed ones have a newer version on Flathub (`flatpak remote-ls --updates`).
  update     `flatpak update --user <id>` for one emulator, or for every installed one.

Games (ROMs), BIOS files, console keys and firmware are the person's own; STONE does not download
them. A console without a usable emulator on Flathub is listed in NOT_YET and said plainly in
STONE Home (D-18): nothing is installed for it and nothing is promised.
"""

import json
import os
import subprocess

from . import shortcuts as SC

FLATPAK = "/usr/bin/flatpak"
FLATHUB_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"

# key -> (Flathub id, name shown, what it plays)
CATALOG = {
    "retrodeck": ("net.retrodeck.retrodeck", "RetroDECK", "Todo en uno: la mayoría de consolas clásicas en una sola app, pensada para mando"),
    "retroarch": ("org.libretro.RetroArch", "RetroArch", "Consolas clásicas con núcleos de libretro"),
    "dolphin": ("org.DolphinEmu.dolphin-emu", "Dolphin", "GameCube y Wii"),
    "pcsx2": ("net.pcsx2.PCSX2", "PCSX2", "PlayStation 2"),
    "ppsspp": ("org.ppsspp.PPSSPP", "PPSSPP", "PlayStation Portable"),
    "rpcs3": ("net.rpcs3.RPCS3", "RPCS3", "PlayStation 3"),
    "cemu": ("info.cemu.Cemu", "Cemu", "Wii U"),
    "azahar": ("org.azahar_emu.Azahar", "Azahar", "Nintendo 3DS"),
    "melonds": ("net.kuribo64.melonDS", "melonDS", "Nintendo DS"),
    "mgba": ("io.mgba.mGBA", "mGBA", "Game Boy Advance"),
    "flycast": ("org.flycast.Flycast", "Flycast", "Dreamcast"),
    "xemu": ("app.xemu.xemu", "xemu", "Xbox original"),
    # Nintendo Switch (Flathub ids and versions checked on 2026-11-11: Eden 0.2.1, Ryujinx 1.3.3).
    # Both need the person's own console keys (prod.keys) and firmware, set up in the emulator.
    "eden": ("dev.eden_emu.eden", "Eden", "Nintendo Switch"),
    "ryujinx": ("io.github.ryubing.Ryujinx", "Ryujinx (Ryubing)", "Nintendo Switch"),
}

# key -> (console, why there is no emulator to install). Checked on 2026-11-11: no Switch 2 emulator
# is published on Flathub; the projects that exist are early experiments (builds for Windows only,
# or sources that start very few games).
NOT_YET = {
    "switch2": ("Nintendo Switch 2",
                "Todavía no hay un emulador de Switch 2 que se pueda instalar en esta consola. Los proyectos que existen "
                "son experimentales: no están publicados en Flathub y arrancan muy pocos juegos. Cuando haya uno publicado, "
                "llegará a esta lista con una actualización de STONE OS."),
}

PENDING = "pending-shortcuts.json"


def _run(args, timeout):
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)


def installed_ids(run=_run):
    out = set()
    for scope in ("--user", "--system"):
        try:
            r = run([FLATPAK, "list", scope, "--app", "--columns=application"], 30)
        except (OSError, subprocess.SubprocessError):
            continue
        out.update(x.strip() for x in r.stdout.splitlines() if x.strip())
    return out


def installed_versions(run=_run):
    """{Flathub id: version text} of the installed apps (user and system Flatpak)."""
    out = {}
    for scope in ("--user", "--system"):
        try:
            r = run([FLATPAK, "list", scope, "--app", "--columns=application,version"], 30)
        except (OSError, subprocess.SubprocessError):
            continue
        for line in r.stdout.splitlines():
            parts = line.split("\t") if "\t" in line else line.split(None, 1)
            if parts and parts[0].strip():
                out.setdefault(parts[0].strip(), parts[1].strip()[:40] if len(parts) > 1 else "")
    return out


def catalog(run=_run):
    vers = installed_versions(run)
    ids = set(vers) or installed_ids(run)
    rows = [{"key": k, "name": n, "plays": p, "installed": fid in ids, "version": vers.get(fid) or None}
            for k, (fid, n, p) in CATALOG.items()]
    return rows + [{"key": k, "name": n, "plays": n, "installed": False, "version": None, "not_yet": why}
                   for k, (n, why) in NOT_YET.items()]


def updates(run=_run):
    """{"keys": [catalog keys with a newer version on Flathub], "checked": True} or {"error": ...}.
    Asks Flathub (needs internet); only installed emulators are looked at."""
    ids = installed_ids(run)
    mine = {fid: k for k, (fid, _n, _p) in CATALOG.items() if fid in ids}
    if not mine:
        return {"keys": [], "checked": True}
    found, answered, last = set(), False, "sin detalle"
    for scope in ("--user", "--system"):
        try:
            r = run([FLATPAK, "remote-ls", scope, "--updates", "--app", "--columns=application"], 120)
        except (OSError, subprocess.SubprocessError) as e:
            last = str(e)
            continue
        if r.returncode == 0:
            answered = True
            found.update(x.strip() for x in r.stdout.splitlines() if x.strip())
        else:
            last = ((r.stderr or r.stdout).strip().splitlines()[-1:] or [last])[0][:160]
    if not answered:
        return {"error": f"No se pudo consultar Flathub: {last}"}
    return {"keys": sorted(k for fid, k in mine.items() if fid in found), "checked": True}


def update(key, progress, run=_run):
    """Update one installed emulator from Flathub. progress(state, text): updating|done|error.
    Returns True when it is up to date afterwards."""
    if key not in CATALOG:
        progress("error", "Emulador desconocido")
        return False
    fid, name, _ = CATALOG[key]
    before = installed_versions(run)
    if fid not in before:
        progress("error", f"{name} no está instalado")
        return False
    progress("updating", f"Actualizando {name} desde Flathub…")
    try:
        r = run([FLATPAK, "update", "--user", "-y", "--noninteractive", fid], 3600)
        if r.returncode != 0:           # installed for the whole system (not by STONE): no scope given
            r = run([FLATPAK, "update", "-y", "--noninteractive", fid], 3600)
    except (OSError, subprocess.SubprocessError) as e:
        progress("error", f"No se pudo actualizar {name}: {e}")
        return False
    if r.returncode != 0:
        last = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["sin detalle"]
        progress("error", f"No se pudo actualizar {name}: {last[0][:160]}")
        return False
    after = installed_versions(run).get(fid) or ""
    if after and after != (before.get(fid) or ""):
        progress("done", f"{name} actualizado a la versión {after}")
    else:
        progress("done", f"{name} ya está al día" + (f" (versión {after})" if after else ""))
    return True


def _shortcut_fields(key):
    fid, name, _ = CATALOG[key]
    return name, FLATPAK, "/", f"run {fid}"


def queue_shortcut(key):
    """Remember a shortcut to add the next time Steam is closed (register, before Steam starts)."""
    path = os.path.join(SC.state_dir(), PENDING)
    try:
        with open(path) as f:
            keys = [k for k in json.load(f) if k in CATALOG]
    except (OSError, ValueError, TypeError):
        keys = []
    if key not in keys:
        keys.append(key)
    os.makedirs(SC.state_dir(), exist_ok=True)
    SC._write_atomic(path, (json.dumps(keys) + "\n").encode())


def take_pending():
    path = os.path.join(SC.state_dir(), PENDING)
    try:
        with open(path) as f:
            keys = [k for k in json.load(f) if k in CATALOG]
    except (OSError, ValueError, TypeError):
        return []
    try:
        os.remove(path)
    except OSError:
        pass
    return keys


PENDING_ENTRIES = "pending-entries.json"


def queue_entries(entries):
    """Shortcuts other than catalog emulators (games of emulators, roms.py) to add when Steam is
    closed: [{name, exe, start, options}] with exe/start already quoted as Steam writes them."""
    path = os.path.join(SC.state_dir(), PENDING_ENTRIES)
    try:
        with open(path) as f:
            have = [e for e in json.load(f) if isinstance(e, dict)]
    except (OSError, ValueError, TypeError):
        have = []
    keys = {(e.get("exe"), e.get("options")) for e in have}
    have += [e for e in entries if (e["exe"], e["options"]) not in keys]
    os.makedirs(SC.state_dir(), exist_ok=True)
    SC._write_atomic(path, (json.dumps(have) + "\n").encode())


def pending_entries():
    """Shortcut entries for register() / prepare_session(): written into shortcuts.vdf while Steam is
    closed. Taken from the queue: requeue_entries() puts them back if they could not be written."""
    out = []
    for key in take_pending():
        name, exe, start, opts = _shortcut_fields(key)
        out.append({"name": name, "exe": f'"{exe}"', "start": f'"{start}"', "options": opts})
    path = os.path.join(SC.state_dir(), PENDING_ENTRIES)
    try:
        with open(path) as f:
            out += [e for e in json.load(f) if isinstance(e, dict) and {"name", "exe", "start", "options"} <= set(e)]
        os.remove(path)
    except (OSError, ValueError, TypeError):
        pass
    return out


def requeue_entries(entries):
    if entries:
        queue_entries(entries)


def install(key, progress, run=_run, steam_ui=None):
    """Install one catalog entry and add it to Steam. progress(state, text) is called from this
    thread with state in installing|done|error. Returns True on success."""
    if key not in CATALOG:
        progress("error", "Emulador desconocido")
        return False
    fid, name, _ = CATALOG[key]
    progress("installing", f"Descargando {name} desde Flathub…")
    try:
        run([FLATPAK, "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB_REPO], 120)
        r = run([FLATPAK, "install", "--user", "-y", "--noninteractive", "flathub", fid], 3600)
    except (OSError, subprocess.SubprocessError) as e:
        progress("error", f"No se pudo instalar {name}: {e}")
        return False
    if r.returncode != 0 and fid not in installed_ids(run):
        last = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["sin detalle"]
        progress("error", f"No se pudo instalar {name}: {last[0][:160]}")
        return False
    if steam_ui is None:
        from . import steamcef as steam_ui
    if steam_ui.add_shortcut(*_shortcut_fields(key)) is not None:
        progress("done", f"{name} instalado. Ya está en tu biblioteca")
    else:
        queue_shortcut(key)
        progress("done", f"{name} instalado. Aparece en tu biblioteca al reiniciar la consola")
    return True
