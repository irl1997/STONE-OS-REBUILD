"""Games sent from the phone (stone_home/phonedrop.py): a real local server on 127.0.0.1, files sent
as the phone's page sends them. Pure Python, temporary folders only.

    python3 tests/test_phonedrop.py     (or: pytest tests/test_phonedrop.py)
"""

import http.client
import json
import os
import shutil
import sys
import tempfile
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import phonedrop as P  # noqa: E402


def _req(url, method="GET", body=None, path=None):
    u = urllib.parse.urlparse(url)
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=10)
    c.request(method, path or u.path, body=body)
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, data


def test_files_from_the_phone_land_in_their_systems_folder_and_nothing_else_does():
    t = tempfile.mkdtemp(prefix="stone-drop-")
    events = []
    d = P.Drop(lambda n, data: events.append(data), base=os.path.join(t, "Emulation"))
    try:
        info = d.start(host="127.0.0.1")
        url = info["url"]
        assert info["open"] and url.startswith("http://127.0.0.1:") and len(url.rstrip("/").split("/")[-1]) >= 16
        st, page = _req(url)
        assert st == 200 and b"ELEGIR JUEGOS" in page and b"PlayStation 2" in page and b"http" not in page.split(b"<script>")[1]
        up = urllib.parse.urlparse(url).path + "up?name="
        st, r = _req(url, "PUT", b"x" * 3000, up + urllib.parse.quote("Metroid Fusion.gba"))
        assert st == 200 and json.loads(r)["system"] == "Game Boy Advance"
        assert os.path.getsize(os.path.join(t, "Emulation", "roms", "gba", "Metroid Fusion.gba")) == 3000
        st, r = _req(url, "PUT", b"x" * 10, up + urllib.parse.quote("Juego.iso") + "&system=ps2")       # .iso: the console chosen
        assert st == 200 and os.path.exists(os.path.join(t, "Emulation", "roms", "ps2", "Juego.iso"))
        assert _req(url, "PUT", b"x", up + "Juego.iso")[0] == 400                                    # .iso without a console: which?
        assert _req(url, "PUT", b"#!/bin/sh", up + "script.sh")[0] == 400
        st, _ = _req(url, "PUT", b"x", up + urllib.parse.quote("../../.bashrc.gba"))
        assert not os.path.exists(os.path.join(t, ".bashrc.gba"))                                    # a bare name, never a path
        bad = url.replace(url.rstrip("/").split("/")[-1], "x" * 16)
        assert _req(bad)[0] == 404 and _req(bad, "PUT", b"x", urllib.parse.urlparse(bad).path + "up?name=a.gba")[0] == 404
        assert [e["name"] for e in events if e["state"] == "received"] == ["Metroid Fusion.gba", "Juego.iso"]
        d.until = 0                                                                                 # 30 minutes later
        assert _req(url)[0] == 404
    finally:
        out = d.stop()
        shutil.rmtree(t, ignore_errors=True)
    assert len(out["received"]) == 2 and d.info() == {"open": False}


if __name__ == "__main__":
    sys.exit(run_module(globals()))
