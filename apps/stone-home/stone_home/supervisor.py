"""`stone-session`: the STONE session (M24, D-21). STONE Home in front, Steam as a hidden component.

gamescope-session-plus starts this as the session's CLIENTCMD (sessions.d/stone), as the console
user, inside the session's Gamescope. It:

  1. starts Steam in the background (no Game Mode interface)                        [V-14]
  2. starts STONE Home (/usr/bin/stone-home: Chromium, WebKit fallback)
  3. restarts either when it stops, but at most RESTART_LIMIT times in RESTART_WINDOW_S;
     when STONE Home keeps failing, the console falls back to Steam's own Game Mode interface in
     this same session (the recovery path of D-21), and the reason is recorded.
  4. keeps Gamescope's focus: Home marked as the main interface, the running game in front of it
     (gamescope_x11.py) [V-13]; the guide button during a game brings Home to the front, the game
     still running behind it, until Home's REANUDAR (guide.py, plan B of V-13).
  5. shows Steam's own window when STONE Home asks for it (sign-in, store and checkout: D-34) and
     takes the screen back with the guide button, when a game starts or when Steam closes it.
  6. plan B of D-34, when STONE Home asks for it (session.request): Steam's own Game Mode interface
     takes the whole session (the same command as the recovery path) and STONE Home comes back when
     the person has signed in, holds the guide button GUIDE_HOLD_S, or Steam ends.
  7. never lets a Steam window STONE did not ask for on screen: its mark is removed and it is moved
     off the screen (board, 12-11-2026, 3.0.0-rc1: Steam's sign-in drawn over the first-run setup).
  8. on a new console Steam waits while the first-run setup runs: it starts when the setup reaches its
     Steam step (STONE Home leaves steam.wanted), or when the setup ends.

Commands:
  stone-session run                 the session client (never returns while the session lives)
  stone-session status [--json]     last session start, fallback state and reason
  stone-session boot [--json]       BOOT TO VISUAL / BOOT TO READY of the last boots (M02)
  sudo stone-session default on     make the STONE session the console's automatic session (the image's
                                    default since 0.4.0, D-29; also undoes the boot guard)
  sudo stone-session default off    back to Bazzite's own automatic session
  stone-session switch desktop      log out to Bazzite's desktop, for the next login only (M15)
  stone-session switch stone        from the desktop, log out back to the STONE session

Nothing here is privileged except `default`, which only writes or removes one SDDM drop-in
(/etc/sddm.conf.d/zz-stone-session.conf), and `switch`, which asks polkit to run
/usr/libexec/stone/stone-session-select (next-login-only session) and then logs out.
Environment (tests and board tuning only):
  STONE_SESSION_STEAM      command that starts Steam in the background
  STONE_SESSION_HOME       command that starts STONE Home
  STONE_SESSION_FALLBACK   Steam's Game Mode interface, used when STONE Home keeps failing
  STONE_SESSION_SDDM_DIR   where the SDDM drop-in goes
  STONE_SESSION_GUARD_DIR  the boot guard's state (/var/lib/stone)
  STONE_SESSION_SELECT     command that picks the next login's session (pkexec + helper)
  STONE_SESSION_LOGOUT     command that ends this login
  STONE_SESSION_SIGNED_GRACE  seconds Steam keeps the session after the account appears (plan B)
"""

import json
import os
import shlex
import signal
import subprocess
import sys
import time

