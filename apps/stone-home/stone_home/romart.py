"""Covers for the games of emulators (3.1.0-rc6).

Steam has no artwork for non-Steam shortcuts, so emulator games showed blank (board, 14-11-2026).
Their box art comes from libretro's public thumbnail server, the one RetroArch and most emulation
front-ends use: https://thumbnails.libretro.com/<system>/Named_Boxarts/<No-Intro name>.png.

A game's file name rarely is its No-Intro name ("Shadow of the Colossus.iso" vs "Shadow of the
Colossus (USA).png"): the system's list of names is read once (cached for two weeks) and the file name
is matched on its words (regions, discs and punctuation left out; a close match only above 0.88).
The cover is written where Steam itself keeps a shortcut's artwork, <account>/config/grid/<appid>p.png,
so Steam and STONE both show it. Only PNG files, of a sane size, are written; nothing is executed.
Nintendo Switch has no folder on that server: those games keep STONE's own cover.

The same pictures are kept in libretro's repositories on GitHub (libretro-thumbnails/<system with _>).
When the server does not answer or lists nothing (20-11-2026: its index was empty and every system's
folder answered 404, so no emulator game got a cover), the names come from GitHub's list of that
repository's Named_Boxarts folder and the picture from its raw files.
"""

import difflib
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

from . import roms
from . import shortcuts as SC

SERVER = "https://thumbnails.libretro.com/"
DIRS = {"gc": "Nintendo - GameCube", "wii": "Nintendo - Wii", "ps2": "Sony - PlayStation 2",
        "psp": "Sony - PlayStation Portable", "ps3": "Sony - PlayStation 3", "wiiu": "Nintendo - Wii U",
        "3ds": "Nintendo - Nintendo 3DS", "nds": "Nintendo - Nintendo DS", "gba": "Nintendo - Game Boy Advance",
        "dreamcast": "Sega - Dreamcast", "xbox": "Microsoft - Xbox"}
MIRROR = "https://raw.githubusercontent.com/libretro-thumbnails/{repo}/master/Named_Boxarts/{name}.png"
TREE = "https://api.github.com/repos/libretro-thumbnails/{repo}/git/trees/{ref}"
LIST_TTL_S = 14 * 86400
MAX_LIST = 8 * 2**20
MAX_TREE = 24 * 2**20            # GitHub's list of a large system (PlayStation 2) is several MB of JSON
MAX_PNG = 8 * 2**20
REGIONS = ("usa", "world", "europe", "spain", "japan")          # preferred when names tie
PNG = b"\x89PNG\r\n\x1a\n"
HREF = re.compile(r'href="([^"?/][^"]*\.png)"')


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "stone", "romart")


