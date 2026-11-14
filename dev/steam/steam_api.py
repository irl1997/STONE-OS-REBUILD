#!/usr/bin/env python3
"""Steam's own interface code as the reference for everything STONE asks of Steam.

Valve publishes the Steam client's interface (a web app: steamui/*.js) with every client version, in
the public update files that every Steam client downloads:

    https://client-update.steamstatic.com/steam_client_ubuntu12      the manifest (version, files, sha2)
    https://client-update.steamstatic.com/<file of steamui_websrc_all> the interface, a zip

STONE talks to that interface (stone_home/steamcef.py: JavaScript run in Steam's own page). Instead of
guessing how Steam works, this tool reads Steam's code and checks STONE against it:

    python3 dev/steam/steam_api.py fetch  [--dir D]        download the current interface (sha2 checked)
    python3 dev/steam/steam_api.py report [--dir D] [--out docs/steam/STEAM_API.md] [--json docs/steam/steam_api.json]
    python3 dev/steam/steam_api.py check  [--dir D]        STONE's calls against Steam's code; exit 1 on a mismatch

What is read: every SteamClient.<Area>.<Function>(...) call Steam's interface makes (how often, the
arguments it passes), the callbacks it registers for, the stores it keeps on window, its enums (name ->
number). Nothing downloaded is ever run: it is read as text. The zip and its manifest stay outside the
repository (--dir, default ~/.cache/stone/steamui); the report keeps only names, counts and arguments.
"""

import argparse
import collections
import hashlib
import json
import os
import re
import sys
import urllib.request
import zipfile

MANIFEST_URL = "https://client-update.steamstatic.com/steam_client_ubuntu12"
FILE_BASE = "https://client-update.steamstatic.com/"
PACKAGE = "steamui_websrc_all"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def default_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "stone", "steamui")


# ---- download -------------------------------------------------------------------------------
def parse_manifest(text):
    """{"version": str, "packages": {name: {"file", "size", "sha2"}}} from Steam's text manifest."""
    version = re.search(r'"version"\s*"(\d+)"', text)
    pk = {}
    for m in re.finditer(r'"([A-Za-z0-9_]+)"\s*\{([^{}]*)\}', text):
        f = dict(re.findall(r'"(file|size|sha2)"\s*"([^"]*)"', m.group(2)))
        if "file" in f:
            pk[m.group(1)] = f
    return {"version": version.group(1) if version else "", "packages": pk}


