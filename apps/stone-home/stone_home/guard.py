"""STONE session boot guard (D-29): the console never stays stuck in a STONE session that fails.

Runs as root at every boot, before the display manager (stone-session-guard.service):

  1. Removes STONE's next-login-only session (zzz-stone-temp-login.conf): a reboot always returns
     to the default session.
  2. While the STONE session is the automatic one (zz-stone-session.conf), it remembers which boots
     started with it (/var/lib/stone/session-guard.json).
  3. If the two previous of those boots never reached "Home operable" (BOOT TO READY in the console
     user's ~/.local/state/stone/boot-metrics.jsonl, written by STONE Home), the STONE session stops
     being the automatic one: zz-stone-session.conf moves to /var/lib/stone and the reason is kept.
     The console starts in Bazzite's Game Mode; `stone-session status` explains why and
     `sudo stone-session default on` brings the STONE session back.

A boot switched off by hand before Home appeared also counts as failed: two in a row disable the
STONE session too. That is the price of never leaving the console on a black screen.
"""

import json
import os
import pwd
import re
import shutil
import sys
import tempfile
import time

SDDM_DIR = "/etc/sddm.conf.d"
DROPIN = "zz-stone-session.conf"
TEMP = "zzz-stone-temp-login.conf"
STATE_DIR = "/var/lib/stone"
STATE = "session-guard.json"
KEEP = 10
FAILS = 2


def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def console_home(sddm_dir=SDDM_DIR, getpw=pwd.getpwnam, getuid=pwd.getpwuid):
    """Home of the autologin user (the last User= in SDDM's drop-ins, as SDDM reads them), or of uid 1000."""
    user = None
    try:
        names = sorted(os.listdir(sddm_dir))
    except OSError:
        names = []
    for n in names:
        if not n.endswith(".conf"):
            continue
        for m in re.finditer(r"^\s*User\s*=\s*(\S+)\s*$", _read(os.path.join(sddm_dir, n)) or "", re.M):
            user = m.group(1)
    try:
        return getpw(user).pw_dir if user else getuid(1000).pw_dir
    except KeyError:
        return None


def ready_boots(home):
    """Boot ids in which STONE Home became operable (boot-metrics.jsonl)."""
    out = set()
    text = _read(os.path.join(home, ".local", "state", "stone", "boot-metrics.jsonl")) if home else None
    for line in (text or "").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("boot_id"), str) and d.get("ready_s") is not None:
            out.add(d["boot_id"])
    return out


def load_state(state_dir=STATE_DIR):
    try:
        d = json.loads(_read(os.path.join(state_dir, STATE)) or "{}")
    except ValueError:
        d = {}
    if not isinstance(d, dict):
        d = {}
    boots = [b for b in d.get("boots", []) if isinstance(b, str)]
    return {"boots": boots, "disabled": d.get("disabled") if isinstance(d.get("disabled"), dict) else None}


def save_state(st, state_dir=STATE_DIR):
    os.makedirs(state_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".guard-", dir=state_dir)
    with os.fdopen(fd, "w") as f:
        json.dump(st, f)
    os.chmod(tmp, 0o644)                  # stone-session status reads it as the console user
    os.replace(tmp, os.path.join(state_dir, STATE))


def run(boot_id, sddm_dir=SDDM_DIR, state_dir=STATE_DIR, home=None, now=time.time, log=print):
    """One boot. Returns the action taken: stone-not-default, watching or disabled."""
    temp = os.path.join(sddm_dir, TEMP)
    if os.path.exists(temp):
        os.remove(temp)
        log("next-login-only session cleared")
    dropin = os.path.join(sddm_dir, DROPIN)
    st = load_state(state_dir)
    if not os.path.exists(dropin):
        save_state(st, state_dir)
        return "stone-not-default"
    home = home if home is not None else console_home(sddm_dir)
    ok = ready_boots(home)
    previous = [b for b in st["boots"] if b != boot_id][-FAILS:]
    if len(previous) == FAILS and not any(b in ok for b in previous):
        os.makedirs(state_dir, exist_ok=True)
        shutil.move(dropin, os.path.join(state_dir, DROPIN + ".disabled"))
        reason = f"STONE Home no llegó a estar operable en los {FAILS} últimos arranques"
        st = {"boots": [], "disabled": {"time": int(now()), "reason": reason, "boots": previous}}
        save_state(st, state_dir)
        log(f"STONE session disabled: {reason}; Bazzite's Game Mode starts instead")
        return "disabled"
    if boot_id not in st["boots"]:
        st["boots"] = (st["boots"] + [boot_id])[-KEEP:]
    st["disabled"] = None
    save_state(st, state_dir)
    return "watching"


def enable(sddm_dir=SDDM_DIR, state_dir=STATE_DIR):
    """`stone-session default on`: forget the boots and the reason (the drop-in is written by the caller)."""
    stale = os.path.join(state_dir, DROPIN + ".disabled")
    if os.path.exists(stale):
        os.remove(stale)
    if os.path.isdir(state_dir):
        save_state({"boots": [], "disabled": None}, state_dir)


def main():
    boot_id = (_read("/proc/sys/kernel/random/boot_id") or "").strip()
    if not boot_id:
        print("stone-session-guard: no boot id; nothing done", file=sys.stderr)
        return 0
    try:
        print(f"stone-session-guard: {run(boot_id, log=lambda m: print('stone-session-guard: ' + m))}")
    except OSError as e:                  # never blocks the display manager
        print(f"stone-session-guard: {e}", file=sys.stderr)
    return 0