def _get(url, limit, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "STONE-OS"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError("too big")
    return data


def norm(name):
    """The words of a title: no extension, regions, discs, versions or punctuation."""
    n = os.path.splitext(name)[0] if re.search(r"\.[A-Za-z0-9]{2,4}$", name) else name
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()           # Pokémon -> Pokemon
    n = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", n).lower().replace("&", " and ")
    n = re.sub(r"[^0-9a-z]+", " ", n)
    n = re.sub(r"^the |, the\b| the$", " ", n)
    return " ".join(n.split())


def system_of(display_name):
    """("Juego", "ps2") from a shortcut named "Juego (PlayStation 2)", else None."""
    m = re.match(r"^(.*) \(([^()]+)\)$", display_name or "")
    if not m:
        return None
    for key, (_f, name, *_rest) in roms.SYSTEMS.items():
        if name == m.group(2):
            return m.group(1), key
    return None


def repo(system):
    """libretro's GitHub repository of a system: "Nintendo - GameCube" -> "Nintendo_-_GameCube"."""
    return DIRS[system].replace(" ", "_")


def _server_names(system, get):
    html = get(SERVER + urllib.parse.quote(DIRS[system]) + "/Named_Boxarts/", MAX_LIST).decode("utf-8", "replace")
    return sorted({urllib.parse.unquote(h)[:-4] for h in HREF.findall(html)})


def _mirror_names(system, get):
    def tree(ref):
        d = json.loads(get(TREE.format(repo=repo(system), ref=ref), MAX_TREE).decode("utf-8", "replace"))
        return d.get("tree") if isinstance(d, dict) and isinstance(d.get("tree"), list) else []
    box = [e.get("sha") for e in tree("master") if isinstance(e, dict) and e.get("path") == "Named_Boxarts" and e.get("type") == "tree"]
    if not box or not isinstance(box[0], str) or not re.fullmatch(r"[0-9a-f]{40}", box[0]):
        return []
    return sorted({e["path"][:-4] for e in tree(box[0]) if isinstance(e, dict) and isinstance(e.get("path"), str)
                   and e["path"].endswith(".png") and "/" not in e["path"]})


def listing(system, get=_get, now=time.time):
    """Names (without .png) of the box arts libretro has for a system, cached; and where they are:
    (names, "server" | "mirror")."""
    if system not in DIRS:
        return [], "server"
    path = os.path.join(cache_dir(), system + ".json")
    try:
        with open(path) as f:
            d = json.load(f)
        # an empty list (kept by 3.1.0-rc11 when the server answered with nothing) is asked again
        if now() - d.get("t", 0) < LIST_TTL_S and isinstance(d.get("names"), list) and d["names"]:
            return d["names"], d.get("src") if d.get("src") in ("server", "mirror") else "server"
    except (OSError, ValueError):
        pass
    try:
        names, src = _server_names(system, get), "server"
    except (OSError, ValueError):
        names, src = [], "server"
    if not names:                                       # the server is down or empty: libretro's GitHub copy
        names, src = _mirror_names(system, get), "mirror"
    if not names:
        return [], src                                  # nothing to keep: asked again next time
    os.makedirs(cache_dir(), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"t": now(), "names": names, "src": src}, f)
    os.replace(tmp, path)
    return names, src


def cover_url(system, name, src="server"):
    if src == "mirror":
        return MIRROR.format(repo=repo(system), name=urllib.parse.quote(name))
    return SERVER + urllib.parse.quote(DIRS[system]) + "/Named_Boxarts/" + urllib.parse.quote(name + ".png")


def best(title, names):
    """The libretro name for a game title, or None."""
    want = norm(title)
    if not want:
        return None
    by = {}
    for n in names:
        by.setdefault(norm(n), []).append(n)
    cands = by.get(want)
    if not cands:
        close = difflib.get_close_matches(want, list(by), n=1, cutoff=0.88)
        cands = by.get(close[0]) if close else None
    if not cands and len(want.split()) >= 2:
        # every word of the title, in a name with at most two more ("Pokemon Emerald" ->
        # "Pokemon - Emerald Version"): the one with the fewest extra words
        w = set(want.split())
        fits = sorted((len(k.split()) - len(w), k) for k in by if w <= set(k.split()) and len(k.split()) - len(w) <= 2)
        cands = by.get(fits[0][1]) if fits else None
    if not cands:
        return None

    def rank(n):
        low = n.lower()
        reg = next((i for i, r in enumerate(REGIONS) if r in low), len(REGIONS))
        return (("disc" in low) and "disc 1" not in low, "demo" in low or "beta" in low or "proto" in low, reg, len(n))
    return sorted(cands, key=rank)[0]


def grid_paths(root, appid):
    return [os.path.join(a, "config", "grid", f"{appid}p.png") for a in SC.accounts(root)]


def fetch(root, appid, display_name, get=_get):
    """Write the cover of one emulator game. Returns the libretro name used, or None."""
    sg = system_of(display_name)
    if not sg or not str(appid).isdigit():
        return None
    title, system = sg
    names, src = listing(system, get=get)
    name = best(title, names)
    if not name:
        return None
    try:
        data = get(cover_url(system, name, src), MAX_PNG)
    except (OSError, ValueError):
        if src != "server":
            raise
        data = get(cover_url(system, name, "mirror"), MAX_PNG)    # the server's list was kept, its pictures are gone
    if not data.startswith(PNG):
        return None
    written = False
    for p in grid_paths(root, appid):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".stone-tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, p)
        written = True
    return name if written else None
