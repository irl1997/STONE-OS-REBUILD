"""STONE CONNECT and SETTINGS (M12, M16): Bluetooth, audio output and network from STONE Home.

Through the standard tools of the image, with fixed argument lists (never a shell, never a string
built from the page except a Bluetooth address, a PipeWire node id or a Wi-Fi name, each checked):

  Bluetooth   bluetoothctl (BlueZ): list, scan for a few seconds, pair + trust + connect, disconnect,
              forget. Controllers, headphones and keyboards alike.
  Audio       wpctl (PipeWire/WirePlumber): outputs, the default one, its volume and mute.
  Network     nmcli (NetworkManager): wired and Wi-Fi state, visible Wi-Fi networks, connect (with a
              password typed on STONE Home's on-screen keyboard), disconnect.

Every function returns data or {"error": "<Spanish sentence>"}; a missing tool or service is
"no disponible", never a crash (D-31). In the STONE session Home runs outside the logind session:
NetworkManager's polkit actions are allowed to the console administrator by rules.d/50-stone.rules.
"""

import re
import subprocess

MAC = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")


def _run(argv, timeout=20):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return None, "", f"{argv[0]} no está instalado"
    except (OSError, subprocess.SubprocessError) as e:
        return None, "", str(e)


# ---- Bluetooth ---------------------------------------------------------------------------------
def _bt_info(text):
    info = {}
    for line in text.splitlines():
        k, sep, v = line.strip().partition(":")
        if sep:
            info[k.strip()] = v.strip()
    return info


def bt_devices(run=_run):
    rc, out, err = run(["bluetoothctl", "devices"])
    if rc is None:
        return {"error": "Bluetooth no disponible: " + err}
    if rc != 0:
        return {"error": "El servicio de Bluetooth no responde"}
    devs = []
    for line in out.splitlines():
        m = re.match(r"^Device ([0-9A-F:]{17}) (.*)$", line.strip())
        if not m:
            continue
        rc2, info_txt, _ = run(["bluetoothctl", "info", m.group(1)])
        info = _bt_info(info_txt) if rc2 == 0 else {}
        bat = re.search(r"\((\d+)\)", info.get("Battery Percentage", ""))
        devs.append({"mac": m.group(1), "name": info.get("Alias") or m.group(2), "icon": info.get("Icon") or "",
                     "paired": info.get("Paired") == "yes", "connected": info.get("Connected") == "yes",
                     "battery": int(bat.group(1)) if bat else None})
    devs.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return {"devices": devs}


def bt_scan(seconds=8, run=_run):
    rc, _, err = run(["bluetoothctl", "--timeout", str(int(seconds)), "scan", "on"], timeout=seconds + 10)
    if rc is None:
        return {"error": "Bluetooth no disponible: " + err}
    return bt_devices(run)


def bt_action(action, mac, run=_run):
    if not isinstance(mac, str) or not MAC.match(mac):
        return {"error": "Dirección no válida"}
    steps = {"pair": [["--agent", "NoInputNoOutput", "pair", mac], ["trust", mac], ["connect", mac]], "connect": [["connect", mac]],
             "disconnect": [["disconnect", mac]], "forget": [["remove", mac]]}.get(action)
    if steps is None:
        return {"error": "Acción no válida"}
    for step in steps:
        rc, out, err = run(["bluetoothctl", "--timeout", "20", *step], timeout=30)
        if rc is None:
            return {"error": "Bluetooth no disponible: " + err}
        if rc != 0 and not ("pair" in step and "AlreadyExists" in out + err):
            return {"error": f"No se pudo ({step[-2]}): " + ((out + err).strip().splitlines() or ["sin respuesta"])[-1]}
    return {"ok": True}


