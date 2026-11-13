"""The Steam account's games between boots, and whether someone is signed in.

Steam's files on disk list only the installed games. The rest of the account comes from Steam's
interface (steamcef.owned_games), which answers some seconds after Steam starts, and not at all
without internet or before the first sign-in. The last list Steam gave is kept here, per account,
so the library is complete from the first frame of the next boot:

    ~/.cache/stone/account.json    {"account": "<userdata id>", "time": ..., "games": [[appid, name,
                                    installed, minutes, last_played, size], ...]}

The cache is only what Steam itself said, for the account that was signed in then. It is not
used for another account, nor once Steam says nobody is signed in.
"""

import json
import os
import tempfile
import time

MAX_GAMES = 20000
OUT_CONFIRM_S = 20           # "signed out" is believed after Steam has said it for this long


def path():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "stone", "account.json")


def clean(rows):
    """[(appid, name, installed, minutes, last_played, size)] from anything; bad rows are dropped."""
    out = []
    for r in rows if isinstance(rows, (list, tuple)) else []:
        if (isinstance(r, (list, tuple)) and len(r) == 6 and isinstance(r[0], int) and not isinstance(r[0], bool)
                and 0 < r[0] < 0x80000000 and isinstance(r[1], str)
                and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in r[3:])):
            out.append((r[0], r[1][:200], bool(r[2]), int(r[3]), int(r[4]), int(r[5])))
        if len(out) >= MAX_GAMES:
            break
    return out


def save(account_id, rows):
    """Keep the list Steam gave for this account. An empty list is not kept: Steam answers with
    one while it is still loading, and it would hide the games until the next answer."""
    rows = clean(rows)
    if not rows or not isinstance(account_id, str) or not account_id.isdigit():
        return False
    p = path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".account-", dir=os.path.dirname(p))
        with os.fdopen(fd, "w") as f:
            json.dump({"account": account_id, "time": int(time.time()), "games": rows}, f)
        os.replace(tmp, p)
    except OSError:
        return False
    return True


def load(account_id):
    """The list kept for this account, or None."""
    try:
        with open(path()) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not account_id or d.get("account") != account_id:
        return None
    return clean(d.get("games")) or None


def forget():
    try:
        os.remove(path())
    except OSError:
        pass


def signature_rows(rows):
    """What makes one answer of Steam different from the last one kept."""
    return tuple(sorted((r[0], r[1], bool(r[2])) for r in rows))


def signature(games, live):
    """What makes the library on screen different: the games, their state and their artwork. The
    background at twice the size (hero2x) is not part of it: it only sharpens a picture already shown,
    and the page hears of it by itself (the "art" event)."""
    return (bool(live), tuple(sorted((g["appid"], bool(g.get("installed")), bool(g.get("updating")), g.get("name"),
                                      tuple(sorted((k, v) for k, v in (g.get("art") or {}).items() if k != "hero2x")))
                                     for g in games)))


class SignIn:
    """Steam's answer about the signed-in user, steadied: Steam says "nobody" for a moment at
    every start, before it signs in by itself with the saved account."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.out_since = None

    def state(self, raw, has_games=False):
        """raw: "in" | "out" | None from Steam's interface. Returns "in", "out" or None (not known)."""
        if has_games or raw == "in":
            self.out_since = None
            return "in"
        if raw != "out":
            return None
        if self.out_since is None:
            self.out_since = self.clock()
        return "out" if self.clock() - self.out_since >= OUT_CONFIRM_S else None
