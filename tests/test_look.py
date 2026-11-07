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
    for look in ("cinema", "vivid", "retro"):
        lines = L.cube(look, size=5).splitlines()
        assert lines[1] == "LUT_3D_SIZE 5" and len(lines) == 2 + 5 ** 3
        vals = [tuple(map(float, ln.split())) for ln in lines[2:]]
        assert all(0.0 <= v <= 1.0 for t in vals for v in t)
        black, white = vals[0], vals[-1]
        assert max(black) <= 0.06 and min(white) >= 0.85, (look, black, white)
    # identity-like natural looks have no LUT; retro has no sharpening
    assert "lut" not in L.conf("natural") and "cas" in L.conf("natural")
    assert "cas" not in L.conf("retro", "/x/retro.cube").split("effects = ")[1].splitlines()[0]


def test_choice_per_game_and_launch_variables():
    with Env() as e:
        facts, game = {}, {}
        assert L.env_for_game("1001", facts, game) == {}
        L.set_look("1001", "cinema")
        env = L.env_for_game("1001", facts, game)
        assert env["ENABLE_VKBASALT"] == "1" and env["STONE_LOOK"] == "cinema"
        text = open(env["VKBASALT_CONFIG_FILE"]).read()
        assert "effects = cas:lut" in text and os.path.exists(text.split("lutFile = ")[1].strip())
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
        assert o["available"] is False and "vkBasalt" in o["reason"] and len(o["looks"]) == 5


if __name__ == "__main__":
    sys.exit(run_module(globals()))
