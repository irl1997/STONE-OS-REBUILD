"""stone_home/guide.py and the session's focus logic (plan B of V-13), with a fake python-evdev and a
fake Gamescope: the guide button during a game brings Home in front, REANUDAR gives the game back.
Pure Python: runs anywhere. Real controllers and Gamescope are board tests (T-SESS-04).

    python3 tests/test_guide.py     (or: pytest tests/test_guide.py)
"""

import os
import shutil
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import gamescope_x11 as GX  # noqa: E402
from stone_home import guide as G  # noqa: E402
from stone_home import supervisor as SV  # noqa: E402

EV_KEY, BTN_MODE, BTN_SOUTH = 1, 316, 304


class FakeDev:
    def __init__(self, path, keys):
        self.path, self.keys = path, keys
        self.r, self.w = os.pipe()
        os.set_blocking(self.r, False)
        self.queue, self.gone, self.closed = [], False, False

    def fileno(self):
        return self.r

    def capabilities(self):
        return {EV_KEY: self.keys}

    def push(self, code, value):
        self.queue.append(types.SimpleNamespace(type=EV_KEY, code=code, value=value))
        os.write(self.w, b"x")

    def read(self):
        if self.gone:
            raise OSError(19, "No such device")
        try:
            os.read(self.r, 4096)
        except BlockingIOError:
            raise BlockingIOError from None
        q, self.queue = self.queue, []
        return q

    def close(self):
        self.closed = True


def fake_evdev(devs):
    return types.SimpleNamespace(
        ecodes=types.SimpleNamespace(EV_KEY=EV_KEY, BTN_MODE=BTN_MODE),
        list_devices=lambda: [d.path for d in devs],
        InputDevice=lambda p: next(d for d in devs if d.path == p))


class Clock:
    t = 100.0

    def __call__(self):
        return self.t


def test_guide_press_counts_once_across_devices_and_ignores_other_buttons():
    pad, virt, kbd = FakeDev("/dev/input/event5", [BTN_SOUTH, BTN_MODE]), FakeDev("/dev/input/event9", [BTN_MODE]), FakeDev("/dev/input/event1", [30])
    clock, presses = Clock(), []
    w = G.GuideWatcher(lambda: presses.append(clock.t), evdev=fake_evdev([pad, virt, kbd]), clock=clock)
    assert w.poll() == 0 and sorted(w.devices) == ["/dev/input/event5", "/dev/input/event9"] and kbd.closed
    pad.push(BTN_SOUTH, 1)
    pad.push(BTN_MODE, 1)
    virt.push(BTN_MODE, 1)                         # the same press through Steam's virtual pad
    pad.push(BTN_MODE, 0)                          # release
    assert w.poll() == 1 and presses == [100.0]
    clock.t += G.DEBOUNCE_S + 0.1
    virt.push(BTN_MODE, 1)
    assert w.poll() == 1
    pad.gone = True
    pad.push(BTN_MODE, 1)
    clock.t += 1
    assert w.poll() == 0 and list(w.devices) == ["/dev/input/event9"]     # unplugged: dropped


def test_holding_the_guide_button_is_measured_until_it_is_released():
    pad, clock = FakeDev("/dev/input/event5", [BTN_MODE]), Clock()
    w = G.GuideWatcher(lambda: None, evdev=fake_evdev([pad]), clock=clock)
    assert w.poll() == 0 and w.held() == 0.0
    pad.push(BTN_MODE, 1)
    w.poll()
    clock.t += 2.5
    pad.push(BTN_MODE, 2)                          # key repeat while held: still the same press
    w.poll()
    assert w.held() == 2.5
    clock.t += 1
    assert w.held() == 3.5
    pad.push(BTN_MODE, 0)
    w.poll()
    assert w.held() == 0.0
    pad.push(BTN_MODE, 1)
    w.poll()
    pad.gone = True                                # unplugged while held: not held any more
    pad.push(BTN_MODE, 1)
    w.poll()
    assert w.held() == 0.0


def test_controller_connected_later_is_found_at_the_next_scan():
    devs, clock = [], Clock()
    w = G.GuideWatcher(lambda: None, evdev=fake_evdev(devs), clock=clock)
    assert w.poll() == 0 and not w.devices
    devs.append(FakeDev("/dev/input/event7", [BTN_MODE]))
    clock.t += 1
    w.poll()
    assert not w.devices
    clock.t += G.RESCAN_S
    w.poll()
    assert list(w.devices) == ["/dev/input/event7"]


