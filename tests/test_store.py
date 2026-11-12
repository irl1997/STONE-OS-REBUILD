"""Search (stone_home/store.py) and installing without Steam's dialog (steamcef expressions).
Pure Python: no network, no Steam.

    python3 tests/test_store.py     (or: pytest tests/test_store.py)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import steamcef as CEF  # noqa: E402
from stone_home import store as ST  # noqa: E402


def test_store_search_parses_free_and_paid_and_refuses_bad_terms():
    seen = []

    def get(url):
        seen.append(url)
        return json.dumps({"total": 3, "items": [
            {"type": "app", "name": "Dota 2", "id": 570},
            {"type": "app", "name": "Juego de pago", "id": 1245620, "price": {"currency": "USD", "initial": 5999, "final": 5999}},
            {"type": "sub", "name": "Paquete", "id": 9},
            {"type": "app", "name": "", "id": 11}]})
    r = ST.search("  dota ", get=get)
    assert r == {"results": [{"appid": "570", "name": "Dota 2", "free": True, "price": None},
                             {"appid": "1245620", "name": "Juego de pago", "free": False, "price": "59,99 USD"}]}
    assert "term=dota" in seen[0] and "l=spanish" in seen[0] and seen[0].startswith(ST.API)
    assert "cc=" not in seen[0]                        # no country: Steam answers with the console's own prices
    assert "error" in ST.search("", get=get) and "error" in ST.search("x" * 61, get=get)
    assert "no responde" in ST.search("dota", get=lambda u: (_ for _ in ()).throw(OSError("offline")))["error"]
    assert ST.search("dota", get=lambda u: "not json").get("error")


def test_prices_are_written_from_steams_hundredths():
    assert ST.money(5999, "USD") == "59,99 USD" and ST.money(264500, "clp") == "2.645 CLP" and ST.money(0, "EUR") == "0 EUR"
    assert ST.money(123456789, "ARS") == "1.234.567,89 ARS"
    for bad in ((None, "USD"), (-1, "USD"), (True, "USD"), (100, "US"), (100, "U$D"), (100, None), ("100", "USD")):
        assert ST.money(*bad) is None, bad


FEATURED = {"specials": {"id": "cat_specials", "name": "Ofertas", "items": [
    {"id": 266410, "type": 0, "name": "iRacing", "discounted": True, "discount_percent": 60, "original_price": 661300,
     "final_price": 264500, "currency": "CLP", "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/266410/header.jpg?t=1"},
    {"id": 99, "type": 1, "name": "Un paquete", "final_price": 100, "currency": "CLP"},
    {"id": 0, "type": 0, "name": "Sin id"}, "basura", {"id": 5, "type": 0, "name": "  "}]},
    "top_sellers": {"items": [{"id": 266410, "type": 0, "name": "iRacing", "final_price": 264500, "original_price": 661300, "currency": "CLP"},
                              {"id": 730, "type": 0, "name": "Counter-Strike 2", "final_price": 0, "original_price": 0, "currency": "CLP",
                               "discount_percent": 0, "header_image": 7}]},
    "coming_soon": {"items": [{"id": 4000000, "type": 0, "name": "Lo que viene", "final_price": 0, "original_price": 0, "currency": "CLP"}]},
    "new_releases": {"items": []}, "status": 1}


def test_shop_window_keeps_games_once_with_prices_and_leaves_packs_out():
    seen = []
    r = ST.featured(get=lambda u: (seen.append(u), json.dumps(FEATURED))[1])
    assert seen[0].startswith(ST.FEATURED) and "l=spanish" in seen[0] and "cc=" not in seen[0]
    assert [(s["key"], s["title"], [i["appid"] for i in s["items"]]) for s in r["sections"]] == [
        ("specials", "Ofertas", ["266410"]), ("top_sellers", "Lo más vendido", ["730"]), ("coming_soon", "Próximamente", ["4000000"])]
    offer = r["sections"][0]["items"][0]
    assert offer == {"appid": "266410", "name": "iRacing", "free": False, "price": "2.645 CLP", "was": "6.613 CLP", "discount": 60,
                     "_header": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/266410/header.jpg?t=1"}
    free = r["sections"][1]["items"][0]
    assert free["free"] is True and free["price"] is None and free["_header"] is None
    soon = r["sections"][2]["items"][0]
    assert soon["soon"] is True and soon["free"] is False and soon["price"] is None      # not out yet: nothing to install
    assert "error" in ST.featured(get=lambda u: "{}") and "error" in ST.featured(get=lambda u: "[1]")
    assert "no responde" in ST.featured(get=lambda u: (_ for _ in ()).throw(OSError("offline")))["error"]


def test_game_page_is_plain_text_with_its_price_and_refuses_bad_ids():
    page = {"3527290": {"success": True, "data": {
        "type": "game", "name": "PEAK", "is_free": False, "steam_appid": 3527290,
        "short_description": "Un juego <b>cooperativo</b> de escalada &amp; ca&iacute;das.<br>Sube.<script>alert(1)</script>",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/3527290/31ba/header.jpg?t=1",
        "price_overview": {"currency": "CLP", "initial": 420000, "final": 260400, "discount_percent": 38},
        "release_date": {"coming_soon": False, "date": "16 JUN 2025"}, "developers": ["Team PEAK", 5, ""],
        "genres": [{"id": "1", "description": "Acción"}, {"description": "Aventura"}, "x", {"description": 3}]}}}
    seen = []
    r = ST.details("3527290", get=lambda u: (seen.append(u), json.dumps(page))[1])
    assert "appids=3527290" in seen[0] and seen[0].startswith(ST.DETAILS) and "cc=" not in seen[0]
    assert r["name"] == "PEAK" and r["price"] == "2.604 CLP" and r["was"] == "4.200 CLP" and r["discount"] == 38
    assert r["about"] == "Un juego cooperativo de escalada & caídas.\nSube.alert(1)" and "<" not in r["about"]
    assert r["genres"] == ["Acción", "Aventura"] and r["by"] == ["Team PEAK"] and r["release"] == "16 JUN 2025"
    assert r["free"] is False and r["soon"] is False and r["kind"] == "game" and r["_header"].endswith("header.jpg?t=1")
    assert ST.header_url("3527290", get=lambda u: json.dumps(page)) == r["_header"]
    free = {"570": {"success": True, "data": {"type": "game", "name": "Dota 2", "is_free": True, "release_date": {"date": "9 JUL 2013"}}}}
    r = ST.details("570", get=lambda u: json.dumps(free))
    assert r["free"] is True and r["price"] is None and r["was"] is None and r["_header"] is None
    soon = {"9": {"success": True, "data": {"type": "game", "name": "Pronto", "is_free": True, "release_date": {"coming_soon": True, "date": "2027"}}}}
    assert ST.details("9", get=lambda u: json.dumps(soon))["free"] is False           # not out: not installable
    for bad in ("", "abc", "12345678901", "0", None, 620, "../1"):
        assert ST.details(bad, get=lambda u: (_ for _ in ()).throw(AssertionError("fetched"))) == {"error": "Juego desconocido"}, bad
    assert "región" in ST.details("1", get=lambda u: json.dumps({"1": {"success": False}}))["error"]
    assert "no responde" in ST.details("1", get=lambda u: "<html>")["error"]
    assert ST.page_url("3527290") == "https://store.steampowered.com/app/3527290"
    for bad in ("x", "", None, "1/../2"):
        try:
            ST.page_url(bad)
            raise AssertionError(bad)
        except ValueError:
            pass


def test_install_and_uninstall_need_no_dialog_and_library_has_two_sources():
    e = CEF.install_expression(570)
    assert "OpenInstallWizard([570])" in e and "ContinueInstall" in e and "SetInstallFolder(0)" in e
    assert "OpenUninstallWizard([570],true)" in CEF.uninstall_expression(570)
    for bad in (0, -1, 0x80000000):
        for fn in (CEF.install_expression, CEF.uninstall_expression):
            try:
                fn(bad)
                raise AssertionError(bad)
            except ValueError:
                pass
    assert "collectionStore" in CEF.OWNED_EXPRESSION and "appStore" in CEF.OWNED_EXPRESSION and "app_type===1" in CEF.OWNED_EXPRESSION
    for source in ("allGamesCollection", "allAppsCollection", "allApps", "m_mapApps"):      # every source is joined
        assert source in CEF.OWNED_EXPRESSION, source
    assert "m_CurrentUser" in CEF.LOGIN_EXPRESSION and CEF.login_state(port=1) is None
    assert CEF.reachable(port=1) is False


if __name__ == "__main__":
    sys.exit(run_module(globals()))
