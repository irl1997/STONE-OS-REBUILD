"""STONE's diagnostic report (Ajustes → Salud → Informe de diagnóstico), 3.1.0-rc7; checks in rc8.

Until now a failure on the console reached the developer as a photo of the TV. The report gathers, in
one .zip the person takes away with the phone (QR) or a USB drive:

  resumen.txt          what STONE found: what the person ticked, what works and what does not (one line
                       per function, diagchecks.py), version, failed services, errors, findings
  comprobaciones.txt   every check with its evidence and, when there is no data, how to get it
  eventos.jsonl        what STONE did and what came of it (events.py): games, looks, Steam in front
  juegos/vkbasalt-*.txt  vkBasalt's own log of the last launch of each game with a look
  pantalla/gamescope.json  the properties gamescope, Steam and STONE keep on the root window (HDR...)
  dispositivos.txt     input devices (the controllers) and the sound outputs
  release.txt          STONE OS and Bazzite versions, deployments (rpm-ostree status)
  sistema.txt          kernel, uptime, memory, disks, failed units, the GPU
  stone-home.txt       this boot's user journal (STONE Home, the session, Steam's output)
  stoned.txt           stoned's journal
  sistema-avisos.txt   this boot's system warnings and errors
  arranque-anterior.txt  the errors of the previous boot (a hang, a crash)
  steam-*.txt          the end of Steam's own logs (console, content, compat, bootstrap)
  estado/*.json        STONE's own state and preferences (no passwords: STONE never keeps one)
  vivo.json            what the host knows now: Steam's state, the functions of Steam's interface that
                       STONE uses and whether this Steam has them, network, screen, health

Privacy, before anything is written: e-mail addresses, Steam account ids (7656119…), the last part of
IPv4 and MAC addresses are masked, and any line that names a password, token, secret, cookie or
authorization is left out. Wi-Fi passwords are never read (NetworkManager does not print them). Nothing
leaves the console unless the person takes the file: STONE does not send it anywhere.
"""

import io
import json
import os
import re
import subprocess
import time
import zipfile

MAX_FILE = 2 * 2**20               # the end of each log: what matters is the latest
MAX_STATE = 256 * 1024

# Functions of Steam's interface that STONE relies on (steamcef.py, stone_display, stone_games):
# checked against THIS console's Steam, so an update of Steam that removed one is seen at once.
STEAM_NEEDS = ("Apps.RunGame", "Apps.TerminateApp", "Apps.GetActiveGameActions", "Apps.ContinueGameAction",
               "Apps.CancelGameAction", "Apps.RegisterForGameActionUserRequest", "Apps.RegisterForGameActionTaskChange",
               "Apps.RegisterForGameActionShowError", "Apps.LoadEula", "Apps.MarkEulaAccepted", "Apps.AddShortcut",
               "Apps.SetShortcutLaunchOptions", "Apps.SetShortcutExe", "Apps.SetShortcutStartDir", "Apps.RemoveShortcut",
               "Apps.RegisterForAppDetails", "Apps.SetAppLaunchOptions", "Apps.SetAppResolutionOverride",
               "Apps.GetLaunchOptionsForApp", "Installs.OpenInstallWizard", "Installs.RegisterForShowInstallWizard",
               "Installs.SetInstallFolder", "Installs.ContinueInstall", "Installs.CancelInstall", "Installs.OpenUninstallWizard",
               "Downloads.EnableAllDownloads", "Downloads.ResumeAppUpdate")

