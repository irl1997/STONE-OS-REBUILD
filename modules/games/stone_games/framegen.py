"""Frame generation (D-22), EXPERIMENTAL: OptiScaler's own FSR frame generation (OptiFG) in a game
where STONE installed OptiScaler (install.py).

D-22 conditions, all enforced here:
  · off by default; only the person turns it on, per game
  · never in games with anti-cheat or online-only games
  · only where STONE installed OptiScaler (its OptiScaler.ini sits next to the game's executable)
  · the person is told plainly that the FPS counter then includes generated frames

On: [FrameGen] FGType=optifg in that OptiScaler.ini (a copy of the ini as STONE found it is kept
once as OptiScaler.ini.stone-orig). Off: FGType=nofg. Uninstalling OptiScaler (install.uninstall)
removes the ini with the rest. The key and values are OptiScaler's (FGType = auto | nofg | optifg).
"""

import os
import re
import shutil

from . import install

INI = "OptiScaler.ini"


def _ini_path(appid):
    rec = install.installed_by_stone(appid)
    if not rec or rec.get("kind") != "optiscaler":
        return None
    p = os.path.join(rec["exe_dir"], INI)
    return p if os.path.isfile(p) else None


def blocked(facts, game):
    if facts.get("anti_cheat") or game.get("anti_cheat"):
        return "No se usa en juegos con anti-cheat"
    if game.get("online_only"):
        return "No se usa en juegos en línea"
    return None


def read_state(text):
    """'optifg' | 'nofg' | 'auto' | None from an OptiScaler.ini text."""
    sec = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^\[(.+)\]$", s)
        if m:
            sec = m.group(1).strip().lower()
            continue
        k, sep, v = s.partition("=")
        if sep and sec == "framegen" and k.strip().lower() == "fgtype":
            return v.split(";")[0].strip().lower() or None
    return None


def set_state(text, value):
    """The ini text with [FrameGen] FGType=<value>, adding the key or the section when missing."""
    lines = text.splitlines()
    sec, start, done = None, None, False
    for i, line in enumerate(lines):
        s = line.strip()
        m = re.match(r"^\[(.+)\]$", s)
        if m:
            if sec == "framegen" and not done:
                lines.insert(i, f"FGType={value}")
                done = True
                break
            sec = m.group(1).strip().lower()
            if sec == "framegen":
                start = i
            continue
        k, sep, _ = s.partition("=")
        if sep and sec == "framegen" and k.strip().lower() == "fgtype":
            lines[i] = f"FGType={value}"
            done = True
            break
    if not done:
        if start is not None:
            lines.append(f"FGType={value}")
        else:
            lines += ["", "[FrameGen]", f"FGType={value}"]
    return "\n".join(lines) + "\n"


def status(appid, facts, game):
    why = blocked(facts, game)
    p = _ini_path(appid)
    if why is None and p is None:
        why = "Solo con FSR (OptiScaler) instalado por STONE en este juego"
    state = None
    if p:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                state = read_state(f.read())
        except OSError:
            pass
    return {"available": why is None, "reason": why, "on": state == "optifg", "experimental": True}


def set_on(appid, facts, game, on):
    st = status(appid, facts, game)
    if not st["available"]:
        return {"error": st["reason"]}
    p = _ini_path(appid)
    orig = p + ".stone-orig"
    if not os.path.exists(orig):
        shutil.copyfile(p, orig)
    with open(p, encoding="utf-8", errors="replace") as f:
        text = f.read()
    tmp = p + ".stone-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(set_state(text, "optifg" if on else "nofg"))
    os.replace(tmp, p)
    return {"ok": True, "on": bool(on)}
