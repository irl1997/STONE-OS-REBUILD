"""STONE STORAGE and DOWNLOADS (stone_home/storage.py) on the fake Steam folder. Pure Python.

    python3 tests/test_storage.py     (or: pytest tests/test_storage.py)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import run_module  # noqa: E402

import steam_fixture as FX  # noqa: E402
from stone_home import storage as ST  # noqa: E402


def _cache(root, lib, appid, n):
    d = os.path.join(lib, "steamapps", "shadercache", str(appid), "fozpipelinesv6")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cache.foz"), "wb") as f:
        f.write(b"x" * n)


def test_libraries_games_downloads_and_cache_cleaning():
    t = tempfile.mkdtemp(prefix="stone-storage-")
    try:
        root = FX.build(os.path.join(t, "Steam"))
        lib2 = os.path.join(root, "lib2")
        _cache(root, root, 1001, 5000)
        with open(os.path.join(lib2, "steamapps", "appmanifest_1003.acf")) as f:
            text = f.read()
        with open(os.path.join(lib2, "steamapps", "appmanifest_1003.acf"), "w") as f:
            f.write(text.replace('"StateFlags"', '"BytesDownloaded"\t\t"250"\n\t"BytesToDownload"\t\t"1000"\n\t"StateFlags"'))
        s = ST.status(root)
        assert len(s["libraries"]) == 2 and all(lib["total"] for lib in s["libraries"])
        names = [g["name"] for g in s["games"]]
        assert "Marea Lenta" in names and "Proton 9.0" not in names and len(names) == len(set(names)), names
        mar = next(g for g in s["games"] if g["appid"] == "1001")
        assert mar["shader_cache"] == 5000 and mar["library"] == os.path.realpath(root)
        assert s["downloads"] == [{"appid": "1003", "name": "Ceniza", "downloaded": 250, "total": 1000, "progress": 0.25, "installed": True}]
        r = ST.clear_shader_cache(root, "1001")
        assert r == {"ok": True, "freed": 5000} and not os.path.exists(os.path.join(root, "steamapps", "shadercache", "1001"))
        assert ST.clear_shader_cache(root, "../../etc") == {"error": "Juego no válido"}
        assert ST.clear_shader_cache(root, "1002") == {"ok": True, "freed": 0}
    finally:
        shutil.rmtree(t)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