_SECRET_LINE = re.compile(r"password|passwd|passphrase|token|secret|authorization|cookie|psk=", re.I)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_STEAMID = re.compile(r"\b7656119\d{10}\b")
_IPV4 = re.compile(r"\b((?:25[0-5]|2[0-4]\d|1?\d?\d)\.(?:25[0-5]|2[0-4]\d|1?\d?\d)\.(?:25[0-5]|2[0-4]\d|1?\d?\d))\.(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_MAC = re.compile(r"\b((?:[0-9A-Fa-f]{2}:){3})(?:[0-9A-Fa-f]{2}:){2}[0-9A-Fa-f]{2}\b")
_ERR = re.compile(r"Traceback|\bERROR\b|\berror:|\bFAILED\b|segfault|GPU reset|ring .* timeout|\bOops\b|Kernel panic", re.I)
# Written at every start of a BC-250 and meaning nothing for play (amdgpu's display block, the CPU's RDSEED,
# ACPI names of the original board): not counted (the console's first report, 14-11-2026, said "147 errors"
# for a boot that ended well).
_BENIGN = re.compile(r"dal_irq_service_dummy_(set|ack)|Unsupported clock type|Failed to clear hpd\(rx\) source=\d+ on init|"
                     r"RDSEED is not reliable|ACPI Error: AE_NOT_FOUND|"
                     r"ACPI Error: Aborting method|Failed to subscribe to NameOwnerChanged|Activation request for '[^']+' failed", re.I)
# What really means a previous boot ended badly
_SERIOUS = re.compile(r"GPU reset|ring \S+ timeout|page fault|\bOops\b|Kernel panic|hung_task|blocked for more than|watchdog: BUG|"
                      r"Out of memory|segfault", re.I)


def redact(text):
    """The text with nothing personal in it (see the module's docstring)."""
    out = []
    for line in text.splitlines():
        if _SECRET_LINE.search(line):
            out.append("[línea omitida: nombraba una contraseña o un token]")
            continue
        line = _EMAIL.sub("[correo]", line)
        line = _STEAMID.sub("[cuenta de Steam]", line)
        line = _IPV4.sub(r"\1.x", line)
        line = _MAC.sub(r"\1xx:xx:xx", line)
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _run(argv, timeout=20):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (f"\n[salida de error]\n{r.stderr}" if r.returncode != 0 and r.stderr else "")
    except FileNotFoundError:
        return f"[{argv[0]} no está instalado]\n"
    except (OSError, subprocess.SubprocessError) as e:
        return f"[no se pudo ejecutar {argv[0]}: {e}]\n"


def _tail(path, limit=MAX_FILE):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - limit))
            data = f.read()
        text = data.decode("utf-8", "replace")
        return ("[…principio recortado]\n" + text.split("\n", 1)[-1]) if size > limit else text
    except OSError as e:
        return f"[no se pudo leer {os.path.basename(path)}: {e.strerror or e}]\n"


def _read_proc(path, limit=131072):
    """/proc files have no size: seeking from their end fails (EINVAL), so they are read from the start."""
    try:
        with open(path, "rb") as f:
            return f.read(limit).decode("utf-8", "replace")
    except OSError as e:
        return f"[no se pudo leer {os.path.basename(path)}: {e.strerror or e}]\n"


def steam_since_start(text):
    """The part of Steam's console log written since its last start ("Client version:")."""
    i = text.rfind("Client version:")
    return text[text.rfind("\n", 0, i) + 1:] if i >= 0 else text


def _cut(text, limit=MAX_FILE):
    b = text.encode("utf-8", "replace")
    return text if len(b) <= limit else "[…principio recortado]\n" + b[-limit:].decode("utf-8", "replace").split("\n", 1)[-1]


def steam_functions(probe_rows):
    """{"page", "missing": [...], "have": n} from steamcef.probe(): which of STEAM_NEEDS this Steam lacks."""
    tree = next((r.get("tree") for r in probe_rows or [] if r.get("has_steamclient") and r.get("tree")), None)
    if not tree:
        return {"page": None, "missing": None, "have": 0, "note": "La interfaz de Steam no respondió"}
    missing, have = [], 0
    for name in STEAM_NEEDS:
        area, fn = name.split(".")
        node = tree.get(area) if isinstance(tree, dict) else None
        if isinstance(node, dict) and isinstance(node.get(fn), str):
            have += 1
        else:
            missing.append(name)
    page = next((r.get("title") for r in probe_rows if r.get("tree") is tree), None)
    return {"page": page, "missing": missing, "have": have}


