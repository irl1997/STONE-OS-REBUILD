"""FIRST RUN (M22): the console's first start, shown once by STONE Home.

State: ~/.config/stone/firstrun.json ({"done": true, "time": ..., "version": ...}). A console that
already has STONE Home settings (home.json, an older STONE image) counts as done: FIRST RUN is for
a new installation. Delete the file to see it again.

FIRST RUN only reads: the configuration stoned detected, the display and whether a Steam account
has signed in on this console. It never overclocks, calibrates or turns on anything experimental
(A2): the performance profile stays BALANCED, the factory one.
"""

import json
import os
import tempfile
import time

from . import shortcuts
from . import system


def path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "stone", "firstrun.json")


def status(steam_root=None):
    try:
        with open(path()) as f:
            d = json.load(f)
        done = isinstance(d, dict) and d.get("done") is True
    except (OSError, ValueError):
        done = os.path.exists(system.prefs_path())
    root = steam_root or shortcuts.steam_root()
    return {"done": done, "steam_account": bool(shortcuts.accounts(root))}


def complete(version=None):
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".firstrun-", dir=os.path.dirname(p))
    with os.fdopen(fd, "w") as f:
        json.dump({"done": True, "time": int(time.time()), "version": version}, f)
    os.replace(tmp, p)
    return {"done": True}