STEAM_CMD = "steam -silent"                                             # [V-14] plan B: add -gamepadui
HOME_CMD = "/usr/bin/stone-home"
FALLBACK_CMD = "steam -gamepadui -steamos3 -steampal -steamdeck"       # sessions.d/steam's CLIENTCMD
RESTART_LIMIT = 3
RESTART_WINDOW_S = 120
POLL_S = 0.2                 # children and the guide button
GAME_EVERY = 5               # ticks between /proc scans for the running game (1 s)
STEAM_WAIT_S = 25            # Steam's window may take this long to appear once asked in front
STEAM_GONE_SCANS = 3         # scans (1 s apart) without a Steam window before Home comes back
STEAM_SWEEP = 12             # scans after Steam leaves the front in which its windows stay unmarked
STEAM_BIG_WAIT_S = 12        # the store was asked: only Big Picture is shown for this long
# Values of the root property STONE_STEAM_FRONT: not asked; any Steam window (the sign-in); the
# supervisor's answer "Steam showed no window"; Big Picture (the store).
STEAM_OFF, STEAM_ON, STEAM_NO_WINDOW, STEAM_ON_BIG = 0, 1, 2, 3
GUIDE_HOLD_S = 3.0           # plan B: holding the guide button gives the session back to STONE
SIGNED_GRACE_S = 20.0        # plan B: Steam keeps the session this long after the account appears
REQUEST_MAX_AGE_S = 30       # a request older than this was left by a session that ended
REQUEST_WHYS = ("login", "store")
SESSION_DESKTOP = "gamescope-session-stone.desktop"
SDDM_DROPIN = "zz-stone-session.conf"
SELECT_CMD = "pkexec /usr/libexec/stone/stone-session-select"
LOGOUT_CMD = "systemctl --user stop graphical-session.target"     # what steamos-manager does
RETURN_LAUNCHER = "/usr/share/applications/stone-volver.desktop"


def state_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "stone")


def _cmd(env_key, default):
    return shlex.split(os.environ.get(env_key, default))


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(f"stone-session: {msg}", file=sys.stderr, flush=True)
    try:
        os.makedirs(state_dir(), exist_ok=True)
        with open(os.path.join(state_dir(), "session.log"), "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _write_state(doc):
    os.makedirs(state_dir(), exist_ok=True)
    path = os.path.join(state_dir(), "session.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f)
    os.replace(tmp, path)


def request_path():
    return os.path.join(state_dir(), "session.request")


def write_request(why):
    """STONE Home asks the supervisor for Steam's own Game Mode interface (plan B of D-34)."""
    if why not in REQUEST_WHYS:
        raise ValueError("why")
    os.makedirs(state_dir(), exist_ok=True)
    tmp = request_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"want": "steam", "why": why, "time": time.time()}, f)
    os.replace(tmp, request_path())


def wanted_path():
    return os.path.join(state_dir(), "steam.wanted")


def want_steam():
    """STONE Home needs Steam now (the setup's Steam step, its sign-in, an install): a held Steam starts."""
    os.makedirs(state_dir(), exist_ok=True)
    with open(wanted_path(), "w") as f:
        f.write(str(time.time()))


def _take_wanted():
    try:
        os.remove(wanted_path())
        return True
    except OSError:
        return False


def first_run_pending():
    """True on a new console whose first-run setup has not ended (Steam then waits, run())."""
    try:
        from . import firstrun
        return not firstrun.status()["done"]
    except Exception:  # noqa: BLE001  (never keeps Steam from starting)
        return False


def take_request():
    """The request STONE Home left, once: "login", "store" or None. Old or damaged ones are dropped."""
    try:
        with open(request_path()) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = None
    try:
        os.remove(request_path())
    except OSError:
        return None
    if not isinstance(d, dict) or d.get("want") != "steam" or d.get("why") not in REQUEST_WHYS:
        return None
    t = d.get("time")
    if not isinstance(t, (int, float)) or not 0 <= time.time() - t <= REQUEST_MAX_AGE_S:
        return None
    return d["why"]


def read_state():
    try:
        with open(os.path.join(state_dir(), "session.json")) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


