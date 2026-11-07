"""D-29 "llegar y jugar": the boot guard, the next-login session helper and `stone-session switch`.

Everything runs in temporary folders with stand-in commands: nothing touches SDDM, polkit or a
real login. Pure Python and bash: runs anywhere.

    python3 tests/test_session_guard.py     (or: pytest tests/test_session_guard.py)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import guard as G  # noqa: E402

SELECT = os.path.join(REPO, "system", "usr", "libexec", "stone", "stone-session-select")
HOME_LIB = os.path.join(REPO, "apps", "stone-home")


class Box:
    def __init__(self):
        self.t = tempfile.mkdtemp(prefix="stone-guard-")
        self.sddm = self.p("sddm")
        self.state = self.p("state")
        self.home = self.p("home")
        os.makedirs(self.sddm)
        os.makedirs(os.path.join(self.home, ".local", "state", "stone"))

    def p(self, *a):
        return os.path.join(self.t, *a)

    def stone_default(self):
        with open(os.path.join(self.sddm, G.DROPIN), "w") as f:
            f.write("[Autologin]\nSession=gamescope-session-stone.desktop\n")

    def ready(self, *boots):
        with open(os.path.join(self.home, ".local", "state", "stone", "boot-metrics.jsonl"), "a") as f:
            for b in boots:
                f.write(json.dumps({"boot_id": b, "visual_s": 20.0, "ready_s": 24.0}) + "\n")

    def boot(self, bid):
        return G.run(bid, sddm_dir=self.sddm, state_dir=self.state, home=self.home, now=lambda: 1800000000, log=lambda m: None)

    def close(self):
        shutil.rmtree(self.t, ignore_errors=True)


def test_two_boots_without_home_ready_give_the_console_back_to_bazzite():
    b = Box()
    try:
        b.stone_default()
        assert b.boot("b1") == "watching"
        b.ready("b1")
        assert b.boot("b2") == "watching"           # b1 reached Home
        assert b.boot("b3") == "watching"           # b2 failed, b1 fine: one failure only
        assert b.boot("b4") == "disabled"           # b2 and b3 failed
        assert not os.path.exists(os.path.join(b.sddm, G.DROPIN))
        assert os.path.exists(os.path.join(b.state, G.DROPIN + ".disabled"))
        st = G.load_state(b.state)
        assert st["disabled"]["boots"] == ["b2", "b3"] and "operable" in st["disabled"]["reason"], st
        assert b.boot("b5") == "stone-not-default"   # Bazzite's session from now on
        assert oct(os.stat(os.path.join(b.state, G.STATE)).st_mode & 0o777) == "0o644"
    finally:
        b.close()


def test_a_healthy_console_is_never_touched_and_the_temp_session_is_cleared():
    b = Box()
    try:
        b.stone_default()
        for i in range(15):
            b.ready(f"x{i}")
            assert b.boot(f"x{i}") == "watching"
            b.ready(f"x{i}")
        assert len(G.load_state(b.state)["boots"]) == G.KEEP
        with open(os.path.join(b.sddm, G.TEMP), "w") as f:
            f.write("[Autologin]\nSession=plasma.desktop\n")
        b.boot("y")
        assert not os.path.exists(os.path.join(b.sddm, G.TEMP))
        assert os.path.exists(os.path.join(b.sddm, G.DROPIN))
    finally:
        b.close()


def test_enable_forgets_the_failures_and_damaged_files_are_tolerated():
    b = Box()
    try:
        b.stone_default()
        for bid in ("a", "b", "c"):
            b.boot(bid)
        assert G.load_state(b.state)["disabled"] is not None
        G.enable(sddm_dir=b.sddm, state_dir=b.state)
        assert G.load_state(b.state) == {"boots": [], "disabled": None}
        assert not os.path.exists(os.path.join(b.state, G.DROPIN + ".disabled"))
        with open(os.path.join(b.state, G.STATE), "w") as f:
            f.write("{broken")
        with open(os.path.join(b.home, ".local", "state", "stone", "boot-metrics.jsonl"), "w") as f:
            f.write("not json\n[1]\n")
        b.stone_default()
        assert b.boot("d") == "watching"
    finally:
        b.close()


def test_console_home_follows_sddm_autologin_user():
    b = Box()
    try:
        with open(os.path.join(b.sddm, "zz-bazzite-autologin.conf"), "w") as f:
            f.write("[Autologin]\nUser=stone\n")
        users = {"stone": types.SimpleNamespace(pw_dir="/var/home/stone")}
        assert G.console_home(b.sddm, getpw=users.__getitem__, getuid=None) == "/var/home/stone"
        os.remove(os.path.join(b.sddm, "zz-bazzite-autologin.conf"))
        assert G.console_home(b.sddm, getpw=None, getuid=lambda uid: types.SimpleNamespace(pw_dir=f"/home/u{uid}")) == "/home/u1000"
    finally:
        b.close()


def _select(b, *args):
    env = dict(os.environ, STONE_SDDM_DIR=b.sddm, STONE_SESSIONS_DIR=b.p("sessions"))
    return subprocess.run(["bash", SELECT, *args], env=env, capture_output=True, text=True)


def test_select_writes_only_the_next_login_file_and_only_known_sessions():
    b = Box()
    try:
        os.makedirs(b.p("sessions"))
        for n in ("plasma.desktop", "gamescope-session-stone.desktop"):
            open(b.p("sessions", n), "w").close()
        r = _select(b, "desktop")
        assert r.returncode == 0 and r.stdout.strip() == "plasma.desktop", r.stderr
        text = open(os.path.join(b.sddm, G.TEMP)).read()
        assert "[Autologin]\nSession=plasma.desktop\n" in text
        r = _select(b, "stone")
        assert r.returncode == 0 and "Session=gamescope-session-stone.desktop" in open(os.path.join(b.sddm, G.TEMP)).read()
        for bad in ([], ["plasma.desktop"], ["desktop; rm -rf /"], ["../x"]):
            assert _select(b, *bad).returncode == 2, bad
        os.remove(b.p("sessions", "plasma.desktop"))
        assert _select(b, "desktop").returncode == 2
        assert sorted(os.listdir(b.sddm)) == [G.TEMP]
        # SDDM reads in name order and the last file wins: the STONE files sort where they must
        names = sorted(["zz-holo-autologin.conf", G.DROPIN, "zzt-holo-temp-login.conf", G.TEMP])
        assert names == ["zz-holo-autologin.conf", G.DROPIN, "zzt-holo-temp-login.conf", G.TEMP], names
    finally:
        b.close()


def _session(b, *args, select="true", logout="true"):
    env = dict(os.environ, PYTHONPATH=HOME_LIB, XDG_STATE_HOME=b.p("xdg"), HOME=b.home,
               STONE_SESSION_SDDM_DIR=b.sddm, STONE_SESSION_GUARD_DIR=b.state,
               STONE_SESSION_SELECT=select, STONE_SESSION_LOGOUT=logout)
    return subprocess.run([sys.executable, "-m", "stone_home.supervisor", *args], env=env, capture_output=True, text=True, timeout=60)


def test_switch_asks_for_the_next_session_then_logs_out_and_leaves_a_way_back():
    b = Box()
    try:
        calls = b.p("calls")
        os.makedirs(os.path.join(b.home, "Desktop"))
        r = _session(b, "switch", "desktop", select=f"sh -c 'echo select $0 >> {calls}; echo plasma.desktop'",
                     logout=f"sh -c 'echo logout >> {calls}'")
        assert r.returncode == 0, r.stdout + r.stderr
        assert open(calls).read().split("\n")[:2] == ["select desktop", "logout"]
        # the way back is copied only where the image has the launcher; here the test checks no crash
        r = _session(b, "switch", "stone", select="sh -c 'exit 126'", logout=f"sh -c 'echo logout2 >> {calls}'")
        assert r.returncode == 1 and "No se pudo cambiar" in r.stdout and "logout2" not in open(calls).read()
        assert _session(b, "switch", "plasma").returncode == 2
    finally:
        b.close()


def test_status_says_when_the_guard_took_the_stone_session_away():
    b = Box()
    try:
        b.stone_default()
        for bid in ("a", "b", "c"):
            b.boot(bid)
        r = _session(b, "status")
        assert "Sesión automática: la de Bazzite" in r.stdout and "guardia de arranque" in r.stdout, r.stdout
        assert json.loads(_session(b, "status", "--json").stdout)["guard"]["disabled"]["boots"] == ["a", "b"]
        r = _session(b, "default", "on")
        assert r.returncode == 0, r.stdout + r.stderr
        r = _session(b, "status")
        assert "Sesión automática: STONE" in r.stdout and "guardia" not in r.stdout, r.stdout
    finally:
        b.close()


if __name__ == "__main__":
    sys.exit(run_module(globals()))
