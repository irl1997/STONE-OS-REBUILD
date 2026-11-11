"""What STONE Home asks of the rest of the system, besides performance.

  power        logind PowerOff / Reboot (the active local session is allowed by the
               default polkit rules; no root, no shell)
  steam URLs   a fixed set of steam:// URLs handed to the running Steam client
  system info  /usr/lib/stone-release, the boot time, the image deployments and the
               automatic update timer (systemd properties, read-only)
  prefs        STONE Home's own settings in ~/.config/stone/home.json

Nothing here runs a shell or a command built from UI input. The only commands are
`steam <url>` with a URL from STEAM_URLS or library.launch_url(), and
`rpm-ostree status --json`.
"""

import json
import os
import subprocess
import tempfile
import threading

from gi.repository import Gio, GLib

STEAM_BIN = "/usr/bin/steam"
# Steam browser protocol (https://developer.valvesoftware.com/wiki/Steam_browser_protocol).
# [VERIFICAR EN PLACA] how each one shows inside Game Mode.
STEAM_URLS = {
    "store": "steam://url/StoreFrontPage",
    "downloads": "steam://open/downloads",
    "screenshots": "steam://open/screenshots",
}
# Steam's own interface in front of STONE Home (D-34): Big Picture is the one made for a controller.
FRONT_URLS = {"bigpicture": "steam://open/bigpicture", "bigpicture_close": "steam://close/bigpicture"}
RELEASE = os.environ.get("STONE_RELEASE_FILE", "/usr/lib/stone-release")


def prefs_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "stone", "home.json")


# key -> (validator, default)
def _bool(v):
    return v if isinstance(v, bool) else None


def _intr(lo, hi):
    return lambda v: v if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi else None


def _vol(v):
    return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 else None


def _favs(v):
    if not isinstance(v, list):
        return None
    out = [a for a in v if isinstance(a, str) and a.isdigit() and 0 < len(a) <= 10]
    return out[:500]


PREFS = {
    "sound": (_bool, True), "vol": (_vol, 0.7), "hc": (_bool, False), "rm": (_bool, False),
    "ts": (_intr(0, 2), 0), "safe": (_intr(0, 8), 5), "idle": (_intr(0, 3), 2), "tech": (_bool, False),
    "adv_ack": (_bool, False), "favorites": (_favs, []),
    # How STONE Home draws inside Game Mode (read by /usr/libexec/stone-home at start):
    # 0 GPU (Chromium, at the screen's resolution), 1 no GPU (WebKit shell in software, the
    # fallback). Replaces RC7's "render" (WebKit GPU experiments), which is dropped.
    "engine": (_intr(0, 1), 0),
    # Game resolution environment (STONE DISPLAY): 0 games see the display's own resolution
    # (Steam "Native" on games left at "Default"), 1 Steam's default size.
    "game_res": (_intr(0, 1), 0),
    "display_goal": (lambda v: v if v in ("fluid", "max_res") else None, "fluid"),   # STONE DISPLAY link goal
    "optimized": (_intr(0, 1), 1),        # STONE OPTIMIZED: JUGAR launches with the game profile
    "frame": (_intr(0, 6), 0),            # TV framing: % of the picture kept clear on each side (overscan)
    # Games bought away from the console (the phone): installed by STONE as soon as Steam lists them.
    "wanted": (_favs, []),
    "report": (_bool, True),              # PARTE DE SESIÓN: the summary shown when a game ends
}


def clean_prefs(d):
    out = {}
    for k, (check, default) in PREFS.items():
        v = check(d.get(k)) if isinstance(d, dict) and k in d else None
        out[k] = default if v is None else v
    return out


def load_prefs():
    try:
        with open(prefs_path()) as f:
            return clean_prefs(json.load(f))
    except (OSError, ValueError):
        return clean_prefs({})


def save_prefs(d):
    p = clean_prefs(d)
    path = prefs_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".home-", dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        json.dump(p, f, indent=1, sort_keys=True)
    os.replace(tmp, path)
    return p


def read_release(path=None):
    out = {}
    try:
        with open(path or RELEASE) as f:
            for line in f:
                k, sep, v = line.strip().partition("=")
                if sep and k.startswith("STONE_"):
                    out[k] = v.strip().strip('"')
    except OSError:
        pass
    return out


