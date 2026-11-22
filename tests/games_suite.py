"""STONE OPTIMIZED: game profiles, STONE GRAPHICS, metrics, STONE EXPERIENCE SCORE and the
optimizer's launch / exit / crash flows, against a fake Steam (folder + interface), a fake stoned
and fake game processes. Mocks live only in this file, never in production.

    python3 tests/games_suite.py [name-filter...]
"""

import json
import os
import random
import re
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BUILTIN = os.path.join(REPO, "modules", "games", "game-profiles")
os.environ["STONE_GAME_PROFILES"] = BUILTIN
os.environ["STONE_DETECT_CACHE_S"] = "0"          # tests change game folders between calls; G29 tests the cache
sys.path[0:0] = [os.path.join(REPO, p) for p in ("services/stoned", "apps/stone-home", "modules/display", "modules/games")]

from stone_games import detect, graphics, metrics, optimizer, schema, score, store  # noqa: E402

TESTS = []
CP = "1091500"


def test(fn):
    TESTS.append(fn)
    return fn


# ---------------------------------------------------------------- the fake world
class World:
    """A Steam folder with Cyberpunk 2077 (and an unknown game), Steam's interface for launch
    options, stoned, the game's process and a clock. Everything in a temporary folder."""

    def __init__(self, injected=None, proxy="winmm", anti_cheat=False, hz=60, vrr=False, display=True,
                 validated=1850, user_options=""):
        self.d = tempfile.mkdtemp(prefix="stone-games-")
        self.old_env = {k: os.environ.get(k) for k in ("XDG_STATE_HOME", "XDG_DATA_HOME")}
        os.environ["XDG_STATE_HOME"] = os.path.join(self.d, "state")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.d, "data")
        self.root = os.path.join(self.d, "Steam")
        self.game_dir = os.path.join(self.root, "steamapps", "common", "Cyberpunk 2077")
        os.makedirs(os.path.join(self.game_dir, "bin", "x64"))
        self.write_manifest(CP, "Cyberpunk 2077", "Cyberpunk 2077", build="19000000")
        self.write_manifest("4242", "Juego Desconocido", "Juego Desconocido", build="7")
        os.makedirs(os.path.join(self.root, "steamapps", "common", "Juego Desconocido"))
        os.makedirs(os.path.join(self.root, "config"))
        self.set_proton("proton_9")
        if injected:
            self.install(injected, proxy)
        if anti_cheat:
            os.makedirs(os.path.join(self.game_dir, "EasyAntiCheat"))
        self.options = {CP: user_options, "4242": ""}
        self.cef_up = True
        self.set_calls = []
        self.perf = FakePerf(validated)
        self.now = 1_800_000_000.0
        self.hz, self.vrr, self.has_display = hz, vrr, display
        self.launched = []
        self.e = optimizer.Engine(root=lambda: self.root, cef=self, display=self.display, perf=self.perf,
                                  watch=self, clock=lambda: self.now, log=lambda m: None)

    def close(self):
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.d, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # Steam folder
    def write_manifest(self, appid, name, installdir, build):
        p = os.path.join(self.root, "steamapps", f"appmanifest_{appid}.acf")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(f'"AppState"\n{{\n\t"appid"\t"{appid}"\n\t"name"\t"{name}"\n\t"StateFlags"\t"4"\n'
                    f'\t"installdir"\t"{installdir}"\n\t"buildid"\t"{build}"\n}}\n')

    def set_proton(self, name):
        with open(os.path.join(self.root, "config", "config.vdf"), "w") as f:
            f.write(f'"InstallConfigStore"\n{{ "Software" {{ "Valve" {{ "Steam" {{ "CompatToolMapping" {{\n'
                    f'\t"{CP}" {{ "name" "{name}" "config" "" "priority" "250" }}\n}} }} }} }} }}\n')

    def install(self, kind, proxy):
        x64 = os.path.join(self.game_dir, "bin", "x64")
        with open(os.path.join(x64, "OptiScaler.ini"), "w") as f:
            f.write("[Upscalers]\n")
        with open(os.path.join(x64, f"{proxy}.dll"), "wb") as f:
            f.write(b"MZ" + bytes(100))
        if kind == "helixsr":
            os.makedirs(os.path.join(x64, "HelixSR"), exist_ok=True)
            with open(os.path.join(x64, "HelixSR", "helixsr.dll"), "wb") as f:
                f.write(b"MZ" + bytes(200))

    # Steam's interface (cef.ui_value / run_game)
    def ui_value(self, expr):
        if not self.cef_up:
            return None
        m = re.search(r"RegisterForAppDetails\((\d+),", expr)
        if m:
            return json.dumps({"options": self.options.get(m.group(1), "")})
        m = re.search(r"SetAppLaunchOptions\((\d+),(\".*\")\);", expr)
        if m:
            self.options[m.group(1)] = json.loads(m.group(2))
            self.set_calls.append((m.group(1), self.options[m.group(1)]))
            return json.dumps({"ok": True})
        return None

    def owned_games(self):
        return None

    def run_game(self, gid):
        self.launched.append(gid)
        return "cef[SharedJSContext]: ok"

    # STONE DISPLAY
    def display(self):
        if not self.has_display:
            return {"primary": None, "output": None}
        return {"primary": {"native_resolution": {"w": 3840, "h": 2160, "hz": self.hz}, "vrr_supported": self.vrr,
                            "vrr_range": {"min": 48, "max": self.hz} if self.vrr else None, "vrr_active": self.vrr,
                            "hdr_supported": False, "hdr_active": False, "modes": [{}] * 12},
                "output": {"w": 3840, "h": 2160, "hz": self.hz}}

    # game process (watch)
    def running(self, appid):  # the watch interface
        return appid in self.running_set

    @property
    def running_set(self):
        return self.__dict__.setdefault("_run", set())

    def play(self, appid, seconds, log=None):
        """The game starts, runs `seconds` and ends; MangoHud writes `log` (frametimes) if given."""
        self.running_set.add(appid)
        self.now += 5
        assert self.e.tick() == "started"
        self.now += seconds
        if log is not None:
            s = self.e._session()
            if s and s.get("measure"):
                write_log(os.path.join(s["measure"]["folder"], f"Cyberpunk2077_{int(self.now)}.csv"), *log)
        self.running_set.discard(appid)
        return self.e.tick()


class FakePerf:
    def __init__(self, validated=1850):
        self.validated = validated
        self.calls = []
        self.refuse = set()
        self.per_game = {}
        self.safe_mode = False

    def state(self):
        return {"profile": "balanced", "safe_mode": self.safe_mode, "per_game": dict(self.per_game),
                "range": {"validated_max": self.validated}, "profiles": {"silent": {}, "balanced": {}, "performance": {}}}

    def capabilities(self):
        return {"driver": "amdgpu", "governor": True, "cu40": {"active": True}}

    def set_game_profile(self, appid, pid):
        self.calls.append((appid, pid))
        if pid in self.refuse:
            return False, "InvalidValue: not validated"
        if pid == "global":
            self.per_game.pop(appid, None)
        else:
            self.per_game[appid] = pid
        return True, None


