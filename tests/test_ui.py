"""STONE Home in real browsers, each against a real stoned on a private bus (fake governor).

  webkit_selftest.py    the GTK 4 + WebKitGTK shell (the fallback), WebKit message transport
  chromium_selftest.py  the Chromium shell (the default), token-protected HTTP transport, 4K
  e2e_home.py           ESLint on the page, then the page driven like the console (Playwright),
                        checking what reached the governor, Steam and logind

They need xvfb-run, Chromium, WebKitGTK 6, node and dev/e2e's packages: the dev container and CI
have them. On a Mac without the container they are skipped (failed under STONE_REQUIRE_ALL=1).

    python3 tests/test_ui.py     (or: pytest tests/test_ui.py)
"""

import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need  # noqa: E402

SCRIPTS = ("webkit_selftest.py", "chromium_selftest.py", "e2e_home.py")


def _has_gi():
    try:
        import gi  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.parametrize("script", SCRIPTS)
def test_ui(script):
    need(_has_gi(), f"{script} needs PyGObject (dev container, CI)")
    need(shutil.which("dbus-daemon") is not None, f"{script} needs dbus-daemon (dev container, CI)")
    need(shutil.which("xvfb-run") is not None, f"{script} needs xvfb-run (dev container, CI)")
    if script == "e2e_home.py":
        need(shutil.which("node") is not None, "e2e needs node (dev container, CI)")
    env = dict(os.environ, PYTHONWARNINGS="ignore::DeprecationWarning")
    r = subprocess.run([sys.executable, os.path.join(REPO, "tests", script)],
                       capture_output=True, text=True, timeout=900, env=env)
    out = r.stdout + r.stderr
    print(out[-3000:])
    need("SKIP" not in r.stdout, f"{script}: " + next((x for x in r.stdout.splitlines() if "SKIP" in x), ""))
    assert r.returncode == 0 and "PASS" in r.stdout, out[-6000:]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
