"""Everything STONE asks of Steam's interface is what Steam's own interface does (dev/steam/steam_api.py),
checked offline against the snapshot of Steam's code kept in docs/steam/steam_api.json.

    python3 tests/test_steam_api.py     (or: pytest tests/test_steam_api.py)
"""

import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "dev", "steam"))
import steam_api as API  # noqa: E402

SNAPSHOT = os.path.join(REPO, "docs", "steam", "steam_api.json")


def test_every_call_and_field_stone_uses_is_steams_own():
    version, idx = API.from_snapshot(SNAPSHOT)
    problems = API.check(idx)
    errors = [m for level, m in problems if level == "error"]
    assert not errors, "\n".join(errors) + "\nRead how Steam's interface does it (docs/steam/COMO_HABLA_STONE_CON_STEAM.md)"
    warns = [m for level, m in problems if level == "warn"]
    assert all(m.split(":")[0] in API.OPTIONAL for m in warns), warns
    ok = {m.split(":")[0] for level, m in problems if level == "ok"}
    for key in ("Installs.OpenInstallWizard", "Apps.RunGame", "Apps.ContinueGameAction", "Installs.OpenUninstallWizard",
                "Apps.RegisterForGameActionUserRequest", "Installs.RegisterForShowInstallWizard"):
        assert key in ok, key                                # what the board fixes of 3.1.0-rc4 rest on
    assert version.isdigit()


def test_reading_steams_code():
    manifest = '"ubuntu12"\n{\n\t"version"\t\t"1792618285"\n\t"steamui_websrc_all"\n\t{\n\t\t"file"\t\t"steamui_websrc_all.zip.abc"\n' \
               '\t\t"size"\t\t"10"\n\t\t"sha2"\t\t"' + "a" * 64 + '"\n\t}\n}\n'
    m = API.parse_manifest(manifest)
    assert m["version"] == "1792618285" and m["packages"]["steamui_websrc_all"]["file"] == "steamui_websrc_all.zip.abc"
    js = ('x=(y=>(y[y.k_EInstallMgrStateNone=0]="k_EInstallMgrStateNone",y[y.k_EInstallMgrStateShowConfig=7]="k_EInstallMgrStateShowConfig",y));'
          'SteamClient.Installs.OpenInstallWizard([G],U);SteamClient.Apps.RunGame(a.GetGameID(),"",-1,b);'
          'SteamClient.Apps.RunGame(c.GetGameID(),"",-1,d.e);window.downloadsStore=new Q;f(SteamClient.Installs.ContinueInstall());')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("steamui/sp.js", js)
        z.writestr("steamui/localization/steamui_spanish-json.js", "SteamClient.Fake.Call(1)")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(buf.getvalue())
    try:
        idx = API.index(f.name)
    finally:
        os.remove(f.name)
    assert idx["calls"]["Installs.OpenInstallWizard"]["arities"] == [2]
    assert idx["calls"]["Apps.RunGame"]["count"] == 2 and idx["calls"]["Apps.RunGame"]["arities"] == [4]
    assert idx["calls"]["Installs.ContinueInstall"]["arities"] == [0] and "Fake.Call" not in idx["calls"]
    assert idx["stores"] == ["downloadsStore"] and idx["enums"] == {"k_EInstallMgrStateNone": 0, "k_EInstallMgrStateShowConfig": 7}
    # a call Steam never makes, or with another number of arguments, is reported
    bad = API.check(idx, {"x": "const I=window.SteamClient&&SteamClient.Installs;I.OpenInstallWizard([1]);I.Nope();"})
    assert ("error", "Installs.Nope: Steam's interface never calls it (x)") in bad
    assert any(level == "warn" and m.startswith("Installs.OpenInstallWizard: STONE passes 1") for level, m in bad), bad


def test_fetch_refuses_what_does_not_match_its_sum():
    manifest = ('"ubuntu12"{"version" "7" "steamui_websrc_all"{"file" "steamui_websrc_all.zip.x" "size" "3" "sha2" "' + "0" * 64 + '"}}').encode()
    d = tempfile.mkdtemp(prefix="stone-steamapi-")

    def get(url, limit):
        return manifest if url == API.MANIFEST_URL else b"zip"
    try:
        API.fetch(d, get=get)
        raise AssertionError("a file that does not match its sum was kept")
    except ValueError as e:
        assert "sha2 mismatch" in str(e)
    assert not [n for n in os.listdir(d) if n.endswith(".zip")]


if __name__ == "__main__":
    run_module(globals())
