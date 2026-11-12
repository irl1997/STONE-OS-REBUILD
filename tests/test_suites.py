"""The script suites ported from rc23, each with its own runner and case ids, run once under pytest.

  stoned_suite.py    stoned: recovery, governor, telemetry, thermal, Safe Mode, games, calibration,
                     reference configuration (R, I, P, T, S, G, C, B, REF)
  home_suite.py      STONE Home: VDF, library, Steam shortcut, host, bridge to a real stoned (V, L, K, P, H, E, B)
  display_suite.py   STONE DISPLAY: EDID, connectors, Steam display state, link budget (D)
  games_suite.py     STONE OPTIMIZED: profiles, graphics paths, metrics, score, launch/exit/crash (G)
  server_suite.py    STONE Home transport: secret path, Host and Origin checks

Each needs PyGObject; stoned and home also need dbus-daemon (the dev container has both).

    python3 tests/test_suites.py     (or: pytest tests/test_suites.py)
"""

import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need  # noqa: E402

SUITES = {"stoned_suite.py": True, "home_suite.py": True, "display_suite.py": False,
          "games_suite.py": False, "server_suite.py": False}       # value: needs dbus-daemon


def _has_gi():
    try:
        import gi  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.parametrize("suite", sorted(SUITES))
def test_suite(suite):
    need(_has_gi(), f"{suite} needs PyGObject (dev container, CI)")
    if SUITES[suite]:
        need(shutil.which("dbus-daemon") is not None, f"{suite} needs dbus-daemon (dev container, CI)")
    env = dict(os.environ, PYTHONWARNINGS="ignore::DeprecationWarning")
    r = subprocess.run([sys.executable, os.path.join(REPO, "tests", suite)],
                       capture_output=True, text=True, timeout=1500, env=env)
    lines = r.stdout.splitlines()
    failed = [x for x in lines if x.startswith("FAIL")]
    summary = [x for x in lines if " passed" in x or " failed" in x or x.strip() == "all passed"]
    report = "\n".join(failed + summary + ["--- last output ---"] + (r.stdout + r.stderr).splitlines()[-40:])
    print(f"{suite}: " + " | ".join(summary))
    assert r.returncode == 0 and not failed, report


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
