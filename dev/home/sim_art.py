#!/usr/bin/env python3
"""The real covers of the simulation's games, for a local preview (never committed: it is the publishers' art).

The simulation paints a landscape for every game unless the page brings real art (sim_host.js artOf,
window.STONE_SIM_ART). This fetches it, the same way the console does:

  - Steam games and the store's: capsule (600 x 900), hero (1920 x 620), hero2x (3840 x 1240, when the
    game has it) and header, from Steam's image server (artcache.CLASSIC);
  - emulator games ("Juego (GameCube)"): the box art from libretro's thumbnails (romart);
  - the emulators themselves and the made-up store entries keep STONE's own cover.

    python3 dev/home/sim_art.py ART_DIR                  # ART_DIR/<appid>/<kind>.jpg|png
    python3 dev/home/build_simulation.py OUT.html --art ART_DIR

What comes back is kept only if it is a JPEG or PNG picture; nothing fetched is run. Files already
there are not fetched again.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))

from stone_home import artcache, romart  # noqa: E402

KINDS = ("capsule", "hero", "hero2x", "header")
ENTRY = re.compile(r"\{ appid: '(\d+)', name: (?:'((?:[^'\\]|\\.)*)'|\"([^\"]*)\")")


def games(src):
    """(appid, name) of every game and store entry in sim_host.js."""
    seen = {}
    for m in ENTRY.finditer(src):
        seen.setdefault(m.group(1), (m.group(2) or m.group(3) or "").replace("\\'", "'"))
    return list(seen.items())


def picture(data):
    return artcache._ext(data) if data and len(data) >= artcache.MIN_BYTES else None


def save(d, kind, data):
    ext = picture(data)
    if not ext:
        return False
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, kind + ext), "wb") as f:
        f.write(data)
    return True


def have(d, kind):
    return any(os.path.isfile(os.path.join(d, kind + e)) for e in (".jpg", ".png"))


STORE_ITEMS = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?input_json="
STORE_KEYS = {"capsule": "library_capsule", "hero": "library_hero", "hero2x": "library_hero_2x", "header": "header"}
STORE_HOST = "https://shared.akamai.steamstatic.com/store_item_assets/"


def store_assets(appid):
    """{kind: address} from Steam's store: newer games keep their pictures under hashed names only."""
    q = {"ids": [{"appid": int(appid)}], "context": {"language": "english", "country_code": "US"},
         "data_request": {"include_assets": True}}
    try:
        d = json.loads(artcache._get(STORE_ITEMS + urllib.parse.quote(json.dumps(q)), timeout=20))
        a = d["response"]["store_items"][0]["assets"]
        fmt = a["asset_url_format"]
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError):
        return {}
    out = {}
    for kind, key in STORE_KEYS.items():
        if isinstance(a.get(key), str) and isinstance(fmt, str):
            url = STORE_HOST + fmt.replace("${FILENAME}", a[key])
            if artcache.allowed(url):
                out[kind] = url
    return out


def steam(appid, d):
    got, store = [], None
    for kind in KINDS:
        if have(d, kind):
            got.append(kind)
            continue
        try:
            data = artcache._get(artcache.CLASSIC.format(a=appid, f=artcache.FILES[kind]), timeout=20)
        except (urllib.error.URLError, OSError, ValueError):
            data = None
        if not picture(data):
            store = store_assets(appid) if store is None else store
            try:
                data = artcache._get(store[kind], timeout=20) if kind in store else None
            except (urllib.error.URLError, OSError, ValueError):
                data = None
        if save(d, kind, data):
            got.append(kind)
    return got


def rom(name, d):
    if have(d, "capsule"):
        return ["capsule"]
    sg = romart.system_of(name)
    if not sg:
        return []
    title, system = sg
    names, src = romart.listing(system)
    found = romart.best(title, names)
    if not found:
        return []
    return ["capsule"] if save(d, "capsule", romart._get(romart.cover_url(system, found, src), romart.MAX_PNG)) else []


def main(out):
    os.environ["XDG_CACHE_HOME"] = os.path.join(out, ".cache")      # libretro's lists, next to the art
    with open(os.path.join(HERE, "sim_host.js"), encoding="utf-8") as f:
        src = f.read()
    for appid, name in games(src):
        d = os.path.join(out, appid)
        try:
            # Steam's app ids are short; STONE's shortcuts have ten digits (the emulators: STONE's cover)
            got = rom(name, d) if romart.system_of(name) else steam(appid, d) if len(appid) < 10 else []
        except Exception as e:  # noqa: BLE001  (one game without art never stops the rest)
            print(f"{appid} {name}: {e!r}")
            continue
        print(f"{appid} {name}: {', '.join(got) or 'STONE cover'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
