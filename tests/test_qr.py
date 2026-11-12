"""STONE Home's own QR code encoder (dev/home/home_parts/qr.js), run in node.

The page cannot load anything from the internet, so the code a phone scans to open a game's page on
Steam's web store is drawn by STONE itself. GOLDEN holds matrices recorded on 2026-11-11 from the
python-qrcode library 8.2 (byte mode, error correction M, the same mask): the encoder must give the
same modules, one by one. Versions 1, 3, 4 (two blocks) and 6 (four blocks) are covered.

    python3 tests/test_qr.py     (or: pytest tests/test_qr.py)
"""

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need, run_module  # noqa: E402

QR_JS = os.path.join(REPO, "dev", "home", "home_parts", "qr.js")
UI = os.path.join(REPO, "apps", "stone-home", "ui", "index.html")

# (text, version, mask, rows as hexadecimal numbers)
GOLDEN = [
    ('STONE', 1, 4,
     '1fdc7f 104141 174f5d 17515d 175d5d 105641 1fd57f 1f00 117af9 1a972d 1a767a 1d10d3 f4dc7 11c9 1fd186 104b22 175675 174b0b 17427c 1044d0 1fdde5'),
    ('https://store.steampowered.com/app/3527290', 3, 3,
     '1fdf477f 10521c41 1742f55d 1757b95d 17462e5d 10420b41 1fd5557f 107a00 16eb3c4b ca347f1 1a678db6 cbfd6c1 975b9ac 10873a47 85417b7 1c2025e2 14dfd3ba 3bf69ae 14cc3994 4b709c4 bda1ffc 1b551f 1fdb535a 1059a518 174d09f7 1752e399 17520ca5 104a312a 1fdda72a'),
    ('https://store.steampowered.com/app/1234567890?x=1', 4, 4,
     '1fd4f037f 1048d6041 17484ff5d 17511a75d 175312f5d 1050a9c41 1fd55557f 1f4fe00 117a69ff9 13087ce8c e75e428a 133490800 10c992cfb bafc7704 42ad6ca 989fcaf8 94ecae52 12acf0e0c 1ad1b9faa c230dda2 475e5afb 1a229270a 3d612b26 23b0bdfa 1af9e9dfb 1dec916 1fdc3595a 104e60913 1750939f8 174147574 174c6d8f0 104cbc988 1fd3cbd89'),
    ('uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu', 6, 1,
     '1fdb588887f 1043a555541 175d5aaaa5d 1741edddd5d 174b988885d 1053a555541 1fd5555557f 62555500 146b9222225 219c7777eb 1e746aaaa55 1e3d55555aa 1b5b8222241 139cc7777eb 6754aaaa55 173f55555aa 5bb222241 81ee7777eb d424aaaa55 fa635555aa 1d7f222241 2a6e7777eb b4ecaaaa55 fa2f5555a9 5eba222242 149e17777eb 1c7deaaaa55 f36a5555aa cae222241 c1f27777eb 1c7ceaaaa55 73495555aa 1a5bd2223f1 16a77771b 1fdaaaaa955 1048b55571a 1743fe223f1 17466b776b9 1752aeaa915 1040f5557a8 1fd6fa22151'),
]

RUN = """
const T = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(T.map(t => { const Q = qrMatrix(t); return Q ? {v: Q.version, m: Q.mask, n: Q.length,
  rows: Q.map(r => parseInt(r.map(x => x ? 1 : 0).join(''), 2).toString(16)).join(' '), svg: qrSvg(t, 300)} : null; })));
"""


def _encode(texts):
    need(shutil.which("node") is not None, "node not installed (dev container, CI)")
    with open(QR_JS, encoding="utf-8") as f:
        js = f.read()
    r = subprocess.run(["node", "-e", js + RUN], input=json.dumps(texts), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_modules_match_the_reference_encoder_one_by_one():
    out = _encode([g[0] for g in GOLDEN])
    assert len(out) == len(GOLDEN)
    for i, (text, version, mask, rows) in enumerate(GOLDEN):
        o = out[i]
        assert o["v"] == version and o["n"] == 17 + 4 * version, (text, o["v"])
        assert o["m"] == mask, (text, o["m"])
        assert o["rows"] == rows, text


def test_sizes_limits_and_the_drawn_code():
    texts = ["a", "x" * 14, "x" * 15, "x" * 26, "x" * 27, "x" * 42, "x" * 43, "x" * 62, "x" * 63, "x" * 84, "x" * 85, "x" * 106, "x" * 107,
             "https://store.steampowered.com/app/9999999999", "ñ" * 7, "ñ" * 8]
    out = _encode(texts)
    versions = [o and o["v"] for o in out]
    assert versions == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, None, 4, 1, 2], versions     # bytes, not letters, are counted
    svg = out[13]["svg"]
    n = out[13]["n"]
    assert svg.startswith("<svg") and f'viewBox="0 0 {n + 8} {n + 8}"' in svg          # 4 quiet modules on each side
    assert 'fill="#ede9e3"' in svg and 'fill="#0a0a0b"' in svg and "http" not in svg   # dark on light, nothing fetched
    assert svg.count("h1v1h-1z") == sum(bin(int(r, 16)).count("1") for r in out[13]["rows"].split())
    assert _encode(["x" * 107])[0] is None


def test_the_page_carries_the_same_encoder():
    with open(QR_JS, encoding="utf-8") as f:
        part = f.read().strip()
    with open(UI, encoding="utf-8") as f:
        assert part in f.read(), "apps/stone-home/ui/index.html does not carry qr.js: run dev/home/build_home.py"


if __name__ == "__main__":
    sys.exit(run_module(globals()))
