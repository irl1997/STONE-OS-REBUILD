"""`stone-session`: the STONE session (M24, D-21). STONE Home in front, Steam as a hidden component.

gamescope-session-plus starts this as the session's CLIENTCMD (sessions.d/stone), as the console
user, inside the session's Gamescope. It:

  1. starts Steam in the background (no Game Mode interface)                        [V-14]
  2. starts STONE Home (/usr/bin/stone-home: Chromium, WebKit fallback)
  3. restarts either when it stops, but at most RESTART_LIMIT times in RESTART_WINDOW_S;
     when STONE Home keeps failing, the console falls back to Steam's own Game Mode interface in
     this same session (the recovery path of D-21), and the reason is recorded.
  4. keeps Gamescope's focus: Home marked as the main interface, the running game in front of it
     (gamescope_x11.py) [V-13].

Commands:
  stone-session run                 the session client (never returns while the session lives)
  stone-session status [--json]     last session start, fallback state and reason
  stone-session boot [--json]       BOOT TO VISUAL / BOOT TO READY of the last boots (M02)
  sudo stone-session default on     make the STONE session the console's automatic session
  sudo stone-session default off    back to Bazzite's own automatic session

Nothing here is privileged except `default`, which only writes or removes one SDDM drop-in
(/etc/sddm.conf.d/zz-stone-session.conf). Environment (tests and board tuning only):
  STONE_SESSION_STEAM      command that starts Steam in the background
  STONE_SESSION_HOME       command that starts STONE Home
  STONE_SESSION_FALLBACK   Steam's Game Mode interface, used when STONE Home keeps failing
  STONE_SESSION_SDDM_DIR   where the SDDM drop-in goes
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
POLL_S = 1.0
SESSION_DESKTOP = "gamescope-session-stone.desktop"
SDDM_DROPIN = "zz-stone-session.conf"


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
    """Home as Gamescope's main interface and the running game in front (gamescope_x11.py).
    Never fatal: without python-xlib or $DISPLAY the session runs and the fact is logged once."""

    def __init__(self):
        self.gx = None
        self.focus = None
        self.marked = set()
        self.game = "unset"
        self.disabled = None
        try:
            from . import gamescope_x11 as GX
            self.gx = GX
            if not os.environ.get("DISPLAY"):
                raise RuntimeError("no DISPLAY")
            self.focus = GX.Focus()
        except Exception as e:  # noqa: BLE001  (no Xlib, no display: focus is left to Gamescope)
            self.disabled = str(e)
            log(f"gamescope focus not managed: {e}")

    def tick(self):
        if self.focus is None:
            return
        try:
            for win in self.focus.find_home():
                if win.id not in self.marked:
                    self.focus.mark_home(win)
                    self.marked.add(win.id)
                    log(f"STONE Home window {win.id:#x} marked as the main interface")
            game = self.gx.running_game()
            if game != self.game:
                self.focus.front(game)
                log("in front: " + ("STONE Home" if game is None else f"game {game}"))
                self.game = game
        except Exception as e:  # noqa: BLE001  (a window that vanished, a lost display)
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


def status(as_json=False, out=sys.stdout):
    st = read_state()
    if as_json:
        out.write(json.dumps(st) + "\n")
        return 0
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
    if on:
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


def main(argv):
    if argv == ["run"]:
        return run()
    if argv in ([], ["status"]):
        return status()
    if argv == ["status", "--json"]:
        return status(as_json=True)
    if argv in (["boot"], ["boot", "--json"]):
        return boot(as_json=len(argv) == 2)
    if len(argv) == 2 and argv[0] == "default" and argv[1] in ("on", "off"):
        return default(argv[1] == "on")
    sys.stdout.write("uso: stone-session run | status [--json] | boot [--json] | default on|off\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
