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
    def __init__(self):
        self.hold, self.fronts, self.marked = False, [], []

    def find_home(self):
        return [types.SimpleNamespace(id=0x400001)]

    def mark_home(self, w):
        self.marked.append(w.id)

    def front(self, game):
        self.fronts.append(game)

    def home_front(self):
        return self.hold

    def set_home_front(self, on):
        self.hold = on


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


if __name__ == "__main__":
    sys.exit(run_module(globals()))
