"""STONE Home in Chromium: GPU drawing at the screen's own resolution inside Steam Game Mode.

Why Chromium: inside Gamescope the GPU paths of GTK 4 + WebKitGTK flickered and came out
see-through on the BC-250 (RC2), so the WebKit shell had to draw in software, which is slow
at 4K. Steam's own Game Mode interface is Chromium (CEF) drawing on the GPU inside the same
Gamescope, so that path is the proven one on this machine.

How it runs:
  * this process (the one Steam starts and tracks) runs the Host (host.py) and the local
    HTTP transport (server.py) on 127.0.0.1 with a per-start secret path;
  * Chromium shows that page full screen as an app window (kiosk), with its own profile in
    ~/.local/state/stone/chromium, no extensions, no sync, no network beyond 127.0.0.1;
  * the page is laid out at 1920 x 1080 CSS pixels and Chromium draws it at the window's real
    resolution (device scale factor = window / 1920 x 1080: 2 on a 4K screen), so text and
    edges are sharp at 4K and nothing is scaled as a bitmap;
  * if Chromium cannot run (missing, or crashing at start three times), this returns
    UNUSABLE and /usr/libexec/stone-home starts the WebKit shell without GPU instead.

Start order (BOOT TO VISUAL): the local transport and Chromium are started first; the Host (its
imports: the display model, the game profiles, the bridge to stoned) is created while Chromium
is starting, instead of before it. The page's first requests wait for the main loop, which only
runs once the Host exists. The screen's size is read from the X server (python-xlib), without
loading GTK; GTK is the fallback.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time

from gi.repository import GLib

from .server import HomeServer

UI_DIR = os.environ.get("STONE_HOME_UI", "/usr/share/stone-home")
CANDIDATES = ("/usr/bin/chromium-browser", "/usr/bin/chromium")
DESIGN_W, DESIGN_H = 1920, 1080
UNUSABLE = 75                       # exit status: Chromium could not run; use the WebKit shell
CRASH_WINDOW_S = 120
CRASH_LIMIT = 3
SELFTEST_TIMEOUT_S = 90
# Chromium features that would talk to the network, show browser UI or watch media keys.
DISABLED_FEATURES = ("Translate", "MediaRouter", "HardwareMediaKeyHandling", "GlobalMediaControls",
                     "OptimizationHints", "AutofillServerCommunication", "InterestFeedContentSuggestions",
                     "PrivacySandboxSettings4", "DialMediaRouteProvider", "CalculateNativeWinOcclusion")


def find_binary():
    env = os.environ.get("STONE_CHROMIUM")
    for p in ((env,) if env else CANDIDATES):
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def state_dir():
    return os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"), "stone")


def _x_screen_size():
    """The X screen's size in pixels straight from the X server, or None (no python-xlib, no display)."""
    try:
        from Xlib import display as xdisplay
        d = xdisplay.Display()
        try:
            s = d.screen()
            w, h = int(s.width_in_pixels), int(s.height_in_pixels)
        finally:
            d.close()
        return (w, h) if w >= 320 and h >= 240 else None
    except Exception:  # noqa: BLE001  (GTK is asked instead)
        return None


def screen_size(x_size=_x_screen_size):
    """(width, height) of the X screen STONE's window fills (Gamescope's size for this app), or None."""
    forced = os.environ.get("STONE_HOME_SIZE", "")
    w, _, h = forced.partition("x")
    if w.isdigit() and h.isdigit():
        return int(w), int(h)
    size = x_size() if os.environ.get("DISPLAY") else None
    if size:
        return size
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk, Gtk
        if not Gtk.init_check():
            return None
        disp = Gdk.Display.get_default()
        mons = disp.get_monitors() if disp else None
        if not mons or mons.get_n_items() == 0:
            return None
        mon = mons.get_item(0)
        g = mon.get_geometry()
        scale = mon.get_scale_factor() or 1
        return g.width * scale, g.height * scale
    except Exception as e:  # noqa: BLE001  (without a size the page scales itself)
        print(f"[stone] chromium: screen size unknown ({e})", file=sys.stderr, flush=True)
        return None


