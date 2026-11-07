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


def read_state():
    try:
        with open(os.path.join(state_dir(), "session.json")) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


class FocusKeeper:
    """Home as Gamescope's main interface and the running game in front (gamescope_x11.py); the
    guide button brings Home in front of the game (guide.py). Never fatal: without python-xlib,
    $DISPLAY or python-evdev the session runs and the fact is logged once."""

    def __init__(self, focus=None, running_game=None, guide=None):
        self.focus = focus
        self.running_game = running_game
        self.marked = set()
        self.game = None             # the running game (None: no game)
        self.shown = "unset"         # what Gamescope was last told to show in front
        self.ticks = 0
        self.guide = guide
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

    def on_guide(self):
        if self.game is not None and not self.focus.home_front():
            self.focus.set_home_front(True)
            log(f"guide button: STONE Home in front, game {self.game} keeps running")

    def tick(self):
        if self.focus is None:
            return
        try:
            if self.ticks % GAME_EVERY == 0:
                for win in self.focus.find_home():
                    if win.id not in self.marked:
                        self.focus.mark_home(win)
                        self.marked.add(win.id)
                        log(f"STONE Home window {win.id:#x} marked as the main interface")
                game = self.running_game()
                if game != self.game:
                    if self.focus.home_front():        # a new game, or none: Home's hold ends
                        self.focus.set_home_front(False)
                    self.game = game
            self.ticks += 1
            if self.guide is not None:
                self.guide.poll()
            want = None if self.game is None or self.focus.home_front() else self.game
            if want != self.shown:
                self.focus.front(want)
                log("in front: " + ("STONE Home" if want is None else f"game {want}"))
                self.shown = want
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
    steam.start()
    home.start()
    focus = FocusKeeper()
    try:
        while not stopping["flag"]:
            time.sleep(POLL_S)
            focus.tick()
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
