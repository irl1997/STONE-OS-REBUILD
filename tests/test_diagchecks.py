"""What works and what does not (stone_home/diagchecks.py, 3.1.0-rc8), from STONE's events, the
journal and the live state; and the report putting it first. Pure Python, temporary folders only.

    python3 tests/test_diagchecks.py     (or: pytest tests/test_diagchecks.py)
"""

import json
import os
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import diagchecks as C, diagreport as D, events as E  # noqa: E402

JOURNAL = ("2026-11-14T21:43:23-03:00 bazzite systemd[2765]: Started Gamescope Session Plus.\n"
           "2026-11-14T21:43:24-03:00 bazzite gamescope-session-plus[3070]: [gamescope] [Info]  console: gamescope version 3.17.0\n"
           "2026-11-14T21:43:30-03:00 bazzite gamescope-session-plus[3070]: [gamescope] [Info]  xwm: HDR output enabled\n")


def _restore(k, v):
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v


class Box:
    """A home with STONE's folders and an image root with (or without) vkBasalt."""

    def __init__(self, layer=True, library=True):
        self.t = tempfile.mkdtemp(prefix="stone-checks-")
        self.home = os.path.join(self.t, "home")
        self.root = os.path.join(self.t, "root")
        os.makedirs(os.path.join(self.home, ".config", "stone"))
        os.makedirs(os.path.join(self.home, ".local", "state", "stone", "looks"))
        if layer:
            d = os.path.join(self.root, "usr", "share", "vulkan", "implicit_layer.d")
            os.makedirs(d)
            with open(os.path.join(d, "vkBasalt.json"), "w") as f:
                json.dump({"layer": {"name": "VK_LAYER_VKBASALT_post_processing", "library_path": "libvkbasalt.so"}}, f)
        if library:
            os.makedirs(os.path.join(self.root, "usr", "lib64"))
            open(os.path.join(self.root, "usr", "lib64", "libvkbasalt.so"), "w").close()

    def looks(self, d):
        with open(os.path.join(self.home, ".config", "stone", "looks.json"), "w") as f:
            json.dump(d, f)

    def filters(self, ev=(), logs="", prefs=None):
        return C.check_filters(list(ev), logs, self.home, prefs or {}, {"620": "Portal 2"}, self.root)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        shutil.rmtree(self.t, ignore_errors=True)


def effects(**kw):
    e = {"kind": "game_effects", "appid": "620", "look": "vivid", "processes": 3, "env": {"ENABLE_VKBASALT": "1"},
         "vkbasalt_loaded": True, "vulkan_loaded": True, "names": ["portal2_linux"]}
    e.update(kw)
    return e


def test_filters_say_works_or_why_not():
    with Box() as b:
        b.looks({"620": "vivid"})
        assert b.filters([effects()])["status"] == C.OK
        r = b.filters([effects(env={})])
        assert r["status"] == C.FAIL and "ENABLE_VKBASALT" in r["detail"] and "Portal 2" in r["detail"]
        r = b.filters([effects(vulkan_loaded=False, vkbasalt_loaded=False)])
        assert r["status"] == C.FAIL and "Vulkan" in r["detail"]
        r = b.filters([effects(vkbasalt_loaded=False)])
        assert r["status"] == C.FAIL and "no se cargó" in r["detail"]
        assert b.filters([effects(processes=0)])["status"] == C.NODATA
        assert b.filters([effects()], prefs={"optimized": 0})["status"] == C.FAIL
        r = b.filters([])                                     # chosen, never played with it
        assert r["status"] == C.NODATA and r["how"]
    with Box() as b:                                          # rc7's silent rule, seen in the log
        r = b.filters([], logs="[stone] optimized: monitor: {'appid': '620', 'healed': 'look vivid turned off'}")
        assert r["status"] == C.FAIL and "apagó" in r["detail"]
        assert b.filters([])["status"] == C.NODATA and "Ningún juego" in b.filters([])["detail"]
    with Box(layer=False) as b:
        assert b.filters([effects()])["status"] == C.FAIL and "no está instalado" in b.filters([])["detail"]
    with Box(library=False) as b:
        assert "biblioteca no existe" in b.filters([effects()])["detail"]


