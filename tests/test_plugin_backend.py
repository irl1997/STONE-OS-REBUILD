"""The STONE plugin's backend with fake commands: it runs only what it should, with checked values,
and never touches 40 CU unless asked. Frontend: `npm run typecheck` and the build in the image.

    python3 tests/test_plugin_backend.py     (or: pytest tests/test_plugin_backend.py)
"""

import asyncio
import json
import logging
import os
import shutil
import stat
import sys
import tempfile
import time
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.modules.setdefault("decky", types.SimpleNamespace(logger=logging.getLogger("decky")))
sys.path.insert(0, os.path.join(REPO, "plugins", "stone"))
import main as M  # noqa: E402

FAKE = """#!/bin/sh
echo "$(basename "$0") $* LD=${LD_LIBRARY_PATH:-none}" >> "$STONE_TEST_LOG"
case "$(basename "$0") $1 $2" in
  "stonectl --json status") echo '{"profile": "balanced"}' ;;
  "stonectl --json metrics") echo '{"gpu_temp_c": 50}' ;;
  "stonectl --json calibration") echo '{"running": null}' ;;
  "stone-cu40 status --json") echo '{"state": "off"}' ;;
  "stone-cu40 enable --yes") [ -n "$STONE_TEST_FAIL" ] && { echo "GPU caliente"; exit 1; }; echo ok ;;
  "stone-doctor --json ") echo '{"checks": [["ok", "CPU", "bien"]]}' ;;
  "stonectl profile"*|"stonectl game-profile"*|"stonectl ui-ready"*) echo '{"ok": true, "error": null}' ;;
esac
"""


class Box:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="stone-plugin-")
        self.log = os.path.join(self.dir, "calls")
        open(self.log, "w").close()
        for name in ("stonectl", "stone-cu40", "stone-doctor", "systemctl"):
            p = os.path.join(self.dir, name)
            with open(p, "w") as f:
                f.write(FAKE)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        M.BIN = self.dir
        os.environ["STONE_TEST_LOG"] = self.log
        os.environ["LD_LIBRARY_PATH"] = "/frozen/python"
        os.environ.pop("STONE_TEST_FAIL", None)
        self.p = M.Plugin()
        self.p.test_task = self.p.test_result = None

    def calls(self):
        with open(self.log) as f:
            return [line.rsplit(" LD=", 1)[0] for line in f.read().splitlines()]

    def close(self):
        shutil.rmtree(self.dir)
        os.environ.pop("LD_LIBRARY_PATH", None)


def _box(fn):
    def wrapped():
        b = Box()
        try:
            asyncio.run(fn(b))
        finally:
            b.close()
    wrapped.__name__ = fn.__name__
    return wrapped


@_box
async def test_state_reads_only_and_gathers_everything(b):
    s = await b.p.state()
    assert s["stoned"] == {"profile": "balanced"} and s["cu40"] == {"state": "off"}
    assert s["metrics"]["gpu_temp_c"] == 50 and s["test"] == {"running": False, "result": None}
    assert sorted(b.calls()) == ["stone-cu40 status --json", "stonectl --json calibration",
                                 "stonectl --json metrics", "stonectl --json status"]


@_box
async def test_frozen_python_libraries_do_not_reach_the_commands(b):
    await b.p.ui_ready()
    with open(b.log) as f:
        assert "LD=none" in f.read()


@_box
async def test_profiles_are_checked_before_running(b):
    assert (await b.p.set_profile("performance"))["ok"]
    assert (await b.p.set_game_profile("570", "global"))["ok"]
    assert b.calls() == ["stonectl profile performance", "stonectl game-profile 570 global"]
    assert "error" in await b.p.set_profile("--help")
    assert "error" in await b.p.set_game_profile("570; reboot", "silent")
    assert "error" in await b.p.set_game_profile("570", "c1")
    assert len(b.calls()) == 2


@_box
async def test_40_cu_changes_only_when_asked_and_reports_refusals(b):
    await b.p.state()
    await b.p.ui_ready()
    assert not [c for c in b.calls() if "enable" in c or "disable" in c or "kargs" in c]
    assert (await b.p.cu40_enable())["ok"]
    assert b.calls()[-1] == "stone-cu40 enable --yes"
    os.environ["STONE_TEST_FAIL"] = "1"
    r = await b.p.cu40_enable()
    assert not r["ok"] and "GPU caliente" in r["error"]


@_box
async def test_cu40_test_runs_in_the_background_once(b):
    assert (await b.p.cu40_test())["ok"]
    assert (await b.p.cu40_test())["ok"]
    t0 = time.time()
    await b.p.test_task
    assert time.time() - t0 < 5 and b.p.test_result["ok"]
    assert b.calls() == ["stone-cu40 test --minutes 3"]


@_box
async def test_missing_command_is_an_answer_not_a_crash(b):
    os.remove(os.path.join(b.dir, "stone-doctor"))
    r = await b.p.doctor()
    assert "error" in r
    json.dumps(r)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
