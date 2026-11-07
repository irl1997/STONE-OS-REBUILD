"""The controller's guide button (BTN_MODE) for the STONE session: plan B of V-13.

While a game is in front, pressing the guide button brings STONE Home to the front (the game keeps
running behind it); Home's REANUDAR puts the game back. This reads the button straight from the
input devices (python-evdev), so it does not depend on Steam's own guide-button handling [V-14].
The console user may read game controllers (logind's uaccess on the seat's joystick devices).

Every device that has BTN_MODE is watched, rescanned every RESCAN_S for controllers connected
later. One press can arrive on two devices (the controller and Steam's virtual one): presses closer
than DEBOUNCE_S count once. Never fatal: a device that goes away is dropped.
"""

import select
import time

RESCAN_S = 5.0
DEBOUNCE_S = 0.6


class GuideWatcher:
    def __init__(self, on_press, evdev=None, clock=time.monotonic):
        if evdev is None:
            import evdev  # python3-evdev; ImportError tells the caller the button is not watched
        self.ev = evdev
        self.on_press = on_press
        self.clock = clock
        self.devices = {}             # path -> InputDevice
        self.next_scan = 0.0
        self.last_press = -DEBOUNCE_S

    def _scan(self):
        e = self.ev.ecodes
        for path in self.ev.list_devices():
            if path in self.devices:
                continue
            try:
                dev = self.ev.InputDevice(path)
            except OSError:
                continue
            try:
                keys = dev.capabilities().get(e.EV_KEY, [])
            except OSError:
                keys = []
            if e.BTN_MODE in keys:
                self.devices[path] = dev
            else:
                dev.close()

    def poll(self):
        """Read what is pending without blocking; returns the number of presses reported."""
        now = self.clock()
        if now >= self.next_scan:
            self._scan()
            self.next_scan = now + RESCAN_S
        if not self.devices:
            return 0
        try:
            ready, _, _ = select.select(list(self.devices.values()), [], [], 0)
        except (OSError, ValueError):
            ready = list(self.devices.values())
        e, pressed = self.ev.ecodes, 0
        for dev in ready:
            try:
                events = list(dev.read())
            except BlockingIOError:
                continue
            except OSError:                       # unplugged
                self.devices.pop(dev.path, None)
                continue
            for ev in events:
                if ev.type == e.EV_KEY and ev.code == e.BTN_MODE and ev.value == 1:
                    t = self.clock()
                    if t - self.last_press >= DEBOUNCE_S:
                        self.last_press = t
                        pressed += 1
                        self.on_press()
        return pressed
