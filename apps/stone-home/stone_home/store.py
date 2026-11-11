"""Steam's store inside STONE Home (M13, D-30): search, the shop window and a game's page, read
from Steam's public store API (no account, no key).

    https://store.steampowered.com/api/storesearch/?term=<words>&l=spanish
    https://store.steampowered.com/api/featuredcategories/?l=spanish
    https://store.steampowered.com/api/appdetails/?appids=<id>&l=spanish

No country is sent: Steam answers with the prices and the currency of the place the console
connects from, the same ones the person will see when paying.

Read only. STONE never handles a payment or a password: a paid game is bought in Steam's own
interface (shown in front by the STONE session) or on the person's phone; a free game and a game
already in the account are installed from STONE.

Image addresses in the answers ("_header") are for the host's artwork cache (artcache.py), which
only fetches from Steam's own image servers; they never reach the page.
"""

import html
import json
import os
import re
import urllib.parse
import urllib.request

API = "https://store.steampowered.com/api/storesearch/"
FEATURED = "https://store.steampowered.com/api/featuredcategories/"
DETAILS = "https://store.steampowered.com/api/appdetails/"
MAX = 20
SECTIONS = (("specials", "Ofertas"), ("top_sellers", "Lo más vendido"), ("new_releases", "Novedades"),
            ("coming_soon", "Próximamente"))
SECTION_MAX = 12
OFFLINE = "La tienda de Steam no responde ({}): ¿hay conexión a internet?"