class FocusKeeper:
    """Home as Gamescope's main interface and the running game in front (gamescope_x11.py); the
    guide button brings Home in front of the game (guide.py). When STONE Home asks for Steam's own
    window (sign-in, store: root property STONE_STEAM_FRONT, D-34) Steam's windows are marked and the
    one to show is named; the guide button, a game starting or Steam closing its window gives the
    screen back to Home. Never fatal: without python-xlib, $DISPLAY or python-evdev the session
    runs and the fact is logged once."""

    def __init__(self, focus=None, running_game=None, guide=None, clock=time.monotonic):
        self.focus = focus
        self.running_game = running_game
        self.clock = clock
        self.marked = set()
        self.game = None             # the running game (None: no game)
        self.shown = "unset"         # what Gamescope was last told to show in front
        self.ticks = 0
        self.guide = guide
        self.steam = False           # Steam's own window was asked in front
        self.steam_mode = STEAM_OFF  # STEAM_ON (any window) or STEAM_ON_BIG (Big Picture)
        self.steam_big = False       # Big Picture has been shown since it was asked
        self.steam_win = None        # the Steam window shown (X id), once there is one
        self.steam_marked = {}       # X id -> window marked while Steam is in front
        self.steam_since = 0.0
        self.steam_missing = 0
        self.sweep = 0               # scans left in which Steam's windows are unmarked again
        self.restored = 0            # times the root properties had to be written again
        self.paused = False          # Steam's own interface has the session (plan B)
        self.parked = {}             # X id -> (x, y): Steam windows moved off the screen, unasked
        self.unasked = set()         # X ids of unasked Steam windows already logged
        if self.focus is None:
            try:
                from . import gamescope_x11 as GX
                self.running_game = self.running_game or GX.running_game
                if not os.environ.get("DISPLAY"):
                    raise RuntimeError("no DISPLAY")
                self.focus = GX.Focus()
            except Exception as e:  # noqa: BLE001  (no Xlib, no display: focus is left to Gamescope)
                log(f"gamescope focus not managed: {e}")
                return
        if self.guide is None:
            try:
                from .guide import GuideWatcher
                self.guide = GuideWatcher(self.on_guide)
            except Exception as e:  # noqa: BLE001  (no python-evdev: the guide button is Steam's)
                log(f"guide button not watched: {e}")

    def release(self):
        """Steam's own interface takes the session (plan B): nothing is kept in front by STONE."""
        self.paused = True
        if self.focus is None:
            return
        try:
            if self.steam:
                self._steam_end("Steam takes the session", STEAM_OFF)
            self.focus.set_home_front(False)
        except Exception as e:  # noqa: BLE001
            log(f"gamescope focus: {e}")

    def resume(self):
        """STONE Home is back: its new window is marked and put in front again."""
        self.paused = False
        self.marked, self.shown, self.game, self.ticks = set(), "unset", None, 0

    def guide_held(self):
        """Seconds the guide button has been held (0 without python-evdev)."""
        if self.guide is None:
            return 0.0
        try:
            self.guide.poll()
            return self.guide.held()
        except Exception:  # noqa: BLE001  (an unplugged pad)
            return 0.0

    def on_guide(self):
        if self.paused:
            return
        if self.steam:
            self._steam_end("guide button", STEAM_OFF)
        elif self.game is not None and not self.focus.home_front():
            self.focus.set_home_front(True)
            log(f"guide button: STONE Home in front, game {self.game} keeps running")

    # ---- Steam's own window in front (D-34) --------------------------------------------
    def _steam_end(self, why, value):
        for win in list(self.steam_marked.values()):
            try:
                self.focus.unmark_steam(win)
            except Exception:  # noqa: BLE001  (the window is gone)
                pass
        self.steam_marked = {}
        self.steam, self.steam_win, self.steam_missing = False, None, 0
        self.sweep = STEAM_SWEEP
        self.focus.set_steam_value(value)
        log(f"Steam's window leaves the front ({why}); STONE Home is back")

    def _steam_unasked(self, wins):
        """Steam's windows while STONE did not ask for them are never on screen: a mark (Steam's or
        anyone's) is removed and the window is moved off the screen, whatever way Gamescope would draw
        it (board, 12-11-2026: Steam's sign-in at its own size over the setup, STONE had not asked).
        Small ones (menus, tooltips), Steam's in-game overlay and anything while a game runs are left."""
        from . import gamescope_x11 as GX
        if self.game is not None:
            return
        for win, w, h, title in wins:
            if w < GX.STEAM_MIN_SIZE[0] or h < GX.STEAM_MIN_SIZE[1]:
                continue
            try:
                info = self.focus.window_info(win)
            except Exception:  # noqa: BLE001  (the window is gone)
                continue
            if info.get("overlay"):
                continue
            if win.id not in self.unasked:
                self.unasked.add(win.id)
                log(f"Steam window {win.id:#x} unasked ({title!r} {w}x{h} at {info['x']},{info['y']}"
                    f"{', override-redirect' if info.get('override') else ''}{', marked' if info.get('steam_game') else ''}); kept off the screen")
            if info.get("steam_game"):
                self.focus.unmark_steam(win)
            if (info["x"], info["y"]) != GX.STEAM_PARK:
                self.parked.setdefault(win.id, (info["x"], info["y"]))
                self.focus.move(win, *GX.STEAM_PARK)

    def _unpark(self, wins):
        """Asked in front: Steam's windows go back where they were (0, 0 if unknown)."""
        live = {win.id: win for win, _w, _h, _t in wins}
        for wid, (x, y) in list(self.parked.items()):
            if wid in live:
                try:
                    self.focus.move(live[wid], max(0, x), max(0, y))
                except Exception:  # noqa: BLE001
                    pass
        self.parked = {}

    def _steam_scan(self):
        from . import gamescope_x11 as GX
        value = self.focus.steam_value()
        asked = value in (STEAM_ON, STEAM_ON_BIG)
        if asked and not self.steam:
            self.steam, self.steam_win, self.steam_missing = True, None, 0
            self.steam_mode, self.steam_big = value, False
            self.steam_since = self.clock()
            log("STONE Home asked for Steam's own window" + (" (Big Picture)" if value == STEAM_ON_BIG else ""))
        elif not asked and self.steam:
            self._steam_end("STONE Home asked", STEAM_OFF)
        wins = self.focus.steam_windows()
        if not self.steam:
            if self.sweep > 0:          # Steam may mark its window again while it closes
                self.sweep -= 1
            self._steam_unasked(wins)
            return
        if self.parked:
            self._unpark(wins)
        for win, _w, _h, _t in wins:
            if win.id not in self.steam_marked:
                self.focus.mark_steam(win)
                self.steam_marked[win.id] = win
        live = {win.id for win, _w, _h, _t in wins}
        self.steam_marked = {i: w for i, w in self.steam_marked.items() if i in live}
        # The store: Big Picture only. The desktop client's window is shown only if this Steam
        # never shows one that says "Big Picture" (a title this code does not know).
        strict = self.steam_mode == STEAM_ON_BIG and (self.steam_big or self.clock() - self.steam_since < STEAM_BIG_WAIT_S)
        target = GX.choose_steam([(win.id, w, h, t) for win, w, h, t in wins], big_only=strict)
        if target is not None:
            title = next((t for win, _w, _h, t in wins if win.id == target), "")
            if target != self.steam_win:
                log(f"Steam window {target:#x} in front ({title!r})")
            self.steam_big = self.steam_big or GX.is_big_picture(title)
            self.steam_win, self.steam_missing = target, 0
        elif self.steam_win is not None:
            self.steam_missing += 1
            if self.steam_missing >= STEAM_GONE_SCANS:
                self._steam_end("Steam closed its window", STEAM_OFF)
        elif self.clock() - self.steam_since > STEAM_WAIT_S:
            self._steam_end(f"Steam showed no window in {STEAM_WAIT_S} s", STEAM_NO_WINDOW)

    def _apply(self, want):
        if isinstance(want, tuple):
            self.focus.front_window(want[1])
        else:
            self.focus.front(want)

    @staticmethod
    def _expected(want):
        from . import gamescope_x11 as GX
        if isinstance(want, tuple):
            return GX.baselayer_for(None), want[1]
        return GX.baselayer_for(want), 0

    def tick(self):
        if self.focus is None or self.paused:
            return
        try:
            scan = self.ticks % GAME_EVERY == 0
            if scan:
                for win in self.focus.find_home():
                    if win.id not in self.marked:
                        self.focus.mark_home(win)
                        self.marked.add(win.id)
                        log(f"STONE Home window {win.id:#x} marked as the main interface")
                game = self.running_game()
                if game != self.game:
                    if self.focus.home_front():        # a new game, or none: Home's hold ends
                        self.focus.set_home_front(False)
                    if game is not None and self.steam:     # a game started from Steam's own interface
                        self._steam_end(f"game {game} started", STEAM_OFF)
                    self.game = game
                self._steam_scan()
            self.ticks += 1
            if self.guide is not None:
                self.guide.poll()
            if self.steam and self.steam_win is not None:
                want = ("window", self.steam_win)
            else:
                want = None if self.game is None or self.focus.home_front() else self.game
            if want != self.shown:
                self._apply(want)
                log("in front: " + ("STONE Home" if want is None else "Steam's window" if isinstance(want, tuple) else f"game {want}"))
                self.shown = want
            elif scan and self.focus.shown() != self._expected(want):
                self._apply(want)                      # someone else (Steam's own interface) rewrote them
                self.restored += 1
                if self.restored in (1, 10, 100, 1000):
                    log(f"gamescope focus properties were rewritten by another program; restored ({self.restored})")
        except Exception as e:  # noqa: BLE001  (a window that vanished, a lost display, an unplugged pad)
            log(f"gamescope focus: {e}")


