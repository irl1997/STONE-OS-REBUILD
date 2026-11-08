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
    assert r == {"results": [{"appid": "570", "name": "Dota 2", "free": True}, {"appid": "1245620", "name": "Juego de pago", "free": False}]}
    assert "term=dota" in seen[0] and "l=spanish" in seen[0] and seen[0].startswith(ST.API)
    assert "error" in ST.search("", get=get) and "error" in ST.search("x" * 61, get=get)
    assert "no responde" in ST.search("dota", get=lambda u: (_ for _ in ()).throw(OSError("offline")))["error"]
    assert ST.search("dota", get=lambda u: "not json").get("error")


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
    assert CEF.reachable(port=1) is False


if __name__ == "__main__":
    sys.exit(run_module(globals()))
