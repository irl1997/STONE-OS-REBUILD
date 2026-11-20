"""STONE IMAGE (stone_games/look.py): looks, LUTs, vkBasalt configs, the person's choice and the
launch variables. Pure Python: runs anywhere (no GPU, no vkBasalt needed).

    python3 tests/test_look.py     (or: pytest tests/test_look.py)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "modules", "games"))
from stone_games import look as L  # noqa: E402


class Env:
    def __enter__(self):
        self.t = tempfile.mkdtemp(prefix="stone-look-")
        self.old = {k: os.environ.get(k) for k in ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "STONE_VKBASALT_LAYER")}
        os.environ["XDG_STATE_HOME"] = os.path.join(self.t, "state")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.t, "cfg")
        self.layer = os.path.join(self.t, "vkBasalt.json")
        open(self.layer, "w").close()
        os.environ["STONE_VKBASALT_LAYER"] = self.layer
        return self

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.t, ignore_errors=True)


def test_luts_are_valid_cubes_and_keep_black_and_white_sane():
    for look in ("cinema", "vivid", "retro", "nextgen", "realistic"):
        lines = L.cube(look, size=5).splitlines()
        assert lines[1] == "LUT_3D_SIZE 5" and len(lines) == 2 + 5 ** 3
        vals = [tuple(map(float, ln.split())) for ln in lines[2:]]
        assert all(0.0 <= v <= 1.0 for t in vals for v in t)
        black, white = vals[0], vals[-1]
        assert max(black) <= (0.08 if look == "retro" else 0.03) and min(white) >= 0.84, (look, black, white)   # retro lifts blacks
        grey = L._grade(look, 0.5, 0.5, 0.5)
        assert max(grey) - min(grey) < 0.08 and 0.4 < sum(grey) / 3 < 0.6, (look, grey)                         # no colour cast on grey
    assert L.LUT_SIZE == 33


def test_rc11_looks_are_noticeable_and_do_not_sharpen_grain():
    """The console (19-11-2026): "los filtros no se notan tanto" and the games looked grainy (CAS)."""
    import itertools
    pts = [(r / 4, g / 4, b / 4) for r, g, b in itertools.product(range(5), repeat=3)]
    change = {k: sum(abs(L._grade(k, *p)[i] - p[i]) for p in pts for i in range(3)) / len(pts) / 3 for k in L.GRADE}
    assert all(v >= 0.05 for v in change.values()), change
    v = L._grade("vivid", 0.6, 0.5, 0.45)
    assert v[0] - v[2] > 0.2                                                # red-blue spread 0.15 -> more: more colour
    assert L._grade("realistic", 1.0, 0.0, 0.0)[0] - L._grade("realistic", 1.0, 0.0, 0.0)[1] < 1.0                # loud colours calmed
    for look in L.LOOKS:
        text = L.conf(look, "/x/l.cube")
        effects = text.split("effects = ")[1].splitlines()[0].split(":")
        assert "cas" not in effects, look                                   # DLS everywhere: it holds back on noise
        assert all(e in ("dls", "deband", "smaa", "lut", "fxaa") for e in effects), (look, effects)
        if "dls" in effects:
            assert "dlsDenoise = " in text
    assert L.conf("clean").split("effects = ")[1].splitlines()[0] == "dls:deband" and "dlsDenoise = 1.0" in L.conf("clean")
    for look in L.LOOKS:                    # rc12: deband last, so nothing sharpens or grades its dither into grain
        effects = L.conf(look, "/x/l.cube").split("effects = ")[1].splitlines()[0].split(":")
        assert "deband" not in effects or effects[-1] == "deband", (look, effects)
    assert "smaa" in L.conf("nextgen", "/x/n.cube") and "lut" not in L.conf("natural")
    assert [k for k in L.LOOKS] == ["natural", "clarity", "cinema", "vivid", "retro", "nextgen", "realistic", "clean"]
    assert all(L.DESCRIPTIONS[k] and L.LABELS[k] for k in L.LOOKS)


def test_choice_per_game_and_launch_variables():
    with Env() as e:
        facts, game = {}, {}
        assert L.env_for_game("1001", facts, game) == {}
        L.set_look("1001", "cinema")
        env = L.env_for_game("1001", facts, game)
        assert env["ENABLE_VKBASALT"] == "1" and env["STONE_LOOK"] == "cinema"
        text = open(env["VKBASALT_CONFIG_FILE"]).read()
        assert "effects = dls:lut:deband" in text and os.path.exists(text.split("lutFile = ")[1].strip())
        assert L.env_for_game("1001", facts, game, measuring=True) == {}          # numbers stay clean
        assert L.env_for_game("1001", {"anti_cheat": ["EasyAntiCheat"]}, game) == {}
        assert L.env_for_game("1001", facts, {"online_only": True}) == {}
        L.set_look("1001", None)
        assert L.env_for_game("1001", facts, game) == {} and L.load_prefs() == {}
        for bad in (("1001", "neon"), ("../x", "cinema")):
            try:
                L.set_look(*bad)
                raise AssertionError(bad)
            except ValueError:
                pass
        os.remove(e.layer)
        o = L.options("1001", facts, game)
        assert o["available"] is False and "vkBasalt" in o["reason"] and len(o["looks"]) == 8


if __name__ == "__main__":
    sys.exit(run_module(globals()))
