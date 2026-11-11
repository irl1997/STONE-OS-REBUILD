"""Artwork for games that are not installed and for the store's pages.

Steam keeps artwork on disk only for games its own library has shown. STONE Home's page cannot
reach the internet (it is confined to 127.0.0.1), so the host fetches the public images of a game
from Steam's image servers and keeps them:

    ~/.cache/stone/art/<appid>/<kind>.jpg|.png     kind: capsule | hero | header
    ~/.cache/stone/art/<appid>/<kind>.none         looked for and not there (asked again after MISS_DAYS)

Without internet nothing is kept and the same pictures are asked for again later, with a pause
after repeated failures (PAUSE_S). STONE_HOME_NO_FETCH=1 (tests, development) turns fetching off.

Nothing here takes a path or an address from the page: the app id is validated, the kind is one
of KINDS, and an address (from Steam's store API) is fetched only if it is https on one of
Steam's image hosts. What comes back is kept only if it really is a JPEG or PNG picture.
"""

import itertools
import os
import queue
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

KINDS = ("capsule", "hero", "header")
CLASSIC = "https://cdn.cloudflare.steamstatic.com/steam/apps/{a}/{f}"
FILES = {"capsule": "library_600x900.jpg", "hero": "library_hero.jpg", "header": "header.jpg"}
HOST_SUFFIX = ".steamstatic.com"
MAX_BYTES = 6 * 2**20
MIN_BYTES = 2048                 # smaller than this is a placeholder, not artwork
MISS_DAYS = 7
MAX_FILES = 12000                # the cache is pruned (oldest first) beyond this
WORKERS = 3
BATCH_S = 2.0                    # news of fetched artwork is given at most this often
RETRY_S = 300                    # a picture that could not be asked for (no network) waits this long
PAUSE_AFTER = 3                  # this many network failures in a row ...
PAUSE_S = 120                    # ... and nothing is asked for this long


def disabled():
    return os.environ.get("STONE_HOME_NO_FETCH") == "1"


def root():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "stone", "art")


def valid(appid, kind):
    return isinstance(appid, str) and appid.isdigit() and 0 < len(appid) <= 10 and int(appid) > 0 and kind in KINDS


def have(appid, kind):
    """Path of the cached picture, or None."""
    if not valid(appid, kind):
        return None
    for ext in (".jpg", ".png"):
        p = os.path.join(root(), appid, kind + ext)
        if os.path.isfile(p):
            return p
    return None


def missed(appid, kind, now=None):
    """True when the picture was looked for recently and Steam did not have it."""
    if not valid(appid, kind):
        return True
    try:
        age = (now or time.time()) - os.path.getmtime(os.path.join(root(), appid, kind + ".none"))
    except OSError:
        return False
    return 0 <= age < MISS_DAYS * 86400


def allowed(url):
    """Only https addresses on Steam's own image servers are fetched."""
    if not isinstance(url, str) or len(url) > 400:
        return False
    try:
        u = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and host.endswith(HOST_SUFFIX) and u.port in (None, 443) and not u.username