class Child:
    """One supervised process with a restart budget."""

    def __init__(self, name, argv):
        self.name, self.argv = name, argv
        self.proc = None
        self.starts = []          # monotonic times of starts inside the window

    def start(self):
        now = time.monotonic()
        self.starts = [t for t in self.starts if now - t < RESTART_WINDOW_S] + [now]
        log(f"start {self.name}: {' '.join(self.argv)}")
        self.proc = subprocess.Popen(self.argv, stdin=subprocess.DEVNULL)

    def exhausted(self):
        now = time.monotonic()
        return len([t for t in self.starts if now - t < RESTART_WINDOW_S]) >= RESTART_LIMIT

    def poll(self):
        return None if self.proc is None else self.proc.poll()

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()


def _steam_gone(timeout=20.0):
    """Wait until no Steam client is alive: a new one started too early only hands its arguments
    to the old one and exits."""
    try:
        from . import shortcuts
        end = time.monotonic() + timeout
        while time.monotonic() < end and shortcuts.steam_running():
            time.sleep(0.5)
    except Exception as e:  # noqa: BLE001
        log(f"waiting for Steam to end: {e}")


def steam_takes_the_session(why, focus, stopping):
    """Plan B of D-34: Steam's own Game Mode interface until the person signs in (asked for the
    sign-in on a console without an account), holds the guide button, or Steam ends. Returns why
    it ended."""
    from . import shortcuts
    root = shortcuts.steam_root()
    had = bool(shortcuts.accounts(root))
    grace = _seconds("STONE_SESSION_SIGNED_GRACE", SIGNED_GRACE_S)
    full = Child("steam (its Game Mode interface)", _cmd("STONE_SESSION_FALLBACK", FALLBACK_CMD))
    full.start()
    reason, signed, n = None, None, 0
    while not stopping["flag"]:
        time.sleep(POLL_S)
        n += 1
        rc = full.poll()
        if rc is not None:
            reason = f"Steam ended ({rc})"
            break
        if focus.guide_held() >= GUIDE_HOLD_S:
            reason = f"guide button held {GUIDE_HOLD_S:g} s"
            break
        if why == "login" and not had and n % GAME_EVERY == 0:
            if signed is None and shortcuts.accounts(root):
                signed = time.monotonic()
                log(f"a Steam account signed in; STONE Home returns in {grace:g} s")
            if signed is not None and time.monotonic() - signed >= grace:
                reason = "signed in"
                break
    full.stop()
    return reason or "session ending"


