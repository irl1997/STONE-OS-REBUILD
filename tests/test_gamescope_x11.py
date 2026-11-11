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


def test_steam_windows_are_told_from_games_and_the_one_to_show_is_chosen():
    assert GX.is_steam_class(("steamwebhelper", "steam")) and GX.is_steam_class(("steam", "Steam"))
    assert not GX.is_steam_class(("steam_app_1091500", "steam_app_1091500"))      # a Proton game
    assert not GX.is_steam_class(("stone", "STONE")) and not GX.is_steam_class(None)
    menu, sign, big, store = (1, 220, 90, ""), (2, 705, 440, "Sign in to Steam"), (3, 1920, 1080, "Steam Big Picture Mode"), (4, 1280, 800, "Steam")
    assert GX.choose_steam([]) is None and GX.choose_steam([menu]) is None        # menus and tooltips: never
    assert GX.choose_steam([menu, sign]) == 2
    assert GX.choose_steam([store, sign]) == 2                                     # the sign-in before the client
    assert GX.choose_steam([store, sign, big, menu]) == 3                          # Big Picture before all
    assert GX.choose_steam([store, menu]) == 4
    assert GX.choose_steam([(5, 800, 600, None), (6, 900, 700, None)]) == 6       # else the largest
    assert GX.choose_steam([store, sign, menu], big_only=True) is None             # the store: Big Picture or nothing
    assert GX.choose_steam([store, big], big_only=True) == 3
    assert GX.is_big_picture("Steam Big Picture Mode") and not GX.is_big_picture("Steam") and not GX.is_big_picture(None)


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

        # Steam's own window in front (D-30): only mapped, Steam-class windows count
        assert f.steam_windows() == [] and f.steam_value() == 0
        big = root.create_window(0, 0, 800, 600, 0, d.screen().root_depth, X.InputOutput, X.CopyFromParent)
        big.set_wm_class("steamwebhelper", "steam")
        big.set_wm_name("Sign in to Steam")
        big.map()
        other.map()
        d.sync()
        wins = f.steam_windows()
        assert sorted((w.id, wd, ht) for w, wd, ht, _t in wins) == sorted([(big.id, 800, 600), (other.id, 10, 10)]), wins
        assert GX.choose_steam([(w.id, wd, ht, t) for w, wd, ht, t in wins]) == big.id
        assert [t for w, _wd, _ht, t in wins if w.id == big.id] == ["Sign in to Steam"]
        f.mark_steam(big)
        assert f.get(big, "STEAM_GAME") == [769] and f.get(big, "STEAM_INPUT_FOCUS") is None
        f.front_window(big.id)
        assert f.shown() == ([413091, 769], big.id)
        f.unmark_steam(big)
        assert f.get(big, "STEAM_GAME") == [0]
        f.front(None)
        assert f.shown() == ([413091, 769], 0)
        f.set_steam_value(2)
        assert f.steam_value() == 2 and GX.Focus(disp).steam_value() == 2
        f.set_steam_value(0)
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