class FakeFocus:
    """Gamescope as the session's focus logic sees it: Home's window, Steam's own windows and the
    root properties that say what is in front."""

    def __init__(self):
        self.hold, self.fronts, self.marked = False, [], []
        self.steam, self.wins, self.steam_marks = 0, [], {}
        self.root = None
        self.pos, self.overlay = {}, set()          # window id -> (x, y); ids with STEAM_OVERLAY

    def find_home(self):
        return [types.SimpleNamespace(id=0x400001)]

    def mark_home(self, w):
        self.marked.append(w.id)

    def front(self, game):
        self.fronts.append(game)
        self.root = (GX.baselayer_for(game), 0)

    def front_window(self, window_id):
        self.fronts.append(("window", window_id))
        self.root = (GX.baselayer_for(None), window_id)

    def shown(self):
        return self.root

    def home_front(self):
        return self.hold

    def set_home_front(self, on):
        self.hold = on

    def steam_value(self):
        return self.steam

    def set_steam_value(self, value):
        self.steam = value

    def steam_windows(self):
        return [(types.SimpleNamespace(id=i), w, h, t) for i, w, h, t in self.wins]

    def mark_steam(self, win):
        self.steam_marks[win.id] = 769

    def unmark_steam(self, win):
        self.steam_marks[win.id] = 0

    def window_info(self, win):
        x, y = self.pos.get(win.id, (0, 0))
        return {"x": x, "y": y, "override": False, "steam_game": self.steam_marks.get(win.id, 0),
                "overlay": win.id in self.overlay}

    def move(self, win, x, y):
        self.pos[win.id] = (x, y)


class NoGuide:
    def poll(self):
        return 0


def _ticks(k, n):
    for _ in range(n):
        k.tick()


def test_guide_brings_home_in_front_of_the_game_and_reanudar_gives_it_back():
    tmp = tempfile.mkdtemp(prefix="stone-guide-")
    old = os.environ.get("XDG_STATE_HOME")
    os.environ["XDG_STATE_HOME"] = tmp                 # the session log goes here, not to ~/.local/state
    try:
        _focus_scenario()
        with open(os.path.join(tmp, "stone", "session.log")) as f:
            assert "guide button: STONE Home in front, game 1091500 keeps running" in f.read()
    finally:
        if old is None:
            del os.environ["XDG_STATE_HOME"]
        else:
            os.environ["XDG_STATE_HOME"] = old
        shutil.rmtree(tmp, ignore_errors=True)


def _focus_scenario():
    game = {"id": None}
    f = FakeFocus()
    k = SV.FocusKeeper(focus=f, running_game=lambda: game["id"], guide=NoGuide())
    _ticks(k, SV.GAME_EVERY)
    assert f.fronts == [None] and f.marked == [0x400001]
    k.on_guide()                                   # no game: nothing to do
    assert f.hold is False
    game["id"] = 1091500
    _ticks(k, SV.GAME_EVERY)
    assert f.fronts == [None, 1091500]
    k.on_guide()
    k.tick()
    assert f.hold is True and f.fronts[-1] is None, f.fronts          # Home in front, game still running
    _ticks(k, SV.GAME_EVERY * 2)
    assert f.fronts[-1] is None                                        # it stays until REANUDAR
    f.set_home_front(False)                                            # REANUDAR (host session.resume)
    k.tick()
    assert f.fronts[-1] == 1091500
    k.on_guide()
    k.tick()
    game["id"] = None                                                  # the game ends while Home is in front
    _ticks(k, SV.GAME_EVERY * 2)
    assert f.hold is False and f.fronts[-1] is None
    game["id"] = 730                                                   # the next game is shown normally
    _ticks(k, SV.GAME_EVERY)
    assert f.fronts[-1] == 730


def _keeper(game=None):
    f, clock, state = FakeFocus(), Clock(), {"id": game}
    k = SV.FocusKeeper(focus=f, running_game=lambda: state["id"], guide=NoGuide(), clock=clock)
    _ticks(k, SV.GAME_EVERY)
    return f, k, clock, state


def _quiet(test):
    """Run a focus scenario with the session log in a temporary directory."""
    tmp = tempfile.mkdtemp(prefix="stone-guide-")
    old = os.environ.get("XDG_STATE_HOME")
    os.environ["XDG_STATE_HOME"] = tmp
    try:
        test()
        with open(os.path.join(tmp, "stone", "session.log")) as f:
            return f.read()
    finally:
        if old is None:
            del os.environ["XDG_STATE_HOME"]
        else:
            os.environ["XDG_STATE_HOME"] = old
        shutil.rmtree(tmp, ignore_errors=True)