def test_colours_hdr_timeline_and_steams_switch():
    tl = C.hdr_timeline(JOURNAL)
    assert tl[0][:2] == (6, "enabled")                       # 6 s after gamescope started
    r = C.check_display(JOURNAL, {"steam_display": {"gamescope_hdr_enabled": True}})
    assert r["status"] == C.WARN and "6 s" in r["detail"] and "HDR en la salida de vídeo" in r["how"]
    assert any("activado" in e for e in r["evidence"])
    assert C.check_display(JOURNAL.replace("enabled", "disabled"), {})["status"] == C.OK
    assert C.check_display("", {})["status"] == C.NODATA
    assert C.check_display("", {"steam_display": {"gamescope_hdr_enabled": False}})["status"] == C.OK


def test_games_steam_sound_controllers_network():
    ends = [{"kind": "game_started", "appid": "620"}, {"kind": "game_end", "appid": "620", "reason": "not started", "seconds": None}]
    assert C.check_games(ends, "", {"620": "Portal 2"})["status"] == C.FAIL
    assert C.check_games([{"kind": "game_started", "appid": "620"}], "", {})["status"] == C.OK
    assert C.check_games([], "", {})["status"] == C.NODATA
    live = {"steam_reachable": True, "steam_functions": {"have": 27, "missing": []}}
    assert C.check_steam(live, "", [])["status"] == C.OK
    r = C.check_steam(live, "x steam[1]: RaiseJSException: Method call failed: Storage.GetJSON requires 2 arguments\n" * 3, [])
    assert r["status"] == C.WARN and "Storage.GetJSON ×3" in " ".join(r["evidence"])
    assert C.check_steam(live, "", [{"kind": "steam_front", "page": "settings", "state": "navfail"}])["status"] == C.FAIL
    assert C.check_steam({"steam_reachable": False}, "", [])["status"] == C.FAIL

    def run(vol):
        return lambda argv, timeout=20: vol if "get-volume" in argv else "Audio\n"
    assert C.check_sound(run("Volume: 0.70\n"))["status"] == C.OK
    assert C.check_sound(run("Volume: 0.70 [MUTED]\n"))["status"] == C.WARN
    assert C.check_sound(run("[wpctl no está instalado]\n"))["status"] == C.NODATA
    with Box() as b:
        os.makedirs(os.path.join(b.root, "proc", "bus", "input"))
        with open(os.path.join(b.root, "proc", "bus", "input", "devices"), "w") as f:
            f.write('I: Bus=0003\nN: Name="Xbox Wireless Controller"\nH: Handlers=event5 js0\n\n'
                    'I: Bus=0011\nN: Name="AT Keyboard"\nH: Handlers=sysrq kbd event0\n\n')
        r = C.check_controllers(b.root)
        assert r["status"] == C.OK and r["evidence"] == ["Xbox Wireless Controller"]
    assert C.check_network({"net": {"online": True, "ssid": "Casa", "internet": "full"}})["status"] == C.OK
    assert C.check_network({"net": {"online": True, "ssid": "Casa", "internet": "limited"}})["status"] == C.FAIL