def scale_factor(size):
    """Device scale factor so the 1920 x 1080 layout fills the screen at its real resolution."""
    if not size:
        return None
    f = min(size[0] / DESIGN_W, size[1] / DESIGN_H)
    if not 0.25 <= f <= 4:
        return None
    return round(f, 4)


def build_args(binary, url, profile, dsf=None, extra=(), size=None):
    args = [binary, f"--user-data-dir={profile}", "--ozone-platform=x11", "--kiosk", f"--app={url}",
            "--no-first-run", "--no-default-browser-check", "--disable-sync", "--disable-extensions",
            "--disable-component-update", "--disable-background-networking", "--disable-default-apps",
            "--disable-breakpad", "--password-store=basic", "--noerrdialogs", "--hide-crash-restore-bubble",
            "--disable-pinch", "--overscroll-history-navigation=0", "--autoplay-policy=no-user-gesture-required",
            "--enable-gpu-rasterization", "--enable-zero-copy", "--ignore-gpu-blocklist",
            # Nothing but 127.0.0.1 (never proxied) is reachable: every other address goes to a
            # proxy that does not exist.
            "--proxy-server=socks5://127.0.0.1:9", "--disk-cache-size=67108864",
            "--disable-features=" + ",".join(DISABLED_FEATURES),
            "--enable-logging=stderr", "--log-level=0", "--class=STONE"]
    if dsf and dsf != 1:
        args.append(f"--force-device-scale-factor={dsf:g}")
    if size:
        # The whole screen from the first frame, also where no window manager makes kiosk windows
        # full screen (sizes in device-independent pixels).
        f = dsf or 1
        args += ["--window-position=0,0", f"--window-size={round(size[0] / f)},{round(size[1] / f)}"]
    return args + list(extra)


def mark_clean_exit(profile):
    """A crash or power-off must not bring up Chromium's "restore pages?" bubble."""
    path = os.path.join(profile, "Default", "Preferences")
    try:
        with open(path) as f:
            prefs = json.load(f)
    except (OSError, ValueError):
        return
    p = prefs.setdefault("profile", {})
    if p.get("exit_type") == "Normal" and p.get("exited_cleanly") is True:
        return
    p["exit_type"], p["exited_cleanly"] = "Normal", True
    try:
        with open(path + ".stone", "w") as f:
            json.dump(prefs, f)
        os.replace(path + ".stone", path)
    except OSError:
        pass


KEEP = ("CONSOLE", ":ERROR:", ":FATAL:", "[stone]")


def _pipe_log(stream):
    """Chromium's log, reduced to page console messages and errors, into home.log."""
    for line in iter(stream.readline, b""):
        text = line.decode("utf-8", "replace").rstrip()
        if any(k in text for k in KEEP):
            print(text[:600], file=sys.stderr, flush=True)


class LateHost:
    """What the transport talks to until the Host exists. Requests are answered on the main loop,
    which starts after the Host is created, so handle() normally finds it; artwork is asked for
    from the transport's own threads and waits for it."""

    def __init__(self):
        self.host = None
        self.ready = threading.Event()

    def set(self, host):
        self.host = host
        self.ready.set()

    def handle(self, req, done):
        if self.host is None:
            return done(None, "ServiceUnavailable", "STONE Home is starting")
        return self.host.handle(req, done)

    def art_path(self, appid, kind):
        if not self.ready.wait(15):
            return None
        return self.host.art_path(appid, kind)


