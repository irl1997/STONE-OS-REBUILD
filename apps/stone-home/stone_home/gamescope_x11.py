"""Gamescope focus for the STONE session (M24, D-21): STONE Home in front, the running game on top of it.

Gamescope decides what is on screen from X11 properties of its primary Xwayland (sources read on
2026-11-07: ValveSoftware/gamescope 309eee7 src/steamcompmgr.cpp; ShadowBlip/OpenGamepadUI 0db5812
core/ui/card_ui/card_ui.gd, core/systems/launcher/running_app.gd, extensions/core/src/gamescope.rs):

  STEAM_GAME = 769               on a window: this is the main interface (Gamescope looks for Steam's id)
  STEAM_INPUT_FOCUS = 1          on a window: it gets the controller and keyboard
  GAMESCOPECTRL_BASELAYER_APPID  on the root: app ids in front, in order; Steam (and OpenGamepadUI)
                                 write [413091, <game>, ..., 769]
  GAMESCOPECTRL_BASELAYER_WINDOW on the root: the window to show (0 = let Gamescope choose)

STONE Home is marked as the main interface. While Steam runs a game (seen in /proc as
`reaper SteamLaunch AppId=<id>`, as stoned does), the game's id is put in front; when it ends,
Home comes back. Behaviour on the board is [V-13]: until then this is CODE TESTED only.

  STONE_HOME_FRONT = 1           on the root, STONE's own: Home stays in front of the running game
                                 (guide button, guide.py); STONE Home's REANUDAR sets it back to 0
"""

import os
import re

STEAM_APPID = 769                 # Gamescope's hard-coded main-interface id (Steam's)
EXTRA_UNKNOWN_APPID = 413091      # the extra id Steam always writes first
HOME_WM_CLASS = "STONE"
HOME_FRONT = "STONE_HOME_FRONT"           # chromium.py starts Chromium with --class=STONE
REAPER = re.compile(rb"(?:^|/)reaper\x00SteamLaunch\x00AppId=(\d+)\x00")


def running_game(proc_root="/proc"):
    """AppID of the game Steam is running now (newest process wins), or None. STONE Home itself,
    also started through a reaper in rc23's model, is never a game."""
    best = None
    try:
        names = os.listdir(proc_root)
    except OSError:
        return None
    for name in names:
        if not name.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, name, "cmdline"), "rb") as f:
                cmd = f.read()
        except OSError:
            continue
        m = REAPER.search(cmd)
        if not m or b"stone-home" in cmd:
            continue
        pid = int(name)
        if best is None or pid > best[0]:
            best = (pid, int(m.group(1)))
    return None if best is None else best[1]


def baselayer_for(game_appid):
    """The id list Steam writes: Home alone, or the game in front of it."""
    if game_appid is None:
        return [EXTRA_UNKNOWN_APPID, STEAM_APPID]
    return [EXTRA_UNKNOWN_APPID, int(game_appid), STEAM_APPID]


class Focus:
    """Writes the properties on the session's primary Xwayland ($DISPLAY). Needs python-xlib."""

    def __init__(self, display_name=None):
        from Xlib import display as xdisplay
        self.d = xdisplay.Display(display_name)
        self.root = self.d.screen().root
        self.atoms = {}

    def _atom(self, name):
        if name not in self.atoms:
            self.atoms[name] = self.d.intern_atom(name)
        return self.atoms[name]

    def _set(self, window, name, values):
        from Xlib import Xatom
        window.change_property(self._atom(name), Xatom.CARDINAL, 32, [int(v) for v in values])
        self.d.flush()

    def get(self, window, name):
        from Xlib import Xatom
        prop = window.get_full_property(self._atom(name), Xatom.CARDINAL)
        return list(prop.value) if prop else None

    def find_home(self):
        """Top-level windows whose WM_CLASS is STONE's."""
        out = []

        def walk(win):
            for child in win.query_tree().children:
                try:
                    cls = child.get_wm_class()
                except Exception:  # noqa: BLE001  (windows vanish while walking)
                    cls = None
                if cls and HOME_WM_CLASS in cls:
                    out.append(child)
                walk(child)
        walk(self.root)
        return out

    def mark_home(self, window):
        self._set(window, "STEAM_GAME", [STEAM_APPID])
        self._set(window, "STEAM_INPUT_FOCUS", [1])

    def front(self, game_appid):
        self._set(self.root, "GAMESCOPECTRL_BASELAYER_APPID", baselayer_for(game_appid))
        self._set(self.root, "GAMESCOPECTRL_BASELAYER_WINDOW", [0])

    def home_front(self):
        """True while Home was asked to stay in front of the running game."""
        return (self.get(self.root, HOME_FRONT) or [0])[0] == 1

    def set_home_front(self, on):
        self._set(self.root, HOME_FRONT, [1 if on else 0])
