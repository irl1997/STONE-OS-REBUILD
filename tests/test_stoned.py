"""stoned: the rc23 suite (recovery, governor, telemetry, thermal, Safe Mode, games, calibration).

The suite lives in tests/stoned_suite.py with its own runner and ids (R01..., I01..., P01...): each
integration case starts a private D-Bus daemon, the fake governor and a real stoned process. This
file runs it once under pytest. Needs dbus-daemon and PyGObject (the dev container has both).

    python3 tests/test_stoned.py     (or: pytest tests/test_stoned.py)
"""

import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need, run_module  # noqa: E402


def _can_run():
    try:
        import gi  # noqa: F401
    except ImportError:
        return False
    return shutil.which("dbus-daemon") is not None


def test_stoned_suite():
    need(_can_run(), "stoned suite needs PyGObject and dbus-daemon (dev container, CI)")
    env = dict(os.environ, PYTHONWARNINGS="ignore::DeprecationWarning")   # GLib deprecations in the fake governor
    r = subprocess.run([sys.executable, os.path.join(REPO, "tests", "stoned_suite.py")],
                       capture_output=True, text=True, timeout=1500, env=env)
    lines = r.stdout.splitlines()
    failed = [x for x in lines if x.startswith("FAIL")]
    summary = [x for x in lines if " passed, " in x]
    report = "\n".join(failed + summary + ["--- last output ---"] + (r.stdout + r.stderr).splitlines()[-40:])
    print("\n".join(summary))
    assert r.returncode == 0 and not failed, report


if __name__ == "__main__":
    sys.exit(run_module(globals()))
