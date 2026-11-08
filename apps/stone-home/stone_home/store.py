"""Search Steam's store from STONE Home (M13): Steam's public store search (no account, no key).

    https://store.steampowered.com/api/storesearch/?term=<words>&l=spanish&cc=<country>

Returns games with their app id and whether they are free. STONE Home lists them next to the
matches of the person's own library: a game of the account opens its page (install, play), a free
game can be installed from STONE, a paid game is bought in Steam (STONE never handles payments).
"""

import json
import urllib.parse
import urllib.request

API = "https://store.steampowered.com/api/storesearch/"
MAX = 20


def _get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "STONE-OS"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(2 * 2**20).decode("utf-8", "replace")


def search(term, cc="US", get=_get):
    """[{"appid", "name", "free"}] or {"error": "..."}."""
    if not isinstance(term, str) or not 1 <= len(term.strip()) <= 60:
        return {"error": "Escribe entre 1 y 60 letras"}
    if not isinstance(cc, str) or len(cc) != 2 or not cc.isalpha():
        cc = "US"
    url = API + "?" + urllib.parse.urlencode({"term": term.strip(), "l": "spanish", "cc": cc})
    try:
        d = json.loads(get(url))
    except (OSError, ValueError) as e:
        return {"error": f"La tienda de Steam no responde ({e.__class__.__name__}): ¿hay conexión a internet?"}
    out = []
    for it in (d.get("items") or [] if isinstance(d, dict) else []):
        if not isinstance(it, dict) or it.get("type") not in (None, "app") or not isinstance(it.get("id"), int):
            continue
        name = it.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        out.append({"appid": str(it["id"]), "name": name.strip()[:120], "free": "price" not in it})
        if len(out) >= MAX:
            break
    return {"results": out}
