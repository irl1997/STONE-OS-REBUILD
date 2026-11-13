"""The account's games kept between boots (stone_home/account.py) and the artwork STONE fetches for
games Steam has not cached (stone_home/artcache.py). Pure Python: no network, no Steam.

    python3 tests/test_account_art.py     (or: pytest tests/test_account_art.py)
"""

import os
import shutil
import sys
import tempfile
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import account as AC  # noqa: E402
from stone_home import artcache as ART  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"j" * 4000
PNG = b"\x89PNG\r\n\x1a\n" + b"p" * 4000


class Cache:
    """A private ~/.cache for one test."""

    def __enter__(self):
        self.d = tempfile.mkdtemp(prefix="stone-cache-")
        self.old = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = self.d
        return self.d

    def __exit__(self, *a):
        if self.old is None:
            del os.environ["XDG_CACHE_HOME"]
        else:
            os.environ["XDG_CACHE_HOME"] = self.old
        shutil.rmtree(self.d, ignore_errors=True)


def test_account_list_is_kept_per_account_and_bad_rows_are_dropped():
    rows = [(35140, "Batman", False, 48, 99, 0), (620, "Portal 2", True, 600, 1700000000, 12_000)]
    with Cache():
        assert AC.load("12345678") is None
        assert AC.save("12345678", rows + [("x", "bad", 0, 0, 0, 0), (0, "zero", 0, 0, 0, 0), (7, 5, 0, 0, 0, 0), [1, "short"]])
        assert AC.load("12345678") == rows
        assert AC.load("999") is None and AC.load(None) is None            # another account never sees it
        assert not AC.save("12345678", [])                                # Steam still loading: the list stays
        assert AC.load("12345678") == rows
        assert not AC.save("../etc", rows) and not AC.save(None, rows)
        with open(AC.path(), "w") as f:
            f.write("{damaged")
        assert AC.load("12345678") is None
        AC.forget()
        assert not os.path.exists(AC.path())
    assert AC.clean("nope") == [] and AC.clean([[1, "a", 1, True, 0, 0]]) == []   # booleans are not numbers


def test_signature_changes_with_games_state_artwork_and_liveness():
    g = [{"appid": "620", "installed": True, "updating": False, "name": "Portal 2", "art": {"capsule": True, "hero": False}}]
    base = AC.signature(g, True)
    assert AC.signature([dict(g[0])], True) == base
    assert AC.signature(g, False) != base
    assert AC.signature([dict(g[0], installed=False)], True) != base
    assert AC.signature([dict(g[0], art={"capsule": True, "hero": True})], True) != base
    assert AC.signature(g + [dict(g[0], appid="730")], True) != base
    assert AC.signature_rows([(1, "a", True, 5, 6, 7)]) == AC.signature_rows([(1, "a", 1, 9, 9, 9)])


def test_signed_out_is_believed_only_after_steam_keeps_saying_it():
    t = [100.0]
    s = AC.SignIn(clock=lambda: t[0])
    assert s.state(None) is None
    assert s.state("out") is None                      # Steam says "nobody" for a moment at every start
    t[0] += AC.OUT_CONFIRM_S - 1
    assert s.state("out") is None
    t[0] += 2
    assert s.state("out") == "out"
    assert s.state("in") == "in" and s.state("out") is None        # the count starts again
    t[0] += AC.OUT_CONFIRM_S + 1
    assert s.state("out") == "out" and s.state("out", has_games=True) == "in"