def _get(url, timeout=12):
    if disabled():
        raise OSError("fetching is off (STONE_HOME_NO_FETCH)")
    req = urllib.request.Request(url, headers={"User-Agent": "STONE-OS"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(MAX_BYTES + 1)


def _ext(data):
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    return None


def fetch(appid, kind, url=None, get=None):
    """Fetch one picture into the cache. True: it is there. False: Steam does not have it
    (remembered for MISS_DAYS) or it may not be fetched. None: it could not be asked for (no
    network): nothing is left behind and it is asked for again later. Never raises."""
    if not valid(appid, kind):
        return False
    if have(appid, kind):
        return True
    if url is not None and not allowed(url):
        return False
    d = os.path.join(root(), appid)
    try:
        data = (get or _get)(url or CLASSIC.format(a=appid, f=FILES[kind]))
    except urllib.error.HTTPError as e:
        data = b"" if e.code in (403, 404, 410) else None
    except (OSError, ValueError):
        data = None
    if data is None:
        return None
    ext = _ext(data) if MIN_BYTES <= len(data) <= MAX_BYTES else None
    try:
        os.makedirs(d, exist_ok=True)
        if ext is None:
            with open(os.path.join(d, kind + ".none"), "w"):
                pass
            return False
        fd, tmp = tempfile.mkstemp(prefix="." + kind + "-", dir=d)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, os.path.join(d, kind + ext))
    except OSError:
        return None
    return True


def flags(appid):
    return {k: have(appid, k) is not None for k in KINDS}


def prune(limit=MAX_FILES):
    """Drop the oldest pictures beyond the limit. Returns how many were removed."""
    files = []
    try:
        for a in os.listdir(root()):
            d = os.path.join(root(), a)
            if a.isdigit() and os.path.isdir(d):
                for n in os.listdir(d):
                    p = os.path.join(d, n)
                    files.append((os.path.getmtime(p), p))
    except OSError:
        return 0
    files.sort()
    gone = 0
    for _t, p in files[:max(0, len(files) - limit)]:
        try:
            os.remove(p)
            gone += 1
        except OSError:
            pass
    return gone


class Fetcher:
    """Fetches artwork in the background, a few at a time, and tells which games got new pictures
    (on_news({appid: flags}), called from a worker thread, at most every BATCH_S)."""

    def __init__(self, on_news, lookup=None, fetch_one=None, workers=WORKERS, batch_s=BATCH_S):
        self.on_news, self.lookup, self.fetch_one = on_news, lookup, fetch_one or fetch
        self.batch_s = batch_s
        self.q = queue.PriorityQueue()        # (0 asked for now | 1 library, order asked, ...)
        self.seq = itertools.count()
        self.lock = threading.Lock()
        self.pending = set()             # (appid, kind) queued or being fetched
        self.news = {}
        self.last_news = 0.0
        self.workers = workers
        self.started = False
        self.retry = {}                  # (appid, kind) -> monotonic time before which it is not asked again
        self.errors = 0                  # network failures in a row
        self.pause_until = 0.0

    def want(self, appid, kinds=("capsule",), urls=None, first=False):
        """Queue the missing pictures of a game. urls: {kind: address from Steam's store API}."""
        now = time.monotonic()
        if disabled() or now < self.pause_until:
            return 0
        with self.lock:
            start, self.started = not self.started, True
        if start:
            for _ in range(self.workers):
                threading.Thread(target=self._work, daemon=True).start()
        n = 0
        for kind in kinds:
            if not valid(appid, kind) or have(appid, kind) or missed(appid, kind):
                continue
            with self.lock:
                if (appid, kind) in self.pending or now < self.retry.get((appid, kind), 0):
                    continue
                self.pending.add((appid, kind))
            url = (urls or {}).get(kind)
            self.q.put((0 if first else 1, next(self.seq), appid, kind, url if allowed(url) else None))
            n += 1
        return n

    def idle(self):
        with self.lock:
            return not self.pending

    def _work(self):
        while True:
            _prio, _seq, appid, kind, url = self.q.get()
            ok = False
            try:
                ok = self.fetch_one(appid, kind, url)
                with self.lock:
                    if ok is None:               # no network: this one later, and all of them after a few
                        self.retry[(appid, kind)] = time.monotonic() + RETRY_S
                        self.errors += 1
                        if self.errors >= PAUSE_AFTER:
                            self.pause_until, self.errors = time.monotonic() + PAUSE_S, 0
                    else:
                        self.errors = 0
                        self.retry.pop((appid, kind), None)
                if ok is False and kind == "header" and url is None and self.lookup is not None and not have(appid, kind):
                    # newer games keep their pictures under an address only the store API knows
                    found = self.lookup(appid)
                    if allowed(found):
                        self._forget_miss(appid, kind)
                        ok = self.fetch_one(appid, kind, found)
                if ok is False and kind == "capsule" and not have(appid, "header") and not missed(appid, "header"):
                    self.want(appid, ("header",))        # no tall cover: the store's wide picture instead
            except Exception as e:  # noqa: BLE001  (artwork never takes anything down)
                print(f"[stone] art: {appid}/{kind}: {e!r}", flush=True)
            with self.lock:
                self.pending.discard((appid, kind))
                if ok:
                    self.news[appid] = flags(appid)
                last = not self.pending
                due = self.news and (last or time.monotonic() - self.last_news >= self.batch_s)
                news = self.news if due else None
                if due:
                    self.news, self.last_news = {}, time.monotonic()
            if news:
                try:
                    self.on_news(news)
                except Exception as e:  # noqa: BLE001
                    print(f"[stone] art: news not delivered: {e!r}", flush=True)

    @staticmethod
    def _forget_miss(appid, kind):
        try:
            os.remove(os.path.join(root(), appid, kind + ".none"))
        except OSError:
            pass