def test_symptoms_come_first_and_the_report_says_it():
    t = tempfile.mkdtemp(prefix="stone-diagsym-")
    try:
        home = os.path.join(t, "home")
        st = os.path.join(home, ".local", "state", "stone")
        os.makedirs(os.path.join(st, "looks"))
        lay = os.path.join(t, "usr", "share", "vulkan", "implicit_layer.d")
        os.makedirs(lay)
        with open(os.path.join(lay, "vkBasalt.json"), "w") as f:
            json.dump({"layer": {"library_path": "/usr/lib64/libvkbasalt.so"}}, f)
        os.makedirs(os.path.join(t, "usr", "lib64"))
        open(os.path.join(t, "usr", "lib64", "libvkbasalt.so"), "w").close()
        with open(os.path.join(st, "looks", "vkbasalt-620.log"), "w") as f:
            f.write("vkBasalt info: effect cas\n")
        prev = os.environ.get("XDG_STATE_HOME")
        os.environ["XDG_STATE_HOME"] = os.path.join(home, ".local", "state")
        try:
            E.record("game_effects", appid="620", look="vivid", processes=2, env={"ENABLE_VKBASALT": "1"},
                     vkbasalt_loaded=False, vulkan_loaded=True, names=["portal2_linux"])
        finally:
            _restore("XDG_STATE_HOME", prev)

        def run(argv, timeout=20):
            if argv[0] == "journalctl" and "--user" in argv:
                return JOURNAL
            return "Volume: 0.50\n" if "get-volume" in argv else ""
        live = {"steam_probe": [], "steam_display": {"gamescope_hdr_enabled": True}, "names": {"620": "Portal 2"},
                "gamescope_atoms": {"GAMESCOPE_HDR_OUTPUT_FEEDBACK": [1]}}
        r = D.build(out_dir=os.path.join(t, "out"), live=live, run=run, home=home, now=lambda: 1794600000,
                    symptoms=["colors", "filters", "nonsense"], root=t)
        s = r["summary"]
        assert [c["id"] for c in s["checks"][:2]] == ["display", "filters"]               # what the person ticked, first
        assert s["checks"][0]["symptom"] == [C.SYMPTOMS["colors"][0]] and s["failing"] >= 1
        assert s["symptoms"] == [C.SYMPTOMS["colors"][0], C.SYMPTOMS["filters"][0]]
        with zipfile.ZipFile(r["path"]) as z:
            names = z.namelist()
            for n in ("comprobaciones.txt", "eventos.jsonl", "juegos/vkbasalt-620.txt", "pantalla/gamescope.json", "dispositivos.txt"):
                assert n in names, n
            resumen = z.read("resumen.txt").decode()
            assert "LO QUE MARCASTE" in resumen and "QUÉ FUNCIONA Y QUÉ NO" in resumen and "[FALLA] Filtros de imagen" in resumen
            assert "[ATENCIÓN] Colores de la pantalla" in resumen
            assert "Portal 2" in z.read("comprobaciones.txt").decode()
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_second_report_false_alarms():
    """The console's second report (15-11-2026, rc8): Fedora's vkBasalt declares /usr/$LIB/...; Steam's
    log still had rc7's rejected calls from the day before; a controller seen by name."""
    with Box(library=False) as b:
        d = os.path.join(b.root, "usr", "share", "vulkan", "implicit_layer.d", "vkBasalt.json")
        with open(d, "w") as f:
            json.dump({"layer": {"library_path": "/usr/$LIB/vkbasalt/libvkbasalt.so"}}, f)
        assert C.layer_state(b.root)[:2] == (True, False)
        os.makedirs(os.path.join(b.root, "usr", "lib64", "vkbasalt"))
        open(os.path.join(b.root, "usr", "lib64", "vkbasalt", "libvkbasalt.so"), "w").close()
        assert C.layer_state(b.root)[:2] == (True, True)
        os.makedirs(os.path.join(b.root, "proc", "bus", "input"))
        with open(os.path.join(b.root, "proc", "bus", "input", "devices"), "w") as f:
            f.write('N: Name="Xbox Wireless Controller"\nH: Handlers=event7\n\nN: Name="Xbox Wireless Controller Consumer Control"\nH: Handlers=kbd event8\n\n')
        assert C.check_controllers(b.root)["evidence"] == ["Xbox Wireless Controller"]
    log = ("[2026-11-14 21:44:51] Client version: 1792618285\n"
           "[2026-11-14 21:44:52] RaiseJSException: Method call failed: Apps.GetPlaytime requires 2 arguments; only 1 given\n"
           "[2026-11-15 10:31:05] Client version: 1794536281\n[2026-11-15 10:31:06] Startup\n")
    rest = D.steam_since_start(log)
    assert rest.startswith("[2026-11-15 10:31:05]") and "RaiseJSException" not in rest
    assert C.check_steam({"steam_reachable": True, "steam_functions": {"have": 27, "missing": []}}, rest, [])["status"] == C.OK


def test_events_are_kept_small_and_never_fail():
    t = tempfile.mkdtemp(prefix="stone-ev-")
    try:
        prev = os.environ.get("XDG_STATE_HOME")
        os.environ["XDG_STATE_HOME"] = t
        E.MAX_BYTES, old = 2048, E.MAX_BYTES
        try:
            for i in range(200):
                E.record("x", i=i, text="y" * 500, nested={"a": object()})
            assert os.path.getsize(E.path()) < 4096
            rows = E.read()
            assert rows[-1]["i"] == 199 and len(rows[-1]["text"]) == 300 and E.read(kinds=["none"]) == []
        finally:
            E.MAX_BYTES = old
            _restore("XDG_STATE_HOME", prev)
    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    run_module(globals())