class Shell:
    def __init__(self, selftest=False):
        self.selftest = selftest
        self.loop = GLib.MainLoop()
        self.exit_code = 0
        self.proc = None
        self.crashes = []
        self.stopping = False
        self.host = None
        self.late = LateHost()
        self.server = HomeServer(self.late, UI_DIR).start()
        self.binary = find_binary()
        self.profile = os.path.join(state_dir(), "chromium")
        self.size = screen_size()
        self.dsf = scale_factor(self.size)

    def start_host(self):
        """The Host, created while Chromium starts (its imports are the slow part of Python's start)."""
        from .host import Host
        self.host = Host(lambda name, data: self.server.clients.send(name, data))
        self.host.restart = self._restart
        if self.selftest:
            self.host.selftest = self._selftest_done
        self.late.set(self.host)

    def start_browser(self):
        os.makedirs(self.profile, mode=0o700, exist_ok=True)
        mark_clean_exit(self.profile)
        url = self.server.url + ("#selftest" if self.selftest else "")
        extra = tuple(os.environ.get("STONE_CHROMIUM_EXTRA", "").split()) if self.selftest else ()
        env = dict(os.environ)
        env.pop("LD_PRELOAD", None)
        env.pop("LD_LIBRARY_PATH", None)
        self.t0 = time.time()
        self.proc = subprocess.Popen(build_args(self.binary, url, self.profile, self.dsf, extra, self.size), env=env,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        threading.Thread(target=_pipe_log, args=(self.proc.stderr,), daemon=True).start()
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, self.proc.pid, self._exited)

    def _exited(self, pid, status):
        if self.stopping:
            return
        code = os.waitstatus_to_exitcode(status) if hasattr(os, "waitstatus_to_exitcode") else status
        quick = time.time() - self.t0 < 20
        print(f"[stone] chromium exited ({code}) after {time.time() - self.t0:.0f} s", file=sys.stderr, flush=True)
        if code == 0 and not quick:
            # Closed on purpose (Alt+F4, the window closed): STONE Home ends, as the WebKit shell did.
            self.exit_code = 0
            return self.loop.quit()
        now = time.time()
        self.crashes = [t for t in self.crashes if now - t < CRASH_WINDOW_S] + [now]
        if len(self.crashes) >= CRASH_LIMIT or self.selftest:
            self.exit_code = UNUSABLE
            return self.loop.quit()
        GLib.timeout_add(1000, lambda: (self.start_browser(), False)[1])

    def _stop_browser(self):
        self.stopping = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

    def _restart(self):
        """A new drawing mode: the same process (Steam keeps tracking it) starts again through
        /usr/bin/stone-home."""
        launcher = "/usr/bin/stone-home"
        if not os.access(launcher, os.X_OK):
            print("stone-home: restart not possible here", file=sys.stderr, flush=True)
            return
        print("[stone] restarting", file=sys.stderr, flush=True)
        self._stop_browser()
        self.server.stop()
        sys.stdout.flush()
        sys.stderr.flush()
        os.execv(launcher, [launcher])

    def _selftest_done(self, result):
        print(json.dumps({"selftest": result}, ensure_ascii=False), flush=True)
        self.exit_code = 0 if isinstance(result, dict) and result.get("pass") else 1
        GLib.timeout_add(100, lambda: (self.loop.quit(), False)[1])

    def _selftest_timeout(self):
        print(json.dumps({"selftest": {"pass": False, "reason": "timeout"}}), flush=True)
        self.exit_code = 1
        self.loop.quit()
        return False

    def run(self):
        if not self.binary:
            print("[stone] chromium: not installed; using the WebKit shell", file=sys.stderr, flush=True)
            self.server.stop()
            return UNUSABLE
        size = f"{self.size[0]}x{self.size[1]}" if self.size else "unknown"
        print(f"[stone] start: engine=chromium binary={self.binary} screen={size} scale={self.dsf if self.dsf is None else format(self.dsf, 'g')}", file=sys.stderr, flush=True)
        for sig in (signal.SIGTERM, signal.SIGINT):
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, lambda: (self.loop.quit(), False)[1])
        if self.selftest:
            GLib.timeout_add_seconds(SELFTEST_TIMEOUT_S, self._selftest_timeout)
        self.start_browser()
        if not self.selftest:
            try:
                from . import shortcuts
                print(f"[stone] start: steam_ids={shortcuts.record_ids()}", file=sys.stderr, flush=True)
            except Exception as e:  # noqa: BLE001  (diagnostics must never stop the interface)
                print(f"stone-home: could not record Steam ids: {e}", file=sys.stderr, flush=True)
        self.start_host()
        self.loop.run()
        self._stop_browser()
        self.server.stop()
        return self.exit_code


def main(argv):
    return Shell("--selftest" in argv).run()
