"""Ports of Switch 2 games (stone_home/ports.py) against a stand-in of GitHub: the Linux x86-64 build is
chosen, checked against the SHA-256 GitHub publishes, unpacked and added to the library. No network.

    python3 tests/test_ports.py     (or: pytest tests/test_ports.py)
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import ports as P  # noqa: E402

BLOB = b"\x7fELF fake appimage"


def gh(blob=BLOB, digest=None):
    rel = {"tag_name": "v0.1.11", "assets": [
        {"name": "mkw-recomp-0.1.11-aarch64.AppImage", "size": 10, "digest": "sha256:" + "0" * 64, "browser_download_url": "https://x/arm"},
        {"name": "mkw-recomp-0.1.11-windows-x64.zip", "size": 10, "digest": "sha256:" + "0" * 64, "browser_download_url": "https://x/win"},
        {"name": "mkw-recomp-0.1.11-x86_64.AppImage", "size": len(blob), "browser_download_url": "https://x/linux",
         "digest": "sha256:" + (digest or hashlib.sha256(BLOB).hexdigest())}]}
    calls = []

    def get(url, limit, timeout=60):
        calls.append(url)
        return json.dumps(rel).encode() if "api.github.com" in url else blob
    get.calls = calls
    return get


class UI:
    def __init__(self):
        self.added = []

    def add_shortcut(self, name, exe, start, opts):
        self.added.append((name, exe, start, opts))
        return 3000000001


def _extract(argv, cwd, capture_output, timeout):
    os.makedirs(os.path.join(cwd, "squashfs-root"))
    with open(os.path.join(cwd, "squashfs-root", "AppRun"), "w") as f:
        f.write("#!/bin/sh\n")
    os.chmod(os.path.join(cwd, "squashfs-root", "AppRun"), 0o755)
    return type("R", (), {"returncode": 0})()


def test_a_port_is_installed_from_its_projects_linux_build_checked_and_in_the_library():
    t = tempfile.mkdtemp(prefix="stone-ports-")
    old = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = t
    try:
        seen, ui, get = [], UI(), gh()
        assert P.install("mkw", lambda st, txt: seen.append((st, txt)), get=get, run=_extract, steam_ui=ui)
        assert get.calls == ["https://api.github.com/repos/adriadam10/mkw-recomp/releases/latest", "https://x/linux"]
        exe = os.path.join(t, "stone", "ports", "mkw", "app", "AppRun")
        assert ui.added == [("Mario Kart World (Switch 2)", exe, os.path.join(t, "stone", "ports", "mkw"), "")]
        assert seen[-1][0] == "done" and P.exe_of("mkw") == exe
        row = [r for r in P.catalog() if r["key"] == "mkw"][0]
        assert row["installed"] and row["tag"] == "v0.1.11" and "volcada de tu Switch 2" in row["needs"]
        # a download that is not what GitHub says it is: refused, nothing kept
        seen.clear()
        assert not P.install("eglantine", lambda st, txt: seen.append((st, txt)), get=gh(), run=_extract, steam_ui=ui)
        assert seen[-1][0] == "error"                       # no eglantine asset in this stand-in release
        bad = gh(blob=b"something else")
        assert not P.install("mkw", lambda st, txt: seen.append((st, txt)), get=bad, run=_extract, steam_ui=ui)
        assert "no coincide" in seen[-1][1]
        assert not P.install("zelda", lambda st, txt: seen.append((st, txt)), get=gh(), run=_extract, steam_ui=ui)
    finally:
        if old is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = old
        shutil.rmtree(t, ignore_errors=True)


def test_only_projects_with_a_linux_x86_64_build_are_listed():
    for k, c in P.CATALOG.items():
        assert "linux" in c["asset"].lower() or "x86_64" in c["asset"], k
        assert c["repo"].count("/") == 1 and c["needs"] and c["note"]


if __name__ == "__main__":
    sys.exit(run_module(globals()))
