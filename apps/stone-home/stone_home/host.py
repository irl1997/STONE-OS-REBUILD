"""One request dispatcher for every transport (WebKit in STONE OS, HTTP in development).

A request is {"method": str, "args": list}. The method must be in the table below; the
arguments are checked by the module that owns them. The result goes back through
done(result) or done(None, code, message), with the same error codes as stoned.
"""

import os
import subprocess
import threading
import time

from gi.repository import GLib

import stone_display
from stone_games import optimizer as games_opt
from stone_games import schema as games_schema
from stone_games.perf import PerfAsync

from . import account
from . import artcache
from . import bootmetrics
from . import connect
from . import bridge
from . import emulators
from . import firstrun
from . import health
from . import library
from . import media
from . import roms
from . import shortcuts
from . import steamcef
from . import steamsettings
from . import storage
from . import store
from . import system


LIB_FAST_S = 4               # the library is read again this often while something is expected ...
LIB_SLOW_S = 45              # ... and this often the rest of the time (a game bought on the phone)
LIB_FAST_FOR_S = 150         # "expected": the boot, an install, coming back from Steam's store
LIB_FRESH_S = 3              # a read this recent is not repeated
LIB_FIRST_WAIT_S = 1.5       # the first read waits this long for Steam's interface, no more (boot)
FRONT_POLL_MS = 500          # Steam's own window in front: how often its state is looked at
FRONT_URL_WAIT_S = 8         # the page is asked of Steam at the latest this long after Big Picture
FRONT_URL_SETTLE_S = 1.5     # ... or this long after Big Picture is on screen
STORE_FRESH_S = 600          # the shop window is read from Steam again after this long
SHOW_WHAT = ("login", "store", "app")