def _get(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": "STONE-OS steam_api"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"{url}: larger than {limit} bytes")
    return data


def fetch(dest, get=_get):
    """Download the manifest and the interface zip into dest. Returns (version, zip path)."""
    os.makedirs(dest, exist_ok=True)
    text = get(MANIFEST_URL, 2**20).decode("utf-8", "replace")
    man = parse_manifest(text)
    p = man["packages"].get(PACKAGE)
    if not p or not re.fullmatch(r"[A-Za-z0-9_.]+", p["file"]) or not re.fullmatch(r"[0-9a-f]{64}", p.get("sha2", "")):
        raise ValueError("the manifest does not name the interface package as expected")
    out = os.path.join(dest, f"steamui-{man['version']}.zip")
    if not (os.path.exists(out) and hashlib.sha256(open(out, "rb").read()).hexdigest() == p["sha2"]):
        data = get(FILE_BASE + p["file"], 200 * 2**20)
        got = hashlib.sha256(data).hexdigest()
        if got != p["sha2"]:
            raise ValueError(f"sha2 mismatch: {got} != {p['sha2']}")
        with open(out + ".tmp", "wb") as f:
            f.write(data)
        os.replace(out + ".tmp", out)
    with open(os.path.join(dest, "manifest.vdf"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(dest, "current"), "w") as f:
        f.write(json.dumps({"version": man["version"], "zip": os.path.basename(out), "sha2": p["sha2"]}))
    return man["version"], out


def current(dest):
    with open(os.path.join(dest, "current")) as f:
        c = json.load(f)
    return c["version"], os.path.join(dest, c["zip"])


# ---- reading Steam's code -------------------------------------------------------------------
CALL = re.compile(r"SteamClient\??\.([A-Z][A-Za-z0-9]*)\??\.([A-Z][A-Za-z0-9]*)(?:\??\.([A-Z][A-Za-z0-9]*))?\??\.?(\()?")
ENUM = re.compile(r"\w\[\w\.(k_E[A-Za-z0-9_]+)=(-?\d+)\]=\"\1\"")
STORE = re.compile(r"window\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[A-Za-z_$]")


def _args(text, i):
    """The argument text of a call whose "(" is at i (balanced, at most 200 characters)."""
    depth, j = 0, i
    while j < len(text) and j - i < 400:
        c = text[j]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
        j += 1
    return None


def _arity(args):
    if args is None:
        return None
    if not args.strip():
        return 0
    depth, n = 0, 1
    for c in args:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            n += 1
    return n


def index(zip_path):
    """What Steam's interface uses: {"calls": {"Area.Fn": {"count", "arities", "samples"}},
    "stores": [...], "enums": {name: value}, "identifiers": set of every identifier (for property checks)}."""
    calls = collections.defaultdict(lambda: {"count": 0, "arities": collections.Counter(), "samples": []})
    stores, enums, idents = set(), {}, set()
    routes, pages, gamepad_settings = [], [], False
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if not info.filename.endswith(".js") or "/localization/" in info.filename:
                continue
            t = z.read(info).decode("utf-8", "replace")
            for m in CALL.finditer(t):
                key = f"{m.group(1)}.{m.group(2)}" + (f".{m.group(3)}" if m.group(3) else "")   # System.DisplayManager.GetState
                c = calls[key]
                c["count"] += 1
                if m.group(4):
                    a = _args(t, m.end() - 1)
                    c["arities"][_arity(a)] += 1
                    if a is not None and len(c["samples"]) < 3 and a not in c["samples"] and len(a) <= 90:
                        c["samples"].append(a)
            stores.update(STORE.findall(t))
            for name, val in ENUM.findall(t):
                enums.setdefault(name, int(val))
            idents.update(re.findall(r"[A-Za-z_$][A-Za-z0-9_$]{2,}", t))
            routes = routes or _object_keys(t, "Settings:{Root:()=>")
            pages = pages or _object_keys(t, "{Home:(A={},M={})=>") or _object_keys(t, "{Home:(")
            gamepad_settings = gamepad_settings or bool(GAMEPAD_SETTINGS.search(t))
    out = {k: {"count": v["count"], "arities": sorted(a for a in v["arities"] if a is not None), "samples": v["samples"]}
           for k, v in sorted(calls.items())}
    return {"calls": out, "stores": sorted(stores), "enums": dict(sorted(enums.items())), "identifiers": idents,
            "settings_routes": routes, "navigator_pages": pages, "gamepad_settings": gamepad_settings}


# Game Mode's navigator: Settings(section, ...) navigates to the route Settings[section](...)
GAMEPAD_SETTINGS = re.compile(r"Settings:\(\w+,\.\.\.\w+\)=>\{[^}]{0,200}\.Settings\[\w+\]\(")


def _object_keys(t, start):
    """Top-level keys of the object literal that begins at the first `start` (its first `{`):
    Steam's settings routes, the entries of its navigator."""
    i = t.find(start)
    if i < 0:
        return []
    j = t.index("{", i)
    depth, keys = 0, []
    for m in re.finditer(r"[{}()\[\]]|(?<=[{,])([A-Za-z_$][\w$]*):", t[j:j + 200000]):
        s = m.group(0)
        if s in "{([":
            depth += 1
        elif s in "})]":
            depth -= 1
            if depth == 0:
                break
        elif depth == 1:
            keys.append(m.group(1))
    return keys


# ---- what STONE asks of Steam ---------------------------------------------------------------
def stone_expressions():
    """Every piece of JavaScript STONE runs in Steam's page, built with sample arguments."""
    sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
    from stone_home import steamcef as C
    ex = {"run_game": C.run_game_expression(620), "install": C.install_expression(620), "accept_eula": C.accept_eula_expression(620),
          "uninstall": C.uninstall_expression(620), "cancel_install": C.CANCEL_INSTALL_EXPRESSION, "downloads": C.DOWNLOADS_EXPRESSION,
          "launch": C.launch_expression(620), "launch_state": C.launch_state_expression(620),
          "launch_answer": C.launch_answer_expression(620, "ShowEula"), "owned": C.OWNED_EXPRESSION, "login": C.LOGIN_EXPRESSION,
          "dialog": C.DIALOG_EXPRESSION, "open_settings": C.open_settings_expression("Display"), "open_page": C.open_page_expression("Downloads"),
          "add_shortcut": C.add_shortcut_expression("x", "/x", "/", ""), "terminate": C.terminate_expression(620),
          "download_pause": C.download_control_expression(620, "pause"), "download_resume": C.download_control_expression(620, "resume")}
    for sub in ("modules/display", "modules/games"):
        sys.path.insert(0, os.path.join(REPO, sub))
    try:
        from stone_display import steam as D
        from stone_games import graphics as GR
    except ImportError:                       # these modules need nothing more than the standard library
        return ex
    ex.update({"display_state": D.STATE_EXPRESSION, "display_native": D.ensure_native_expression([620]),
               "display_default": D.restore_default_expression([620]), "display_size": D.set_default_expression(1920, 1080),
               "graphics_get": GR.get_options_expression(620), "graphics_set": GR.set_options_expression(620, "%command%")})
    return ex


ALIAS = re.compile(r"\b(?:const|let|var)?\s*([A-Za-z_$][\w$]{0,2})\s*=\s*(?:window\.)?SteamClient(?:\s*&&\s*SteamClient)?\.([A-Z]\w*)")
PROP = re.compile(r"\b(?:window\.)?(collectionStore|appStore|downloadsStore|SteamUIStore|App)\b((?:\.[A-Za-z_]\w*)+)")


def stone_calls(expressions):
    """{"Area.Fn": [(expression name, arity)]} and the store properties STONE reads, from its JavaScript."""
    calls, props, fields = collections.defaultdict(list), collections.defaultdict(set), collections.defaultdict(set)
    for name, js in expressions.items():
        aliases = {a: area for a, area in ALIAS.findall(js)}
        for a, area, sub in re.findall(r"\b([A-Za-z_$][\w$]{0,2})\s*=\s*window\.SteamClient(?:\s*&&\s*SteamClient)?\.([A-Z]\w*)"
                                       r"\s*&&\s*SteamClient\.\2\.([A-Z]\w*)", js):
            aliases[a] = f"{area}.{sub}"
        pats = [(r"SteamClient\.([A-Z]\w*)\.([A-Z]\w*)", None)] + [(re.escape(a) + r"\.([A-Z]\w*)", area) for a, area in aliases.items()]
        for pat, area in pats:
            for m in re.finditer(r"(?<![\w$.])" + pat + r"(\()?", js):
                ar, fn = (m.group(1), m.group(2)) if area is None else (area, m.group(1))
                paren = m.group(m.lastindex) if m.lastindex and m.group(m.lastindex) == "(" else None
                arity = _arity(_args(js, m.end() - 1)) if paren else None
                calls[f"{ar}.{fn}"].append((name, arity))
        # callbacks registered by name through a short alias: on('RegisterForGameActionStart', ...) with A[f]
        for a, area in aliases.items():
            if re.search(re.escape(a) + r"\[\w+\]", js):
                for fn in re.findall(r"\(\s*'((?:RegisterFor|Get|Set)[A-Z]\w*)'\s*,", js):
                    calls[f"{area}.{fn}"].append((name, None))
        for f in re.findall(r"\.([a-z][A-Za-z0-9]*_[a-z_0-9]+|[a-z]{1,3}[A-Z]\w+|m_[A-Za-z]\w*)\b", js):
            fields[f].add(name)
        # Steam's own objects and methods: w.MenuStore.OpenMainMenu(), n.Settings(...), S.GetFocusedWindowInstance()
        for f in re.findall(r"\.([A-Z][A-Za-z0-9]+)\b", js):
            fields[f].add(name)
        for store, chain in PROP.findall(js):
            for p in chain.strip(".").split("."):
                props[store].add(p)
        # stores kept in a short name first: const S=window.SteamUIStore; S.WindowStore.GamepadUIMainWindowInstance
        for a, store in re.findall(r"\b([A-Za-z_$][\w$]{0,2})\s*=\s*window\.(\w+Store|App)\b", js):
            for chain in re.findall(r"(?<![\w$.])" + re.escape(a) + r"((?:\.[A-Za-z_]\w*)+)", js):
                for p in chain.strip(".").split("."):
                    props[store].add(p)
    return calls, props, fields


# Functions STONE calls that Steam's own interface does not, each with the reason it is allowed.
OPTIONAL = {"Installs.GetInstallManagerInfo": "only when present (feature-tested): the steps come from RegisterForShowInstallWizard, "
                                              "as in Steam's interface; this only finds a wizard left open before STONE asked",
            "Apps.GetResolutionOverrideForApp": "only when present and a game's details do not come: the resolution is read "
                                                "from RegisterForAppDetails (strResolutionOverride), as in Steam's interface"}
# Names in STONE's JavaScript that are the browser's or STONE's own, not Steam's
OWN = {"__stoneGA", "addEventListener", "getBoundingClientRect", "innerText", "querySelector", "querySelectorAll", "toUpperCase",
       "unregister", "classList", "readyState"}


def check(idx, expressions=None):
    """[(level, message)]: a call Steam's interface never makes, an argument count it never uses, a
    property name that does not occur anywhere in its code."""
    calls, props, fields = stone_calls(expressions or stone_expressions())
    out = []
    for key, uses in sorted(calls.items()):
        steam = idx["calls"].get(key)
        where = ", ".join(sorted({u[0] for u in uses}))
        if steam is None:
            if key in OPTIONAL:
                out.append(("warn", f"{key}: Steam's interface never calls it; {OPTIONAL[key]} ({where})"))
            else:
                out.append(("error", f"{key}: Steam's interface never calls it ({where})"))
            continue
        for _n, ar in uses:
            if ar is not None and steam["arities"] and ar not in steam["arities"]:
                out.append(("warn", f"{key}: STONE passes {ar} arguments, Steam {steam['arities']} ({where}; Steam: {steam['samples'][:2]})"))
                break
        else:
            out.append(("ok", f"{key}: as Steam ({where})"))
    for f, where in sorted(fields.items()):
        if f in OWN or any(k.endswith("." + f) for k in OPTIONAL):
            continue
        out.append(("ok", f"field {f}: occurs in Steam's code") if f in idx["identifiers"]
                   else ("error", f"field {f}: does not occur in Steam's code ({', '.join(sorted(where))})"))
    for store, names in sorted(props.items()):
        for p in sorted(names):
            if p not in idx["identifiers"]:
                out.append(("error", f"{store}.{p}: does not occur in Steam's code"))
            else:
                out.append(("ok", f"{store}.{p}: occurs in Steam's code"))
    if expressions is None:
        out += check_navigation(idx)
    return out


def check_navigation(idx):
    """The settings sections and pages STONE opens through Steam's navigator are Steam's own."""
    sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
    from stone_home import steamcef as C
    out = []
    if not idx.get("gamepad_settings"):
        out.append(("error", "Navigator.Settings: Game Mode's navigator no longer opens Settings[section] (open_settings)"))
    routes, pages = idx.get("settings_routes") or [], idx.get("navigator_pages") or []
    for s in C.SETTINGS_SECTIONS:
        out.append(("ok", f"Navigator.Settings('{s}'): a settings route of Steam's") if s in routes
                   else ("error", f"Navigator.Settings('{s}'): not a settings route of Steam's {routes}"))
    for p in C.PAGES:
        out.append(("ok", f"Navigator.{p}(): an entry of Steam's navigator") if p in pages
                   else ("error", f"Navigator.{p}(): not an entry of Steam's navigator {pages}"))
    return out


# ---- the report -----------------------------------------------------------------------------
AREAS = ("Apps", "Installs", "Downloads", "Settings", "User", "System", "UI", "Window", "Auth", "Storage", "GameSessions", "Overlay")


def report(idx, version, problems):
    lines = [f"# La interfaz de Steam (cliente {version})", "",
             "Generado por `dev/steam/steam_api.py report` a partir del código que Valve publica con el cliente "
             "(`steam_client_ubuntu12` → `steamui_websrc_all`). Es la referencia de lo que STONE puede pedirle a Steam: "
             "las funciones que la propia interfaz de Steam llama, cuántas veces y con qué argumentos.", "",
             "## STONE frente a Steam", ""]
    for level, msg in problems:
        lines.append(f"- {'✅' if level == 'ok' else '⚠️' if level == 'warn' else '❌'} {msg}")
    lines += ["", "## Funciones de `SteamClient` que usa la interfaz de Steam", "",
              "| Función | Veces | Argumentos | Ejemplos de la interfaz de Steam |", "| --- | --- | --- | --- |"]
    for key, v in idx["calls"].items():
        if key.split(".")[0] in AREAS:
            samples = " · ".join(f"`({s})`" for s in v["samples"][:2]).replace("|", "\\|")
            lines.append(f"| `{key}` | {v['count']} | {', '.join(map(str, v['arities'])) or '—'} | {samples} |")
    lines += ["", "## Almacenes en `window`", "", ", ".join(f"`{s}`" for s in idx["stores"]), "",
              "## Enumeraciones que STONE usa", ""]
    for prefix in ("k_EInstallMgrState", "k_EAppUpdateProgress", "k_EAppUpdateError", "k_ELaunchOptionType", "k_EGameActionTask"):
        vals = {k: v for k, v in idx["enums"].items() if k.startswith(prefix)}
        if vals:
            lines.append(f"- `{prefix}`: " + ", ".join(f"{k[len(prefix) + 1:] or k} = {v}" for k, v in sorted(vals.items(), key=lambda x: x[1])))
    return "\n".join(lines) + "\n"


def snapshot(idx, version):
    """What the repository keeps of Steam's interface: names, argument counts, a few sample arguments,
    stores, enums, and which of the names STONE reads occur in Steam's code. No code of Steam's."""
    calls, props, fields = stone_calls(stone_expressions())
    names = set(fields) | {p for ps in props.values() for p in ps}
    return {"version": version, "calls": idx["calls"], "stores": idx["stores"], "enums": idx["enums"],
            "settings_routes": idx["settings_routes"], "navigator_pages": idx["navigator_pages"],
            "gamepad_settings": idx["gamepad_settings"], "names_seen": sorted(n for n in names if n in idx["identifiers"])}


def from_snapshot(path):
    """An index good enough for check(), from the snapshot in the repository (offline, for the tests)."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d["version"], {"calls": d["calls"], "stores": d["stores"], "enums": d["enums"], "identifiers": set(d["names_seen"]),
                          "settings_routes": d.get("settings_routes", []), "navigator_pages": d.get("navigator_pages", []),
                          "gamepad_settings": d.get("gamepad_settings", False)}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("fetch", "report", "check"))
    ap.add_argument("--snapshot", action="store_true", help="check against docs/steam/steam_api.json, offline")
    ap.add_argument("--dir", default=default_dir())
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "steam", "STEAM_API.md"))
    ap.add_argument("--json", default=os.path.join(REPO, "docs", "steam", "steam_api.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        v, z = fetch(a.dir)
        print(f"Steam client {v}: {z}")
        return 0
    if a.snapshot:
        version, idx = from_snapshot(a.json)
    else:
        version, z = current(a.dir)
        idx = index(z)
    problems = check(idx)
    if a.cmd == "check":
        for level, msg in problems:
            if level != "ok":
                print(f"{level.upper():5} {msg}")
        bad = [p for p in problems if p[0] == "error"]
        print(f"steam api: {len([p for p in problems if p[0] == 'ok'])} as Steam, {len(problems) - len(bad) - len([p for p in problems if p[0] == 'ok'])} warnings, {len(bad)} errors (client {version})")
        return 1 if bad else 0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(report(idx, version, problems))
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump(snapshot(idx, version), f, indent=0, sort_keys=True)
        f.write("\n")
    print(f"wrote {a.out} and {a.json} (client {version}, {len(idx['calls'])} functions)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
