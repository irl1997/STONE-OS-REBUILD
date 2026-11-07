"""scripts/release-info.sh: version, channel and tags of a build come only from VERSION.

    python3 tests/test_release_info.py     (or: pytest tests/test_release_info.py)
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402


def _info(version, ref, sha="0123456789abcdef"):
    d = tempfile.mkdtemp()
    try:
        os.mkdir(os.path.join(d, "scripts"))
        shutil.copy(os.path.join(REPO, "scripts", "release-info.sh"), os.path.join(d, "scripts"))
        with open(os.path.join(d, "VERSION"), "w") as f:
            f.write(version + "\n")
        r = subprocess.run(["bash", os.path.join(d, "scripts", "release-info.sh"), ref, sha],
                           capture_output=True, text=True)
        out = dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)
        return r.returncode, out, r.stderr
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_branch_builds_go_to_dev():
    rc, out, err = _info("0.2.0-dev.1", "main")
    assert rc == 0, err
    assert out["channel"] == "dev" and out["tags"] == "dev dev-0123456" and out["prerelease"] == "true", out


def test_dev_tag_stays_in_dev():
    rc, out, err = _info("0.2.0-dev.1", "v0.2.0-dev.1")
    assert rc == 0, err
    assert out["channel"] == "dev" and out["tags"] == "0.2.0-dev.1 dev", out


def test_tag_must_match_version():
    rc, _, err = _info("0.2.0-dev.1", "v0.2.0-dev.2")
    assert rc != 0 and "does not match" in err, err


def test_bad_version_is_refused():
    rc, _, _ = _info("0.2", "main")
    assert rc != 0


def test_current_version_builds_in_dev():
    with open(os.path.join(REPO, "VERSION")) as f:
        version = f.read().strip()
    rc, out, err = _info(version, "main")
    assert rc == 0 and out["channel"] == "dev", (err, out)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