SIGN_IN = (0x600010, 705, 440, "Sign in to Steam")
BIG_PICTURE = (0x600020, 1920, 1080, "Steam Big Picture Mode")
MENU = (0x600030, 220, 90, "")


def test_steam_window_comes_in_front_when_home_asks_and_the_guide_button_gives_home_back():
    def scenario():
        f, k, _clock, _state = _keeper()
        assert f.fronts == [None]
        f.wins = [MENU]                                # Steam has windows all the time; none is shown unasked
        _ticks(k, SV.GAME_EVERY * 2)
        assert f.fronts == [None] and not f.steam_marks
        f.steam = SV.STEAM_ON                          # Home: steam.show("login")
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts == [None] and f.steam_marks == {MENU[0]: 769}      # only a menu so far: wait
        f.wins = [MENU, SIGN_IN]
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] == ("window", SIGN_IN[0]) and f.steam_marks[SIGN_IN[0]] == 769
        f.wins = [MENU, SIGN_IN, BIG_PICTURE]          # signed in: Big Picture replaces the sign-in
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] == ("window", BIG_PICTURE[0])
        k.on_guide()                                   # the guide button returns to STONE
        k.tick()
        assert f.steam == SV.STEAM_OFF and f.fronts[-1] is None
        assert set(f.steam_marks.values()) == {0}      # Steam's windows can no longer take the screen
        f.steam_marks[BIG_PICTURE[0]] = 769            # Steam marks its window again while it closes
        _ticks(k, SV.GAME_EVERY)
        assert f.steam_marks[BIG_PICTURE[0]] == 0
    log = _quiet(scenario)
    assert "STONE Home asked for Steam's own window" in log and "guide button" in log


def test_a_steam_window_nobody_asked_for_is_moved_off_the_screen_and_comes_back_when_asked():
    """Board, 12-11-2026 (3.0.0-rc1): Steam's sign-in drawn over the first-run setup at its own size,
    STONE had not asked. Unasked, it loses any mark and waits off the screen; asked, it comes back."""
    def scenario():
        f, k, _clock, state = _keeper()
        f.wins = [SIGN_IN, MENU]
        f.steam_marks[SIGN_IN[0]] = 769                # marked by someone else (Steam itself)
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts == [None]                      # Home stays in front
        assert f.steam_marks[SIGN_IN[0]] == 0 and f.pos[SIGN_IN[0]] == GX.STEAM_PARK
        assert MENU[0] not in f.pos                    # menus and tooltips are left alone
        f.steam = SV.STEAM_ON                          # now Home asks for it (INICIAR SESIÓN)
        _ticks(k, SV.GAME_EVERY)
        assert f.pos[SIGN_IN[0]] == (0, 0) and f.fronts[-1] == ("window", SIGN_IN[0])
        f.steam = SV.STEAM_OFF
        _ticks(k, SV.GAME_EVERY * 2)
        assert f.pos[SIGN_IN[0]] == GX.STEAM_PARK and f.fronts[-1] is None
        state["id"] = 1091500                          # a game runs: Steam's windows are not touched
        f.pos[SIGN_IN[0]] = (10, 10)
        _ticks(k, SV.GAME_EVERY * 2)
        assert f.pos[SIGN_IN[0]] == (10, 10)
        f.overlay.add(SIGN_IN[0])
        state["id"] = None
        _ticks(k, SV.GAME_EVERY * 2)
        assert f.pos[SIGN_IN[0]] == (10, 10)           # Steam's in-game overlay window is never moved
    log = _quiet(scenario)
    assert "unasked ('Sign in to Steam' 705x440 at 0,0, marked); kept off the screen" in log


def test_steam_waits_during_the_first_run_until_home_asks_for_it():
    tmp = tempfile.mkdtemp(prefix="stone-want-")
    old = os.environ.get("XDG_STATE_HOME")
    os.environ["XDG_STATE_HOME"] = tmp
    try:
        assert SV._take_wanted() is False
        SV.want_steam()
        assert os.path.exists(SV.wanted_path()) and SV._take_wanted() is True and SV._take_wanted() is False
    finally:
        if old is None:
            del os.environ["XDG_STATE_HOME"]
        else:
            os.environ["XDG_STATE_HOME"] = old
        shutil.rmtree(tmp, ignore_errors=True)


def test_steam_that_shows_no_window_gives_up_and_says_so():
    def scenario():
        f, k, clock, _state = _keeper()
        f.steam = SV.STEAM_ON
        _ticks(k, SV.GAME_EVERY)
        clock.t += SV.STEAM_WAIT_S - 1
        _ticks(k, SV.GAME_EVERY)
        assert f.steam == SV.STEAM_ON
        clock.t += 2
        _ticks(k, SV.GAME_EVERY)
        assert f.steam == SV.STEAM_NO_WINDOW and f.fronts == [None]     # Home never left the screen
    assert "showed no window" in _quiet(scenario)


