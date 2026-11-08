"""STONE HEALTH (M19) and `stone-doctor`: what the console is, read-only.

  snapshot()   CPU (cores online, model), memory, storage, STONE's services, GPU errors in this
               boot's kernel log, the black box (logs of earlier boots, stone-blackbox.service)
  doctor()     the same facts as checks: ok / warn / fail with a Spanish sentence each. STONE Home's
               Ajustes → Salud shows them; FIRST RUN shows the summary; `stone-doctor` prints them.

Nothing here writes, starts or stops anything. Every reading that cannot be made says so
("unknown") instead of guessing (D-18). Temperatures, clocks and power come from stoned's
telemetry in the page, not from here.
"""

import json
import os
import re
import subprocess
import sys

SERVICES = (("stoned.service", "Servicio de rendimiento (stoned)", True),
            ("cyan-skillfish-governor-smu.service", "Regulador de GPU", True),
            ("stone-session-guard.service", "Guardia de arranque", False),
            ("stone-blackbox.service", "Caja negra", False))
BLACKBOX = os.environ.get("STONE_BLACKBOX_DIR", "/var/lib/stone/blackbox")
MIN_FREE_GB = 20


def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def _run(argv, timeout=10):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return None, ""


def cpu(proc="/proc", sysfs="/sys"):
    model = None
    for line in (_read(os.path.join(proc, "cpuinfo")) or "").splitlines():
        if line.startswith("model name"):
            model = line.split(":", 1)[1].strip()
            break
    online = (_read(os.path.join(sysfs, "devices/system/cpu/online")) or "").strip()
    threads = 0
    for part in online.split(","):
        if not part:
            continue
        a, _, b = part.partition("-")
        try:
            threads += (int(b) - int(a) + 1) if b else 1
        except ValueError:
            threads = 0
            break
    return {"model": model, "threads": threads or None}


def memory(proc="/proc"):
    kv = {}
    for line in (_read(os.path.join(proc, "meminfo")) or "").splitlines():
        k, _, v = line.partition(":")
        m = re.match(r"\s*(\d+)\s*kB", v)
        if m:
            kv[k] = int(m.group(1)) * 1024
    if "MemTotal" not in kv:
        return None
    return {"total": kv["MemTotal"], "available": kv.get("MemAvailable")}


def storage(paths=("/", "/var/home")):
    out, seen = [], set()
    for p in paths:
        try:
            st = os.statvfs(p)
            dev = os.stat(p).st_dev
        except OSError:
            continue
        if dev in seen:
            continue
        seen.add(dev)
        out.append({"path": p, "total": st.f_blocks * st.f_frsize, "free": st.f_bavail * st.f_frsize})
    return out


def services(run=_run):
    out = []
    for unit, label, required in SERVICES:
        rc, txt = run(["systemctl", "is-active", unit])
        state = txt.strip() or ("unknown" if rc is None else "inactive")
        out.append({"unit": unit, "label": label, "state": state, "required": required})
    return out


def gpu_errors(run=_run):
    """amdgpu error lines in this boot's kernel log; None if the log cannot be read."""
    rc, txt = run(["journalctl", "-k", "-b", "-p", "err", "--no-pager", "-q", "-o", "cat"], timeout=15)
    if rc is None or rc not in (0, 1):
        return None
    return [ln for ln in txt.splitlines() if "amdgpu" in ln.lower()][:20]


def blackbox(directory=BLACKBOX):
    out = []
    try:
        names = sorted(os.listdir(directory), reverse=True)
    except OSError:
        return out
    for n in names:
        if not n.endswith(".json"):
            continue
        try:
            d = json.loads(_read(os.path.join(directory, n)) or "")
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append({k: d.get(k) for k in ("boot_id", "time", "clean", "errors")})
    return out[:10]


def steam_ui():
    """Steam's interface reachable (library of the account, installing, Steam's settings): True,
    False, or None when this is not a STONE Home process (stone-doctor in a terminal still asks)."""
    try:
        from . import steamcef
        return steamcef.reachable()
    except Exception:  # noqa: BLE001
        return None


def snapshot(run=_run):
    return {"cpu": cpu(), "memory": memory(), "storage": storage(), "services": services(run),
            "gpu_errors": gpu_errors(run), "blackbox": blackbox(), "steam_ui": steam_ui()}


def doctor(snap):
    """[(level, title, detail)] with level ok | warn | fail."""
    out = []
    c = snap.get("cpu") or {}
    if c.get("threads"):
        out.append(("ok", "CPU", f"{c['threads']} hilos en línea" + (f" · {c['model']}" if c.get("model") else "")))
    else:
        out.append(("warn", "CPU", "No se pudo leer cuántos núcleos están en línea"))
    m = snap.get("memory")
    out.append(("ok", "Memoria", f"{m['total'] / 2**30:.1f} GB") if m else ("warn", "Memoria", "No se pudo leer"))
    for s in snap.get("storage") or []:
        free_gb = s["free"] / 2**30
        lvl = "ok" if free_gb >= MIN_FREE_GB else "warn"
        out.append((lvl, f"Disco {s['path']}", f"{free_gb:.0f} GB libres de {s['total'] / 2**30:.0f} GB"
                    + ("" if lvl == "ok" else " · queda poco espacio")))
    for s in snap.get("services") or []:
        if s["state"] == "active" or (not s["required"] and s["state"] in ("inactive", "activating")):
            out.append(("ok", s["label"], "en marcha" if s["state"] == "active" else "en espera"))
        else:
            out.append(("fail" if s["required"] else "warn", s["label"], f"estado: {s['state']}"))
    ge = snap.get("gpu_errors")
    if ge is None:
        out.append(("warn", "GPU", "No se pudo leer el registro del kernel"))
    elif ge:
        out.append(("warn", "GPU", f"{len(ge)} errores de amdgpu en este arranque"))
    else:
        out.append(("ok", "GPU", "Sin errores en este arranque"))
    su = snap.get("steam_ui")
    if su is not None:
        out.append(("ok", "Interfaz de Steam", "responde: biblioteca de la cuenta, instalar y ajustes de Steam") if su
                    else ("warn", "Interfaz de Steam", "no responde: solo se ven los juegos instalados. Reinicia la consola; si sigue, avisa"))
    bb = snap.get("blackbox") or []
    crashes = [b for b in bb if b.get("clean") is False]
    out.append(("warn" if crashes else "ok", "Caja negra",
                f"{len(crashes)} arranque{'s' if len(crashes) != 1 else ''} anterior{'es' if len(crashes) != 1 else ''} terminaron mal"
                if crashes else "Los arranques anteriores terminaron bien"))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    snap = snapshot()
    checks = doctor(snap)
    if argv == ["--json"]:
        print(json.dumps({"snapshot": snap, "checks": checks}))
        return 0
    mark = {"ok": "OK   ", "warn": "AVISO", "fail": "FALLO"}
    for lvl, title, detail in checks:
        print(f"{mark[lvl]}  {title}: {detail}")
    worst = "fail" if any(c[0] == "fail" for c in checks) else "warn" if any(c[0] == "warn" for c in checks) else "ok"
    print({"ok": "\nTodo bien.", "warn": "\nHay avisos: la consola funciona, revisa lo marcado.",
           "fail": "\nHay fallos: algo de STONE no está en marcha."}[worst])
    return 1 if worst == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
