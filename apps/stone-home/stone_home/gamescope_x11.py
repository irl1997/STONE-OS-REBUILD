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
  STONE_STEAM_FRONT = 1          on the root, STONE's own (D-34): Steam's own window is in front (its
                                 sign-in, its store and checkout). The session supervisor then marks
                                 Steam's windows as the main interface and names the one to show in
                                 GAMESCOPECTRL_BASELAYER_WINDOW; back to 0, their mark is removed.

Why Steam's windows need this: Gamescope (steamcompmgr.cpp, possible-focus list) only ever shows a
window that has an app id, and `steam -silent` gives its own windows none. Without the mark, Steam's
sign-in window exists and is never on screen. [VERIFICAR EN PLACA: T-STEAM-11, T-STEAM-12]
"""

import os
import re

STEAM_APPID = 769                 # Gamescope's hard-coded main-interface id (Steam's)
EXTRA_UNKNOWN_APPID = 413091      # the extra id Steam always writes first
HOME_WM_CLASS = "STONE"
HOME_FRONT = "STONE_HOME_FRONT"           # chromium.py starts Chromium with --class=STONE
STEAM_FRONT = "STONE_STEAM_FRONT"
# WM_CLASS of the Steam client's own windows, compared whole and in lower case. Games run by
# Proton are "steam_app_<id>": never matched.
STEAM_WM_CLASSES = ("steam", "steamwebhelper")
STEAM_MIN_SIZE = (400, 300)               # smaller ones are menus and tooltips, never the one to show
# Steam's full-screen interface, then its sign-in (English and Spanish titles); otherwise the largest.
STEAM_TITLE_ORDER = (("big picture",), ("sign in", "iniciar sesi", "steam guard"))
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


def is_steam_class(cls):
    return bool(cls) and any(isinstance(c, str) and c.lower() in STEAM_WM_CLASSES for c in cls)


def is_big_picture(title):
    return any(x in (title or "").lower() for x in STEAM_TITLE_ORDER[0])


def choose_steam(windows, big_only=False):
    """The Steam window to show among [(id, width, height, title)], or None: Big Picture, then the
    sign-in, then the largest. Menus and tooltips (small) are never chosen. big_only: nothing but
    Big Picture (the store was asked: the desktop client's window is not for a controller)."""
    big = [w for w in windows if w[1] >= STEAM_MIN_SIZE[0] and w[2] >= STEAM_MIN_SIZE[1]]
    for words in STEAM_TITLE_ORDER[:1] if big_only else STEAM_TITLE_ORDER:
        hit = [w for w in big if any(x in (w[3] or "").lower() for x in words)]
        if hit:
            return max(hit, key=lambda w: (w[1] * w[2], w[0]))[0]
    if big_only:
        return None
    return max(big, key=lambda w: (w[1] * w[2], w[0]))[0] if big else None


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

    # ---- Steam's own window in front (D-34) ------------------------------------------------
    def steam_value(self):
        """STONE_STEAM_FRONT: 1 while Steam's own window was asked in front (any window: the
        sign-in), 3 the same for Big Picture (the store); 0 not asked; 2 the supervisor gave up
        because Steam showed no window."""
        return (self.get(self.root, STEAM_FRONT) or [0])[0]

    def set_steam_value(self, value):
        self._set(self.root, STEAM_FRONT, [int(value)])

    def steam_windows(self):
        """The Steam client's own mapped windows: [(window, width, height, title)]."""
        from Xlib import X
        out = []

        def walk(win):
            for child in win.query_tree().children:
                try:
                    if is_steam_class(child.get_wm_class()):
                        a = child.get_attributes()
                        if a.map_state == X.IsViewable and a.win_class == X.InputOutput:
                            g = child.get_geometry()
                            out.append((child, g.width, g.height, self._title(child)))
                except Exception:  # noqa: BLE001  (windows vanish while walking)
                    pass
                walk(child)
        walk(self.root)
        return out

    def _title(self, window):
        try:
            prop = window.get_full_property(self._atom("_NET_WM_NAME"), self._atom("UTF8_STRING"))
            if prop and prop.value:
                v = prop.value
                return (v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v))[:200]
            return str(window.get_wm_name() or "")[:200]
        except Exception:  # noqa: BLE001
            return ""

    def mark_steam(self, window):
        self._set(window, "STEAM_GAME", [STEAM_APPID])

    def unmark_steam(self, window):
        """Back to no app id: Gamescope stops considering the window (appID 0 is never shown)."""
        self._set(window, "STEAM_GAME", [0])

    def front_window(self, window_id):
        """Show exactly this window (one marked as the main interface); 0 = let the id list decide."""
        self._set(self.root, "GAMESCOPECTRL_BASELAYER_APPID", baselayer_for(None))
        self._set(self.root, "GAMESCOPECTRL_BASELAYER_WINDOW", [int(window_id)])

    def shown(self):
        """What the root properties say now: (app id list, window id), to see if someone rewrote them."""
        return self.get(self.root, "GAMESCOPECTRL_BASELAYER_APPID"), (self.get(self.root, "GAMESCOPECTRL_BASELAYER_WINDOW") or [0])[0]
