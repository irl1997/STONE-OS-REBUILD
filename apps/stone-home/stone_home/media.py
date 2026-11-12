"""STONE MEDIA: the screenshots Steam saved, shown by STONE Home (no Steam screen).

Steam keeps each account's screenshots in
    <Steam>/userdata/<account>/760/remote/<appid>/screenshots/<name>.jpg
(and small copies in .../screenshots/thumbnails/, not listed here). STONE lists them newest first
and serves the N-th one of a game (or of every game, appid "0") as artwork kind "shot<N>".
"""

import os
import re

from . import shortcuts

MAX = 60
SHOT = re.compile(r"^shot([0-9]{1,2})$")
EXT = (".jpg", ".jpeg", ".png")


def _all(root):
    out = []
    for acct in shortcuts.accounts(root):
        base = os.path.join(acct, "760", "remote")
        try:
            apps = os.listdir(base)
        except OSError:
            continue
        for appid in apps:
            d = os.path.join(base, appid, "screenshots")
            if not appid.isdigit() or not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if name.lower().endswith(EXT) and os.path.isfile(p):
                    try:
                        out.append((os.path.getmtime(p), appid, p))
                    except OSError:
                        pass
    out.sort(key=lambda x: (-x[0], x[2]))
    return out


def screenshots(root, appid="0"):
    """[{"appid", "time", "kind"}] newest first, at most MAX; appid "0" = every game."""
    rows = [r for r in _all(root) if appid == "0" or r[1] == appid][:MAX]
    return [{"appid": a, "time": int(t), "kind": f"shot{i}"} for i, (t, a, _p) in enumerate(rows)]


def path(root, appid, kind):
    """The file behind art kind "shot<N>" for appid ("0" = every game), or None."""
    m = SHOT.match(kind or "")
    if not m or not isinstance(appid, str) or not appid.isdigit() or len(appid) > 10:
        return None
    rows = [r for r in _all(root) if appid == "0" or r[1] == appid][:MAX]
    i = int(m.group(1))
    return rows[i][2] if i < len(rows) else None
