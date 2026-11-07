"""STONE session (M24, D-21): supervisor, recovery path, automatic-session switch and session file.

Steam, STONE Home and the fallback are stand-in shell commands; nothing starts a real Steam,
Gamescope or SDDM. Pure Python and sh: runs on any machine.

    python3 tests/test_session.py     (or: pytest tests/test_session.py)
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

HOME_LIB = os.path.join(REPO, "apps", "stone-home")      # run as a package, like /usr/bin/stone-session
SESSION_FILE = os.path.join(REPO, "system", "usr", "share", "gamescope-session-plus", "sessions.d", "stone")
DESKTOP = os.path.join(REPO, "system", "usr", "share", "wayland-sessions", "gamescope-session-stone.desktop")


class Box:
    def __init__(self, steam, home, fallback="true"):
        self.tmp = tempfile.mkdtemp(prefix="stone-session-")
        self.state = os.path.join(self.tmp, "state")
        self.env = dict(os.environ, XDG_STATE_HOME=self.state, STONE_SESSION_STEAM=steam,
                        STONE_SESSION_HOME=home, STONE_SESSION_FALLBACK=fallback,
                        STONE_SESSION_SDDM_DIR=os.path.join(self.tmp, "sddm.conf.d"), PYTHONPATH=HOME_LIB)
        self.env.pop("DISPLAY", None)        # no X server here: focus management stays off (logged)

    def path(self, *p):
        return os.path.join(self.tmp, *p)

    def run(self, *args, timeout=40):
        return subprocess.run([sys.executable, "-m", "stone_home.supervisor", *args], env=self.env, capture_output=True,
                              text=True, timeout=timeout)

    def start(self, *args):
        return subprocess.Popen([sys.executable, "-m", "stone_home.supervisor", *args], env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def session_state(self):
        with open(os.path.join(self.state, "stone", "session.json")) as f:
            return json.load(f)

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def _wait_file(path, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        if os.path.exists(path):
            return True
        time.sleep(0.1)
    return False


def test_home_that_keeps_failing_falls_back_to_game_mode_and_says_why():
    token = f"{600 + os.getpid() % 300}.{int(time.time()) % 1000}"     # unique: never matches another process
    b = Box(steam=f"sleep {token}", home="sh -c 'exit 3'", fallback="")
    marker = b.path("fallback-ran")
    b.env["STONE_SESSION_FALLBACK"] = f"sh -c 'touch {marker}'"
    try:
        r = b.run("run")
        assert r.returncode == 0, r.stderr
        assert os.path.exists(marker), "the fallback (Steam's Game Mode interface) did not run"
        fb = b.session_state()["fallback"]
        assert "STONE Home stopped 3 times" in fb["reason"] and "last exit 3" in fb["reason"], fb
        assert subprocess.run(["pgrep", "-f", f"^sleep {token}$"], capture_output=True).returncode != 0 \
            if shutil.which("pgrep") else True, "background Steam was left running"
    finally:
        b.close()


def test_steam_that_stops_is_restarted_and_home_keeps_running():
    b = Box(steam="", home="sleep 600")
    count = b.path("steam-starts")
    b.env["STONE_SESSION_STEAM"] = f"sh -c 'echo x >> {count}; exit 0'"
    p = b.start("run")
    try:
        end = time.time() + 15
        while time.time() < end:
            if os.path.exists(count) and len(open(count).read().split()) >= 2:
                break
            time.sleep(0.2)
        assert len(open(count).read().split()) >= 2, "steam was not restarted"
        assert p.poll() is None, "the session ended because Steam stopped"
        assert b.session_state()["fallback"] is None
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=20)
        b.close()


def test_session_end_stops_both_children():
    b = Box(steam="", home="")
    pids = b.path("pids")
    b.env["STONE_SESSION_STEAM"] = f"sh -c 'echo $$ >> {pids}; exec sleep 600'"
    b.env["STONE_SESSION_HOME"] = f"sh -c 'echo $$ >> {pids}; exec sleep 600'"
    p = b.start("run")
    try:
        end = time.time() + 15
        while time.time() < end and not (os.path.exists(pids) and len(open(pids).read().split()) >= 2):
            time.sleep(0.1)
        children = [int(x) for x in open(pids).read().split()]
        p.send_signal(signal.SIGTERM)
        assert p.wait(timeout=30) == 0
        for pid in children:
            try:
                os.kill(pid, 0)
                alive = True
            except ProcessLookupError:
                alive = False
            assert not alive, f"child {pid} still running after the session ended"
    finally:
        if p.poll() is None:
            p.kill()
        b.close()


def test_default_on_and_off_only_touch_their_own_dropin():
    b = Box(steam="true", home="true")
    try:
        d = b.path("sddm.conf.d")
        os.makedirs(d)
        with open(os.path.join(d, "steamos.conf"), "w") as f:
            f.write("[Autologin]\nUser=console\nSession=gamescope-session-steam.desktop\n")
        r = b.run("default", "on")
        assert r.returncode == 0, r.stdout + r.stderr
        text = open(os.path.join(d, "zz-stone-session.conf")).read()
        assert "[Autologin]\nSession=gamescope-session-stone.desktop" in text, text
        assert "User=" not in text, "the user stays Bazzite's"
        r = b.run("default", "off")
        assert r.returncode == 0 and sorted(os.listdir(d)) == ["steamos.conf"], os.listdir(d)
    finally:
        b.close()


def test_status_and_bad_arguments():
    b = Box(steam="true", home="true")
    try:
        r = b.run("status")
        assert r.returncode == 0 and "no ha arrancado" in r.stdout, r.stdout
        r = b.run("whatever")
        assert r.returncode == 2 and "uso:" in r.stdout
    finally:
        b.close()


def test_session_file_uses_the_supervisor_and_steams_features():
    tmp = tempfile.mkdtemp()
    try:
        r = subprocess.run(["bash", "-c", f". {SESSION_FILE}; echo \"$CLIENTCMD\"; declare -F short_session_recover"],
                           capture_output=True, text=True, cwd=tmp, env=dict(os.environ, HOME=tmp))
        out = r.stdout.splitlines()
        assert r.returncode == 0 and out[0] == "/usr/bin/stone-session run" and out[1] == "short_session_recover", (r.stdout, r.stderr)
    finally:
        shutil.rmtree(tmp)
    text = open(SESSION_FILE).read()
    assert ". /usr/share/gamescope-session-plus/sessions.d/steam" in text
    desk = open(DESKTOP).read()
    assert "Exec=gamescope-session-plus stone" in desk and "DesktopNames=gamescope" in desk


if __name__ == "__main__":
    sys.exit(run_module(globals()))