def _get(url, timeout=10):
    if os.environ.get("STONE_HOME_NO_FETCH") == "1":          # tests and development: nothing is fetched
        raise OSError("fetching is off (STONE_HOME_NO_FETCH)")
    req = urllib.request.Request(url, headers={"User-Agent": "STONE-OS"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(2 * 2**20).decode("utf-8", "replace")


def money(cents, currency):
    """'12,99 USD' / '2.604 CLP' from Steam's hundredths; None when it is not a price."""
    if not isinstance(cents, int) or isinstance(cents, bool) or cents < 0 \
            or not isinstance(currency, str) or not currency.isalpha() or len(currency) != 3:
        return None
    whole, part = divmod(cents, 100)
    text = f"{whole:,}".replace(",", ".")
    return f"{text},{part:02d} {currency.upper()}" if part else f"{text} {currency.upper()}"


def _text(v, limit):
    """Plain text from one of Steam's strings (they carry HTML): tags out, entities decoded."""
    if not isinstance(v, str):
        return ""
    v = re.sub(r"<br\s*/?>|</p>|</h\d>|</li>", "\n", v, flags=re.I)
    v = html.unescape(re.sub(r"<[^>]{0,400}>", "", v))
    v = re.sub(r"[ \t\r\f\v]+", " ", v)
    v = re.sub(r"\s*\n\s*", "\n", v).strip()
    return v[:limit]


def _price(final, initial, currency, discount):
    """(price text or None, price before the discount or None, discount %)."""
    now = money(final, currency)
    pct = discount if isinstance(discount, int) and not isinstance(discount, bool) and 0 < discount <= 100 else 0
    was = money(initial, currency) if pct and isinstance(initial, int) and isinstance(final, int) and initial > final else None
    return now, was, pct if was else 0


def search(term, get=None):
    """{"results": [{"appid", "name", "free", "price"}]} or {"error": "..."}."""
    if not isinstance(term, str) or not 1 <= len(term.strip()) <= 60:
        return {"error": "Escribe entre 1 y 60 letras"}
    url = API + "?" + urllib.parse.urlencode({"term": term.strip(), "l": "spanish"})
    try:
        d = json.loads((get or _get)(url))
    except (OSError, ValueError) as e:
        return {"error": OFFLINE.format(e.__class__.__name__)}
    out = []
    for it in (d.get("items") or [] if isinstance(d, dict) else []):
        if not isinstance(it, dict) or it.get("type") not in (None, "app") or not isinstance(it.get("id"), int) or it["id"] <= 0:
            continue
        name = it.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        p = it.get("price") if isinstance(it.get("price"), dict) else None
        now = _price(p.get("final"), p.get("initial"), p.get("currency"), 0)[0] if p else None
        out.append({"appid": str(it["id"]), "name": name.strip()[:120], "free": p is None, "price": now})
        if len(out) >= MAX:
            break
    return {"results": out}


def _item(it):
    if not isinstance(it, dict) or it.get("type") != 0 or not isinstance(it.get("id"), int) or it["id"] <= 0:
        return None                                   # 0 = a game or program; packs and bundles are left out
    name = it.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    now, was, pct = _price(it.get("final_price"), it.get("original_price"), it.get("currency"), it.get("discount_percent"))
    free = it.get("final_price") == 0 and it.get("original_price") in (0, None)
    return {"appid": str(it["id"]), "name": name.strip()[:120], "free": bool(free),
            "price": None if free else now, "was": was, "discount": pct,
            "_header": it.get("header_image") if isinstance(it.get("header_image"), str) else None}


def featured(get=None):
    """{"sections": [{"key", "title", "items": [...]}]} (the store's own lists) or {"error"}."""
    try:
        d = json.loads((get or _get)(FEATURED + "?" + urllib.parse.urlencode({"l": "spanish"})))
    except (OSError, ValueError) as e:
        return {"error": OFFLINE.format(e.__class__.__name__)}
    out, seen = [], set()
    for key, title in SECTIONS:
        sec = d.get(key) if isinstance(d, dict) else None
        items = []
        for it in (sec.get("items") or [] if isinstance(sec, dict) else []):
            row = _item(it)
            if row is None or row["appid"] in seen:
                continue
            if key == "coming_soon":
                row["price"], row["free"], row["soon"] = None, False, True
            seen.add(row["appid"])
            items.append(row)
            if len(items) >= SECTION_MAX:
                break
        if items:
            out.append({"key": key, "title": title, "items": items})
    if not out:
        return {"error": "La tienda de Steam respondió sin listas. Prueba a buscar el juego por su nombre."}
    return {"sections": out}


def details(appid, get=None):
    """A game's page: {"appid", "name", "about", "price", "was", "discount", "free", "soon",
    "genres", "release", "by", "kind", "_header"} or {"error"}."""
    if not isinstance(appid, str) or not appid.isdigit() or not 0 < len(appid) <= 10 or int(appid) <= 0:
        return {"error": "Juego desconocido"}
    try:
        d = json.loads((get or _get)(DETAILS + "?" + urllib.parse.urlencode({"appids": appid, "l": "spanish"})))
    except (OSError, ValueError) as e:
        return {"error": OFFLINE.format(e.__class__.__name__)}
    node = d.get(appid) if isinstance(d, dict) else None
    data = node.get("data") if isinstance(node, dict) and node.get("success") else None
    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
        return {"error": "Steam no tiene ficha de tienda para este juego en tu región."}
    p = data.get("price_overview") if isinstance(data.get("price_overview"), dict) else None
    now, was, pct = _price(p.get("final"), p.get("initial"), p.get("currency"), p.get("discount_percent")) if p else (None, None, 0)
    rel = data.get("release_date") if isinstance(data.get("release_date"), dict) else {}
    soon = bool(rel.get("coming_soon"))
    free = bool(data.get("is_free")) and not soon
    genres = [g["description"].strip()[:30] for g in data.get("genres") or []
              if isinstance(g, dict) and isinstance(g.get("description"), str) and g["description"].strip()][:4]
    by = [x.strip()[:60] for x in data.get("developers") or [] if isinstance(x, str) and x.strip()][:2]
    return {"appid": appid, "name": data["name"].strip()[:120], "about": _text(data.get("short_description"), 600),
            "price": None if free else now, "was": was, "discount": pct, "free": free, "soon": soon,
            "genres": genres, "release": _text(rel.get("date"), 40), "by": by,
            "kind": data.get("type") if data.get("type") in ("game", "dlc", "demo", "application", "music") else "other",
            "_header": data.get("header_image") if isinstance(data.get("header_image"), str) else None}


def header_url(appid, get=None):
    """The address of a game's store image when the classic one does not exist (newer games)."""
    d = details(appid, get=get)
    return d.get("_header")


def page_url(appid):
    """The game's page on Steam's web store: what the QR code for the phone carries."""
    if not isinstance(appid, str) or not appid.isdigit() or not 0 < len(appid) <= 10:
        raise ValueError("appid")
    return f"https://store.steampowered.com/app/{appid}"
