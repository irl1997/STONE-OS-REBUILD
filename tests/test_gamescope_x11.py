"""stone_home/gamescope_x11.py: which game is running, the base-layer list, and the X11 properties.

The /proc and list cases run anywhere. The X11 case starts a private Xvfb and checks the
properties really land on the window and the root (needs Xvfb and python-xlib: dev container, CI).
Gamescope itself is not involved: how it reacts is a board test (T-SESS-02, T-SESS-04).

    python3 tests/test_gamescope_x11.py     (or: pytest tests/test_gamescope_x11.py)
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import gamescope_x11 as GX  # noqa: E402


def _proc(entries):
    root = tempfile.mkdtemp(prefix="stone-proc-")
    for pid, argv in entries.items():
        os.makedirs(os.path.join(root, str(pid)))
        with open(os.path.join(root, str(pid), "cmdline"), "wb") as f:
            f.write(b"\x00".join(a.encode() for a in argv) + b"\x00")
    os.makedirs(os.path.join(root, "self"))
    return root


def test_running_game_is_the_newest_steam_launch_and_never_stone_home():
    root = _proc({
        100: ["/usr/bin/bash"],
        200: ["/home/u/.local/share/Steam/ubuntu12_32/reaper", "SteamLaunch", "AppId=1091500", "--", "game.exe"],
        300: ["/home/u/.local/share/Steam/ubuntu12_32/reaper", "SteamLaunch", "AppId=730", "--", "cs2"],
        400: ["reaper", "SteamLaunch", "AppId=3456789012", "--", "/usr/bin/stone-home"],
    })
    try:
        assert GX.running_game(root) == 730
    finally:
        shutil.rmtree(root)


def test_no_game_and_unreadable_proc():
    root = _proc({100: ["/usr/bin/steam", "-silent"]})
    try:
        assert GX.running_game(root) is None
    finally:
        shutil.rmtree(root)
    assert GX.running_game("/nonexistent-proc") is None


def test_baselayer_lists_match_what_steam_writes():
    assert GX.baselayer_for(None) == [413091, 769]
    assert GX.baselayer_for(1091500) == [413091, 1091500, 769]


def test_properties_land_on_the_home_window_and_the_root():
    need(shutil.which("Xvfb") is not None, "Xvfb not installed (dev container, CI)")
    try:
        from Xlib import X, display as xdisplay
    except ImportError:
        need(False, "python-xlib not installed (dev container, CI)")
    disp = ":97"
    xvfb = subprocess.Popen(["Xvfb", disp, "-nolisten", "tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        end = time.time() + 10
        d = None
        while time.time() < end:
            try:
                d = xdisplay.Display(disp)
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        assert d is not None, "Xvfb did not start"
        root = d.screen().root
        win = root.create_window(0, 0, 100, 100, 0, d.screen().root_depth, X.InputOutput, X.CopyFromParent)
        win.set_wm_class("stone", "STONE")
        other = root.create_window(0, 0, 10, 10, 0, d.screen().root_depth, X.InputOutput, X.CopyFromParent)
        other.set_wm_class("steam", "Steam")
        d.flush()

        f = GX.Focus(disp)
        found = f.find_home()
        assert [w.id for w in found] == [win.id], found
        f.mark_home(found[0])
        assert f.get(win, "STEAM_GAME") == [769] and f.get(win, "STEAM_INPUT_FOCUS") == [1]
        assert f.get(other, "STEAM_GAME") is None
        f.front(1091500)
        assert f.get(f.root, "GAMESCOPECTRL_BASELAYER_APPID") == [413091, 1091500, 769]
        assert f.get(f.root, "GAMESCOPECTRL_BASELAYER_WINDOW") == [0]
        f.front(None)
        assert f.get(f.root, "GAMESCOPECTRL_BASELAYER_APPID") == [413091, 769]
        assert f.home_front() is False
        f.set_home_front(True)
        assert f.home_front() is True and GX.Focus(disp).home_front() is True     # another client sees it
        f.set_home_front(False)
        assert f.home_front() is False
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
