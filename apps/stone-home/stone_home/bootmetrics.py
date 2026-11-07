"""Boot metrics (M02): BOOT TO VISUAL and BOOT TO READY, one record per boot.

  visual   STONE Home's page is on screen (its first frame: the line over black)
  ready    STONE Home is operable (library, settings and stoned answered; the grid is shown)

Both are seconds since the kernel started (/proc/uptime), so firmware and boot-loader time are
not in them; when systemd knows those (EFI), `systemd-analyze time` is stored next to them. The
Plymouth splash comes earlier than "visual" and is not measured here.

Records go to ~/.local/state/stone/boot-metrics.jsonl (the newest KEEP boots). The first mark of
each stage in a boot wins: a STONE Home restart never rewrites the boot's numbers. Read with
`stone-session boot`. Nothing here is privileged or blocks the interface.
"""

import json
import os
import re
import subprocess
import tempfile

STAGES = ("visual", "ready")
KEEP = 50
ANALYZE_KEYS = ("firmware", "loader", "kernel", "initrd", "userspace")


def state_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "stone")


def metrics_path():
    return os.path.join(state_dir(), "boot-metrics.jsonl")


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def boot_id(proc="/proc"):
    v = _read(os.path.join(proc, "sys", "kernel", "random", "boot_id"))
    return v or None


def uptime(proc="/proc"):
    v = _read(os.path.join(proc, "uptime"))
    try:
        return float(v.split()[0])
    except (AttributeError, ValueError, IndexError):
        return None


def _seconds(text):
    """'1min 2.345s' / '812ms' / '3.1s' -> seconds."""
    total, found = 0.0, False
    for num, unit in re.findall(r"([\d.]+)\s*(min|ms|us|s)\b", text):
        total += float(num) * {"min": 60, "s": 1, "ms": 0.001, "us": 0.000001}[unit]
        found = True
    return round(total, 3) if found else None


def parse_analyze(out):
    """`systemd-analyze time` -> {"firmware": s, "loader": s, "kernel": s, "initrd": s, "userspace": s}."""
    line = (out or "").splitlines()[0] if out else ""
    if not line.startswith("Startup finished in"):
        return None
    res = {}
    for part in line[len("Startup finished in"):].split("=")[0].split("+"):
        m = re.match(r"\s*(.+?)\s*\((\w+)\)\s*$", part)
        if m and m.group(2) in ANALYZE_KEYS:
            res[m.group(2)] = _seconds(m.group(1))
    return res or None


def systemd_analyze(run=subprocess.run):
    try:
        r = run(["systemd-analyze", "time"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_analyze(r.stdout) if r.returncode == 0 else None


def history(path=None):
    out = []
    try:
        with open(path or metrics_path()) as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict) and isinstance(d.get("boot_id"), str):
                    out.append(d)
    except OSError:
        pass
    return out


def _write(recs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".boot-", dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        for r in recs[-KEEP:]:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, path)


def mark(stage, proc="/proc", path=None, release=None, analyze=None):
    """Record a stage for this boot (first mark wins). Returns this boot's record, or None if the
    boot cannot be identified."""
    if stage not in STAGES:
        raise ValueError("stage")
    bid, up = boot_id(proc), uptime(proc)
    if bid is None or up is None:
        return None
    path = path or metrics_path()
    recs = history(path)
    rec = next((r for r in recs if r["boot_id"] == bid), None)
    if rec is None:
        rec = {"boot_id": bid, "version": (release or {}).get("STONE_VERSION"),
               "session": os.environ.get("STONE_SESSION") or "other"}
        recs.append(rec)
    key = stage + "_s"
    if key in rec:
        return rec
    rec[key] = round(up, 2)
    if stage == "ready" and analyze is not None and "systemd" not in rec:
        rec["systemd"] = analyze()
    _write(recs, path)
    return rec


def report(recs, n=5):
    """Spanish text for `stone-session boot`."""
    if not recs:
        return "Todavía no hay arranques medidos en esta consola.\n"
    lines = ["Arranques medidos (segundos desde el kernel; sin firmware ni cargador):"]
    for r in recs[-n:]:
        vis, rdy = r.get("visual_s"), r.get("ready_s")
        sd = r.get("systemd") or {}
        extra = " · firmware {firmware} s, cargador {loader} s".format(**sd) if "firmware" in sd and "loader" in sd else ""
        lines.append(f"  {r['boot_id'][:8]}  {r.get('version') or '?'}  sesión {r.get('session')}  "
                     f"BOOT TO VISUAL {vis if vis is not None else '—'}  BOOT TO READY {rdy if rdy is not None else '—'}{extra}")
    return "\n".join(lines) + "\n"
