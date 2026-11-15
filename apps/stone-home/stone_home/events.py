"""What STONE did and what came of it, as one JSON line per event (3.1.0-rc8).

The diagnostic report (diagreport.py, diagchecks.py) reads these to say what works and what does not:
a game started and with what, whether an image look reached the game and vkBasalt was loaded in it,
a look turned off after a crash, Steam's window in front and how it ended, the screen going HDR...
Logs say it in words; this says it in data a check can count.

~/.local/state/stone/events.jsonl, at most MAX_BYTES (the older half is dropped). Never anything
personal: app ids, names of STONE's own settings, states. Writing never fails the caller.
"""

import json
import os
import threading
import time

MAX_BYTES = 512 * 1024
_lock = threading.Lock()


def path():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "stone", "events.jsonl")


def record(kind, **data):
    """Append one event: {"t": unix time, "kind": kind, ...data}."""
    row = {"t": round(time.time(), 1), "kind": str(kind)[:40]}
    for k, v in data.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            row[k] = v[:300] if isinstance(v, str) else v
        elif isinstance(v, (list, tuple)):
            row[k] = [x if isinstance(x, (int, float, bool)) else str(x)[:120] for x in list(v)[:20]]
        elif isinstance(v, dict):
            row[k] = {str(a)[:60]: (b if isinstance(b, (int, float, bool)) or b is None else str(b)[:200]) for a, b in list(v.items())[:30]}
    p = path()
    try:
        with _lock:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if os.path.exists(p) and os.path.getsize(p) > MAX_BYTES:
                with open(p, "rb") as f:
                    f.seek(-MAX_BYTES // 2, os.SEEK_END)
                    keep = f.read().split(b"\n", 1)[-1]
                with open(p, "wb") as f:
                    f.write(keep)
            with open(p, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return row


def read(kinds=None, since=None, limit=2000, file=None):
    """The latest events (oldest first), optionally of some kinds or after a time."""
    out = []
    try:
        with open(file or path(), encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(e, dict) or (kinds and e.get("kind") not in kinds) or (since and e.get("t", 0) < since):
                    continue
                out.append(e)
    except OSError:
        return []
    return out[-limit:]