def test_only_steams_image_servers_and_real_pictures_reach_the_cache():
    for ok in ("https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/3527290/abc/header.jpg?t=1",
               "https://cdn.cloudflare.steamstatic.com/steam/apps/620/header.jpg"):
        assert ART.allowed(ok), ok
    for bad in ("http://cdn.cloudflare.steamstatic.com/steam/apps/620/header.jpg", "https://steamstatic.com.evil.example/x.jpg",
                "https://evil.example/steamstatic.com/x.jpg", "file:///etc/passwd", "https://user@cdn.cloudflare.steamstatic.com/x",
                "https://cdn.cloudflare.steamstatic.com:8443/x", "", None, 5, "https://127.0.0.1/x", "https://x.steamstatic.com/" + "a" * 500):
        assert not ART.allowed(bad), bad
    assert ART.valid("620", "capsule") and not ART.valid("620", "logo") and not ART.valid("../620", "hero")
    assert not ART.valid("0", "hero") and not ART.valid(620, "hero") and not ART.valid("1" * 11, "hero")
    with Cache():
        seen = []

        def get(url):
            seen.append(url)
            return {"library_600x900.jpg": JPEG, "library_hero.jpg": PNG}.get(url.rsplit("/", 1)[-1], b"<html>not found</html>" * 200)
        assert ART.fetch("620", "capsule", get=get) and ART.have("620", "capsule").endswith("capsule.jpg")
        assert ART.fetch("620", "hero", get=get) and ART.have("620", "hero").endswith("hero.png")
        assert seen == [ART.CLASSIC.format(a="620", f="library_600x900.jpg"), ART.CLASSIC.format(a="620", f="library_hero.jpg")]
        assert ART.fetch("620", "capsule", get=get) and len(seen) == 2          # already there: nothing is fetched
        assert not ART.fetch("620", "header", get=get)                          # a web page, not a picture
        assert ART.have("620", "header") is None and ART.missed("620", "header")
        assert not ART.missed("620", "header", now=time.time() + (ART.MISS_DAYS + 1) * 86400)   # asked again later
        assert ART.flags("620") == {"capsule": True, "hero": True, "header": False, "hero2x": False}
        # the background at twice the size (3.1.0-rc4): its own file on Steam's servers; older games have none
        assert ART.valid("620", "hero2x") and ART.FILES["hero2x"] == "library_hero_2x.jpg"
        assert not ART.fetch("620", "hero2x", get=get) and ART.missed("620", "hero2x")
        assert seen[-1] == ART.CLASSIC.format(a="620", f="library_hero_2x.jpg")
        assert not ART.fetch("620", "header", url="https://evil.example/x.jpg", get=get)       # never fetched
        assert not ART.fetch("../../x", "capsule", get=get) and not ART.fetch("620", "logo", get=get)
        assert len(seen) == 4                    # the cover, the big picture, the wide one, the big one at twice the size

        def offline(url):
            raise OSError("no network")
        assert ART.fetch("730", "capsule", get=offline) is None                 # could not be asked for: later
        assert not ART.missed("730", "capsule")                                 # a network error is not "not there"

        def gone(url):
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        assert not ART.fetch("730", "capsule", get=gone) and ART.missed("730", "capsule")
        assert not ART.fetch("731", "capsule", get=lambda u: JPEG[:100]) and ART.missed("731", "capsule")   # a placeholder
        assert not ART.fetch("732", "capsule", get=lambda u: b"\xff\xd8\xff" + b"x" * (ART.MAX_BYTES + 1))
        assert ART.prune(limit=2) >= 2 and ART.prune(limit=100) == 0


def _wait(cond, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_fetcher_falls_back_to_the_stores_wide_picture_and_tells_what_arrived():
    with Cache():
        news, asked = [], []
        hashed = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/3527290/31ba/header.jpg?t=1"

        def get(url):
            asked.append(url)
            if url.endswith("/620/library_600x900.jpg") or url == hashed:
                return JPEG
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

        def lookup(appid):
            asked.append(("lookup", appid))
            return hashed if appid == "3527290" else "https://evil.example/header.jpg"
        f = ART.Fetcher(news.append, lookup=lookup, fetch_one=lambda a, k, u=None: ART.fetch(a, k, u, get=get), batch_s=0)
        assert f.want("620", ("capsule",)) == 1 and f.want("620", ("capsule",)) <= 1
        assert f.want("3527290", ("capsule",)) == 1              # a newer game: no classic pictures
        assert f.want("999", ("capsule",)) == 1                  # nothing anywhere
        assert f.want("../x", ("capsule",)) == 0 and f.want("620", ("logo",)) == 0
        assert _wait(f.idle), "the fetcher did not finish"
        got = {}
        for n in news:
            got.update(n)
        assert got["620"] == {"capsule": True, "hero": False, "header": False, "hero2x": False}
        assert got["3527290"] == {"capsule": False, "hero": False, "header": True, "hero2x": False}     # the wide picture instead
        assert "999" not in got and ART.missed("999", "capsule") and ART.missed("999", "header")
        assert ("lookup", "3527290") in asked and ("lookup", "999") in asked
        assert "https://evil.example/header.jpg" not in asked
        n = len(asked)
        assert f.want("620", ("capsule",)) == 0 and f.want("999", ("capsule", "header")) == 0   # there, or known missing
        time.sleep(0.1)
        assert len(asked) == n


def test_without_network_the_fetcher_waits_instead_of_asking_again_and_again():
    with Cache():
        asked = []

        def offline(a, k, u=None):
            asked.append((a, k))
            return ART.fetch(a, k, u, get=lambda url: (_ for _ in ()).throw(OSError("no network")))
        f = ART.Fetcher(lambda news: None, fetch_one=offline, workers=1, batch_s=0)
        for a in ("1", "2", "3"):
            assert f.want(a, ("capsule",)) == 1
        assert _wait(f.idle) and len(asked) == ART.PAUSE_AFTER
        assert f.pause_until > time.monotonic()
        assert f.want("4", ("capsule",)) == 0 and f.want("1", ("capsule",)) == 0      # paused: nothing is asked
        f.pause_until = 0
        assert f.want("1", ("capsule",)) == 0                                          # this one waits RETRY_S
        assert f.want("4", ("capsule",)) == 1 and _wait(f.idle)
        assert not ART.missed("1", "capsule")                                          # still not "missing"
        os.environ["STONE_HOME_NO_FETCH"] = "1"
        try:
            f.pause_until = 0
            assert ART.disabled() and f.want("5", ("capsule",)) == 0
            assert ART.fetch("5", "capsule") is None and not ART.missed("5", "capsule")
        finally:
            del os.environ["STONE_HOME_NO_FETCH"]


if __name__ == "__main__":
    sys.exit(run_module(globals()))
