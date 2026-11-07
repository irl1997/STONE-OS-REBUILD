"""image/build_files/governor-config.py: only [dbus] enabled changes; bad packages stop the build.

Ported from rc23 tests/run_tests.py (B01, B02; ids kept).

    python3 tests/test_governor_config.py     (or: pytest tests/test_governor_config.py)
"""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need, run_module  # noqa: E402

GOVCFG = os.path.join(REPO, "image", "build_files", "governor-config.py")
SAMPLE_CFG = """[timing]
burst-samples = 60

[gpu]
set-method = "smu"

[dbus]
enabled = false

[frequency-range]
min = 1000
max = 1850

[temperature]
throttling = 85
throttling_recovery = 75

[[safe-points]]
frequency = 1000
voltage = 800

[[safe-points]]
frequency = 2000
voltage = 960
"""


def _govcfg(text):
    need(sys.version_info >= (3, 11), "governor-config.py needs Python 3.11+ (tomllib), as in Fedora 44")
    d = tempfile.mkdtemp()
    p = os.path.join(d, "config.toml")
    with open(p, "w") as f:
        f.write(text)
    r = subprocess.run([sys.executable, GOVCFG, p], capture_output=True, text=True)
    with open(p) as f:
        return r.returncode, r.stdout + r.stderr, f.read()


def test_B01_governor_config_only_enables_dbus():
    code, out, after = _govcfg(SAMPLE_CFG)
    assert code == 0 and "STONE_GOV_RANGE=1000-1850" in out and "1000@800,2000@960" in out, out
    assert after == SAMPLE_CFG.replace("enabled = false", "enabled = true"), after


def test_B02_governor_config_refuses_bad_packages():
    assert _govcfg(SAMPLE_CFG.replace("[dbus]\nenabled = false\n", ""))[0] == 1          # no D-Bus
    assert _govcfg(SAMPLE_CFG.replace("max = 1850", "max = 2300"))[0] == 1                # outside the sanity range
    assert _govcfg(SAMPLE_CFG.replace("throttling = 85", "throttling = 0"))[0] == 1       # protection off
    assert _govcfg("not toml [[[")[0] == 1
    code, _, after = _govcfg(SAMPLE_CFG.replace("enabled = false", "enabled = true"))
    assert code == 0 and after.count("enabled = true") == 1


if __name__ == "__main__":
    sys.exit(run_module(globals()))