def _seconds(env_key, default):
    try:
        return max(0.0, float(os.environ.get(env_key, default)))
    except ValueError:
        return default


def run():
    stopping = {"flag": False}

    def _stop(*_):
        stopping["flag"] = True
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    os.environ["STONE_SESSION"] = "stone"         # inherited by Steam and Home: boot metrics say which session
    steam = Child("steam", _cmd("STONE_SESSION_STEAM", STEAM_CMD))
    home = Child("stone-home", _cmd("STONE_SESSION_HOME", HOME_CMD))
    started = time.time()
    _write_state({"started": started, "fallback": None})
    try:                                          # Steam's interface flag and waiting shortcuts
        from . import shortcuts
        log(f"prepare: {shortcuts.prepare_session()}")
    except Exception as e:  # noqa: BLE001  (never keeps the session from starting)
        log(f"prepare: {e}")
    take_request()                                # one left by a session that ended is not obeyed
    _take_wanted()                                # nor a wish for Steam left by an earlier session
    home.start()                                  # the interface first: it is what the person waits for
    held = first_run_pending()                    # a new console: no Steam window over the setup
    if held:
        log("first run: Steam starts when the setup reaches its Steam step, or when the setup ends")
    else:
        steam.start()
    focus = FocusKeeper()
    ticks = 0
    try:
        while not stopping["flag"]:
            time.sleep(POLL_S)
            focus.tick()
            ticks += 1
            if held and ticks % GAME_EVERY == 0:
                wanted = _take_wanted()
                if wanted or not first_run_pending():
                    held = False
                    log("first run: Steam starts now (" + ("STONE Home asked for it" if wanted else "the setup ended") + ")")
                    steam.start()
            why = take_request() if ticks % GAME_EVERY == 0 else None
            if why:
                log(f"plan B: Steam's own Game Mode interface takes the session ({why}), asked by STONE Home")
                focus.release()
                home.stop()
                steam.stop()
                _steam_gone()
                reason = steam_takes_the_session(why, focus, stopping)
                log(f"plan B ends ({reason}); STONE Home comes back")
                if stopping["flag"]:
                    break
                _steam_gone()
                home.starts, steam.starts = [], []
                home.start()
                steam.start()
                held = False
                focus.resume()
                continue
            rc = steam.poll()
            if rc is not None:
                log(f"steam exited ({rc})")
                if steam.exhausted():
                    log("steam keeps stopping; it is left stopped and STONE Home stays usable")
                    steam.proc = None
                else:
                    steam.start()
            rc = home.poll()
            if rc is not None:
                log(f"stone-home exited ({rc})")
                if home.exhausted():
                    reason = f"STONE Home stopped {RESTART_LIMIT} times in {RESTART_WINDOW_S} s (last exit {rc})"
                    log(f"recovery: {reason}; Steam's Game Mode interface takes over this session")
                    _write_state({"started": started, "fallback": {"time": time.time(), "reason": reason}})
                    steam.stop()
                    return _fallback()
                home.start()
    finally:
        if stopping["flag"]:
            log("session ending")
        home.stop()
        steam.stop()
    return 0


