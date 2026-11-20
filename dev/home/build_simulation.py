#!/usr/bin/env python3
"""A self-contained page that plays STONE OS with simulated data (for looking at the interface, not for measuring).

It is the production page (apps/stone-home/ui/index.html) with the transport to the host
replaced by dev/home/sim_host.js and the stoned simulation of the prototype. Nothing in it is measured.

    python3 dev/home/build_simulation.py OUT.html [--art ART_DIR]

--art: the games' real covers fetched by sim_art.py (ART_DIR/<appid>/<kind>.jpg|png), linked from
the page by relative address (they stay out of the page and out of the repository).
"""
import base64
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))   # dev/home -> repository root
PAGE = os.path.join(REPO, "apps/stone-home/ui")


def rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


KINDS = ("capsule", "hero", "hero2x", "header")


def art_script(out, art):
    """window.STONE_SIM_ART for sim_host.js artOf: each game's pictures, relative to the page."""
    found = {}
    for appid in sorted(os.listdir(art)):
        d = os.path.join(art, appid)
        if not appid.isdigit() or not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            kind, ext = os.path.splitext(n)
            if kind in KINDS and ext in (".jpg", ".png"):
                rel = os.path.relpath(os.path.join(d, n), os.path.dirname(os.path.abspath(out)))
                found.setdefault(appid, {})[kind] = rel.replace(os.sep, "/")
    return "<script>window.STONE_SIM_ART = " + json.dumps(found) + ";</script>\n", len(found)


def main(out, art=None):
    page, proto = rd(os.path.join(PAGE, "index.html")), rd(os.path.join(HERE, "stone-os-prototipo.html"))
    a = proto.index("const SimStoned = (() => {")
    b = proto.index("const PerfAPI = SimStoned;", a)
    sim_stoned = proto[a:b]
    f0 = proto.index("function sim(id, load) {")
    f1 = proto.index("/* ---------- STONE PERFORMANCE API", f0)
    sim_stoned = proto[f0:f1] + sim_stoned          # the prototype's reading model, used by SimStoned's metrics
    start = page.index("const Bridge = (() => {")
    end = page.index("/* Everything else the console needs", start)
    page = page[:start] + sim_stoned + "\n" + rd(os.path.join(HERE, "sim_host.js")) + "\n" + page[end:]
    page = re.sub(r"url\((fonts/[^)]+\.woff2)\)", lambda m: "url(data:font/woff2;base64,"
                  + base64.b64encode(open(os.path.join(PAGE, m.group(1)), "rb").read()).decode() + ")", page)
    page = re.sub(r"<meta http-equiv=\"Content-Security-Policy\"[^>]*>\n?", "", page)
    page = re.sub(r"<title>.*?</title>", "", page)
    page = page.replace("<!doctype html>", "").replace("</head><body>", "")
    page = re.sub(r"<html[^>]*><head>", "", page)
    page = re.sub(r"<meta (charset|name)=[^>]*>\n?", "", page)
    page = page.replace("</body></html>", "")
    real = ""
    if art:
        real, n = art_script(out, art)
        print(f"real covers of {n} games from {art}")
    page = '<meta charset="utf-8">\n<title>STONE OS Simulación</title>\n' + real + page + "\n" + rd(os.path.join(HERE, "sim_panel.html"))
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"{out}: {len(page)} bytes")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) not in (1, 3) or (len(args) == 3 and args[1] != "--art"):
        sys.exit(__doc__)
    main(args[0], args[2] if len(args) == 3 else None)
