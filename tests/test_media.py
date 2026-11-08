"""STONE MEDIA (stone_home/media.py) and the Steam dialog bridge (steamcef dialog helpers).
Pure Python: a fake Steam folder, no Steam.

    python3 tests/test_media.py     (or: pytest tests/test_media.py)
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import media as M  # noqa: E402
from stone_home import steamcef as CEF  # noqa: E402


def _shot(root, appid, name, t):
    d = os.path.join(root, "userdata", "1234", "760", "remote", appid, "screenshots")
    os.makedirs(os.path.join(d, "thumbnails"), exist_ok=True)
    p = os.path.join(d, name)
    with open(p, "wb") as f:
        f.write(b"\xff\xd8")
    os.utime(p, (t, t))
    with open(os.path.join(d, "thumbnails", name), "wb") as f:
        f.write(b"\xff\xd8")
    return p


def test_screenshots_newest_first_per_game_and_served_by_index():
    with tempfile.TemporaryDirectory() as root:
        a = _shot(root, "570", "a.jpg", 1000)
        b = _shot(root, "730", "b.jpg", 3000)
        c = _shot(root, "570", "c.png", 2000)
        rows = M.screenshots(root)
        assert [r["appid"] for r in rows] == ["730", "570", "570"] and [r["kind"] for r in rows] == ["shot0", "shot1", "shot2"]
        assert M.path(root, "0", "shot0") == b and M.path(root, "0", "shot2") == a
        assert [r["appid"] for r in M.screenshots(root, "570")] == ["570", "570"] and M.path(root, "570", "shot0") == c
        assert M.path(root, "0", "shot9") is None and M.path(root, "0", "hero") is None
        assert M.path(root, "../x", "shot0") is None and M.path(root, "0", "shot123") is None
        assert M.screenshots(os.path.join(root, "nothing")) == []


def test_steam_dialog_is_read_and_answered_only_by_its_own_label():
    raw = json.dumps({"title": "Conflicto de la nube", "text": "x" * 900, "buttons": ["Usar nube", "", 3, "Usar locales"]})
    d = CEF.parse_dialog(raw)
    assert d == {"title": "Conflicto de la nube", "text": "x" * 600, "buttons": ["Usar nube", "Usar locales"]}
    assert CEF.parse_dialog(None) is None and CEF.parse_dialog("nope") is None
    assert CEF.parse_dialog(json.dumps({"title": "t", "buttons": []})) is None
    e = CEF.answer_expression(1, 'Usar "locales" ñ')
    assert "btns[1]" in e and '"Usar \\"locales\\" \\u00f1"' in e and "b.click()" in e
    for bad in ((4, "x"), (-1, "x"), (0, ""), (0, "x" * 41), ("0", "x"), (0, None)):
        try:
            CEF.answer_expression(*bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad!r}")
    assert "DialogButton" in CEF.DIALOG_EXPRESSION and "return null" in CEF.DIALOG_EXPRESSION


if __name__ == "__main__":
    sys.exit(run_module(globals()))