def _fallback():
    """Recovery path (D-21): the session keeps running Steam's own Game Mode interface."""
    argv = _cmd("STONE_SESSION_FALLBACK", FALLBACK_CMD)
    log(f"start fallback: {' '.join(argv)}")
    return subprocess.call(argv, stdin=subprocess.DEVNULL)


def guard_state():
    from . import guard
    st = guard.load_state(os.environ.get("STONE_SESSION_GUARD_DIR", guard.STATE_DIR))
    sddm_dir = os.environ.get("STONE_SESSION_SDDM_DIR", "/etc/sddm.conf.d")
    st["default"] = os.path.exists(os.path.join(sddm_dir, SDDM_DROPIN))
    return st


def status(as_json=False, out=sys.stdout):
    st = read_state()
    g = guard_state()
    if as_json:
        out.write(json.dumps(dict(st, guard=g)) + "\n")
        return 0
    out.write("Sesión automática: " + ("STONE" if g["default"] else "la de Bazzite") + "\n")
    if g["disabled"]:
        out.write(f"La guardia de arranque la desactivó el {time.strftime('%Y-%m-%d %H:%M', time.localtime(g['disabled']['time']))}: "
                  f"{g['disabled']['reason']}. Para volver a usarla: sudo stone-session default on\n")
    if not st:
        out.write("La sesión STONE no ha arrancado todavía en esta consola.\n")
        return 0
    out.write(f"Última sesión STONE: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.get('started', 0)))}\n")
    fb = st.get("fallback")
    out.write("Recuperación: no usada\n" if not fb else f"Recuperación: Game Mode de Steam desde "
              f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(fb['time']))} · {fb['reason']}\n")
    return 0