def boot_time(proc="/proc"):
    try:
        with open(os.path.join(proc, "stat")) as f:
            for line in f:
                if line.startswith("btime "):
                    return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def deployments(run=subprocess.run):
    """Booted, staged and rollback images from rpm-ostree (read-only, unprivileged)."""
    try:
        out = run(["rpm-ostree", "status", "--json"], capture_output=True, text=True, timeout=20).stdout
        d = json.loads(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    res = {"booted": None, "staged": None, "rollback": None}
    for dep in d.get("deployments", []):
        info = {"image": dep.get("container-image-reference") or dep.get("origin"),
                "version": dep.get("version"), "timestamp": dep.get("timestamp")}
        if dep.get("booted"):
            res["booted"] = info
        elif dep.get("staged"):
            res["staged"] = info
        elif res["rollback"] is None and res["booted"] is not None:
            res["rollback"] = info
    return res


# Bazzite's automatic image update (ublue-os/uupd) first; the bootc and rpm-ostree timers are
# what an image without uupd would use. The first one that is loaded is reported. [V-18]
UPDATE_TIMERS = ("uupd.timer", "bootc-fetch-apply-updates.timer", "rpm-ostreed-automatic.timer")
SD = ("org.freedesktop.systemd1", "/org/freedesktop/systemd1")


def _usec(v):
    return v // 1000000 if isinstance(v, int) and v > 0 else None


def update_timer(get_props, timers=UPDATE_TIMERS):
    """{"unit", "enabled", "last", "next"} (epoch seconds) for the first loaded timer, or None.
    get_props(unit) -> {"LoadState", "UnitFileState", "LastTriggerUSec", "NextElapseUSecRealtime"} or None."""
    for unit in timers:
        try:
            p = get_props(unit)
        except Exception:  # noqa: BLE001  (no systemd, no bus: nothing to report)
            p = None
        if not p or p.get("LoadState") != "loaded":
            continue
        return {"unit": unit, "enabled": p.get("UnitFileState") in ("enabled", "static", "alias"),
                "last": _usec(p.get("LastTriggerUSec")), "next": _usec(p.get("NextElapseUSecRealtime"))}
    return None


class System:
    def __init__(self, bus=None, spawn=None):
        self._bus = bus
        self.spawn = spawn or self._spawn_steam

    def bus(self):
        if self._bus is None:
            self._bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        return self._bus

    @staticmethod
    def _spawn_steam(url):
        subprocess.Popen([STEAM_BIN, url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)

    def open_url(self, url):
        # rungameid takes a 64-bit game id (non-Steam shortcuts: appid << 32 | 0x02000000)
        ok_game = (url.startswith("steam://rungameid/") and url[18:].isdigit() and len(url) <= 18 + 20) or \
                  (url.startswith("steam://uninstall/") and url[18:].isdigit() and len(url) <= 18 + 10) or \
                  (url.startswith("steam://install/") and url[16:].isdigit() and len(url) <= 16 + 10) or \
                  (url.startswith("steam://store/") and url[14:].isdigit() and len(url) <= 14 + 10)
        if not ok_game and url not in STEAM_URLS.values() and url not in FRONT_URLS.values():
            raise ValueError("url not allowed")
        self.spawn(url)

    def power(self, action, done):
        method = {"off": "PowerOff", "reboot": "Reboot"}.get(action)
        if method is None:
            return done(None, "InvalidValue", "action")

        def finished(conn, res):
            try:
                conn.call_finish(res)
                done({"ok": True})
            except GLib.Error as e:
                done(None, "PermissionDenied" if "Access" in (Gio.DBusError.get_remote_error(e) or "") else "Unsupported",
                     e.message)

        self.bus().call("org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager",
                        method, GLib.Variant("(b)", (False,)), None, Gio.DBusCallFlags.NONE, 10000, None, finished)

    def _timer_props(self, unit):
        bus = self.bus()
        path = bus.call_sync(SD[0], SD[1], "org.freedesktop.systemd1.Manager", "LoadUnit", GLib.Variant("(s)", (unit,)),
                             GLib.VariantType("(o)"), Gio.DBusCallFlags.NONE, 5000, None).unpack()[0]
        out = {}
        for iface, keys in (("org.freedesktop.systemd1.Unit", ("LoadState", "UnitFileState")),
                            ("org.freedesktop.systemd1.Timer", ("LastTriggerUSec", "NextElapseUSecRealtime"))):
            for k in keys:
                try:
                    out[k] = bus.call_sync(SD[0], path, "org.freedesktop.DBus.Properties", "Get", GLib.Variant("(ss)", (iface, k)),
                                           GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 5000, None).unpack()[0]
                except GLib.Error:
                    out[k] = None
        return out

    def info(self, done):
        def work():
            res = {"release": read_release(), "boot_time": boot_time(), "deployments": deployments(),
                   "updates": update_timer(self._timer_props), "session": os.environ.get("STONE_SESSION") or "other"}
            GLib.idle_add(lambda: (done(res), False)[1])
        threading.Thread(target=work, daemon=True).start()
