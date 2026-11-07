"""STONE Crash Black Box (M19): at every boot, keep what the previous boot logged before it ended.

Run as root by stone-blackbox.service. For the previous boot it stores, in /var/lib/stone/blackbox:

  <time>-<boot8>.json   boot id, when, whether it ended cleanly (a normal power-off or reboot was
                        logged) and how many error lines it had
  <time>-<boot8>.log    its error lines (priority err and worse) and its last lines, for diagnosis

The newest KEEP boots are kept. Read by STONE HEALTH (health.py) and `stone-doctor`. Nothing is sent
anywhere. A boot whose end was not logged (power cut, hang, reset button) counts as not clean.
"""

import json
import os
import re
import subprocess
import time

DIR = os.environ.get("STONE_BLACKBOX_DIR", "/var/lib/stone/blackbox")
KEEP = 10
CLEAN = re.compile(r"Reached target .*(Power-Off|Power Off|Reboot|Halt|Shutdown)|systemd-shutdown|Journal stopped")


def _run(argv, timeout=30):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return None, ""


def previous_boot(run=_run):
    """Boot id of the boot before this one, from `journalctl --list-boots`, or None."""
    rc, txt = run(["journalctl", "--list-boots", "--no-pager"])
    if rc != 0:
        return None
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "-1" and re.fullmatch(r"[0-9a-f]{32}", parts[1]):
            return parts[1]
    return None


def record(run=_run, directory=DIR, now=time.time):
    bid = previous_boot(run)
    if bid is None:
        return None
    os.makedirs(directory, mode=0o755, exist_ok=True)
    if any(n.endswith(f"-{bid[:8]}.json") for n in os.listdir(directory)):
        return "already"
    _, tail = run(["journalctl", "-b", bid, "-n", "300", "--no-pager", "-o", "short-monotonic"])
    _, errs = run(["journalctl", "-b", bid, "-p", "err", "-n", "300", "--no-pager", "-o", "short-monotonic"])
    errors = [ln for ln in errs.splitlines() if ln.strip() and not ln.startswith("--")]
    clean = bool(CLEAN.search(tail))
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now()))
    base = os.path.join(directory, f"{stamp}-{bid[:8]}")
    with open(base + ".log", "w") as f:
        f.write(f"# STONE black box · boot {bid} · {'clean' if clean else 'NOT CLEAN'}\n\n## errors\n")
        f.write("\n".join(errors) + "\n\n## last lines\n" + tail)
    with open(base + ".json", "w") as f:
        json.dump({"boot_id": bid, "time": int(now()), "clean": clean, "errors": len(errors)}, f)
    for p in (base + ".log", base + ".json"):
        os.chmod(p, 0o644)
    stems = sorted({n.rsplit(".", 1)[0] for n in os.listdir(directory) if n.endswith((".json", ".log"))})
    for old in stems[:-KEEP]:
        for ext in (".json", ".log"):
            try:
                os.remove(os.path.join(directory, old + ext))
            except OSError:
                pass
    return "clean" if clean else "not-clean"


def main():
    try:
        print(f"stone-blackbox: {record()}")
    except OSError as e:                  # never blocks the boot
        print(f"stone-blackbox: {e}")
    return 0