def boot(as_json=False, out=sys.stdout):
    from . import bootmetrics as BM
    recs = BM.history()
    out.write(json.dumps(recs) + "\n" if as_json else BM.report(recs))
    return 0


def default(on, out=sys.stdout):
    """Make (or stop making) the STONE session the automatic session. Root only; reversible."""
    sddm_dir = os.environ.get("STONE_SESSION_SDDM_DIR", "/etc/sddm.conf.d")
    if sddm_dir == "/etc/sddm.conf.d" and os.geteuid() != 0:
        out.write("Hace falta sudo: sudo stone-session default on|off\n")
        return 1
    path = os.path.join(sddm_dir, SDDM_DROPIN)
    from . import guard
    if on:
        guard.enable(state_dir=os.environ.get("STONE_SESSION_GUARD_DIR", guard.STATE_DIR))
        os.makedirs(sddm_dir, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write("# STONE OS: the STONE session is the automatic session (stone-session default on).\n"
                    "# Remove with: sudo stone-session default off\n"
                    f"[Autologin]\nSession={SESSION_DESKTOP}\n")
        os.replace(tmp, path)
        out.write("La sesión STONE será la automática desde el próximo arranque.\n")
    else:
        if os.path.exists(path):
            os.remove(path)
        out.write("Vuelve la sesión automática de Bazzite desde el próximo arranque.\n")
    return 0


def switch(target, out=sys.stdout):
    """Next login in Bazzite's desktop (desktop) or back in the STONE session (stone), then log out."""
    if target == "desktop":
        desk = os.path.join(os.path.expanduser("~"), "Desktop")
        dst = os.path.join(desk, "Volver a STONE.desktop")
        try:                                  # a way back on the desktop itself
            if os.path.isdir(desk) and not os.path.exists(dst) and os.path.exists(RETURN_LAUNCHER):
                with open(RETURN_LAUNCHER) as src, open(dst, "w") as f:
                    f.write(src.read())
                os.chmod(dst, 0o755)
        except OSError:
            pass
    r = subprocess.run(_cmd("STONE_SESSION_SELECT", SELECT_CMD) + [target], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log(f"switch {target}: refused ({r.returncode}) {r.stderr.strip()}")
        out.write("No se pudo cambiar de sesión: " + (r.stderr.strip() or f"código {r.returncode}") + "\n")
        return 1
    log(f"switch {target}: next login {r.stdout.strip()}; logging out")
    out.write("Cerrando la sesión…\n")
    out.flush()
    return subprocess.call(_cmd("STONE_SESSION_LOGOUT", LOGOUT_CMD))


def main(argv):
    if argv == ["run"]:
        return run()
    if argv in ([], ["status"]):
        return status()
    if argv == ["status", "--json"]:
        return status(as_json=True)
    if len(argv) == 2 and argv[0] == "switch" and argv[1] in ("desktop", "stone"):
        return switch(argv[1])
    if argv in (["boot"], ["boot", "--json"]):
        return boot(as_json=len(argv) == 2)
    if len(argv) == 2 and argv[0] == "default" and argv[1] in ("on", "off"):
        return default(argv[1] == "on")
    sys.stdout.write("uso: stone-session run | status [--json] | boot [--json] | default on|off | switch desktop|stone\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