# Lines that are STONE's (its host and page, the session, stoned) or that STONE caused in Steam (a call
# Steam refused): what a fix of STONE needs. Steam's, gamescope's and the base image's own warnings stay
# in the files but are not counted (the first report counted 159, most of them not STONE's).
_STONE_LINE = re.compile(r"\[stone\]|stone-session|stone-home|stoned|RaiseJSException|stone_home|Traceback")


def _errors(text, n=8):
    rows = [ln.strip() for ln in text.splitlines()
            if _ERR.search(ln) and not _BENIGN.search(ln) and (_STONE_LINE.search(ln) or _SERIOUS.search(ln))]
    return len(rows), rows[-n:]


def build(out_dir=None, live=None, run=_run, home=None, now=time.time, symptoms=(), events_rows=None, root="/"):
    """Write the report and return {"path", "name", "size", "summary": {...}}. live: what the host knows
    (steam status, steam probe, net, display, health) as plain data. symptoms: what the person ticked
    (diagchecks.SYMPTOMS keys)."""
    from . import diagchecks
    from . import events as E
    home = home or os.path.expanduser("~")
    files = {}
    files["release.txt"] = (_tail("/usr/lib/stone-release", 65536) + "\n" + _tail("/etc/os-release", 65536)
                            + "\n== rpm-ostree status ==\n" + run(["rpm-ostree", "status"]))
    files["sistema.txt"] = "\n".join(f"== {' '.join(a)} ==\n{run(a)}" for a in (
        ["uname", "-a"], ["uptime"], ["free", "-m"], ["df", "-h", "/", "/var", "/var/home"],
        ["systemctl", "--failed", "--no-pager"], ["systemctl", "--user", "--failed", "--no-pager"], ["lspci", "-nnk"],
        ["nmcli", "-t", "general", "status"]))
    # STONE Home's own log (the host and the page: [stone] lines), this start and the one before
    state = os.path.join(home, ".local", "state", "stone")
    for n, out in (("home.log", "stone-home-app.txt"), ("home.log.1", "stone-home-app-anterior.txt")):
        if os.path.isfile(os.path.join(state, n)):
            files[out] = _tail(os.path.join(state, n))
    files["stone-home.txt"] = _cut(run(["journalctl", "--user", "-b", "--no-pager", "-o", "short-iso", "-n", "6000"], 60))
    files["stoned.txt"] = _cut(run(["journalctl", "-b", "-u", "stoned", "--no-pager", "-o", "short-iso", "-n", "2000"], 60))
    files["sistema-avisos.txt"] = _cut(run(["journalctl", "-b", "-p", "warning", "--no-pager", "-o", "short-iso", "-n", "3000"], 60))
    files["arranque-anterior.txt"] = _cut(run(["journalctl", "-b", "-1", "-p", "err", "--no-pager", "-o", "short-iso", "-n", "1500"], 60))
    steam_logs = os.path.join(home, ".local", "share", "Steam", "logs")
    for n in ("console_log.txt", "content_log.txt", "compat_log.txt", "bootstrap_log.txt", "stderr.txt"):
        p = os.path.join(steam_logs, n)
        if os.path.isfile(p):
            files[f"steam-{n}"] = _tail(p)
    for base, sub in ((os.path.join(home, ".local", "state", "stone"), "estado"), (os.path.join(home, ".config", "stone"), "preferencias")):
        try:
            names = sorted(os.listdir(base))
        except OSError:
            names = []
        for n in names:
            p = os.path.join(base, n)
            if n.endswith(".json") and os.path.isfile(p) and os.path.getsize(p) <= MAX_STATE:
                text = _tail(p, MAX_STATE)
                try:                                     # one key per line: a key that names a token goes, not the file
                    text = json.dumps(json.loads(text), indent=1, ensure_ascii=False) + "\n"
                except ValueError:
                    pass
                files[f"{sub}/{n}"] = text
    # rc12: the boot, to make it shorter with data: STONE's own marks per boot (first frame, ready) and
    # systemd's (where the seconds go before STONE: the slowest units and the chain that waited)
    files["arranque.txt"] = ("== STONE: segundos desde el kernel (boot-metrics.jsonl, últimos arranques) ==\n"
                             + "\n".join(_tail(os.path.join(state, "boot-metrics.jsonl"), 65536).splitlines()[-10:])
                             + "\n\n== systemd-analyze time ==\n" + run(["systemd-analyze", "time"], 20)
                             + "\n== systemd-analyze blame (los 40 más lentos) ==\n" + "\n".join(run(["systemd-analyze", "blame", "--no-pager"], 30).splitlines()[:40])
                             + "\n\n== systemd-analyze critical-chain ==\n" + run(["systemd-analyze", "critical-chain", "--no-pager"], 30)
                             + "\n== systemd-analyze --user blame (los 20 más lentos) ==\n" + "\n".join(run(["systemd-analyze", "--user", "blame", "--no-pager"], 30).splitlines()[:20]))
    looks_dir = os.path.join(state, "looks")
    try:
        vk = sorted(n for n in os.listdir(looks_dir) if n.startswith("vkbasalt-") and n.endswith(".log"))
    except OSError:
        vk = []
    for n in vk[-8:]:
        files[f"juegos/{n[:-4]}.txt"] = _tail(os.path.join(looks_dir, n), 256 * 1024)
    files["dispositivos.txt"] = ("== /proc/bus/input/devices ==\n" + _read_proc(os.path.join(root, "proc/bus/input/devices"))
                                 + "\n== wpctl status ==\n" + run(["wpctl", "status"], 10)
                                 + "\n== nmcli device status ==\n" + run(["nmcli", "-t", "device", "status"], 10))
    live = dict(live or {})
    if "steam_probe" in live:
        live["steam_functions"] = steam_functions(live.pop("steam_probe"))
    names = live.pop("names", None) or {}
    if live.get("gamescope_atoms"):
        files["pantalla/gamescope.json"] = json.dumps(live["gamescope_atoms"], indent=1, ensure_ascii=False, default=str)
    ev = events_rows if events_rows is not None else E.read(file=os.path.join(state, "events.jsonl"))
    files["eventos.jsonl"] = "\n".join(json.dumps(e, ensure_ascii=False) for e in ev[-1500:]) + "\n"
    # Steam's console log keeps days: only what this Steam has said since it started counts (the second
    # report, 15-11-2026, counted 184 rejected calls of which none were from the running rc8)
    logs = "\n".join([files.get(k, "") for k in ("stone-home.txt", "stone-home-app.txt", "stoned.txt")]
                      + [steam_since_start(files.get("steam-console_log.txt", ""))])
    checks = diagchecks.run_checks(live, files["stone-home.txt"], logs, home, run, symptoms, ev, root, names)
    symptoms = [x for x in symptoms if x in diagchecks.SYMPTOMS]
    files["comprobaciones.txt"] = diagchecks.text(checks, symptoms)
    files["vivo.json"] = json.dumps(live, indent=1, ensure_ascii=False, default=str)
    files = {k: redact(v) for k, v in files.items()}

    # what a person (and the developer) reads first
    n_err, last = _errors(files["stone-home.txt"] + files["stoned.txt"] + files.get("stone-home-app.txt", ""))
    n_prev, _ = _errors(files["arranque-anterior.txt"])
    serious_prev = [ln.strip() for ln in files["arranque-anterior.txt"].splitlines() if _SERIOUS.search(ln)]
    failed = [ln.split()[1] if ln.split()[0] in ("●", "*") else ln.split()[0]
              for ln in files["sistema.txt"].splitlines() if ".service" in ln and ("failed" in ln or "fallid" in ln)][:10]
    sf = live.get("steam_functions") or {}
    findings = []
    if failed:
        findings.append(f"Servicios con fallo: {', '.join(failed)}")
    if sf.get("missing"):
        findings.append(f"Este Steam no tiene {len(sf['missing'])} funciones que STONE usa: {', '.join(sf['missing'][:5])}")
    elif sf.get("missing") is None:
        findings.append("La interfaz de Steam no respondió al hacer el informe")
    if serious_prev:
        findings.append(f"El arranque anterior terminó con fallos graves ({len(serious_prev)}): {serious_prev[-1][-120:]}")
    for c in (live.get("health") or []):
        if isinstance(c, (list, tuple)) and len(c) >= 3 and c[0] == "fail":
            findings.append(f"{c[1]}: {c[2]}")
    brief = [{k: redact(c[k]) if isinstance(c[k], str) else c[k] for k in ("id", "name", "status", "label", "detail", "symptom", "how")}
             for c in checks]
    summary = {"version": (re.search(r'STONE_VERSION="?([^"\n]+)', files["release.txt"]) or [None, "—"])[1],
               "errors": n_err, "previous_boot_errors": n_prev, "previous_boot_serious": len(serious_prev), "failed_services": failed,
               "steam_functions": sf, "findings": findings[:8], "last_errors": last, "checks": brief,
               "symptoms": [diagchecks.SYMPTOMS[x][0] for x in symptoms],
               "failing": sum(1 for c in checks if c["status"] == diagchecks.FAIL)}
    files["resumen.txt"] = redact(
        "INFORME DE DIAGNÓSTICO DE STONE OS\n"
        f"Hecho: {time.strftime('%d-%m-%Y %H:%M', time.localtime(now()))}\nVersión: {summary['version']}\n\n"
        + ("LO QUE MARCASTE\n" + "\n".join(f"- {x}" for x in summary["symptoms"]) + "\n\n" if symptoms else "")
        + "QUÉ FUNCIONA Y QUÉ NO (detalle y pruebas en comprobaciones.txt)\n"
        + "\n".join(f"[{c['label']}] {c['name']}: {c['detail']}" for c in brief) + "\n\n"
        f"Errores de STONE en este arranque: {n_err}\nErrores de STONE o graves en el arranque anterior: {n_prev}\n"
        f"Funciones de Steam que STONE usa: {sf.get('have', 0)} de {len(STEAM_NEEDS)} presentes"
        + (f" (faltan: {', '.join(sf['missing'])})" if sf.get("missing") else "") + "\n\nHALLAZGOS\n"
        + ("\n".join(f"- {f}" for f in findings) or "- Nada fuera de lo normal") + "\n\nÚLTIMOS ERRORES\n"
        + ("\n".join(last) or "(ninguno)") + "\n")

    out_dir = out_dir or os.path.join(home, "STONE-informes")
    os.makedirs(out_dir, exist_ok=True)
    name = time.strftime("stone-informe-%Y%m%d-%H%M.zip", time.localtime(now()))
    path = os.path.join(out_dir, name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k in ["resumen.txt"] + sorted(f for f in files if f != "resumen.txt"):
            z.writestr(k, files[k])
    with open(path + ".part", "wb") as f:
        f.write(buf.getvalue())
    os.replace(path + ".part", path)
    for old in sorted(n for n in os.listdir(out_dir) if n.startswith("stone-informe-") and n.endswith(".zip"))[:-5]:
        try:
            os.remove(os.path.join(out_dir, old))      # the last five are kept
        except OSError:
            pass
    return {"path": path, "name": name, "size": os.path.getsize(path), "summary": summary}