class Host:
    def __init__(self, emit, stoned=None, sysapi=None, steam_root=None):
        self.emit = emit                                      # emit(event_name, data)
        self.stoned = stoned or bridge.Stoned(emit)
        self.sys = sysapi or system.System()
        self.steam_root = steam_root
        self.games = {}                                       # appid -> launch URL, from the last scan
        self.owned = set()                                    # not installed, in the account: may be installed
        self.store_free = set()                               # free games seen in the store: may be installed
        self.store_seen = set()                               # games seen in the store: their pages may be asked for
        self.store_window = None                              # (monotonic time, the shop window as read)
        # The library is watched: Steam answers about the account some seconds after it starts,
        # and games arrive later (bought on the phone, installed). STONE Home is told ("library").
        self.account_rows = None                              # the account's games as Steam last gave them
        self.saved_rows = None                                # ... and as kept for the next boot (account.py)
        self.signin = account.SignIn()
        self.lib_sig = None                                   # what STONE Home was last given
        self.lib_last = None                                  # (monotonic time, the last read)
        self.lib_busy = False
        self.lib_next = 0.0
        self.lib_fast_until = time.monotonic() + LIB_FAST_FOR_S
        self.running_game = None                              # set lazily: gamescope_x11.running_game
        self.art = artcache.Fetcher(self._art_news, lookup=store.header_url)
        self.front = None                                     # Steam's own window asked in front (D-34)
        self.front_timer = None
        self.request_session = None                           # tests: a fake of supervisor.write_request
        self.emu_busy = set()                                 # catalog keys being installed
        self.selftest = None                                  # set by app.py --selftest
        self.restart = None                                   # set by app.py: restart STONE Home
        self.steam_ui = steamcef                              # Steam's interface (replaced in tests)
        self.session_focus = None                             # gamescope_x11.Focus in the STONE session (tests: a fake)
        self.session_switch = ["/usr/bin/stone-session", "switch"]   # tests: a fake
        self.cu40_cmd = ["pkexec", "/usr/bin/stone-cu40"]             # tests: a fake
        self.rollback_cmd = ["pkexec", "/usr/bin/bootc", "rollback"]  # tests: a fake
        cef = _SteamUIProxy(self)
        # STONE DISPLAY: display model and the game resolution environment (stone_display/).
        self.display = stone_display.Display(game_policy=self.game_policy, cef=cef,
                                             goal=lambda: system.load_prefs().get("display_goal", "fluid"),
                                             on_change=lambda why: GLib.idle_add(self._display_changed, why))
        self.game_env = stone_display.GameEnvironment(cef=cef)
        # STONE OPTIMIZED: game profiles, graphics paths, measured optimization (stone_games/).
        self.optimized = games_opt.Engine(root=self.root, cef=cef, display=lambda: self.display.status(fresh=True),
                                          perf=PerfAsync(self.stoned), log=lambda m: print(m, flush=True))
        self._opt_busy = False
        GLib.timeout_add_seconds(3, self._opt_monitor)
        GLib.timeout_add_seconds(LIB_FAST_S, self._lib_tick)
        GLib.timeout_add_seconds(8, lambda: (self._opt_work(self.optimized.recover, "recover"), False)[1])

    def game_policy(self):
        """"native": games see the display's own resolution; "steam": whatever Steam defaults to."""
        return "steam" if system.load_prefs().get("game_res") == 1 else "native"

    def _display_changed(self, why):
        print(f"[stone] display: DISPLAY_CHANGED ({why})", flush=True)
        self.emit("display", {"changed": True})
        return False

    # ---- STONE OPTIMIZED: monitor and recovery (off the UI thread) ---------------------------
    def _opt_work(self, fn, what):
        if self._opt_busy:
            return
        self._opt_busy = True

        def work():
            try:
                r = fn()
                if isinstance(r, dict) and r:
                    print(f"[stone] optimized: {what}: {r}", flush=True)
                    if what == "monitor" and r.get("appid"):
                        GLib.idle_add(lambda: (self.emit("game", {"ended": r}), False)[1])
            except Exception as e:  # noqa: BLE001  (never take STONE Home down over this)
                print(f"[stone] optimized: {what} failed: {e!r}", flush=True)
            finally:
                self._opt_busy = False
        threading.Thread(target=work, daemon=True).start()

    def _opt_monitor(self):
        """MONITOR: only while a game launched by STONE OPTIMIZED is prepared or running."""
        if os.path.exists(self.optimized.session_path):
            self._opt_work(self.optimized.tick, "monitor")
        return True

    def optimized_on(self):
        return system.load_prefs().get("optimized", 1) == 1

    def root(self):
        return self.steam_root or shortcuts.steam_root()

    def handle(self, req, done):
        if not isinstance(req, dict) or not isinstance(req.get("method"), str):
            return done(None, "InvalidValue", "bad request")
        method, args = req["method"], req.get("args", [])
        if not isinstance(args, list) or len(args) > 4:
            return done(None, "InvalidValue", "bad arguments")
        try:
            if method.startswith("perf."):
                return self.stoned.call(method[5:], args, done)
            fn = getattr(self, "m_" + method.replace(".", "_"), None) if method.replace(".", "").isalnum() else None
            if fn is None:
                return done(None, "InvalidValue", "unknown method")
            return fn(args, done)
        except games_schema.ProfileError as e:
            return done(None, "InvalidValue", str(e))
        except Exception as e:        # a bad request never takes STONE Home down
            return done(None, "HardwareError", f"internal error: {e!r}")

    # ---- library and launching --------------------------------------------------------
    def _owned(self, limit=None):
        """The account's games from Steam's interface, or None. limit: seconds to wait at most (the
        first read, at boot, must not wait for a Steam that is still starting)."""
        box = {}

        def ask():
            try:
                box["rows"] = self.steam_ui.owned_games()
            except Exception as e:  # noqa: BLE001  (Steam's interface changed: the installed games remain)
                print(f"[stone] library: account not read ({e!r})", flush=True)
                box["rows"] = None
        if limit is None:
            ask()
            return box["rows"]
        t = threading.Thread(target=ask, daemon=True)
        t.start()
        t.join(limit)
        if t.is_alive():
            print(f"[stone] library: Steam's interface did not answer in {limit:g} s; the kept list is shown meanwhile", flush=True)
            return None
        return box.get("rows")

    def _lib_read(self, limit=None):
        """The library as it is now (off the UI thread): Steam's files, the account's games from
        Steam's interface (or the list it gave last time), artwork flags, who is signed in."""
        root = self.root()
        try:
            res = library.scan(root)
        except Exception as e:  # damaged Steam files: show an empty library, say why
            res = {"root_found": False, "games": [], "error": repr(e)}
        # Games in the account that are not installed come from Steam's interface (the files on
        # disk only list installed ones).
        owned = None if res.get("error") else self._owned(limit)
        live = owned is not None
        acct = library.account_id(root)
        raw = None
        if live and not owned:
            ask = getattr(self.steam_ui, "login_state", None)
            try:
                raw = ask() if ask else None
            except Exception:  # noqa: BLE001
                raw = None
        # No account folder: nobody has ever signed in on this console (certain, without Steam).
        logged = "out" if acct is None and not owned else self.signin.state(raw, has_games=bool(owned))
        rows, cached = owned, False
        if owned:
            self.account_rows = owned
            if acct and account.signature_rows(owned) != self.saved_rows and account.save(acct, owned):
                self.saved_rows = account.signature_rows(owned)
        elif logged != "out":
            rows = self.account_rows or account.load(acct)      # Steam not answering yet: what it said last
            cached = bool(rows)
        res["games"] += library.not_installed(root, rows, {g["appid"] for g in res["games"]})
        for g in res["games"]:
            art = g.setdefault("art", {})
            art.setdefault("header", False)
            if g.get("source") != "steam" or (art.get("capsule") and art.get("hero")):
                continue
            kept = artcache.flags(g["appid"])                   # fetched by STONE: Steam had not cached it
            art["capsule"] = bool(art.get("capsule") or kept["capsule"])
            art["hero"] = bool(art.get("hero") or kept["hero"])
            art["header"] = kept["header"] and not art["capsule"]
            if not art["capsule"]:
                self.art.want(g["appid"], ("capsule",))
        res["owned_known"] = live
        res["owned_cached"] = cached
        res["logged"] = logged
        res["account"] = acct is not None
        return res, account.signature(res["games"], live) + (logged,)

    def m_library(self, args, done):
        last = self.lib_last
        if last is not None and time.monotonic() - last[0] < LIB_FRESH_S:
            return self._lib_done(last[1], last[2], done)       # read a moment ago by the watcher

        first = self.lib_sig is None        # the boot: Home's first frame waits for this answer

        def work():
            res, sig = self._lib_read(LIB_FIRST_WAIT_S if first else None)
            GLib.idle_add(lambda: (self._lib_done(res, sig, done), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def _lib_done(self, res, sig, done):
        self.lib_sig = sig
        self.lib_last = (time.monotonic(), res, sig)
        self._scanned(res, done)

    def _lib_kick(self, seconds=LIB_FAST_FOR_S):
        """Something is expected to change (an install, a purchase): look often for a while."""
        self.lib_fast_until = max(self.lib_fast_until, time.monotonic() + seconds)
        self.lib_next = 0.0

    def _game_running(self):
        if self.running_game is None:
            from . import gamescope_x11
            self.running_game = gamescope_x11.running_game
        try:
            return self.running_game() is not None
        except Exception:  # noqa: BLE001
            return False

    def _lib_tick(self):
        now = time.monotonic()
        if self.lib_busy or now < self.lib_next or self.lib_sig is None:     # nobody has asked yet
            return True
        if now >= self.lib_fast_until and self._game_running():
            self.lib_next = now + LIB_SLOW_S                                 # a game has the console
            return True
        self.lib_busy = True

        def work():
            try:
                out = self._lib_read()
            except Exception as e:  # noqa: BLE001
                print(f"[stone] library: watch failed: {e!r}", flush=True)
                out = None
            GLib.idle_add(lambda: (self._lib_watched(out), False)[1])
        threading.Thread(target=work, daemon=True).start()
        return True

    def _lib_watched(self, out):
        self.lib_busy = False
        now = time.monotonic()
        self.lib_next = now + (LIB_FAST_S if now < self.lib_fast_until else LIB_SLOW_S)
        if out is None:
            return
        res, sig = out
        self.lib_last = (now, res, sig)
        if sig != self.lib_sig:
            self.lib_sig = sig
            print(f"[stone] library: changed ({len(res['games'])} games, account "
                  f"{'live' if res['owned_known'] else 'kept' if res['owned_cached'] else 'unknown'}, signed {res['logged']})", flush=True)
            self.emit("library", {"reason": "changed"})

    def _art_news(self, news):
        """Artwork fetched by STONE (artcache worker thread): STONE Home redraws those games."""
        GLib.idle_add(lambda: (self.emit("art", {"art": news}), False)[1])

    def m_art_want(self, args, done):
        """art.want(appid): the big picture of a game the person is looking at, fetched first."""
        if len(args) != 1 or not library.valid_appid(args[0]) or \
                (args[0] not in self.games and args[0] not in self.owned and args[0] not in self.store_seen):
            return done(None, "InvalidValue", "unknown game")
        done({"queued": self.art.want(args[0], ("hero", "capsule"), first=True)})

    def _scanned(self, res, done):
        self.games = {g["appid"]: g["launch"] for g in res["games"] if g.get("launch")}
        self.owned = {g["appid"] for g in res["games"] if not g.get("installed") and g.get("source") == "steam"}
        done(res)
        # The game environment for every game, known or not: installed games, shortcuts and STONE itself.
        if self.game_policy() == "native":
            ids = [g["appid"] for g in res["games"] if g.get("installed")]
            root = self.root()
            threading.Thread(target=lambda: self._apply_env(ids + list(shortcuts.shortcut_appids(root))),
                             daemon=True).start()

    def _env_state(self):
        snap = self.display.status(fresh=True)
        # The size to give games: the display's native one, or the best the link carries when it cannot do native.
        return ({"game_default": snap.get("steam_game_default")} if snap.get("steam_available") else None,
                snap.get("game_environment") or (snap.get("primary") or {}).get("native_resolution"))

    def _apply_env(self, ids):
        try:
            d = self.game_env.ensure_default(self._env_state)        # every game, wherever launched
            if d.get("status") not in ("ok", "changed", "unsupported", "unknown"):
                print(f"[stone] display: default game size: {d}", flush=True)
            r = self.game_env.apply(ids)                              # per game, where still "Default"
            if r.get("error"):
                print(f"[stone] display: game environment not applied ({r['error']})", flush=True)
        except Exception as e:  # noqa: BLE001  (never take STONE Home down over this)
            print(f"[stone] display: game environment failed: {e!r}", flush=True)

    def m_install(self, args, done):
        """Installs a game of the account (or a free game found in the store) without Steam's dialog
        (steamcef.install); if Steam's interface does not answer, Steam's install URL."""
        if len(args) != 1 or not isinstance(args[0], str) or not args[0].isdigit() \
                or (args[0] not in self.owned and args[0] not in self.store_free):
            return done(None, "InvalidValue", "unknown game")
        appid = int(args[0])
        self._lib_kick()
        self._in_steam_ui(lambda: self.steam_ui.install(appid), lambda: self.sys.open_url(f"steam://install/{appid}"), done)

    def m_emulators(self, args, done):
        def work():
            rows = emulators.catalog()
            for r in rows:
                r["busy"] = r["key"] in self.emu_busy
            GLib.idle_add(lambda: (done(rows), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_emuInstall(self, args, done):
        if len(args) != 1 or args[0] not in emulators.CATALOG:       # NOT_YET entries cannot be installed
            return done(None, "InvalidValue", "unknown emulator")
        key = args[0]
        if key in self.emu_busy:
            return done({"ok": True, "already": True})
        self.emu_busy.add(key)

        def progress(state, text):
            GLib.idle_add(lambda: (self.emit("emulator", {"key": key, "state": state, "text": text}), False)[1])

        def work():
            try:
                emulators.install(key, progress, steam_ui=self.steam_ui)
            finally:
                self.emu_busy.discard(key)
        threading.Thread(target=work, daemon=True).start()
        done({"ok": True})

    def m_emuCheck(self, args, done):
        """emuCheck(): which installed emulators have a newer version on Flathub (asks Flathub)."""
        def work():
            try:
                r = emulators.updates()
            except Exception as e:  # noqa: BLE001
                r = {"error": f"No se pudo consultar Flathub: {e!r}"}
            res = (None, "Unsupported", r["error"]) if "error" in r else (r, None, "")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_emuUpdate(self, args, done):
        """emuUpdate(key | "all"): update one installed emulator, or every installed one, from
        Flathub. Progress arrives as "emulator" events (state updating|done|error)."""
        if len(args) != 1 or (args[0] != "all" and args[0] not in emulators.CATALOG):
            return done(None, "InvalidValue", "unknown emulator")
        target = args[0]

        def progress_for(key):
            return lambda state, text: GLib.idle_add(
                lambda: (self.emit("emulator", {"key": key, "state": state, "text": text}), False)[1])

        def work():
            try:
                keys = [target] if target != "all" else [r["key"] for r in emulators.catalog() if r["installed"]]
            except Exception as e:  # noqa: BLE001
                print(f"[stone] emulators: {e!r}", flush=True)
                keys = []
            ok = 0
            for key in keys:
                if key in self.emu_busy:
                    continue
                self.emu_busy.add(key)
                try:
                    ok += 1 if emulators.update(key, progress_for(key)) else 0
                except Exception as e:  # noqa: BLE001
                    progress_for(key)("error", f"No se pudo actualizar: {e!r}")
                finally:
                    self.emu_busy.discard(key)
            if target == "all":
                GLib.idle_add(lambda: (self.emit("emulator", {"key": "all", "state": "done", "updated": ok, "of": len(keys)}), False)[1])
        threading.Thread(target=work, daemon=True).start()
        done({"ok": True})

    def _in_steam_ui(self, call, fallback, done):
        """Ask Steam's interface first (in Game Mode steam:// URLs are received and ignored for
        some targets, board RC3); the steam:// URL is the fallback. Runs off the UI thread."""
        def work():
            try:
                st = str(call())
            except Exception as e:  # noqa: BLE001  (Steam's interface changed: the request is still answered)
                st = f"steam ui error: {e!r}"
            ok = st.endswith(": ok")
            err = None
            if not ok and fallback:
                try:
                    fallback()
                    ok = True
                except (OSError, ValueError) as e:
                    err = str(e)
            print(f"[stone] steam ui: {st}{'' if ok or not err else ' / ' + err}", flush=True)
            res = ({"ok": True, "via": "steam-ui" if st.endswith(": ok") else "url"}, None, "") if ok \
                else (None, "Unsupported", st)
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_launch(self, args, done):
        if len(args) != 1 or args[0] not in self.games:
            return done(None, "InvalidValue", "unknown game")
        url = self.games[args[0]]
        gid = url.rsplit("/", 1)[-1]
        if not gid.isdigit():
            return done(None, "InvalidValue", "unknown game")
        appid = args[0]

        def launch():
            if self.game_policy() == "native":
                self._apply_env([appid])          # a game installed since the last scan, too
            if gid == appid and self.optimized_on():
                # GAME -> STONE RECOMMENDED -> PLAY. Any failure here launches the game as it is.
                try:
                    r = self.optimized.prepare(appid)
                    print(f"[stone] optimized: {appid}: {r.get('why') or r.get('error')} "
                          f"graphics={r.get('graphics_applied')} performance={r.get('performance')}", flush=True)
                except Exception as e:  # noqa: BLE001
                    print(f"[stone] optimized: {appid} not prepared ({e!r}); launching unchanged", flush=True)
            return self.steam_ui.run_game(int(gid))
        self._in_steam_ui(launch, lambda: self.sys.open_url(url), done)

    # ---- STONE OPTIMIZED API ---------------------------------------------------------------
    def _opt_call(self, done, fn):
        def work():
            try:
                res = (fn(), None, "")
            except games_schema.ProfileError as e:
                res = (None, "InvalidValue", str(e))
            except Exception as e:  # noqa: BLE001
                res = (None, "HardwareError", f"optimized: {e!r}")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _game_args(args, n_min=1, n_max=2):
        if not n_min <= len(args) <= n_max or not isinstance(args[0], str) or not args[0].isdigit() or len(args[0]) > 10:
            raise games_schema.ProfileError("appid")
        mode = args[1] if len(args) > 1 else None
        if mode is not None and mode not in games_schema.MODES:
            raise games_schema.ProfileError("mode")
        return args[0], mode

    def m_game_profile(self, args, done):
        """getGameProfile(appid)"""
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: frontend_profile(self.optimized.profile(appid)))

    def m_game_recommended(self, args, done):
        """getRecommendedExperience(appid, mode?)"""
        appid, mode = self._game_args(args)
        self._opt_call(done, lambda: frontend_recommended(self.optimized.recommended(appid, mode or self.optimized.chosen_mode(appid))))

    def m_game_modes(self, args, done):
        """getAvailableModes(appid)"""
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: {"chosen": self.optimized.chosen_mode(appid), "modes": self.optimized.modes(appid)})

    def m_game_apply(self, args, done):
        """applyGameProfile(appid, mode, config?) - the mode used from now on (custom: with its config)."""
        if len(args) not in (2, 3):
            return done(None, "InvalidValue", "arguments")
        appid, mode = self._game_args(args[:2], 2, 2)
        cfg = args[2] if len(args) == 3 else None
        if mode == "custom" and not isinstance(cfg, dict):
            return done(None, "InvalidValue", "custom needs a configuration")
        self._opt_call(done, lambda: self.optimized.apply(appid, mode, cfg))

    def m_game_launchOptimized(self, args, done):
        """launchOptimized(appid, mode?)"""
        appid, mode = self._game_args(args)
        if appid not in self.games:
            return done(None, "InvalidValue", "unknown game")
        if mode:
            self.optimized.apply(appid, mode)
        return self.m_launch([appid], done)

    def m_game_image(self, args, done):
        """imageOptions(appid): the enhancement choices of one game and which one is active."""
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.image_options(appid))

    def m_game_setImage(self, args, done):
        """setImage(appid, key, preset?): the person's own choice; unavailable ones are refused."""
        if len(args) not in (2, 3) or not isinstance(args[1], str) or (len(args) == 3 and args[2] is not None and not isinstance(args[2], str)):
            return done(None, "InvalidValue", "arguments")
        appid, _ = self._game_args(args[:1], 1, 1)
        preset = args[2] if len(args) == 3 else None
        self._opt_call(done, lambda: self.optimized.set_image(appid, args[1], preset))

    def m_game_experience(self, args, done):
        """EXPERIENCE ENGINE report of one game."""
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.experience(appid))

    def m_game_frameGen(self, args, done):
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.frame_generation(appid))

    def m_game_setFrameGen(self, args, done):
        if len(args) != 2 or not isinstance(args[1], bool):
            return done(None, "InvalidValue", "arguments")
        appid, _ = self._game_args(args[:1], 1, 1)
        self._opt_call(done, lambda: self.optimized.set_frame_generation(appid, args[1]))

    def m_game_look(self, args, done):
        """lookOptions(appid): STONE IMAGE looks of one game and the chosen one."""
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.look_options(appid))

    def m_game_setLook(self, args, done):
        """setLook(appid, key|null)."""
        if len(args) != 2 or not (args[1] is None or isinstance(args[1], str)):
            return done(None, "InvalidValue", "arguments")
        appid, _ = self._game_args(args[:1], 1, 1)
        self._opt_call(done, lambda: self.optimized.set_look(appid, args[1]))

    def m_components(self, args, done):
        """components(kind?): without kind, what is downloaded; with kind, download the newest official release."""
        if not args:
            return self._opt_call(done, self.optimized.components)
        if len(args) != 1 or args[0] not in ("helixsr", "optiscaler"):
            return done(None, "InvalidValue", "component")
        self._opt_call(done, lambda: self.optimized.fetch_component(args[0]))

    def m_game_installPlan(self, args, done):
        """installPlan(appid, kind): what installing would do (nothing is changed)."""
        if len(args) != 2 or args[1] not in ("helixsr", "optiscaler"):
            return done(None, "InvalidValue", "arguments")
        appid, _ = self._game_args(args[:1], 1, 1)
        self._opt_call(done, lambda: self.optimized.install_plan(appid, args[1]))

    def m_game_install(self, args, done):
        """install(appid): OptiScaler into the game (only after installPlan said ok)."""
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.install_image(appid, "optiscaler"))

    def m_game_uninstallImage(self, args, done):
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.uninstall_image(appid))

    # ---- Steam's settings, inside STONE (stone_home/steamsettings.py) -----------------------
    def _steamset(self):
        if getattr(self, "_ss", None) is None:
            host = self

            class Cef:                                    # always the host's current Steam interface (a fake in tests)
                def ui_value(self, e):
                    return host.steam_ui.ui_value(e)

                def probe(self):
                    return host.steam_ui.probe()
            self._ss = steamsettings.SteamSettings(Cef())
        return self._ss

    def m_steam_settings(self, args, done):
        """steam.settings(refresh?): every setting this Steam offers that STONE may show, with its value."""
        refresh = bool(args and args[0] is True)
        self._opt_call(done, lambda: self._steamset().read(refresh))

    def m_steam_setSetting(self, args, done):
        """steam.setSetting(id, true|false): change one true/false setting that is in the catalog."""
        if len(args) != 2 or not isinstance(args[0], str) or not isinstance(args[1], bool) or len(args[0]) > 120:
            return done(None, "InvalidValue", "arguments")

        def work():
            try:
                return self._steamset().set_bool(args[0], args[1])
            except ValueError as e:
                raise games_schema.ProfileError(str(e)) from e
        self._opt_call(done, work)

    def m_game_optimizeStatus(self, args, done):
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.optimize_status(appid))

    def m_game_optimizeStart(self, args, done):
        """Launch the next measurement of the matrix (the person plays or runs the game's benchmark, then quits)."""
        appid, _ = self._game_args(args, 1, 1)
        if appid not in self.games:
            return done(None, "InvalidValue", "unknown game")
        if self.optimized.status().get("active"):
            return done(None, "InvalidValue", "a game is already being optimized")

        def launch():
            if self.game_policy() == "native":
                self._apply_env([appid])
            r = self.optimized.launch(appid, measure={"config": "next", "delay": 90, "duration": 120})
            return {k: r.get(k) for k in ("ok", "error", "settings", "config")} if not r.get("ok") else \
                {"ok": True, "settings": r.get("settings"), "summary": games_opt.summary(r["config"])}
        self._opt_call(done, launch)

    def m_game_status(self, args, done):
        """getOptimizationStatus()"""
        self._opt_call(done, self.optimized.status)

    def m_game_restoreRecommended(self, args, done):
        """restoreRecommended(appid)"""
        appid, _ = self._game_args(args, 1, 1)
        self._opt_call(done, lambda: self.optimized.restore_recommended(appid))

    # ---- display -------------------------------------------------------------------------
    def m_display_status(self, args, done):
        """STONE DISPLAY for the interface (no Linux access from the page). args: [fresh?]"""
        fresh = bool(args and args[0] is True)

        def work():
            try:
                res = (frontend_display(self.display.status(fresh=fresh)), None, "")
            except Exception as e:  # noqa: BLE001
                res = (None, "HardwareError", f"display: {e!r}")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_display_gamePolicy(self, args, done):
        """0: games see the display's resolution (Native), 1: Steam's default."""
        if len(args) != 1 or args[0] not in (0, 1):
            return done(None, "InvalidValue", "policy")
        prefs = system.load_prefs()
        prefs["game_res"] = args[0]
        system.save_prefs(prefs)
        self.display.invalidate()

        def work():
            if args[0] == 1:
                self.game_env.restore_default()
                r = self.game_env.restore()
            else:
                self.game_env.ensure_default(self._env_state)
                r = self.game_env.apply(list(self.games) + list(shortcuts.shortcut_appids(self.root())))
            GLib.idle_add(lambda: (done({"ok": r.get("error") is None, "changed": len(r.get("changed", [])),
                                          "error": r.get("error")}), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_display_goal(self, args, done):
        """0: fluid (the highest resolution at 60 Hz or more the link carries), 1: the highest resolution at any refresh."""
        if len(args) != 1 or args[0] not in (0, 1):
            return done(None, "InvalidValue", "goal")
        prefs = system.load_prefs()
        prefs["display_goal"] = "max_res" if args[0] else "fluid"
        system.save_prefs(prefs)
        self.display.invalidate()

        def work():
            r = {"error": None}
            if prefs.get("game_res", 0) == 0:
                self.game_env.ensure_default(self._env_state)
            GLib.idle_add(lambda: (done({"ok": True, "goal": prefs["display_goal"], "error": r["error"]}), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_openSteam(self, args, done):
        if len(args) != 1 or args[0] not in system.STEAM_URLS:
            return done(None, "InvalidValue", "unknown target")
        page = {"downloads": "Downloads"}.get(args[0])
        url = system.STEAM_URLS[args[0]]
        call = (lambda: self.steam_ui.open_page(page)) if page else (lambda: "cef: not used")
        self._in_steam_ui(call, lambda: self.sys.open_url(url), done)

    def m_steam_dialog(self, args, done):
        """steam.dialog(): the question Steam is asking now (steamcef.dialog), or {"dialog": null}."""
        def work():
            try:
                d = self.steam_ui.dialog()
            except Exception as e:  # noqa: BLE001  (Steam's interface not there: nothing asked)
                print(f"[stone] steam dialog: not read ({e!r})", flush=True)
                d = None
            GLib.idle_add(lambda: (done({"dialog": d}), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_steam_dialogAnswer(self, args, done):
        """steam.dialogAnswer(index, label): press that button of Steam's dialog."""
        if len(args) != 2 or not isinstance(args[0], int) or isinstance(args[0], bool) or not 0 <= args[0] < 4 \
                or not isinstance(args[1], str) or not 0 < len(args[1]) <= 40:
            return done(None, "InvalidValue", "dialog button")
        index, label = args

        def work():
            try:
                r = self.steam_ui.answer_dialog(index, label)
            except Exception as e:  # noqa: BLE001
                r = f"error: {e!r}"
            print(f"[stone] steam dialog: answered {label!r}: {r}", flush=True)
            GLib.idle_add(lambda: (done({"ok": r == "ok", "result": r}), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_openSteamSettings(self, args, done):
        if len(args) != 1 or args[0] not in steamcef.SETTINGS_SECTIONS:
            return done(None, "InvalidValue", "unknown settings section")
        section = args[0]
        self._in_steam_ui(lambda: self.steam_ui.open_settings(section), None, done)

    def m_restart(self, args, done):
        """Restart STONE Home (a new drawing mode applies at start)."""
        if self.restart is None:
            return done(None, "Unsupported", "restart not available")
        done({"ok": True})
        GLib.timeout_add(300, lambda: (self.restart(), False)[1])

    def art_path(self, appid, kind):
        if isinstance(kind, str) and kind.startswith("shot"):
            return media.path(self.root(), appid, kind)          # STONE MEDIA: a screenshot
        # Steam's own cache first; else what STONE fetched for games Steam has not shown (artcache.py)
        return library.art_path(self.root(), appid, kind) or artcache.have(appid, kind)

    # ---- Steam's own interface in front of STONE Home (D-34) ---------------------------------
    def _focus(self):
        if self.session_focus is None:
            from . import gamescope_x11
            self.session_focus = gamescope_x11.Focus()
        return self.session_focus

    def _steam_url(self, url):
        try:
            self.sys.open_url(url)
            return True
        except (OSError, ValueError) as e:
            print(f"[stone] steam: {url} not sent ({e})", flush=True)
            return False

    def m_steam_show(self, args, done):
        """steam.show(what[, appid]): Steam's own interface in front. "login": its sign-in window;
        "store": its store; "app": a game's store page (to buy it). In the STONE session the
        supervisor shows Steam's window and gives the screen back (guide button, Steam closing it,
        a game starting): a "steam" event says when. Passwords and payments are typed into Steam,
        never into STONE."""
        what = args[0] if args else None
        if what not in SHOW_WHAT or len(args) != (2 if what == "app" else 1) or \
                (what == "app" and not library.valid_appid(args[1])):
            return done(None, "InvalidValue", "what to show")
        url = None if what == "login" else system.STEAM_URLS["store"] if what == "store" else f"steam://store/{args[1]}"
        if os.environ.get("STONE_SESSION") != "stone":
            # Inside Steam's own Game Mode (or in development) Steam shows its pages by itself.
            if url:
                self._steam_url(url)
            return done({"managed": False, "sent": bool(url)})
        try:
            from . import supervisor
            self._focus().set_steam_value(supervisor.STEAM_ON if what == "login" else supervisor.STEAM_ON_BIG)
        except Exception as e:  # noqa: BLE001  (no Xlib or display)
            self.session_focus = None
            return done(None, "Unsupported", f"gamescope focus: {e}")
        self.front = {"what": what, "url": url, "since": time.monotonic(), "sent": url is None, "shown": None,
                      "big": what != "login", "had_account": library.account_id(self.root()) is not None, "signed": None}
        if what != "login":
            self._steam_url(system.FRONT_URLS["bigpicture"])     # the interface made for a controller
        print(f"[stone] steam: its own window asked in front ({what})", flush=True)
        if self.front_timer is None:
            self.front_timer = GLib.timeout_add(FRONT_POLL_MS, self._front_tick)
        done({"managed": True})

    def m_steam_hide(self, args, done):
        """steam.hide(): STONE Home back in front (the guide button, seen by the page)."""
        if self.front is None:
            return done({"managed": False})
        try:
            self._focus().set_steam_value(0)
        except Exception as e:  # noqa: BLE001
            return done(None, "Unsupported", f"gamescope focus: {e}")
        done({"managed": True})

    def _front_tick(self):
        fr = self.front
        if fr is None:
            self.front_timer = None
            return False
        try:
            value = self.session_focus.steam_value()
            window = self.session_focus.shown()[1]
        except Exception as e:  # noqa: BLE001  (the display is gone: nothing is in front any more)
            print(f"[stone] steam: front state not read ({e!r})", flush=True)
            value, window = 0, 0
        now = time.monotonic()
        if value not in (1, 3):
            return self._front_end("nowindow" if value == 2 else "closed")
        if window and fr["shown"] is None:
            fr["shown"] = now
            self.emit("steam", {"front": True, "shown": True, "what": fr["what"]})
        if not fr["sent"] and ((fr["shown"] is not None and now - fr["shown"] >= FRONT_URL_SETTLE_S)
                               or now - fr["since"] >= FRONT_URL_WAIT_S):
            fr["sent"] = True
            self._steam_url(fr["url"])
        if fr["what"] == "login" and not fr["had_account"]:
            # The sign-in is done when the account's folder exists: STONE takes the screen back by
            # itself (Steam may open its main window then, which is not for a controller).
            if fr["signed"] is None and library.account_id(self.root()) is not None:
                fr["signed"] = now
            if fr["signed"] is not None and now - fr["signed"] >= 3:
                try:
                    self.session_focus.set_steam_value(0)
                except Exception:  # noqa: BLE001
                    pass
                return self._front_end("signed")
        return True

    def _front_end(self, why):
        fr, self.front, self.front_timer = self.front, None, None
        if fr["big"]:
            self._steam_url(system.FRONT_URLS["bigpicture_close"])   # Steam back to a hidden component
        self._lib_kick()                                              # a purchase or a sign-in shows up soon
        print(f"[stone] steam: its own window left the front ({why})", flush=True)
        self.emit("steam", {"front": False, "why": why, "what": fr["what"]})
        return False

    def m_steam_full(self, args, done):
        """steam.full(why): plan B of D-34. Steam's own Game Mode interface takes the whole session
        (the supervisor stops STONE Home and brings it back: after the sign-in, when the guide
        button is held, or when Steam ends). why: "login" | "store"."""
        if len(args) != 1 or args[0] not in ("login", "store"):
            return done(None, "InvalidValue", "why")
        if os.environ.get("STONE_SESSION") != "stone":
            return done(None, "Unsupported", "only in the STONE session")
        try:
            if self.request_session is not None:
                self.request_session(args[0])
            else:
                from . import supervisor
                supervisor.write_request(args[0])
        except (OSError, ValueError) as e:
            return done(None, "HardwareError", str(e))
        print(f"[stone] steam: its Game Mode interface asked to take the session ({args[0]})", flush=True)
        done({"ok": True})

    def m_steam_status(self, args, done):
        """steam.status(): what STONE knows about Steam now, for the console's own diagnosis."""
        root = self.root()

        def work():
            reach = getattr(self.steam_ui, "reachable", None)
            try:
                cef = bool(reach()) if reach else None
            except Exception:  # noqa: BLE001
                cef = None
            last = self.lib_last[1] if self.lib_last else {}
            res = {"session": os.environ.get("STONE_SESSION") or "other", "interface": cef,
                   "account": library.account_id(root) is not None, "logged": last.get("logged"),
                   "owned_known": bool(last.get("owned_known")), "owned_cached": bool(last.get("owned_cached")),
                   "front": self.front is not None, "root_found": os.path.isdir(os.path.join(root, "steamapps"))}
            GLib.idle_add(lambda: (done(res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_media_screenshots(self, args, done):
        """media.screenshots(appid?): Steam's screenshots, newest first (served as art kind shot<N>)."""
        appid = args[0] if args else "0"
        if not isinstance(appid, str) or not appid.isdigit() or len(appid) > 10:
            return done(None, "InvalidValue", "appid")
        root = self.root()

        def work():
            try:
                res = ({"shots": media.screenshots(root, appid)}, None, "")
            except OSError as e:
                res = (None, "HardwareError", f"media: {e!r}")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    # ---- system --------------------------------------------------------------------------
    def m_power(self, args, done):
        if len(args) != 1:
            return done(None, "InvalidValue", "action")
        self.sys.power(args[0], done)

    def m_systemInfo(self, args, done):
        self.sys.info(done)

    def m_session_info(self, args, done):
        """session.info(): which session STONE Home runs in, at once (systemInfo also reads the
        image's versions, which takes longer than Home's first frame should wait)."""
        done({"session": os.environ.get("STONE_SESSION") or "other"})

    # ---- STONE session (M24): the game back in front after the guide button -----------------
    def m_session_resume(self, args, done):
        """REANUDAR in the STONE session: Home lets the running game in front again (guide.py)."""
        if os.environ.get("STONE_SESSION") != "stone":
            return done({"managed": False})
        try:
            if self.session_focus is None:
                from . import gamescope_x11
                self.session_focus = gamescope_x11.Focus()
            self.session_focus.set_home_front(False)
        except Exception as e:  # noqa: BLE001  (no Xlib or display: the supervisor keeps Home in front)
            self.session_focus = None
            return done(None, "Unsupported", f"gamescope focus: {e}")
        done({"managed": True})

    def m_session_desktop(self, args, done):
        """Escritorio (M15): `stone-session switch desktop`, which asks polkit and logs out."""
        if os.environ.get("STONE_SESSION") != "stone":
            return done(None, "Unsupported", "only in the STONE session")

        def work():
            try:
                r = subprocess.run(self.session_switch + ["desktop"], capture_output=True, text=True, timeout=90)
                res = ({"ok": True}, None, "") if r.returncode == 0 else (None, "PermissionDenied", r.stdout.strip() or r.stderr.strip())
            except (OSError, subprocess.SubprocessError) as e:
                res = (None, "Unsupported", str(e))
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    # ---- 40 CU from STONE Home (M04): the page confirms, pkexec + polkit allow these lines only --
    CU40_OPS = {"enable": ["enable", "--yes"], "disable": ["disable", "--yes"], "test": ["test", "--minutes", "3"]}

    def m_gpu_cu40(self, args, done):
        if len(args) != 1 or args[0] not in self.CU40_OPS:
            return done(None, "InvalidValue", "operation")
        argv = self.cu40_cmd + self.CU40_OPS[args[0]]

        def work():
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=600)
                text = (r.stdout + r.stderr).strip()
                res = ({"ok": r.returncode == 0, "code": r.returncode, "text": text[-2000:]}, None, "")
                if r.returncode in (126, 127):              # pkexec: refused or dismissed
                    res = (None, "PermissionDenied", text[-500:] or "refused")
            except (OSError, subprocess.SubprocessError) as e:
                res = (None, "Unsupported", str(e))
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    # ---- STONE CONNECT and SETTINGS (M12, M16): Bluetooth, audio, network (connect.py) -----------
    CONNECT = {
        "bt.devices": (lambda: connect.bt_devices(), 0),
        "bt.scan": (lambda: connect.bt_scan(), 0),
        "bt.action": (lambda a, mac: connect.bt_action(a, mac), 2),
        "audio.status": (lambda: connect.audio_status(), 0),
        "audio.default": (lambda i: connect.audio_default(i), 1),
        "audio.volume": (lambda v: connect.audio_volume(v), 1),
        "net.status": (lambda: connect.net_status(), 0),
        "net.wifiList": (lambda: connect.wifi_list(), 0),
        "net.wifiConnect": (lambda ssid, pw: connect.wifi_connect(ssid, pw), 2),
        "net.wifiDisconnect": (lambda dev: connect.wifi_disconnect(dev), 1),
    }

    def _connect(self, name, args, done):
        fn, n = self.CONNECT[name]
        if len(args) != n:
            return done(None, "InvalidValue", "arguments")

        def work():
            try:
                r = fn(*args)
                res = (r, None, "") if "error" not in r else (None, "Unsupported", r["error"])
            except Exception as e:  # noqa: BLE001  (a tool that misbehaves is reported, never fatal)
                res = (None, "HardwareError", f"{name}: {e!r}")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def __getattr__(self, attr):
        if attr.startswith("m_"):
            name = attr[2:].replace("_", ".", 1)
            if name in Host.CONNECT:
                return lambda args, done: self._connect(name, args, done)
        raise AttributeError(attr)

    # ---- Boot options from STONE Home (M02): the boot menu is not reachable with a controller ----
    def m_boot_rollback(self, args, done):
        """Next boot: the previous image (bootc rollback through pkexec; polkit allows this line only)."""
        argv = self.rollback_cmd

        def work():
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
                text = (r.stdout + r.stderr).strip()
                if r.returncode in (126, 127):
                    res = (None, "PermissionDenied", text[-300:] or "refused")
                elif r.returncode != 0:
                    res = (None, "Unsupported", text[-300:] or f"bootc rollback: {r.returncode}")
                else:
                    res = ({"ok": True, "text": text[-500:]}, None, "")
            except (OSError, subprocess.SubprocessError) as e:
                res = (None, "Unsupported", str(e))
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    # ---- STONE EMULATION (M14): the person's games for other consoles (roms.py) ---------------
    def _bg(self, done, fn, what):
        def work():
            try:
                res = (fn(), None, "")
            except Exception as e:  # noqa: BLE001
                res = (None, "HardwareError", f"{what}: {e!r}")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_roms_scan(self, args, done):
        self._bg(done, roms.scan, "roms")

    def m_roms_folders(self, args, done):
        self._bg(done, lambda: {"base": roms.folders()}, "roms")

    def m_roms_add(self, args, done):
        self._bg(done, lambda: roms.add_to_library(steam_ui=self.steam_ui), "roms")

    # ---- Steam's store read by STONE (M13, D-34): search, the shop window, a game's page ---------
    def _store_row(self, row):
        """One game of the store for the page: what STONE knows about it, its picture queued."""
        appid = row["appid"]
        self.store_seen.add(appid)
        if row.get("free"):
            self.store_free.add(appid)
        self.art.want(appid, ("header",), {"header": row.pop("_header", None)})
        row["have"] = "installed" if appid in self.games else "owned" if appid in self.owned else None
        row["art"] = artcache.have(appid, "header") is not None or library.art_path(self.root(), appid, "header") is not None
        return row

    def m_store_search(self, args, done):
        if len(args) != 1 or not isinstance(args[0], str):
            return done(None, "InvalidValue", "term")

        def work():
            r = store.search(args[0])
            res = (None, "Unsupported", r["error"]) if "error" in r else (r, None, "")
            GLib.idle_add(lambda: (self._store_done(res, done), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def _store_done(self, res, done):
        r = res[0]
        if r is not None:
            for row in r.get("results") or []:
                self._store_row(row)
            for sec in r.get("sections") or []:
                for row in sec["items"]:
                    self._store_row(row)
            if "name" in r:
                self._store_row(r)
        done(*res)

    def m_store_featured(self, args, done):
        """store.featured(): the store's own lists (offers, top sellers, new, coming soon)."""
        kept = self.store_window
        if kept is not None and time.monotonic() - kept[0] < STORE_FRESH_S:
            return self._store_done((_copy(kept[1]), None, ""), done)

        def work():
            r = store.featured()
            if "error" in r:
                res = (None, "Unsupported", r["error"])
            else:
                self.store_window = (time.monotonic(), _copy(r))
                res = (r, None, "")
            GLib.idle_add(lambda: (self._store_done(res, done), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_store_details(self, args, done):
        """store.details(appid): a game's page (name, text, price, genres) and where to buy it."""
        if len(args) != 1 or not library.valid_appid(args[0]):
            return done(None, "InvalidValue", "appid")
        appid = args[0]

        def work():
            r = store.details(appid)
            if "error" in r:
                res = (None, "Unsupported", r["error"])
            else:
                r["url"] = store.page_url(appid)
                res = (r, None, "")
            GLib.idle_add(lambda: (self._details_done(appid, res, done), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def _details_done(self, appid, res, done):
        if res[0] is not None:
            self.store_seen.add(appid)
            self.art.want(appid, ("hero",), first=True)
        self._store_done(res, done)

    # ---- STONE STORAGE and DOWNLOADS (M20, M13) ---------------------------------------------
    def m_storage_status(self, args, done):
        root = self.root()

        def work():
            try:
                res = (storage.status(root), None, "")
            except Exception as e:  # noqa: BLE001
                res = (None, "HardwareError", f"storage: {e!r}")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_storage_clearShaderCache(self, args, done):
        if len(args) != 1 or not isinstance(args[0], str):
            return done(None, "InvalidValue", "appid")
        r = storage.clear_shader_cache(self.root(), args[0])
        done(r) if "error" not in r else done(None, "InvalidValue", r["error"])

    def m_storage_uninstall(self, args, done):
        """Uninstall an installed game (STONE Home asked first): through Steam's interface without its
        dialog, else Steam's uninstall URL (Steam then asks in its own dialog)."""
        if len(args) != 1 or not isinstance(args[0], str) or not args[0].isdigit() or not 0 < len(args[0]) <= 10:
            return done(None, "InvalidValue", "appid")
        appid = int(args[0])
        self._in_steam_ui(lambda: self.steam_ui.uninstall(appid), lambda: self.sys.open_url(f"steam://uninstall/{appid}"), done)

    # ---- STONE HEALTH (M19) ---------------------------------------------------------------
    def m_health_status(self, args, done):
        def work():
            try:
                snap = health.snapshot()
                res = ({"snapshot": snap, "checks": [list(c) for c in health.doctor(snap)]}, None, "")
            except Exception as e:  # noqa: BLE001  (a reading that fails is reported, never fatal)
                res = (None, "HardwareError", f"health: {e!r}")
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    # ---- boot metrics (M02) and FIRST RUN (M22) -----------------------------------------
    def m_boot_mark(self, args, done):
        if len(args) != 1 or args[0] not in bootmetrics.STAGES:
            return done(None, "InvalidValue", "stage")
        stage = args[0]

        def work():
            try:
                res = (bootmetrics.mark(stage, release=system.read_release(), analyze=bootmetrics.systemd_analyze), None, "")
            except OSError as e:
                res = (None, "HardwareError", str(e))
            GLib.idle_add(lambda: (done(*res), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def m_boot_history(self, args, done):
        done(bootmetrics.history()[-10:])

    def m_firstrun_status(self, args, done):
        done(firstrun.status(self.root()))

    def m_firstrun_complete(self, args, done):
        try:
            done(firstrun.complete(system.read_release().get("STONE_VERSION")))
        except OSError as e:
            done(None, "HardwareError", str(e))

    def m_prefs_get(self, args, done):
        done(system.load_prefs())

    def m_prefs_set(self, args, done):
        if len(args) != 1 or not isinstance(args[0], dict):
            return done(None, "InvalidValue", "prefs")
        try:
            done(system.save_prefs(args[0]))
        except OSError as e:
            done(None, "HardwareError", str(e))

    def m_selftest(self, args, done):
        if self.selftest is None:
            return done(None, "InvalidValue", "not in self-test mode")
        done({"ok": True})
        self.selftest(args[0] if args else None)


def _copy(d):
    """A deep copy of plain JSON data (what the store answered is kept and given out many times)."""
    if isinstance(d, dict):
        return {k: _copy(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_copy(v) for v in d]
    return d


class _SteamUIProxy:
    """STONE DISPLAY reaches Steam through the host's current Steam interface (a fake in tests)."""

    def __init__(self, host):
        self.host = host

    def ui_value(self, expression):
        fn = getattr(self.host.steam_ui, "ui_value", None)
        return fn(expression) if fn else None

    def __getattr__(self, name):
        # ui_values (per-page answers and errors) only where the Steam interface offers it
        if name == "ui_values" and hasattr(self.host.steam_ui, "ui_values"):
            return self.host.steam_ui.ui_values
        raise AttributeError(name)

    def run_game(self, game_id):
        return self.host.steam_ui.run_game(game_id)


def frontend_display(snap):
    """What the interface needs to show the display (STONE Home never reads Linux itself)."""
    p = snap.get("primary") or {}
    nat, out = p.get("native_resolution"), snap.get("output")
    rates = p.get("refresh_rates") or []
    return {
        "connected": bool(p), "name": p.get("display_name"), "connection": p.get("connection_type"),
        "connector": p.get("connector"), "native": nat, "output": out, "preferred": snap.get("preferred_mode"),
        "max_hz": max(rates) if rates else None, "rates": rates,
        "vrr": {"supported": p.get("vrr_supported"), "range": p.get("vrr_range"), "active": p.get("vrr_active")},
        "hdr": {"supported": p.get("hdr_supported"), "active": p.get("hdr_active")},
        "game_env": snap.get("game_environment"), "steam_default": snap.get("steam_game_default"),
        "policy": snap.get("game_policy"), "safe": snap.get("safe_display_mode"),
        "steam": snap.get("steam_available"), "steam_error": snap.get("steam_error"), "findings": snap.get("findings", []),
        "link": snap.get("link"), "goal": snap.get("goal"),
    }


STATUS_TEXT = {"UNKNOWN": "Sin datos", "AUTO_GENERATED": "Medido en esta consola", "RECOMMENDED": "Recomendado por STONE",
               "USER_MODIFIED": "Tu configuración", "HARDWARE_VERIFIED": "Verificado en esta consola"}


def frontend_recommended(r):
    """What the page shows next to JUGAR (nothing it could not show honestly)."""
    return {"mode": r["mode"], "label": "STONE RECOMMENDED" if r["mode"] == "recommended" else r["mode"].upper(),
            "summary": games_opt.summary(r["config"]), "why": r["why"], "settings": r["settings"],
            "status": r["status"], "status_text": STATUS_TEXT.get(r["status"], r["status"]),
            "target": r["target"], "output": r["output"], "internal": r["internal"], "trail": r["trail"],
            "stale": r["stale"]}


def frontend_profile(p):
    return {"id": p["id"], "appid": p["appid"], "name": p["name"], "status": p["status"], "layers": p["layers"],
            "errors": p["errors"], "db_version": p["db_version"], "game": p["game"],
            "availability": p["availability"], "stale": p["stale"], "targets": p["targets"],
            "measurements": len(p["measurements"]),
            "next_measurement": games_opt.summary(p["next_measurement"]) if p["next_measurement"] else None,
            "anti_cheat": p["facts"]["anti_cheat"], "injected": (p["facts"]["injected"] or {}).get("kind")}