# ---- Audio -------------------------------------------------------------------------------------
def audio_status(run=_run):
    rc, out, err = run(["wpctl", "status"])
    if rc is None or rc != 0:
        return {"error": "Audio no disponible" + (": " + err if err else "")}
    sinks, in_sinks = [], False
    for line in out.splitlines():
        s = line.strip(" │├└─")
        if "Sinks:" in line:
            in_sinks = True
            continue
        if in_sinks and ("Sources:" in line or "Filters:" in line or "Streams:" in line or not s):
            if sinks or "Sources:" in line or "Filters:" in line or "Streams:" in line:
                in_sinks = False
            continue
        if in_sinks:
            m = re.match(r"^(\*)?\s*(\d+)\.\s+(.+?)(?:\s+\[vol:.*\])?$", s)
            if m:
                sinks.append({"id": int(m.group(2)), "name": m.group(3).strip(), "default": bool(m.group(1))})
    rc, vol, _ = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    m = re.search(r"Volume:\s*([\d.]+)", vol or "")
    return {"outputs": sinks, "volume": float(m.group(1)) if m else None, "muted": "[MUTED]" in (vol or "")}


def audio_default(node_id, run=_run):
    if isinstance(node_id, bool) or not isinstance(node_id, int) or not 0 < node_id < 100000:
        return {"error": "Salida no válida"}
    rc, _, err = run(["wpctl", "set-default", str(node_id)])
    return {"ok": True} if rc == 0 else {"error": "No se pudo cambiar la salida" + (": " + err.strip() if err else "")}


def audio_volume(value, run=_run):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        return {"error": "Volumen no válido"}
    rc, _, _ = run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{value:.2f}"])
    run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"])
    return {"ok": True} if rc == 0 else {"error": "No se pudo cambiar el volumen"}


# ---- Network -----------------------------------------------------------------------------------
def _nm_fields(line):
    """nmcli -t splits on ':' and escapes ':' and '\\' inside values."""
    out, cur, esc = [], "", False
    for ch in line:
        if esc:
            cur += ch
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def net_status(run=_run):
    rc, out, err = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
    if rc is None or rc != 0:
        return {"error": "Red no disponible" + (": " + err.strip() if err else "")}
    devs = []
    for line in out.splitlines():
        f = _nm_fields(line)
        if len(f) >= 4 and f[1] in ("ethernet", "wifi"):
            devs.append({"device": f[0], "type": f[1], "state": f[2], "connection": f[3] or None})
    return {"devices": devs, "online": any(d["state"] == "connected" for d in devs)}


def wifi_list(run=_run):
    rc, out, err = run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "auto"], timeout=30)
    if rc is None or rc != 0:
        return {"error": "Wi-Fi no disponible" + (": " + err.strip() if err else "")}
    nets = {}
    for line in out.splitlines():
        f = _nm_fields(line)
        if len(f) < 4 or not f[1]:
            continue
        sig = int(f[2]) if f[2].isdigit() else 0
        if f[1] not in nets or sig > nets[f[1]]["signal"]:
            nets[f[1]] = {"ssid": f[1], "signal": sig, "secure": f[3] not in ("", "--"), "active": f[0].strip() == "*"}
    return {"networks": sorted(nets.values(), key=lambda n: (not n["active"], -n["signal"]))}


def wifi_connect(ssid, password=None, run=_run):
    if not isinstance(ssid, str) or not 0 < len(ssid.encode()) <= 32 or "\n" in ssid:
        return {"error": "Nombre de red no válido"}
    if password is not None and (not isinstance(password, str) or not 8 <= len(password) <= 63):
        return {"error": "La contraseña de Wi-Fi tiene entre 8 y 63 caracteres"}
    argv = ["nmcli", "device", "wifi", "connect", ssid] + (["password", password] if password else [])
    rc, out, err = run(argv, timeout=60)
    if rc == 0:
        return {"ok": True}
    msg = (err or out).strip()
    if "Secrets were required" in msg or "802-11-wireless-security" in msg:
        return {"error": "Contraseña incorrecta"}
    return {"error": "No se pudo conectar" + (": " + msg.splitlines()[-1] if msg else "")}


def wifi_disconnect(device, run=_run):
    if not isinstance(device, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", device):
        return {"error": "Dispositivo no válido"}
    rc, _, _ = run(["nmcli", "device", "disconnect", device])
    return {"ok": True} if rc == 0 else {"error": "No se pudo desconectar"}
