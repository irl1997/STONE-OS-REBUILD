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
        assert out["steam_ui_launch"] is False and out["shortcuts"] == "waiting for the first Steam sign-in"
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
