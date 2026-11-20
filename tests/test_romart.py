"""Covers for emulator games (stone_home/romart.py) against a stand-in of libretro's thumbnail server.
Pure Python, no network.

    python3 tests/test_romart.py     (or: pytest tests/test_romart.py)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import romart as RA  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64
LIST = ('<a href="?C=N;O=D">Name</a><a href="/Sony%20-%20PlayStation%202/">Parent</a>'
        '<a href="Shadow%20of%20the%20Colossus%20(Europe).png">x</a><a href="Shadow%20of%20the%20Colossus%20(USA).png">x</a>'
        '<a href="Shadow%20of%20the%20Colossus%20(USA)%20(Demo).png">x</a><a href="Ratchet%20%26%20Clank%20(USA).png">x</a>'
        '<a href="Final%20Fantasy%20X%20(USA).png">x</a><a href="Final%20Fantasy%20X-2%20(USA).png">x</a>').encode()


class Server:
    def __init__(self, body=PNG):
        self.calls, self.body = [], body

    def __call__(self, url, limit, timeout=30):
        self.calls.append(url)
        return LIST if url.endswith("/Named_Boxarts/") else self.body


def test_a_file_name_finds_its_no_intro_cover():
    names = ["Shadow of the Colossus (Europe)", "Shadow of the Colossus (USA)", "Shadow of the Colossus (USA) (Demo)",
             "Ratchet & Clank (USA)", "Final Fantasy X (USA)", "Final Fantasy X-2 (USA)"]
    assert RA.best("Shadow of the Colossus", names) == "Shadow of the Colossus (USA)"       # USA first, never the demo
    assert RA.best("ratchet and clank [SCUS-97199]", names) == "Ratchet & Clank (USA)"
    assert RA.best("Final Fantasy X", names) == "Final Fantasy X (USA)"                       # not X-2
    assert RA.best("Final Fantasy X-2", names) == "Final Fantasy X-2 (USA)"
    assert RA.best("Un juego casero", names) is None and RA.best("", names) is None
    assert RA.best("Pokémon Emerald", ["Pokemon - Emerald Version (USA, Europe)", "Pokemon - Ruby Version (USA)"]) == "Pokemon - Emerald Version (USA, Europe)"
    assert RA.system_of("Shadow of the Colossus (PlayStation 2)") == ("Shadow of the Colossus", "ps2")
    assert RA.system_of("Ryujinx (Ryubing)") is None and RA.system_of("Dolphin") is None


def test_the_cover_is_written_where_steam_keeps_a_shortcuts_artwork():
    t = tempfile.mkdtemp(prefix="stone-romart-")
    old = os.environ.get("XDG_CACHE_HOME")
    os.environ["XDG_CACHE_HOME"] = os.path.join(t, "cache")
    try:
        root = os.path.join(t, "Steam")
        os.makedirs(os.path.join(root, "userdata", "12345678", "config"))
        srv = Server()
        assert RA.fetch(root, "3000000001", "Shadow of the Colossus (PlayStation 2)", get=srv) == "Shadow of the Colossus (USA)"
        p = os.path.join(root, "userdata", "12345678", "config", "grid", "3000000001p.png")
        assert open(p, "rb").read() == PNG
        assert srv.calls[-1].endswith("/Sony%20-%20PlayStation%202/Named_Boxarts/Shadow%20of%20the%20Colossus%20%28USA%29.png")
        n = len(srv.calls)
        RA.fetch(root, "3000000002", "Ratchet and Clank (PlayStation 2)", get=srv)
        assert len(srv.calls) == n + 1                                  # the list is cached: only the picture is asked
        assert RA.fetch(root, "3000000003", "Zelda (Nintendo Switch)", get=srv) is None         # no Switch on that server
        bad = Server(body=b"<html>not a picture</html>")
        assert RA.fetch(root, "3000000004", "Final Fantasy X (PlayStation 2)", get=bad) is None
        assert not os.path.exists(os.path.join(root, "userdata", "12345678", "config", "grid", "3000000004p.png"))
    finally:
        if old is None:
            os.environ.pop("XDG_CACHE_HOME", None)
        else:
            os.environ["XDG_CACHE_HOME"] = old
        shutil.rmtree(t, ignore_errors=True)


class Mirror:
    """libretro's server down (404 for everything) and its GitHub copy answering."""
    SHA = "41b22bdc" + "0" * 32

    def __init__(self, server_body=None):
        self.calls, self.server_body = [], server_body

    def __call__(self, url, limit, timeout=30):
        import json
        import urllib.error
        self.calls.append(url)
        if url.startswith(RA.SERVER):
            if self.server_body is not None:
                return self.server_body
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        if url.endswith("/git/trees/master"):
            return json.dumps({"tree": [{"path": "Named_Boxarts", "type": "tree", "sha": self.SHA},
                                        {"path": "Named_Snaps", "type": "tree", "sha": "1" * 40}]}).encode()
        if url.endswith("/git/trees/" + self.SHA):
            return json.dumps({"tree": [{"path": "Metroid Prime (USA).png", "type": "blob"}, {"path": "Metroid Prime (Japan).png", "type": "blob"},
                                        {"path": "readme.txt", "type": "blob"}]}).encode()
        if url.startswith("https://raw.githubusercontent.com/libretro-thumbnails/Nintendo_-_GameCube/master/Named_Boxarts/"):
            return PNG
        raise AssertionError(url)


def test_without_libretros_server_the_cover_comes_from_its_github_copy():
    t = tempfile.mkdtemp(prefix="stone-romart-")
    old = os.environ.get("XDG_CACHE_HOME")
    os.environ["XDG_CACHE_HOME"] = os.path.join(t, "cache")
    try:
        root = os.path.join(t, "Steam")
        os.makedirs(os.path.join(root, "userdata", "12345678", "config"))
        for srv in (Mirror(), Mirror(server_body=b"<html>Index of /</html>")):     # 404, or an empty index
            shutil.rmtree(os.path.join(t, "cache"), ignore_errors=True)
            assert RA.fetch(root, "3000000010", "Metroid Prime (GameCube)", get=srv) == "Metroid Prime (USA)"
            assert srv.calls[-1] == ("https://raw.githubusercontent.com/libretro-thumbnails/Nintendo_-_GameCube/master/"
                                     "Named_Boxarts/Metroid%20Prime%20%28USA%29.png")
            assert RA.listing("gc", get=srv) == (["Metroid Prime (Japan)", "Metroid Prime (USA)"], "mirror")
        # a list kept from the server whose pictures are gone: the picture from the copy
        import json
        with open(os.path.join(t, "cache", "stone", "romart", "gc.json"), "w") as f:
            json.dump({"t": __import__("time").time(), "names": ["Metroid Prime (USA)"]}, f)
        srv = Mirror()
        assert RA.fetch(root, "3000000011", "Metroid Prime (GameCube)", get=srv) == "Metroid Prime (USA)"
        assert srv.calls[0].startswith(RA.SERVER) and srv.calls[-1].startswith("https://raw.githubusercontent.com/")
        # an empty list kept by rc11 is not trusted: asked again
        with open(os.path.join(t, "cache", "stone", "romart", "gc.json"), "w") as f:
            json.dump({"t": __import__("time").time(), "names": []}, f)
        assert RA.listing("gc", get=Mirror())[0] == ["Metroid Prime (Japan)", "Metroid Prime (USA)"]
    finally:
        if old is None:
            os.environ.pop("XDG_CACHE_HOME", None)
        else:
            os.environ["XDG_CACHE_HOME"] = old
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
