"""STONE EMULATION (stone_home/roms.py) and the STONE session's Steam preparation
(shortcuts.prepare_session): folders, scan, launch options, library add, waiting shortcuts.
Pure Python on temporary folders; nothing touches a real Steam.

    python3 tests/test_roms.py     (or: pytest tests/test_roms.py)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import emulators as EM  # noqa: E402
from stone_home import roms as R  # noqa: E402
from stone_home import shortcuts as SC  # noqa: E402
from stone_home import vdf  # noqa: E402


class Box:
    def __enter__(self):
        self.t = tempfile.mkdtemp(prefix="stone-roms-")
        self.old = {k: os.environ.get(k) for k in ("HOME", "XDG_STATE_HOME", "STONE_STEAM_ROOT")}
        os.environ["HOME"] = os.path.join(self.t, "home")
        os.environ["XDG_STATE_HOME"] = os.path.join(self.t, "state")
        self.steam = os.path.join(self.t, "Steam")
        os.environ["STONE_STEAM_ROOT"] = self.steam
        os.makedirs(os.environ["HOME"])
        return self

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.t, ignore_errors=True)


class FakeUI:
    def __init__(self, ok=True):
        self.ok, self.calls = ok, []

    def add_shortcut(self, name, exe, start, opts):
        if '"' in opts:
            raise ValueError("unsafe shortcut field")       # as steamcef does
        self.calls.append((name, exe, opts))
        return 2000000000 + len(self.calls) if self.ok else None


def test_folders_scan_and_launch_options():
    with Box():
        base = R.folders()
        assert os.path.exists(os.path.join(base, "roms", "ps2", "LEEME.txt")) and os.path.isdir(os.path.join(base, "bios"))
        for rel in ("ps2/Juego Uno.iso", "ps2/notas.txt", "gc/Otro$.rvz", "nds/.oculto.nds"):
            with open(os.path.join(base, "roms", rel), "w") as f:
                f.write("x")
        s = R.scan(installed={"pcsx2"})
        ps2 = next(x for x in s["systems"] if x["key"] == "ps2")
        gc = next(x for x in s["systems"] if x["key"] == "gc")
        assert [g["name"] for g in ps2["games"]] == ["Juego Uno"] and ps2["installed"] and not gc["installed"]
        assert [g["name"] for g in next(x for x in s["systems"] if x["key"] == "nds")["games"]] == []
        es = R.entries(s)
        assert len(es) == 1                                   # GameCube's emulator is not installed
        e = es[0]
        assert e["name"] == "Juego Uno (PlayStation 2)" and e["exe"] == '"/usr/bin/flatpak"'
        assert e["options"] == 'run net.pcsx2.PCSX2 -batch -fullscreen -- "' + os.path.join(base, "roms", "ps2", "Juego Uno.iso") + '"'
        assert R._dq('a"b$c`d\\e') == '"a\\"b\\$c\\`d\\\\e"'


def test_switch_games_open_with_eden_or_with_ryujinx_when_it_is_the_one_installed():
    with Box():
        base = R.folders()
        leeme = open(os.path.join(base, "roms", "switch", "LEEME.txt")).read()
        assert "Eden o Ryujinx (Ryubing)" in leeme and "prod.keys" in leeme and ".nsp" in leeme
        with open(os.path.join(base, "roms", "switch", "Aventura.nsp"), "w") as f:
            f.write("x")
        game = os.path.join(base, "roms", "switch", "Aventura.nsp")
        sw = next(x for x in R.scan(installed=set())["systems"] if x["key"] == "switch")
        assert sw["installed"] is False and sw["emulator"] == "Eden" and [g["name"] for g in sw["games"]] == ["Aventura"]
        e = R.entries(R.scan(installed={"eden", "ryujinx"}))
        assert [x["options"] for x in e] == [f'run dev.eden_emu.eden -f -g "{game}"'] and e[0]["name"] == "Aventura (Nintendo Switch)"
        s = R.scan(installed={"ryujinx"})
        sw = next(x for x in s["systems"] if x["key"] == "switch")
        assert sw["installed"] is True and sw["emulator"] == "Ryujinx (Ryubing)" and sw["emulator_key"] == "ryujinx"
        assert [x["options"] for x in R.entries(s)] == [f'run io.github.ryubing.Ryujinx --fullscreen "{game}"']
        assert R.launch_args("ps2", "pcsx2") == ["-batch", "-fullscreen", "--"] and R.launch_args("switch", "eden") == ["-f", "-g"]
    assert all(k in EM.CATALOG for _f, _n, k, _e, _a in R.SYSTEMS.values())
    assert all(alt in EM.CATALOG for alts in R.ALTERNATES.values() for alt, _a in alts)


class Flatpak:
    """`flatpak` as emulators.py calls it: list, remote-ls --updates, update."""

    def __init__(self, user=None, system=None, newer=(), online=True):
        self.user, self.system, self.newer, self.online, self.calls = dict(user or {}), dict(system or {}), set(newer), online, []

    def __call__(self, args, timeout):
        self.calls.append(args)

        class Res:
            stdout, stderr, returncode = "", "", 0
        r = Res()
        scope = self.user if "--user" in args else self.system
        if args[1] == "list":
            cols = [a for a in args if a.startswith("--columns=")][0]
            r.stdout = "\n".join(f"{i}\t{v}" if "version" in cols else i for i, v in sorted(scope.items()))
        elif args[1] == "remote-ls":
            if not self.online:
                r.returncode, r.stderr = 1, "error: Unable to load summary from remote flathub: Could not resolve host"
            else:
                r.stdout = "\n".join(sorted(i for i in scope if i in self.newer))
        elif args[1] == "update":
            fid = args[-1]
            if not self.online:
                r.returncode, r.stderr = 1, "error: While pulling: Could not resolve host: dl.flathub.org"
            elif "--user" in args and fid not in self.user:
                r.returncode, r.stderr = 1, f"error: {fid} not installed"
            elif fid in self.newer:
                target = self.user if fid in self.user else self.system
                target[fid] = target[fid] + ".1"
                self.newer.discard(fid)
        return r


def test_catalog_has_switch_says_switch_2_plainly_and_shows_versions():
    fp = Flatpak(user={"dev.eden_emu.eden": "0.2.1"}, system={"net.pcsx2.PCSX2": "2.4.0"})
    rows = {r["key"]: r for r in EM.catalog(run=fp)}
    assert rows["eden"] == {"key": "eden", "name": "Eden", "plays": "Nintendo Switch", "installed": True, "version": "0.2.1"}
    assert rows["ryujinx"]["installed"] is False and rows["ryujinx"]["plays"] == "Nintendo Switch"
    assert rows["pcsx2"]["installed"] is True and rows["pcsx2"]["version"] == "2.4.0"
    sw2 = rows["switch2"]
    assert sw2["installed"] is False and sw2["name"] == "Nintendo Switch 2" and "experimentales" in sw2["not_yet"]
    assert "switch2" not in EM.CATALOG                 # nothing to install: no Flathub id is invented for it
    events = []
    assert not EM.install("switch2", lambda st, t: events.append(st), run=fp) and events == ["error"]
    assert not any(a[1] == "install" for a in fp.calls)


def test_updates_are_asked_of_flathub_and_each_emulator_updates_by_itself():
    fp = Flatpak(user={"dev.eden_emu.eden": "0.2.1", "org.DolphinEmu.dolphin-emu": "2509", "org.example.Other": "1"},
                 system={"net.pcsx2.PCSX2": "2.4.0"}, newer={"dev.eden_emu.eden", "net.pcsx2.PCSX2", "org.example.Other"})
    assert EM.updates(run=fp) == {"keys": ["eden", "pcsx2"], "checked": True}        # only catalog emulators, both scopes
    assert ["/usr/bin/flatpak", "remote-ls", "--user", "--updates", "--app", "--columns=application"] in fp.calls
    seen = []
    assert EM.update("eden", lambda st, t: seen.append((st, t)), run=fp)
    assert ["/usr/bin/flatpak", "update", "--user", "-y", "--noninteractive", "dev.eden_emu.eden"] in fp.calls
    assert seen == [("updating", "Actualizando Eden desde Flathub…"), ("done", "Eden actualizado a la versión 0.2.1.1")]
    del seen[:]
    assert EM.update("dolphin", lambda st, t: seen.append((st, t)), run=fp) and seen[-1] == ("done", "Dolphin ya está al día (versión 2509)")
    del seen[:]
    assert EM.update("pcsx2", lambda st, t: seen.append((st, t)), run=fp)             # installed for the whole system
    assert ["/usr/bin/flatpak", "update", "-y", "--noninteractive", "net.pcsx2.PCSX2"] in fp.calls and seen[-1][0] == "done"
    assert EM.updates(run=fp) == {"keys": [], "checked": True}
    del seen[:]
    assert not EM.update("xemu", lambda st, t: seen.append((st, t)), run=fp) and seen == [("error", "xemu no está instalado")]
    assert not EM.update("switch2", lambda st, t: seen.append(st), run=fp) and not EM.update("; rm -rf /", lambda st, t: None, run=fp)
    off = Flatpak(user={"dev.eden_emu.eden": "0.2.1"}, online=False)
    assert "No se pudo consultar Flathub" in EM.updates(run=off)["error"]
    del seen[:]
    assert not EM.update("eden", lambda st, t: seen.append((st, t)), run=off)
    assert seen[-1][0] == "error" and "Could not resolve host" in seen[-1][1]
    assert EM.updates(run=Flatpak()) == {"keys": [], "checked": True}                 # nothing installed: Flathub is not asked


def test_add_to_library_live_queued_and_never_twice():
    with Box() as b:
        base = R.folders()
        with open(os.path.join(base, "roms", "psp", "Viaje.iso"), "w") as f:
            f.write("x")
        acct = os.path.join(b.steam, "userdata", "12345678")
        os.makedirs(os.path.join(acct, "config"))
        ui = FakeUI()
        r = R.add_to_library(steam_ui=ui, installed={"ppsspp"})
        assert r == {"found": 1, "new": 1, "added": 0, "queued": 1}      # quoted path: through the file
        # the session start writes it (Steam closed), then it is never added again
        out = SC.prepare_session(proc=os.path.join(b.t, "noproc"))
        assert out["shortcuts_added"] == ["Viaje (PlayStation Portable)"], out
        assert R.add_to_library(steam_ui=ui, installed={"ppsspp"})["new"] == 0
        data = vdf.binary_loads(open(os.path.join(acct, "config", "shortcuts.vdf"), "rb").read())
        assert [v["AppName"] for v in data["shortcuts"].values()] == ["Viaje (PlayStation Portable)"]


def test_prepare_session_flags_steam_and_waits_for_the_first_sign_in():
    with Box() as b:
        EM.queue_entries([{"name": "X", "exe": '"/usr/bin/flatpak"', "start": '"/"', "options": "run a.b"}])
        out = SC.prepare_session(proc=os.path.join(b.t, "noproc"))
        assert out["steam_ui_launch"] is True and out["shortcuts"] == "waiting for the first Steam sign-in"   # folder created for Steam
        os.makedirs(os.path.join(b.steam, "userdata", "1", "config"))
        out = SC.prepare_session(proc=os.path.join(b.t, "noproc"))
        assert out["steam_ui_launch"] is True and out["shortcuts_added"] == ["X"]
        assert os.path.exists(os.path.join(b.steam, ".cef-enable-remote-debugging"))
        proc = os.path.join(b.t, "proc", "77")
        os.makedirs(proc)
        open(os.path.join(proc, "comm"), "w").write("steam\n")
        assert SC.prepare_session(proc=os.path.join(b.t, "proc"))["result"] == "skipped"


if __name__ == "__main__":
    sys.exit(run_module(globals()))