def write_log(path, fps=60.0, jitter=0.0, seconds=90, clock=1500, gpu_t=70, cpu_t=72, stutter_every=0):
    rnd = random.Random(7)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["os,cpu,gpu,ram,kernel,driver,cpuscheduler", "Bazzite,AMD BC-250,Cyan Skillfish,16GB,6.17,Mesa,",
             "fps,frametime,cpu_load,gpu_load,cpu_temp,gpu_temp,gpu_core_clock,gpu_mem_clock,gpu_power,elapsed"]
    t, n = 0.0, 0
    while t < seconds:
        ft = 1000.0 / fps * (1 + rnd.uniform(-jitter, jitter))
        if stutter_every and n % stutter_every == stutter_every - 1:
            ft *= 4
        t += ft / 1000
        n += 1
        lines.append(f"{1000 / ft:.1f},{ft:.3f},40,99,{cpu_t},{gpu_t},{clock},1750,95,{int(t * 1e9)}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def measured(w, cfg_path, preset, fps, clock=1500, jitter=0.02, perf="balanced", gpu_t=70):
    """One complete measurement launch of the given configuration."""
    c = optimizer._cfg(cfg_path, preset, perf=perf)
    r = w.e.launch(CP, measure={"config": c, "delay": 30, "duration": 90})
    assert r["ok"], r
    return w.play(CP, 200, log=(fps, jitter, 90, clock, gpu_t))


# ---------------------------------------------------------------- tests
@test
def G01_profile_loading_layers_and_database_version():
    with World():
        p = store.load(CP)
        assert p["status"] == "UNKNOWN" and p["source"] == "builtin" and p["db_version"] == 1 and p["errors"] == []
        assert p["game"]["anti_cheat"] is False and "fsr" in p["game"]["native_upscalers"] and len(p["candidates"]) == 8
        assert p["modes"]["recommended"]["graphics"]["path"] == "game_upscaler"
        # user > auto > built-in, per field
        auto = dict(schema.empty_profile(CP, "Cyberpunk 2077"), source="auto", status="AUTO_GENERATED")
        auto["modes"] = {"recommended": optimizer._cfg("native")}
        store.write_layer("auto", auto)
        user = dict(schema.empty_profile(CP), status="USER_MODIFIED")
        user["modes"] = {"custom": optimizer._cfg("game_upscaler", "balanced")}
        store.write_layer("user", user)
        p = store.load(CP)
        assert p["status"] == "USER_MODIFIED" and p["layers"] == ["auto", "builtin", "user"]
        assert p["modes"]["recommended"]["graphics"]["path"] == "native" and "custom" in p["modes"]
        assert p["game"]["native_upscalers"]                 # facts survive from the built-in layer
        # a broken file is ignored and reported, never trusted
        with open(os.path.join(store.data_dir(), "user", f"{CP}.json"), "w") as f:
            f.write("{not json")
        p = store.load(CP)
        assert p["status"] == "AUTO_GENERATED" and p["errors"] and "user" in p["errors"][0]


@test
def G02_profile_validation():
    ok = optimizer._cfg("helixsr", "quality")
    assert ok["graphics"]["internal"] == {"strategy": "upscaled", "scale": 0.667}
    bad = [{"graphics": {"path": "dlss"}}, {"graphics": {"path": "native", "internal": {"strategy": "native", "scale": 0.1}}},
           {"frame_target": {"fps": 1000}}, {"frame_target": {"fps": True}}, {"graphics": {"frame_generation": "yes"}},
           {"performance": {"profile": "overclock"}}, {"gamescope": {"scaling_filter": "magic"}}, "x"]
    for b in bad:
        try:
            schema.clean_config(b)
            raise AssertionError(b)
        except schema.ProfileError:
            pass
    for raw, src in (({"schema": 2, "appid": "1"}, "builtin"), ({"schema": 1, "appid": "x1"}, "builtin"),
                     ({"schema": 1, "appid": "1", "status": "HARDWARE_VERIFIED"}, "builtin"),
                     ({"schema": 1, "appid": "1", "status": "STONE_VERIFIED"}, "auto")):
        try:
            schema.clean_profile(raw, src)
            raise AssertionError(raw)
        except schema.ProfileError:
            pass
    # every built-in profile passes the run-time rules
    for f in os.listdir(os.path.join(BUILTIN, "steam")):
        with open(os.path.join(BUILTIN, "steam", f)) as fh:
            schema.clean_profile(json.load(fh), "builtin")


@test
def G03_detection_from_disk():
    with World(injected="helixsr", proxy="winmm") as w:
        f = detect.facts(w.root, CP)
        assert f["installed"] and f["build"] == "19000000" and f["proton"] == "proton_9" and f["anti_cheat"] == []
        assert f["injected"]["kind"] == "helixsr" and f["injected"]["proxy"] == "winmm" and f["injected"]["fingerprint"]
        fp = f["injected"]["fingerprint"]
        with open(os.path.join(w.game_dir, "bin", "x64", "HelixSR", "helixsr.dll"), "ab") as fh:
            fh.write(b"new version")                          # HelixSR updated -> new fingerprint
        assert detect.facts(w.root, CP)["injected"]["fingerprint"] != fp
        assert detect.facts(w.root, "777")["installed"] is False
    with World(injected="optiscaler", proxy="dxgi", anti_cheat=True) as w:
        f = detect.facts(w.root, CP)
        assert f["injected"]["kind"] == "optiscaler" and f["injected"]["proxy"] == "dxgi" and f["anti_cheat"] == ["EasyAntiCheat"]


@test
def G04_graphics_availability_and_helixsr_unavailable():
    game = store.load(CP)["game"]
    with World(injected="helixsr", proxy="winmm") as w:
        a = graphics.availability(game, detect.facts(w.root, CP))
        assert all(a[k]["available"] for k in ("native", "game_upscaler", "helixsr")) and not a["optiscaler"]["available"]
        assert a["gamescope"]["guidance_only"]
        assert graphics.env_for(optimizer._cfg("helixsr", "quality"), detect.facts(w.root, CP))["WINEDLLOVERRIDES"] == "winmm=n,b"
        assert graphics.env_for(optimizer._cfg("native"), detect.facts(w.root, CP)) == {}
        a = graphics.availability(game, detect.facts(w.root, CP), 'WINEDLLOVERRIDES="winmm=n,b" %command%')
        assert not a["native"]["available"] and "launch options" in a["native"]["reason"]
    with World() as w:                                        # HELIXSR UNAVAILABLE: not installed
        a = graphics.availability(game, detect.facts(w.root, CP))
        assert not a["helixsr"]["available"] and a["helixsr"]["reason"] == "not installed in the game folder"
        p = w.e.profile(CP)
        rec = w.e.recommended(CP, p=p)
        assert rec["config"]["graphics"]["path"] == "game_upscaler"
        assert all(c["graphics"]["path"] != "helixsr" for c in optimizer.matrix(p, p["availability"]))
    with World(injected="helixsr", proxy="dxgi") as w:       # always loaded: no clean native path
        a = graphics.availability(game, detect.facts(w.root, CP))
        assert not a["native"]["available"] and not a["game_upscaler"]["available"] and a["helixsr"]["available"]
        assert "winmm" in a["native"]["reason"]


@test
def G05_anti_cheat_and_online_safe_path():
    game = store.load(CP)["game"]
    with World(injected="helixsr", anti_cheat=True) as w:
        p = w.e.profile(CP)
        assert not p["availability"]["helixsr"]["available"] and "anti-cheat" in p["availability"]["helixsr"]["reason"]
        assert p["availability"]["game_upscaler"]["available"]
        rec = w.e.recommended(CP, p=p)
        assert rec["config"]["graphics"]["path"] == "game_upscaler"
        # even a person's CUSTOM HelixSR configuration is not injected into an anti-cheat game
        w.e.apply(CP, "custom", optimizer._cfg("helixsr", "quality"))
        r = w.e.launch(CP, "custom")
        assert r["ok"] and r["config"]["graphics"]["path"] == "game_upscaler"
        assert "WINEDLLOVERRIDES" not in w.options[CP]
    online = dict(game, online_only=True, anti_cheat=None)
    with World(injected="optiscaler") as w:
        assert not graphics.availability(online, detect.facts(w.root, CP))["optiscaler"]["available"]


@test
def G06_launch_options_kept_restored_and_recovered():
    assert graphics.compose("gamemoderun %command% -skipStartScreen", {"WINEDLLOVERRIDES": "winmm=n,b"}) == \
        "WINEDLLOVERRIDES=winmm=n,b gamemoderun %command% -skipStartScreen"
    assert graphics.compose("-skipStartScreen", {"DXVK_FRAME_RATE": "40"}) == "DXVK_FRAME_RATE=40 %command% -skipStartScreen"
    assert graphics.compose("DXVK_FRAME_RATE=30 %command%", {"DXVK_FRAME_RATE": "40"}) == "DXVK_FRAME_RATE=30 %command%"
    with World(injected="helixsr", user_options="-skipStartScreen") as w:
        r = w.e.launch(CP, measure={"config": optimizer._cfg("helixsr", "quality"), "delay": 30, "duration": 90})
        assert r["ok"] and r["graphics_applied"] and w.launched == [int(CP)]
        assert w.options[CP].startswith("WINEDLLOVERRIDES=winmm=n,b MANGOHUD=1") and w.options[CP].endswith("%command% -skipStartScreen")
        # STONE Home dies with the game running; at the next start the game is gone: recovered
        w.running_set.add(CP)
        assert w.e.tick() == "started"
        w.running_set.discard(CP)
        e2 = optimizer.Engine(root=lambda: w.root, cef=w, display=w.display, perf=w.perf, watch=w, clock=lambda: w.now, log=lambda m: None)
        out = e2.recover()
        assert out["session"]["reason"] == "exit" or out["session"]["abnormal"] in (True, False)
        assert w.options[CP] == "-skipStartScreen" and e2.status() == {"active": False}
        assert w.perf.per_game == {}
        # the person edits the options while the game runs: theirs are kept
        r = w.e.launch(CP, measure={"config": optimizer._cfg("helixsr", "balanced"), "delay": 30, "duration": 90})
        w.options[CP] = "PROTON_LOG=1 %command%"
        w.running_set.add(CP)
        w.e.tick()
        w.running_set.discard(CP)
        w.now += 300
        assert w.e.tick()["graphics_restored"] == "kept (changed by the person)" and w.options[CP] == "PROTON_LOG=1 %command%"
        # Steam's interface not answering: the game launches as the person left it
        w.cef_up = False
        r = w.e.prepare(CP)
        assert r["ok"] and r["graphics_applied"] is False and w.options[CP] == "PROTON_LOG=1 %command%"


@test
def G07_metrics_and_score():
    d = tempfile.mkdtemp()
    try:
        write_log(os.path.join(d, "steady.csv"), fps=60, jitter=0.02)
        write_log(os.path.join(d, "stutter.csv"), fps=60, jitter=0.25, stutter_every=50)
        write_log(os.path.join(d, "short.csv"), fps=60, seconds=10)
        with open(os.path.join(d, "broken.csv"), "w") as f:
            f.write("garbage\n1,2,3\n")
        a, b = metrics.summarize(os.path.join(d, "steady.csv")), metrics.summarize(os.path.join(d, "stutter.csv"))
        assert 58 < a["avg_fps"] < 62 and a["low1_fps"] > 55 and a["frametime_cv"] < 0.03 and a["stutters"] == 0
        assert a["gpu_clock_avg"] == 1500 and a["gpu_temp_max"] == 70 and a["power_reliable"] is False
        assert b["low1_fps"] < 30 and b["stutters"] > 50 and b["frametime_cv"] > a["frametime_cv"]
        assert "too little" in metrics.summarize(os.path.join(d, "short.csv"))["error"]
        assert "frametime" in metrics.summarize(os.path.join(d, "broken.csv"))["error"]
        cfg = optimizer._cfg("game_upscaler", "quality")
        sa, sb = score.score(a, cfg, "recommended", 60), score.score(b, cfg, "recommended", 60)
        assert sa["score"] > 80 and sb["score"] < sa["score"] - 15          # not reduced to average FPS
        assert score.score(a, cfg, "recommended", 60, crashed=True)["score"] == 0
        assert score.score({"error": "x"}, cfg, "recommended", 60)["score"] is None
        hot = dict(a, gpu_temp_max=91)
        assert score.score(hot, cfg, "recommended", 60)["gate"] == "too hot"
        slow = dict(a, avg_fps=25, low1_fps=20)
        assert score.score(slow, cfg, "recommended", 60)["score"] <= 40
        # QUALITY values the image more than PERFORMANCE does
        nat = optimizer._cfg("native")
        assert score.quality_prior(nat) > score.quality_prior(cfg) > score.quality_prior(optimizer._cfg("game_upscaler", "performance"))
        assert score.WEIGHTS["quality"]["Q"] > score.WEIGHTS["recommended"]["Q"] > score.WEIGHTS["performance"]["Q"]
        assert all(sum(w.values()) == 100 for w in score.WEIGHTS.values())
        assert metrics.mangohud_env("/x", 60, 120)["MANGOHUD_CONFIG"] == "no_display,log_interval=0,output_folder=/x,autostart_log=60,log_duration=120"
    finally:
        shutil.rmtree(d)


@test
def G08_display_changes_and_unknown_display():
    t60 = score.targets(optimizer.display_input({"primary": {"native_resolution": {"w": 3840, "h": 2160}}, "output": {"w": 3840, "h": 2160, "hz": 60}}))
    assert t60["targets"] == {"performance": 60, "recommended": 60, "quality": 30, "custom": 60}
    with World(hz=120, vrr=True) as w:
        p = w.e.profile(CP)
        assert p["targets"]["targets"]["quality"] == 48 and p["targets"]["vrr"]       # no rigid 60
        assert p["targets"]["targets"]["performance"] == 90
        measured(w, "game_upscaler", "quality", 75)
        assert w.e.profile(CP)["stale"] == []
        rec = w.e.recommended(CP)
        assert rec["why"].startswith("measured") and rec["config"]["frame_target"]["fps"] is not None
        w.hz, w.vrr = 60, False                             # another TV: measurements no longer apply
        p = w.e.profile(CP)
        assert p["stale"] == ["display"] and w.e.recommended(CP, p=p)["why"].startswith("STONE profile database")
    with World(display=False) as w:                          # UNKNOWN DISPLAY
        p = w.e.profile(CP)
        assert p["display"]["known"] is False and p["targets"]["targets"]["recommended"] == 60
        assert p["environment"]["display"] == "unknown"
        r = w.e.launch(CP)
        assert r["ok"] and w.launched == [int(CP)] and w.e.recommended(CP)["internal"] is None


@test
def G09_game_exit_saves_metrics_restores_performance_cleans_graphics():
    with World(injected="helixsr") as w:
        nxt = w.e.profile(CP)["next_measurement"]
        assert nxt["graphics"]["path"] == "native"           # matrix order: built-in reference first
        res = measured(w, "helixsr", "quality", 62, clock=1600)
        assert res["reason"] == "exit" and not res["abnormal"] and res["metrics"]["avg_fps"] > 60
        assert res["performance_restored"] is True and res["graphics_restored"] == "restored"
        assert w.options[CP] == "" and w.perf.per_game == {} and (CP, "balanced") in w.perf.calls
        auto, _ = store.read_layer("auto", CP)
        assert auto["status"] == "AUTO_GENERATED" and len(auto["measurements"]) == 1
        m = auto["measurements"][0]
        assert m["internal"] == {"w": 2561, "h": 1441, "expected": True} and m["output"] == {"w": 3840, "h": 2160}
        assert m["score"]["recommended"]["score"] is not None
        p = store.load(CP)
        assert p["status"] == "AUTO_GENERATED" and p["modes"]["recommended"]["graphics"]["path"] == "helixsr"
        # LOAD PROFILE -> VERIFY -> PLAY: a normal launch uses it, no new benchmark
        r = w.e.launch(CP)
        assert r["ok"] and r["measure"] is None and "WINEDLLOVERRIDES=winmm=n,b" in w.options[CP] and "MANGOHUD" not in w.options[CP]
        assert r["config"]["frame_target"]["fps"] == 60 and "DXVK_FRAME_RATE=60" in w.options[CP]
        res = w.play(CP, 1800)
        assert not res["abnormal"] and "metrics" not in res and w.options[CP] == ""


@test
def G10_game_crash_graphics_rollback_and_suspect():
    with World(injected="helixsr") as w:
        measured(w, "helixsr", "quality", 62)
        measured(w, "game_upscaler", "quality", 55)
        assert w.e.recommended(CP)["config"]["graphics"]["path"] == "helixsr"
        w.e.launch(CP)
        res = w.play(CP, 20)                                 # GAME CRASH: gone after 20 s
        assert res["abnormal"] and res["collected"]["config"]["graphics"]["path"] == "helixsr"
        assert w.options[CP] == "" and w.perf.per_game == {}
        rec = w.e.recommended(CP)                            # SAFE NEXT LAUNCH: HelixSR -> game FSR, clean
        assert rec["config"]["graphics"]["path"] == "game_upscaler" and rec["trail"]
        r = w.e.launch(CP)
        assert "WINEDLLOVERRIDES" not in w.options[CP]
        w.play(CP, 900)                                      # the safe launch ends normally
        assert w.e.recommended(CP)["config"]["graphics"]["path"] == "helixsr"    # back to the normal choice
        w.e.launch(CP)
        w.play(CP, 10)                                       # second crash: SUSPECT
        p = w.e.profile(CP)
        assert optimizer.suspect(p, optimizer._cfg("helixsr", "quality"))
        w.e.launch(CP)
        w.play(CP, 900)
        assert w.e.recommended(CP)["config"]["graphics"]["path"] == "game_upscaler"     # stays out
        assert all(not (c["graphics"]["path"] == "helixsr" and c["graphics"]["upscaler_preset"] == "quality")
                   for c in [optimizer.next_candidate(p, p["availability"], p["environment"])] if c)
        assert r["ok"]


@test
def G11_performance_rollback_independent_of_graphics():
    with World() as w:
        measured(w, "game_upscaler", "quality", 50, clock=1500)
        measured(w, "game_upscaler", "quality", 60, clock=1840, perf="performance")
        rec = w.e.recommended(CP)
        assert rec["config"]["performance"]["profile"] == "performance"
        r = w.e.launch(CP)
        assert w.perf.per_game == {CP: "performance"} and r["performance"] == "performance"
        res = w.play(CP, 15)                                 # crash on PERFORMANCE
        assert res["abnormal"] and w.perf.per_game == {}
        rec = w.e.recommended(CP)
        assert rec["config"]["performance"]["profile"] == "balanced"            # performance falls back...
        assert rec["config"]["graphics"]["path"] == "game_upscaler"             # ...graphics untouched (no injection to blame)
        # stoned refuses PERFORMANCE (not validated after a new calibration): BALANCED
        w.e.launch(CP)
        w.play(CP, 900)
        w.perf.refuse.add("performance")
        r = w.e.launch(CP)
        assert r["performance"] == "balanced"
        w.play(CP, 900)
        # a per-game profile the person chose in STONE Performance is kept and never cleared
        w.perf.refuse.clear()
        w.perf.per_game[CP] = "silent"
        r = w.e.launch(CP)
        assert r["performance"] == "silent"
        w.play(CP, 900)
        assert w.perf.per_game == {CP: "silent"}
        # stoned in Safe Mode: STONE does not ask for any profile
        w.perf.per_game.clear()
        w.perf.safe_mode = True
        n = len(w.perf.calls)
        w.e.launch(CP)
        w.play(CP, 900)
        assert len(w.perf.calls) == n


@test
def G12_performance_capability_change_invalidates():
    with World() as w:
        measured(w, "game_upscaler", "quality", 60)
        assert w.e.recommended(CP)["why"].startswith("measured")
        w.perf.validated = 2000                              # new calibration
        p = w.e.profile(CP)
        assert "calibration" in p["stale"] and not w.e.recommended(CP, p=p)["why"].startswith("measured")
        assert p["next_measurement"] is not None
        w.perf.validated = 1850
        w.set_proton("proton_10")                            # Proton changed
        assert "proton" in w.e.profile(CP)["stale"]
        w.set_proton("proton_9")
        w.write_manifest(CP, "Cyberpunk 2077", "Cyberpunk 2077", build="19500000")   # game updated
        assert "game_build" in w.e.profile(CP)["stale"]
        # a measurement under the new environment replaces the old ones
        measured(w, "game_upscaler", "balanced", 66)
        auto, _ = store.read_layer("auto", CP)
        assert len(auto["measurements"]) == 1 and auto["invalidation"]["game_build"] == "19500000"


@test
def G13_unknown_game_changes_nothing():
    with World() as w:
        p = w.e.profile("4242")
        assert p["status"] == "UNKNOWN" and p["layers"] == [] and p["game"]["native_upscalers"] == []
        rec = w.e.recommended("4242", p=p)
        assert rec["config"]["graphics"]["path"] == "native" and rec["why"].startswith("safe")
        r = w.e.launch("4242")
        assert r["ok"] and w.options["4242"] == "" and w.set_calls == [] and w.perf.calls == []
        assert w.launched == [4242]
        res = w.play("4242", 600)
        assert res["graphics_restored"] == "nothing"
        nothing = w.e.profile("777")                          # not even installed
        assert nothing["facts"]["installed"] is False and w.e.recommended("777", p=nothing)["config"]["graphics"]["path"] == "native"


@test
def G14_efficiency_and_helixsr_preference_never_forced():
    with World(injected="helixsr") as w:
        measured(w, "game_upscaler", "quality", 60, clock=1840, perf="performance")
        measured(w, "game_upscaler", "quality", 60, clock=1600)
        rec = w.e.recommended(CP)["config"]
        assert rec["performance"]["profile"] == "balanced"   # same experience, lower clock: EFFICIENCY
        measured(w, "helixsr", "quality", 60, clock=1600)
        assert w.e.recommended(CP)["config"]["graphics"]["path"] == "helixsr"   # equal: HelixSR preferred
    with World(injected="helixsr") as w:
        measured(w, "game_upscaler", "quality", 60, clock=1600)
        measured(w, "helixsr", "quality", 45, clock=1600, )
        assert w.e.recommended(CP)["config"]["graphics"]["path"] == "game_upscaler"   # worse: never forced
        assert w.e.recommended(CP, "quality")["config"]["graphics"]["path"] in ("game_upscaler", "helixsr")


@test
def G15_hardware_verified_only_from_the_person():
    with World() as w:
        try:
            w.e.verify(CP)                                  # nothing measured: refused
            raise AssertionError("verified without data")
        except schema.ProfileError:
            pass
        measured(w, "game_upscaler", "quality", 60)
        assert w.e.verify(CP)["status"] == "HARDWARE_VERIFIED" and store.load(CP)["status"] == "HARDWARE_VERIFIED"
        measured(w, "game_upscaler", "balanced", 64)           # new data: the verification was of the old
        assert store.load(CP)["status"] == "AUTO_GENERATED"
        ex = json.dumps(store.read_layer("auto", CP)[0])
        assert "STONE_VERIFIED" not in ex


@test
def G16_modes_custom_and_restore_recommended():
    with World(injected="helixsr") as w:
        modes = {m["mode"]: m for m in w.e.modes(CP)}
        assert modes["recommended"]["default"] and modes["custom"]["available"] is False
        w.e.apply(CP, "custom", {"graphics": {"path": "helixsr", "upscaler_preset": "balanced",
                                              "internal": {"strategy": "upscaled", "scale": 0.588}},
                                 "performance": {"profile": "silent"}, "frame_target": {"fps": 40}})
        w.e.apply(CP, "custom")
        assert w.e.chosen_mode(CP) == "custom" and store.load(CP)["status"] == "USER_MODIFIED"
        r = w.e.launch(CP)
        assert r["config"]["graphics"]["path"] == "helixsr" and "DXVK_FRAME_RATE=40" in w.options[CP] and r["performance"] == "silent"
        w.play(CP, 900)
        assert w.e.restore_recommended(CP)["removed_user_profile"] and w.e.chosen_mode(CP) == "recommended"
        assert store.load(CP)["status"] == "UNKNOWN"
        assert w.e.status() == {"active": False}


@test
def G17_stage_two_tries_performance_ranges_of_the_best():
    with World() as w:
        p = w.e.profile(CP)
        rows = optimizer.matrix(p, p["availability"])
        assert [c["graphics"]["path"] for c in rows] == ["native", "game_upscaler", "game_upscaler", "game_upscaler"]
        assert all(not c["graphics"]["frame_generation"] and c["performance"]["profile"] == "balanced" for c in rows)
        for c, fps in zip(rows, (24, 50, 58, 64), strict=True):
            r = w.e.launch(CP, measure={"config": c, "delay": 30, "duration": 90})
            assert r["ok"]
            w.play(CP, 200, log=(fps, 0.02, 90, 1500, 70))
        p = w.e.profile(CP)
        nxt = p["next_measurement"]
        assert nxt is not None and nxt["performance"]["profile"] in ("silent", "performance")
        s2 = optimizer.stage2(p, p["availability"], p["environment"])
        assert len(s2) == 4 and {c["performance"]["profile"] for c in s2} == {"silent", "performance"}


@test
def G18_host_api_game_to_recommended_to_play():
    from gi.repository import GLib

    from stone_home import host as host_mod
    from stone_home import system

    class Stoned:
        def __init__(self, perf):
            self.perf = perf

        def call(self, method, args, done):
            if method == "getState":
                return done(self.perf.state())
            if method == "getCapabilities":
                return done(self.perf.capabilities())
            if method == "setGameProfile":
                ok, err = self.perf.set_game_profile(*args)
                return done({"ok": True}) if ok else done(None, "InvalidValue", err)
            done(None, "InvalidValue", "unknown")

    def run(h, method, *args):
        box, loop = {}, GLib.MainLoop()

        def done(result=None, code=None, message=""):
            box["r"] = (result, code)
            loop.quit()
        GLib.idle_add(lambda: (h.handle({"method": method, "args": list(args)}, done), False)[1])
        GLib.timeout_add_seconds(10, loop.quit)
        loop.run()
        return box.get("r")

    with World(injected="helixsr") as w:
        old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(w.d, "config")
        try:
            h = host_mod.Host(lambda *a: None, stoned=Stoned(w.perf), sysapi=system.System(spawn=lambda u: None), steam_root=w.root)
            h.steam_ui = w
            h.display.status = lambda fresh=False: w.display()
            h.optimized.clock = lambda: w.now
            h.optimized.watch = w
            r, code = run(h, "game.recommended", CP)
            assert code is None and r["label"] == "STONE RECOMMENDED" and r["status"] == "UNKNOWN", r
            assert r["summary"].startswith("FSR del juego Calidad") and r["output"] == {"w": 3840, "h": 2160}
            assert run(h, "game.recommended", CP, "turbo")[1] == "InvalidValue"
            assert run(h, "game.recommended", "1; rm")[1] == "InvalidValue"
            r, code = run(h, "game.profile", CP)
            assert code is None and r["availability"]["helixsr"]["available"] and r["injected"] == "helixsr"
            r, code = run(h, "game.modes", CP)
            assert code is None and r["chosen"] == "recommended" and [m["mode"] for m in r["modes"]][0] == "recommended"
            assert run(h, "game.apply", CP, "custom")[1] == "InvalidValue"          # custom needs a configuration
            assert run(h, "game.status")[0] == {"active": False}
            # JUGAR: the library scan, then launch -> prepare (graphics + performance) -> Steam
            run(h, "library")
            r, code = run(h, "launch", CP)
            assert code is None and r["via"] == "steam-ui" and w.launched == [int(CP)]
            st, _ = run(h, "game.status")
            assert st["active"] and st["appid"] == CP and st["graphics_applied"]
            assert w.options[CP] == ""                    # built-in starting point: nothing injected
            w.play(CP, 600)
            assert run(h, "game.status")[0] == {"active": False}
            # prefs: STONE OPTIMIZED can be turned off; JUGAR then launches untouched
            system.save_prefs(dict(system.load_prefs(), optimized=0))
            run(h, "launch", CP)
            assert not os.path.exists(h.optimized.session_path)
            assert run(h, "game.restoreRecommended", CP)[0]["ok"]
        finally:
            if old is None:
                os.environ.pop("XDG_CONFIG_HOME", None)
            else:
                os.environ["XDG_CONFIG_HOME"] = old


@test
def G19_image_choice_is_explicit_available_only_and_reversible():
    with World(injected="helixsr") as w:
        o = w.e.image_options(CP)
        keys = {c["key"]: c for c in o["choices"]}
        assert o["mode"] == "recommended" and keys["auto"]["selected"] and keys["helixsr"]["available"], o
        assert "optiscaler" not in keys                         # not installed: not listed
        r = w.e.set_image(CP, "helixsr", "balanced")
        assert r["mode"] == "custom"
        g = w.e.recommended(CP, "custom")["config"]["graphics"]
        assert g["path"] == "helixsr" and g["upscaler_preset"] == "balanced" and g["internal"]["strategy"] == "upscaled", g
        assert {c["key"]: c for c in w.e.image_options(CP)["choices"]}["helixsr"]["selected"]
        w.e.set_image(CP, "native")
        g = w.e.recommended(CP, "custom")["config"]["graphics"]
        assert g["path"] == "native" and g["upscaler_preset"] is None and g["internal"]["scale"] == 1.0, g
        w.e.set_image(CP, "gamescope", "performance")
        assert w.e.recommended(CP, "custom")["config"]["gamescope"]["scaling_filter"] == "fsr"
        for bad in (("banana", None), ("game_upscaler", "turbo")):
            try:
                w.e.set_image(CP, *bad)
                raise AssertionError(bad)
            except schema.ProfileError:
                pass
        assert w.e.set_image(CP, "auto")["mode"] == "recommended" and w.e.chosen_mode(CP) == "recommended"
    with World(injected=None) as w:                              # HelixSR not installed: refused, not faked
        keys = {c["key"] for c in w.e.image_options(CP)["choices"]}
        assert "helixsr" not in keys, keys
        try:
            w.e.set_image(CP, "helixsr")
            raise AssertionError("helixsr without install")
        except schema.ProfileError as e:
            assert "not installed" in str(e), e


def _release_zip(files):
    import io
    import zipfile
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, data in files.items():
            z.writestr(n, data)
    return b.getvalue()


def _fake_net(kind, files, tag="v9.9.9", name=None, digest=True, bad_digest=False):
    import hashlib
    blob = _release_zip(files)
    name = name or ("HelixSR-9.9.9.zip" if kind == "helixsr" else "OptiScaler_9.9.9.zip")
    sha = hashlib.sha256(blob).hexdigest()

    def get_json(url):
        assert url.startswith("https://api.github.com/repos/"), url
        a = {"name": name, "browser_download_url": f"https://github.com/x/y/releases/download/{tag}/{name}", "size": len(blob)}
        if digest:
            a["digest"] = "sha256:" + ("0" * 64 if bad_digest else sha)
        return {"tag_name": tag, "prerelease": False, "assets": [{"name": "notes.txt"}, a]}

    def download(url, dest):
        with open(dest, "wb") as f:
            f.write(blob)
        return sha, len(blob)
    return get_json, download


@test
def G20_components_download_verify_install_uninstall():
    from stone_games import install
    opti = {"OptiScaler/OptiScaler.dll": b"MZ" + bytes(50), "OptiScaler/OptiScaler.ini": "[Upscalers]\n",
            "OptiScaler/D3D12_Optiscaler/D3D12Core.dll": b"MZ",
            "OptiScaler/setup_linux.sh": "#!/bin/sh\n", "OptiScaler/setup_windows.bat": "@echo off\n",
            "OptiScaler/!! README_EXTRACT ALL FILES TO GAME FOLDER !!.txt": "x"}      # the release's own installer: not copied
    with World() as w:
        gdir = os.path.join(w.game_dir, "bin", "x64")
        with open(os.path.join(gdir, "Cyberpunk2077.exe"), "wb") as f:
            f.write(bytes(5000))
        with open(os.path.join(w.game_dir, "REDlauncher.exe"), "wb") as f:
            f.write(bytes(9000))                                    # a launcher is not the game
        # nothing downloaded yet: the plan says so and changes nothing
        r = w.e.install_plan(CP, "optiscaler")
        assert not r["ok"] and r["needs_download"], r
        # a wrong checksum is refused and nothing is kept
        gj, dl = _fake_net("optiscaler", opti, bad_digest=True)
        try:
            install.fetch("optiscaler", gj, dl)
            raise AssertionError("bad digest accepted")
        except install.InstallError as e:
            assert "SHA-256" in str(e)
        assert install.have("optiscaler") is None
        # only GitHub / its CDN hosts are ever contacted
        try:
            install._check_url("https://evil.example/x.zip")
            raise AssertionError("host allowed")
        except install.InstallError:
            pass
        gj, dl = _fake_net("optiscaler", opti)
        rec = install.fetch("optiscaler", gj, dl)
        assert rec["tag"] == "v9.9.9" and rec["verified_by_github"] and install.have("optiscaler")["tag"] == "v9.9.9"
        assert install.fetch("optiscaler", gj, dl).get("already")       # a second press downloads nothing
        # the plan names the real executable folder; nothing is written yet
        plan = w.e.install_plan(CP, "optiscaler")
        assert plan["ok"] and plan["exe"] == "Cyberpunk2077.exe" and plan["folder"].replace(os.sep, "/") == "bin/x64" and plan["files"] == 3, plan
        assert not os.path.exists(os.path.join(gdir, "winmm.dll"))
        r = w.e.install_image(CP)
        assert r["ok"], r
        assert os.path.isfile(os.path.join(gdir, "winmm.dll")) and os.path.isfile(os.path.join(gdir, "OptiScaler.ini"))
        assert os.path.isfile(os.path.join(gdir, "D3D12_Optiscaler", "D3D12Core.dll"))
        assert not os.path.exists(os.path.join(gdir, "OptiScaler.dll"))           # renamed to the proxy
        # STONE sees it like any installed OptiScaler and can switch it per launch
        keys = {c["key"]: c for c in w.e.image_options(CP)["choices"]}
        assert keys["optiscaler"]["available"], keys["optiscaler"]
        assert not w.e.install_plan(CP, "optiscaler")["ok"]                         # already installed
        u = w.e.uninstall_image(CP)
        assert u["ok"] and u["removed"] == 3
        assert not any(os.path.exists(os.path.join(gdir, n)) for n in ("setup_linux.sh", "setup_windows.bat"))
        assert not os.path.exists(os.path.join(gdir, "winmm.dll")) and not os.path.exists(os.path.join(gdir, "D3D12_Optiscaler"))
        assert os.path.isfile(os.path.join(gdir, "Cyberpunk2077.exe"))              # the game's own files untouched
        assert not w.e.uninstall_image(CP)["ok"]
        # the game's own upscaler libraries stay (Cyberpunk ships libxess*.dll); they are not copied over nor removed
        opti2 = dict(opti, **{"OptiScaler/libxess.dll": b"MZnew", "OptiScaler/libxess_fg.dll": b"MZnew"})
        gj2, dl2 = _fake_net("optiscaler", opti2, tag="v9.9.10")
        install.fetch("optiscaler", gj2, dl2)
        for n in ("libxess.dll", "libxess_fg.dll"):
            with open(os.path.join(gdir, n), "wb") as f:
                f.write(b"MZgame")
        plan = w.e.install_plan(CP, "optiscaler")
        assert plan["ok"] and plan["kept"] == ["libxess.dll", "libxess_fg.dll"] and plan["upscalers"] == ["libxess.dll"], plan
        assert w.e.install_image(CP)["ok"] and open(os.path.join(gdir, "libxess.dll"), "rb").read() == b"MZgame"
        assert w.e.uninstall_image(CP)["ok"] and open(os.path.join(gdir, "libxess_fg.dll"), "rb").read() == b"MZgame"
        for n in ("libxess.dll", "libxess_fg.dll"):
            os.remove(os.path.join(gdir, n))
        # never over existing files
        os.makedirs(os.path.join(gdir, "D3D12_Optiscaler"))
        with open(os.path.join(gdir, "D3D12_Optiscaler", "D3D12Core.dll"), "w") as f:
            f.write("mine")
        assert "already exist" in w.e.install_plan(CP, "optiscaler")["error"]
    with World(anti_cheat=True) as w:                                               # anti-cheat: refused
        gj, dl = _fake_net("optiscaler", opti)
        install.fetch("optiscaler", gj, dl)
        with open(os.path.join(w.game_dir, "bin", "x64", "g.exe"), "wb") as f:
            f.write(bytes(100))
        r = w.e.install_plan(CP, "optiscaler")
        assert not r["ok"] and "anti-cheat" in r["error"], r
        assert not w.e.install_image(CP)["ok"]


@test
def G21_helixsr_is_downloaded_and_the_person_runs_the_authors_installer():
    from stone_games import install
    with World() as w:
        assert not w.e.install_plan(CP, "helixsr")["ok"]
        gj, dl = _fake_net("helixsr", {"HelixSR-9.9.9/helixsr-setup.sh": "#!/bin/sh\n", "HelixSR-9.9.9/README.md": "x"})
        install.fetch("helixsr", gj, dl)
        r = w.e.install_plan(CP, "helixsr")
        assert r["ok"] and "./helixsr-setup.sh" in r["command"] and "--yes" in r["warning"], r
        assert "--yes" not in r["command"]
        sh = os.path.join(r["dir"], "helixsr-setup.sh")
        assert os.access(sh, os.X_OK)
        try:
            w.e.install_image(CP, "helixsr")                         # STONE never runs it for the person
            raise AssertionError("helixsr installed by STONE")
        except schema.ProfileError:
            pass
        # an archive that tries to write outside its folder is refused
        gj, dl = _fake_net("helixsr", {"../evil.sh": "x"}, tag="v9.9.10")
        try:
            install.fetch("helixsr", gj, dl)
            raise AssertionError("path traversal accepted")
        except (install.InstallError, ValueError, OSError):
            pass


@test
def G22_guided_optimization_counts_the_matrix_and_grows_with_installed_paths():
    with World() as w:
        o = w.e.optimize_status(CP)
        assert o["done"] == 0 and o["total"] >= 4 and o["next"] and o["status"] == "UNKNOWN", o
        r = w.e.launch(CP, measure={"config": "next", "delay": 30, "duration": 90})
        assert r["ok"]
        w.play(CP, 200, log=(50, 0.02, 90, 1500, 70))
        o2 = w.e.optimize_status(CP)
        assert o2["done"] == 1 and o2["measured"] == 1 and o2["total"] >= o["total"], o2
        assert o2["next"] != o["next"], (o, o2)
    with World(injected="helixsr") as w2:                       # HelixSR installed -> more rows to measure
        assert w2.e.optimize_status(CP)["total"] > o["total"]


@test
def G26_install_script_is_not_the_game_and_stone_never_keeps_its_own_options():
    """The console's report (15-11-2026): Steam's install script (reaper ... Install=1) was taken for the
    game, its end for a crash at 6 s, and Batman's look was turned off; and STONE's look variables stayed
    in the options as if they were the person's after a restore that could not reach Steam."""
    d = tempfile.mkdtemp(prefix="stone-proc-")
    old = os.environ.get("STONE_SYSFS_ROOT")
    try:
        p = os.path.join(d, "proc", "700")
        os.makedirs(p)
        with open(os.path.join(p, "cmdline"), "wb") as f:
            f.write(b"\0".join([b"/s/steamrt64/reaper", b"SteamLaunch", b"AppId=200260", b"Install=1", b"--", b"iscriptevaluator.exe"]) + b"\0")
        os.environ["STONE_SYSFS_ROOT"] = d
        assert optimizer.ProcWatch().running("200260") is False
        with open(os.path.join(p, "cmdline"), "wb") as f:
            f.write(b"\0".join([b"/s/steamrt64/reaper", b"SteamLaunch", b"AppId=200260", b"--", b"BatmanAC.exe"]) + b"\0")
        assert optimizer.ProcWatch().running("200260") is True
    finally:
        if old is None:
            os.environ.pop("STONE_SYSFS_ROOT", None)
        else:
            os.environ["STONE_SYSFS_ROOT"] = old
        shutil.rmtree(d, ignore_errors=True)
    with World(user_options="-nointro") as w:
        ov = w.e.ov
        assert ov.apply(CP, {"ENABLE_VKBASALT": "1", "STONE_LOOK": "cinema"}, "k")[0].startswith("ENABLE_VKBASALT=1")
        w.cef_up = False                                    # Steam does not answer: the record stays
        assert ov.restore(CP).startswith("error")
        w.cef_up = True
        new, err = ov.apply(CP, {"STONE_OPTIMIZED": "x"}, "k2")  # the next launch, look turned off
        assert err is None and "STONE_LOOK" not in new and "ENABLE_VKBASALT" not in new and new.endswith("-nointro"), new
        assert ov.restore(CP) == "restored" and w.options[CP] == "-nointro"
        # already leaked (no record at all): taken out at the next launch, the person's part kept
        w.options[CP] = "ENABLE_VKBASALT=1 VKBASALT_CONFIG_FILE=/h/.local/state/stone/looks/cinema.conf STONE_LOOK=cinema %command% -nointro"
        new, err = ov.apply(CP, {"DXVK_FRAME_RATE": "60", "STONE_OPTIMIZED": "y"}, "k3")
        assert "STONE_LOOK" not in new and "DXVK_FRAME_RATE=60" in new
        assert ov.restore(CP) == "restored" and w.options[CP] == "%command% -nointro"
        assert graphics.strip_stone("WINEDLLOVERRIDES=dxgi=n,b %command%") == "WINEDLLOVERRIDES=dxgi=n,b %command%"   # the person's own


@test
def G27_optiscaler_goes_next_to_the_game_never_in_an_installer_folder():
    """The console (15-11-2026): Batman: Arkham Asylum got OptiScaler in "redist" (the largest .exe there)."""
    from stone_games import install
    opti = {"OptiScaler/OptiScaler.dll": b"MZ" + bytes(50), "OptiScaler/OptiScaler.ini": "[Upscalers]\n"}
    with World() as w:
        redist = os.path.join(w.game_dir, "redist")
        os.makedirs(redist)
        with open(os.path.join(redist, "PhysX_9.09_SystemSoftware.exe"), "wb") as f:
            f.write(bytes(90000))
        with open(os.path.join(w.game_dir, "bin", "x64", "Cyberpunk2077.exe"), "wb") as f:
            f.write(bytes(5000))
        gj, dl = _fake_net("optiscaler", opti)
        install.fetch("optiscaler", gj, dl)
        plan = w.e.install_plan(CP, "optiscaler")
        assert plan["folder"].replace(os.sep, "/") == "bin/x64" and plan["no_upscaler"] and plan["upscalers"] == []
        with open(os.path.join(w.game_dir, "bin", "x64", "nvngx_dlss.dll"), "wb") as f:
            f.write(b"MZ")                                  # a game with DLSS: something to replace
        assert w.e.install_plan(CP, "optiscaler")["upscalers"] == ["nvngx_dlss.dll"]
        os.remove(os.path.join(w.game_dir, "bin", "x64", "nvngx_dlss.dll"))
        # an install left by rc9 in "redist" is taken out at the next start, and can be done again
        os.makedirs(install.installs_dir(), exist_ok=True)
        with open(os.path.join(redist, "winmm.dll"), "wb") as f:
            f.write(b"MZ")
        with open(os.path.join(install.installs_dir(), f"{CP}.json"), "w") as f:
            json.dump({"appid": CP, "kind": "optiscaler", "tag": "v9.9.9", "exe_dir": redist, "files": ["winmm.dll"]}, f)
        assert install.misplaced() == [CP]
        out = w.e.recover()
        assert out["misplaced_optiscaler"] == {CP: 1} and not os.path.exists(os.path.join(redist, "winmm.dll"))
        assert install.misplaced() == [] and w.e.install_plan(CP, "optiscaler")["ok"]


@test
def G28_cancelled_launch_and_probe_again_after_the_launcher():
    """The console's report (19-11-2026, 23:22): a launch option cancelled by the person showed as
    "Steam no llegó a abrir" three minutes later; Cyberpunk was probed on its launcher (no Vulkan yet)."""
    with World() as w:
        rows = []
        w.e.events = lambda kind, **d: rows.append(dict(d, kind=kind))
        w.e.prepare(CP)
        assert w.e.cancel(CP) is True
        w.now += 3
        res = w.e.tick()
        assert res["reason"] == "cancelled" and not res["abnormal"] and w.e._session() is None
        assert [e["reason"] for e in rows if e["kind"] == "game_end"] == ["cancelled"]
        # probe: on the launcher at 25 s, in the game at 60 s: only the second is recorded
        seen = iter([{"processes": 14, "vulkan_loaded": False, "vkbasalt_loaded": False},
                     {"processes": 24, "vulkan_loaded": True, "vkbasalt_loaded": True}])
        w.e.probe = lambda appid: next(seen)
        w.e.prepare(CP)
        w.running_set.add(CP)
        w.now += 5
        assert w.e.tick() == "started"
        w.now += optimizer.PROBE_AFTER_S + 1
        w.e.tick()
        assert not [e for e in rows if e["kind"] == "game_effects"]
        w.now += optimizer.PROBE_AGAIN_S[0]
        w.e.tick()
        eff = [e for e in rows if e["kind"] == "game_effects"]
        assert len(eff) == 1 and eff[0]["vulkan_loaded"] is True
        w.now += 600
        w.e.tick()
        assert len([e for e in rows if e["kind"] == "game_effects"]) == 1     # never again once in the game
        w.running_set.discard(CP)
        assert w.e.tick()["reason"] == "exit"


@test
def G29_folder_scan_kept_between_launches_and_forgotten_when_stone_installs():
    """rc12: the walk of the game folder is not repeated for every launch and game page."""
    with World() as w:
        calls = []
        real = detect.scan_folder
        detect.scan_folder = lambda folder: (calls.append(folder), real(folder))[1]
        old = detect.CACHE_S, detect.NO_INJECT_S
        detect.CACHE_S, detect.NO_INJECT_S = 120, 30
        try:
            detect.forget()
            for _ in range(3):
                detect.facts(w.root, CP)
            assert len(calls) == 1
            detect.forget(CP)
            detect.facts(w.root, CP)
            assert len(calls) == 2
            w.write_manifest(CP, "Cyberpunk 2077", "Cyberpunk 2077", build="19000001")   # a new build: looked at again
            detect.facts(w.root, CP)
            assert len(calls) == 3
            detect.NO_INJECT_S = 0                   # nothing injected: looked at again soon (an author's installer)
            detect.facts(w.root, CP)
            assert len(calls) == 4
        finally:
            detect.scan_folder = real
            detect.CACHE_S, detect.NO_INJECT_S = old
            detect.forget()



@test
def G30_scaling_one_choice_installs_optiscaler_and_checks_it_really_loaded():
    """3.1.0-rc15 (owner, 22-11-2026: "una manera fácil e intuitiva" and "asegurar que funcionen")."""
    from stone_games import install, scaling
    opti = {"OptiScaler/OptiScaler.dll": b"MZ" + bytes(50), "OptiScaler/OptiScaler.ini": "[Upscalers]\n[FrameGen]\nFGType=nofg\n"}
    with World() as w:
        gdir = os.path.join(w.game_dir, "bin", "x64")
        with open(os.path.join(gdir, "Cyberpunk2077.exe"), "wb") as f:
            f.write(bytes(5000))
        loaded = [True]
        w.e = optimizer.Engine(root=lambda: w.root, cef=w, display=w.display, perf=w.perf, watch=w, clock=lambda: w.now,
                               log=lambda m: None, probe=lambda a: {"processes": 4, "vulkan_loaded": True, "env": {}},
                               injected_probe=lambda a, files: loaded[0] and all(f.endswith("winmm.dll") for f in files))
        sc = w.e.scaling(CP)
        keys = {u["key"]: u for u in sc["upscalers"]}
        assert sc["upscaler"] == "auto" and keys["auto"]["selected"] and sc["framegen"] == "off", sc
        assert keys["optiscaler"]["state"] == "install" and keys["helixsr"]["state"] == "install", (keys["optiscaler"], keys["helixsr"])
        assert keys["helixsr"]["prepare"] and "NVIDIA" in keys["helixsr"]["reason"] and not keys["optiscaler"]["prepare"]
        assert [p["key"] for p in sc["presets"]] == ["quality", "balanced", "performance", "ultra_performance"]
        # choosing FSR 3.1 downloads (the author's release, checked) and installs it: nothing by hand
        gj, dl = _fake_net("optiscaler", opti)
        real_fetch = install.fetch
        install.fetch = lambda kind, log=None: real_fetch(kind, gj, dl)
        try:
            r = w.e.set_scaling(CP, "optiscaler", "balanced")
        finally:
            install.fetch = real_fetch
        assert r["ok"] and "instalado" in r["note"] and os.path.isfile(os.path.join(gdir, "winmm.dll")), r
        sc = r["scaling"]
        assert sc["upscaler"] == "optiscaler" and sc["preset"] == "balanced" and sc["preset_applies"], sc
        assert "Equilibrado" in sc["summary"]
        # frame generation: needs OptiScaler, which is there and chosen
        r = w.e.set_scaling_framegen(CP, "fsr3")
        assert r["ok"] and r["scaling"]["framegen"] == "fsr3", r
        assert "FGType=optifg" in open(os.path.join(gdir, "OptiScaler.ini")).read()
        # a launch where OptiScaler WAS loaded: recorded as working
        w.e.launch(CP)
        w.running_set.add(CP)
        w.now += 5
        assert w.e.tick() == "started"
        w.now += 30
        w.e.tick()
        w.running_set.discard(CP)
        w.now += 300
        end = w.e.tick()
        assert end["scaling_check"] == {"tool": "optiscaler", "ok": True} and not end.get("scaling_failed"), end
        v = scaling.verified(CP)
        assert v["optiscaler"]["ok"] and v["framegen"]["ok"]
        assert "Funcionó" in {u["key"]: u for u in w.e.scaling(CP)["upscalers"]}["optiscaler"]["check"]
        # not seen in the processes but its own log written during the game: it ran (never turned off for nothing)
        loaded[0] = False
        w.e.launch(CP)
        w.running_set.add(CP)
        w.now += 5
        w.e.tick()
        logf = os.path.join(gdir, "OptiScaler.log")
        with open(logf, "w") as f:
            f.write("loaded\n")
        os.utime(logf, (w.now, w.now))
        w.now += 30
        w.e.tick()
        w.running_set.discard(CP)
        w.now += 300
        end = w.e.tick()
        assert end["scaling_check"]["ok"] and not end.get("scaling_failed"), end
        os.remove(logf)
        # a launch where it was NOT loaded: failed, said, and the next launch falls back on its own
        w.e.launch(CP)
        w.running_set.add(CP)
        w.now += 5
        w.e.tick()
        w.now += 30
        w.e.tick()
        w.running_set.discard(CP)
        w.now += 300
        end = w.e.tick()
        assert end["scaling_failed"] == "optiscaler" and not end["scaling_check"]["ok"], end
        assert "No se activó" in {u["key"]: u for u in w.e.scaling(CP)["upscalers"]}["optiscaler"]["check"]
        nxt = w.e.recommended(CP)
        assert nxt["config"]["graphics"]["path"] != "optiscaler", nxt["config"]["graphics"]
        # leaving FSR 3.1 turns frame generation off (it only runs inside OptiScaler), and says so
        r = w.e.set_scaling(CP, "native")
        assert r["scaling"]["framegen"] == "off" and "fotogramas" in r["note"], r
        assert "FGType=nofg" in open(os.path.join(gdir, "OptiScaler.ini")).read()
        try:
            w.e.set_scaling(CP, "dlss")
            raise AssertionError("unknown upscaler accepted")
        except schema.ProfileError:
            pass
    # the real check: the winmm.dll STONE installed, mapped in a process of this AppId (and only of this one)
    root = tempfile.mkdtemp(prefix="stone-proc-")
    try:
        for pid, appid, maps in (("101", CP, "7f00-7f10 r-xp 0 00:00 1 /games/Cyberpunk 2077/bin/x64/winmm.dll\n"),
                                 ("102", "4242", "7f00-7f10 r-xp 0 00:00 1 /games/Other/winmm.dll\n"),
                                 ("103", CP + "0", "7f00-7f10 r-xp 0 00:00 1 /games/Cyberpunk 2077/bin/x64/winmm.dll\n")):
            d = os.path.join(root, "proc", pid)
            os.makedirs(d)
            with open(os.path.join(d, "environ"), "wb") as f:
                f.write(b"HOME=/x\0SteamAppId=" + appid.encode() + b"\0")
            with open(os.path.join(d, "maps"), "w") as f:
                f.write(maps)
        want = ["/games/Cyberpunk 2077/bin/x64/winmm.dll"]
        assert optimizer.files_loaded(CP, want, sysroot=root)
        assert not optimizer.files_loaded("4242", want, sysroot=root)                 # another game's process
        assert not optimizer.files_loaded(CP, ["/games/Cyberpunk 2077/bin/x64/version.dll"], sysroot=root)
        assert not optimizer.files_loaded(CP, [], sysroot=root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    with World(anti_cheat=True) as w:                    # anti-cheat: shown, never offered
        sc = w.e.scaling(CP)
        o = {u["key"]: u for u in sc["upscalers"]}["optiscaler"]
        f = {x["key"]: x for x in sc["framegens"]}["fsr3"]
        assert o["state"] == "blocked" and "anti-cheat" in o["reason"] and f["state"] == "blocked", (o, f)
        try:
            w.e.set_scaling(CP, "optiscaler")
            raise AssertionError("anti-cheat game accepted")
        except schema.ProfileError as e:
            assert "anti-cheat" in str(e)
        assert not os.path.exists(os.path.join(w.game_dir, "bin", "x64", "winmm.dll"))


def _pe(machine):
    head = bytearray(b"MZ" + bytes(62))
    head[0x3C:0x40] = (64).to_bytes(4, "little")
    return bytes(head) + b"PE\0\0" + machine.to_bytes(2, "little") + bytes(200)


@test
def G31_32bit_games_never_get_optiscaler_or_helixsr():
    """3.1.0-rc16 (board, 22-11-2026): Batman Arkham City (32-bit) was offered FSR 3.1; STONE then saw it not loaded."""
    from stone_games import detect, install
    d = tempfile.mkdtemp(prefix="stone-pe-")
    try:
        for name, m in (("a64.exe", 0x8664), ("a32.exe", 0x14C), ("x.exe", 0x1234)):
            with open(os.path.join(d, name), "wb") as f:
                f.write(_pe(m))
        assert detect.pe_bits(os.path.join(d, "a64.exe")) == 64 and detect.pe_bits(os.path.join(d, "a32.exe")) == 32
        assert detect.pe_bits(os.path.join(d, "x.exe")) is None and detect.pe_bits(os.path.join(d, "nada.exe")) is None
    finally:
        shutil.rmtree(d, ignore_errors=True)
    with World() as w:
        x64 = os.path.join(w.game_dir, "bin", "x64")
        with open(os.path.join(x64, "Cyberpunk2077.exe"), "wb") as f:
            f.write(_pe(0x14C) + bytes(5000))                          # the game, 32-bit
        os.makedirs(os.path.join(w.game_dir, "_CommonRedist"))
        with open(os.path.join(w.game_dir, "_CommonRedist", "big.exe"), "wb") as f:
            f.write(_pe(0x8664) + bytes(90000))                        # a bigger installer: not the game
        detect.forget()
        facts = detect.facts(w.root, CP)
        assert facts["exe_bits"] == 32, facts
        sc = w.e.scaling(CP)
        k = {u["key"]: u for u in sc["upscalers"]}
        assert k["optiscaler"]["state"] == "blocked" and "32 bits" in k["optiscaler"]["reason"], k["optiscaler"]
        assert k["helixsr"]["state"] == "blocked" and "32 bits" in k["helixsr"]["reason"], k["helixsr"]
        assert {f["key"]: f for f in sc["framegens"]}["fsr3"]["state"] == "blocked"
        assert "32-bit" in install.install_plan(CP, facts, {})["error"]
        try:
            w.e.set_scaling(CP, "optiscaler")
            raise AssertionError("32-bit game accepted")
        except schema.ProfileError as e:
            assert "32 bits" in str(e), e
    with World(injected="optiscaler") as w:                            # installed before: still never chosen
        with open(os.path.join(w.game_dir, "bin", "x64", "Cyberpunk2077.exe"), "wb") as f:
            f.write(_pe(0x14C) + bytes(5000))
        detect.forget()
        p = w.e.profile(CP)
        assert not p["availability"]["optiscaler"]["available"] and "32-bit" in p["availability"]["optiscaler"]["reason"]
        assert w.e.recommended(CP)["config"]["graphics"]["path"] != "optiscaler"


@test
def G32_helixsr_in_one_press_license_build_install():
    """3.1.0-rc16 (owner, 22-11-2026): "que el usuario lo seleccione y solo juegue". NVIDIA's license is accepted
    only by the person; HelixSR's own setup builds in the background into no game; the bridge installs it in the
    chosen game as winmm.dll; STONE then sees it, chooses it and checks it after the game."""
    import subprocess as sp
    from stone_games import detect, helixsr, install
    with World() as w:
        x64 = os.path.join(w.game_dir, "bin", "x64")
        with open(os.path.join(x64, "Cyberpunk2077.exe"), "wb") as f:
            f.write(_pe(0x8664) + bytes(5000))
        detect.forget()
        # the release, as install.fetch leaves it (no download: a fake component)
        rel = os.path.join(install.components_dir(), "helixsr", "v3.4.1", "x", "HelixSR-3.4.1")
        os.makedirs(os.path.join(rel, "setup"))
        os.makedirs(os.path.join(rel, "helixsr-scaler"))
        for n in ("helixsr-setup.sh", os.path.join("setup", "helixsr_bridge.py")):
            with open(os.path.join(rel, n), "w") as f:
                f.write("# fake\n")
        with open(os.path.join(install.components_dir(), "helixsr", "v3.4.1", "component.json"), "w") as f:
            json.dump({"kind": "helixsr", "tag": "v3.4.1", "time": 1}, f)
        assert helixsr.release_dir() == rel
        k = {u["key"]: u for u in w.e.scaling(CP)["upscalers"]}["helixsr"]
        assert k["state"] == "install" and k["prepare"] and "licencia de NVIDIA" in k["reason"], k
        # choosing it before the license: refused with the code the page answers with the license screen
        try:
            w.e.set_scaling(CP, "helixsr")
            raise AssertionError("HelixSR without its preparation")
        except schema.ProfileError as e:
            assert str(e) == "HELIXSR_PREPARE"
        # the license: fetched whole; only the person accepts it (nothing is built without it)
        lic = helixsr.license_text(get=lambda u: "NVIDIA RTX SDKs LICENSE\n" + "x" * 300)
        assert lic["text"].startswith("NVIDIA") and "v310.7.0" in lic["page"]
        try:
            helixsr.accept("yes")
            raise AssertionError("a license accepted by something else than the person")
        except helixsr.HelixError:
            pass
        try:
            helixsr.build_start(rel, popen=lambda *a, **k: None)
            raise AssertionError("built without the license")
        except helixsr.HelixError:
            pass
        # ACEPTO: the setup starts in the background, unattended, into no game
        started = []

        class P:
            pid = os.getpid()                              # "running" while it is this test's own process
        real_popen = sp.Popen
        sp.Popen = lambda argv, **kw: started.append((argv, kw)) or P()
        try:
            st = w.e.helixsr_prepare(CP)
        finally:
            sp.Popen = real_popen
        argv, kw = started[0]
        assert argv[0] == "bash" and argv[1].endswith("helixsr-setup.sh") and argv[2:] == ["--yes"], argv
        assert kw["cwd"] == rel and kw["stdin"] == sp.DEVNULL and kw["start_new_session"]
        assert helixsr.accepted() and helixsr.pending() == CP
        assert st["state"] == "building", st
        d = json.load(open(helixsr.state_path()))
        d["build"]["pid"] = 999999999                       # the setup ended: its process is gone
        json.dump(d, open(helixsr.state_path(), "w"))
        # the bridge says the network is built -> ready -> the game gets it
        calls = []

        def fake_run(argv, **kw):
            calls.append(argv[3:])
            class R:
                stdout = ""
            if argv[3] == "status":
                R.stdout = json.dumps({"ok": True, "network_ready": True})
            elif argv[3] == "install":
                with open(os.path.join(x64, "OptiScaler.ini"), "w") as f:
                    f.write("[Upscalers]\n")
                with open(os.path.join(x64, "winmm.dll"), "wb") as f:
                    f.write(b"MZ" + bytes(100))
                with open(os.path.join(x64, "HelixSR-Scaler.files"), "w") as f:
                    f.write("winmm.dll\n")
                R.stdout = json.dumps({"ok": True, "game": {"installed": "scaler", "exe_folder": x64, "scaler_dll": "winmm.dll",
                                                            "version": "3.4.1"}})
            return R()
        real_run = sp.run
        sp.run = fake_run
        try:
            st = w.e.helixsr_tick()
        finally:
            sp.run = real_run
        assert st["state"] == "ready" and st.get("installed") == CP, st
        inst = [c for c in calls if c[0] == "install"][0]
        assert inst[inst.index("--scaler-name") + 1] == "winmm.dll" and inst[inst.index("--way") + 1] == "scaler"
        assert os.path.realpath(inst[inst.index("--game") + 1]) == os.path.realpath(w.game_dir)
        assert helixsr.pending() is None and install.installed_by_stone(CP)["kind"] == "helixsr"
        detect.forget()
        sc = w.e.scaling(CP)
        assert sc["upscaler"] == "helixsr", sc["upscaler"]
        assert detect.facts(w.root, CP)["injected"]["kind"] == "helixsr"
        # the launch loads it through STONE's switch, and STONE looks for its winmm.dll in the game
        w.e.launch(CP)
        s = w.e._session()
        assert s["watch"]["tool"] == "helixsr" and s["watch"]["files"][0].endswith("winmm.dll"), s["watch"]
        assert 'winmm=n,b' in w.options[CP], w.options[CP]
    with World(anti_cheat=True) as w:                    # anti-cheat: never, whatever HelixSR's own bridge allows
        k = {u["key"]: u for u in w.e.scaling(CP)["upscalers"]}["helixsr"]
        assert k["state"] == "blocked" and "anti-cheat" in k["reason"]
        try:
            w.e.helixsr_prepare(CP)
            raise AssertionError("anti-cheat game accepted")
        except schema.ProfileError:
            pass

@test
def G25_optiscaler_release_names_in_any_letter_case():
    """3.1.0-rc8 on the console: OptiScaler v0.9.4 publishes "Optiscaler_0.9.4-final.20260718._MM.7z"
    (small s) and STONE said "the latest release has no file I recognise"."""
    from stone_games import install
    for name in ("Optiscaler_0.9.4-final.20260718._MM.7z", "OptiScaler_0.7.7-pre9.7z", "optiscaler-1.0.zip"):
        rel = {"tag_name": "v0.9.4", "assets": [{"name": "notes.txt"}, {"name": name, "browser_download_url": "https://github.com/x/" + name,
                                                 "size": 55016448, "digest": "sha256:" + "a" * 64}]}
        r = install.latest("optiscaler", lambda url, rel=rel: rel)
        assert r["name"] == name and r["sha256"] == "a" * 64, r
    try:
        install.latest("optiscaler", lambda url: {"tag_name": "v1", "assets": [{"name": "Source.tar.gz"}]})
        raise AssertionError("an unknown file accepted")
    except install.InstallError:
        pass
    assert install.SKIP_FILES.match("setup_linux.sh") and install.SKIP_FILES.match("!! README_EXTRACT ALL FILES TO GAME FOLDER !!.txt")
    assert not install.SKIP_FILES.match("OptiScaler.ini") and not install.SKIP_FILES.match("D3D12_Optiscaler/D3D12Core.dll")


@test
def G23_look_effects_probe_events_and_healing_only_after_real_crashes():
    """3.1.0-rc8: the look is not turned off by a short session; two early ends in a row do, and
    say so; the effects probe looks inside the game's processes; every step is an event."""
    with World() as w:
        old = {k: os.environ.get(k) for k in ("XDG_CONFIG_HOME", "STONE_VKBASALT_LAYER")}
        os.environ["XDG_CONFIG_HOME"] = os.path.join(w.d, "config")
        layer = os.path.join(w.d, "vkBasalt.json")
        with open(layer, "w") as f:
            f.write("{}")
        os.environ["STONE_VKBASALT_LAYER"] = layer
        try:
            from stone_games import look
            rows = []
            w.e.events = lambda kind, **d: rows.append(dict(d, kind=kind))
            w.e.probe = lambda appid: {"processes": 3, "env": {"ENABLE_VKBASALT": "1"}, "vkbasalt_loaded": True,
                                       "vulkan_loaded": True, "wine": True, "names": ["Cyberpunk2077.exe"]}
            look.set_look(CP, "vivid")
            r = w.e.launch(CP)
            assert r["ok"] and "ENABLE_VKBASALT=1" in w.options[CP] and "VKBASALT_LOG_FILE=" in w.options[CP]
            res = w.play(CP, 45)                             # left after 45 s: abnormal for metrics, not a look crash
            assert res["abnormal"] and "healed" not in res and look.load_prefs().get(CP) == "vivid"
            w.e.launch(CP)
            assert w.play(CP, 8).get("look_crashes") == 1 and look.load_prefs().get(CP) == "vivid"   # one crash: kept
            w.e.launch(CP)
            w.play(CP, 1800)                                 # a clean run forgets it
            w.e.launch(CP)
            w.play(CP, 8)
            w.e.launch(CP)
            res = w.play(CP, 6)                              # the second early end in a row: off, and said
            assert res["healed"] == "look vivid turned off" and look.load_prefs().get(CP) is None
            kinds = [e["kind"] for e in rows]
            assert kinds.count("game_prepare") == 5 and kinds.count("game_started") == 5 and kinds.count("game_end") == 5
            assert rows[0]["look"] == "vivid" and rows[0]["graphics_applied"] is True
            assert [e for e in rows if e["kind"] == "game_end"][-1]["healed"] == "look vivid turned off"
            # EFFECTS PROBE: once, PROBE_AFTER_S after the game appeared
            look.set_look(CP, "natural")
            w.e.launch(CP)
            w.running_set.add(CP)
            w.now += 5
            assert w.e.tick() == "started"
            w.now += optimizer.PROBE_AFTER_S + 1
            assert w.e.tick() is None and w.e.tick() is None
            eff = [e for e in rows if e["kind"] == "game_effects"]
            assert len(eff) == 1 and eff[0]["vkbasalt_loaded"] is True and eff[0]["look"] == "natural"
            w.running_set.discard(CP)
            end = w.e.tick()
            assert end["reason"] == "exit" and [e for e in rows if e["kind"] == "game_end"][-1]["probed"] is True
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


@test
def G24_effects_probe_reads_the_games_processes():
    d = tempfile.mkdtemp(prefix="stone-proc-")
    try:
        def proc(pid, env, maps, comm):
            p = os.path.join(d, "proc", str(pid))
            os.makedirs(p)
            with open(os.path.join(p, "environ"), "wb") as f:
                f.write(b"\0".join(f"{k}={v}".encode() for k, v in env.items()) + b"\0")
            with open(os.path.join(p, "maps"), "w") as f:
                f.write(maps)
            with open(os.path.join(p, "comm"), "w") as f:
                f.write(comm + "\n")
        proc(100, {"SteamAppId": "620", "ENABLE_VKBASALT": "1", "VKBASALT_CONFIG_FILE": "/home/x/.local/state/stone/looks/vivid.conf",
                   "HOME": "/home/ana"}, "7f00 r-xp /usr/lib/libvulkan.so.1\n7f01 r-xp /run/host/usr/lib64/libvkbasalt.so\n", "portal2_linux")
        proc(101, {"SteamAppId": "999"}, "7f00 r-xp /usr/lib/libvkbasalt.so\n", "other")
        proc(102, {"SteamGameId": "620"}, "7f00 r-xp /usr/lib/wine/x86_64-unix/ntdll.so\n", "wineserver")
        r = optimizer.effects_probe("620", sysroot=d)
        assert r["processes"] == 2 and r["vkbasalt_loaded"] and r["vulkan_loaded"] and r["wine"]
        assert r["env"] == {"ENABLE_VKBASALT": "1", "VKBASALT_CONFIG_FILE": "set"}          # names, never other paths
        assert "HOME" not in json.dumps(r) and set(r["names"]) == {"portal2_linux", "wineserver"}
        assert optimizer.effects_probe("4242", sysroot=d)["processes"] == 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    only = sys.argv[1:]
    failed = 0
    for fn in TESTS:
        if only and not any(o in fn.__name__ for o in only):
            continue
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    print("\nall passed" if not failed else f"\n{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