def test_home_comes_back_when_steam_closes_its_window_or_home_asks():
    def scenario():
        f, k, _clock, _state = _keeper()
        f.steam, f.wins = SV.STEAM_ON, [BIG_PICTURE]
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] == ("window", BIG_PICTURE[0])
        f.wins = []                                    # the person left Big Picture from Steam's own menu
        _ticks(k, SV.GAME_EVERY * (SV.STEAM_GONE_SCANS - 1))
        assert f.steam == SV.STEAM_ON                  # a window that is being replaced is not "closed"
        _ticks(k, SV.GAME_EVERY)
        assert f.steam == SV.STEAM_OFF and f.fronts[-1] is None
        f.steam, f.wins = SV.STEAM_ON, [BIG_PICTURE]   # asked again
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] == ("window", BIG_PICTURE[0])
        f.steam = SV.STEAM_OFF                         # Home: steam.hide
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] is None and f.steam_marks[BIG_PICTURE[0]] == 0
    _quiet(scenario)


CLIENT = (0x600040, 1280, 800, "Steam")


def test_the_store_shows_big_picture_only_and_never_the_desktop_client_after_it():
    def scenario():
        f, k, clock, _state = _keeper()
        f.steam, f.wins = SV.STEAM_ON_BIG, [CLIENT]    # the desktop client's window is there, hidden
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts == [None]                      # not for a controller: Big Picture is awaited
        f.wins = [CLIENT, BIG_PICTURE]
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] == ("window", BIG_PICTURE[0])
        clock.t += SV.STEAM_BIG_WAIT_S * 3
        f.wins = [CLIENT]                              # the person left Big Picture from Steam's menu
        _ticks(k, SV.GAME_EVERY * SV.STEAM_GONE_SCANS)
        assert f.steam == SV.STEAM_OFF and f.fronts[-1] is None and ("window", CLIENT[0]) not in f.fronts

        f.steam, f.wins = SV.STEAM_ON_BIG, [CLIENT]    # a Steam whose Big Picture has another title
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] is None
        clock.t += SV.STEAM_BIG_WAIT_S + 1
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] == ("window", CLIENT[0])   # better Steam's window than none
    _quiet(scenario)


def test_a_game_started_from_steam_takes_the_screen():
    def scenario():
        f, k, _clock, state = _keeper()
        f.steam, f.wins = SV.STEAM_ON, [BIG_PICTURE]
        _ticks(k, SV.GAME_EVERY)
        state["id"] = 620
        _ticks(k, SV.GAME_EVERY)
        assert f.steam == SV.STEAM_OFF and f.fronts[-1] == 620
    _quiet(scenario)


def test_plan_b_releases_the_focus_and_takes_it_back_for_the_new_home_window():
    def scenario():
        f, k, _clock, state = _keeper(game=730)
        f.steam, f.wins = SV.STEAM_ON, [BIG_PICTURE]
        state["id"] = None
        _ticks(k, SV.GAME_EVERY)
        n = len(f.fronts)
        k.release()                                    # Steam's own interface takes the session
        assert f.steam == SV.STEAM_OFF and f.hold is False and f.steam_marks[BIG_PICTURE[0]] == 0
        state["id"] = 620
        k.on_guide()
        _ticks(k, SV.GAME_EVERY * 3)
        assert len(f.fronts) == n and f.hold is False  # nothing is written while Steam has the session
        state["id"] = None
        k.resume()
        _ticks(k, SV.GAME_EVERY)
        assert f.fronts[-1] is None and f.marked[-1] == 0x400001 and len(f.marked) == 2
    _quiet(scenario)


def test_focus_properties_rewritten_by_another_program_are_restored():
    def scenario():
        f, k, _clock, _state = _keeper()
        assert f.root == (GX.baselayer_for(None), 0)
        f.root = ([769], 0)                            # Steam's own interface wrote the base layer
        _ticks(k, SV.GAME_EVERY)
        assert f.root == (GX.baselayer_for(None), 0) and f.fronts == [None, None]
        f.steam, f.wins = SV.STEAM_ON, [BIG_PICTURE]
        _ticks(k, SV.GAME_EVERY)
        f.root = (GX.baselayer_for(None), 0)           # ... and while Steam's window is in front
        _ticks(k, SV.GAME_EVERY)
        assert f.root == (GX.baselayer_for(None), BIG_PICTURE[0])
    assert "restored" in _quiet(scenario)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
