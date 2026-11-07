"""Frame generation (stone_games/framegen.py, D-22): the OptiScaler.ini edit and every condition.
Pure Python on temporary folders.

    python3 tests/test_framegen.py     (or: pytest tests/test_framegen.py)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "modules", "games"))
from stone_games import framegen as FG  # noqa: E402

INI = "[Upscalers]\nDx12Upscaler=auto\n\n[FrameGen]\n; frame generation\nEnabled=auto\nFGType=auto ; auto, nofg, optifg\n\n[Log]\nLogLevel=2\n"


def test_ini_edit_keeps_everything_else():
    on = FG.set_state(INI, "optifg")
    assert FG.read_state(on) == "optifg" and "LogLevel=2" in on and "Dx12Upscaler=auto" in on and on.count("FGType") == 1
    assert FG.read_state(FG.set_state(on, "nofg")) == "nofg"
    assert FG.read_state(FG.set_state("[Upscalers]\nX=1\n", "optifg")) == "optifg"            # section added
    assert FG.read_state(FG.set_state("[FrameGen]\nEnabled=auto\n[Log]\nA=1\n", "optifg")) == "optifg"   # key added in place
    assert "[Log]\nA=1" in FG.set_state("[FrameGen]\nEnabled=auto\n[Log]\nA=1\n", "optifg")
    assert FG.read_state("[Log]\nFGType=optifg\n") is None                                   # other section


def test_conditions_and_switching():
    t = tempfile.mkdtemp(prefix="stone-fg-")
    saved = FG.install.installed_by_stone
    try:
        exe = os.path.join(t, "game")
        os.makedirs(exe)
        with open(os.path.join(exe, FG.INI), "w") as f:
            f.write(INI)
        FG.install.installed_by_stone = lambda a: {"kind": "optiscaler", "exe_dir": exe} if a == "1001" else None
        assert FG.status("1002", {}, {})["available"] is False                                 # not installed by STONE
        assert "anti-cheat" in FG.status("1001", {"anti_cheat": ["EAC"]}, {})["reason"]
        assert "en línea" in FG.status("1001", {}, {"online_only": True})["reason"]
        assert FG.status("1001", {}, {}) == {"available": True, "reason": None, "on": False, "experimental": True}
        assert FG.set_on("1001", {}, {}, True) == {"ok": True, "on": True} and FG.status("1001", {}, {})["on"]
        assert open(os.path.join(exe, FG.INI + ".stone-orig")).read() == INI                   # original kept once
        FG.set_on("1001", {}, {}, False)
        assert FG.status("1001", {}, {})["on"] is False and open(os.path.join(exe, FG.INI + ".stone-orig")).read() == INI
        assert "error" in FG.set_on("1001", {"anti_cheat": ["EAC"]}, {}, True)
    finally:
        FG.install.installed_by_stone = saved
        shutil.rmtree(t)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
