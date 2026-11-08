"""The STONE theme: a valid CSS Loader theme whose files exist, with one source for its colours and
no dependence on anything outside the console. It cannot test Steam's real interface (T-THEME-01).

    python3 tests/test_theme.py     (or: pytest tests/test_theme.py)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

THEME = os.path.join(REPO, "themes", "STONE")


def _css():
    folder = os.path.join(THEME, "css")
    return {n: open(os.path.join(folder, n), encoding="utf-8").read() for n in os.listdir(folder)}


def _manifest():
    with open(os.path.join(THEME, "theme.json"), encoding="utf-8") as f:
        return json.load(f)


def test_manifest_files_and_tabs_exist():
    m = _manifest()
    assert m["name"] == "STONE" and m["manifest_version"] <= 9   # what CSS Loader 2.1.3 supports
    for path, tabs in m["inject"].items():
        assert os.path.isfile(os.path.join(THEME, path)), path
        assert all(t in m["tabs"] for t in tabs), (path, tabs)
    for patch in m["patches"].values():
        assert patch["default"] in patch["values"]
        for value in patch["values"].values():
            for path in value:
                assert os.path.isfile(os.path.join(THEME, path)), path


def test_every_css_file_is_used():
    m = _manifest()
    used = set(m["inject"])
    for patch in m["patches"].values():
        for value in patch["values"].values():
            used |= set(value)
    assert {f"css/{n}" for n in _css()} == used


def test_fonts_are_local_and_exist():
    for name, text in _css().items():
        for url in re.findall(r'url\("([^"]+)"\)', text):
            assert url.startswith("/themes_custom/STONE/"), (name, url)
            assert os.path.isfile(os.path.join(THEME, url[len("/themes_custom/STONE/"):])), url
        assert "http://" not in text and "https://" not in text, name
        assert "@import" not in text, name


def test_colours_are_decided_only_in_tokens():
    for name, text in _css().items():
        if name != "tokens.css":
            assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", text), name


def test_every_token_used_is_defined():
    css = _css()
    defined = set(re.findall(r"(--stone-[a-z-]+)\s*:", css["tokens.css"]))
    for name, text in css.items():
        assert set(re.findall(r"var\((--stone-[a-z-]+)\)", text)) <= defined, name


def test_braces_balance():
    for name, text in _css().items():
        assert text.count("{") == text.count("}"), name


if __name__ == "__main__":
    sys.exit(run_module(globals()))
