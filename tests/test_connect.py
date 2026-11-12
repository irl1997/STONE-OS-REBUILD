"""STONE CONNECT and SETTINGS (stone_home/connect.py) with recorded outputs of bluetoothctl, wpctl
and nmcli. Pure Python: runs anywhere.

    python3 tests/test_connect.py     (or: pytest tests/test_connect.py)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import connect as C  # noqa: E402

WPCTL = """PipeWire 'pipewire-0' [1.4.7, stone@console, cookie:1]
 └─ Clients:
        33. WirePlumber                         [1.4.7, stone@console, pid:1210]

Audio
 ├─ Devices:
 │      45. Navi 10 HDMI/DP Audio               [alsa]
 │
 ├─ Sinks:
 │  *   51. Navi 10 HDMI/DP Audio Digital Stereo (HDMI) [vol: 0.60]
 │      52. USB Audio Analog Stereo             [vol: 1.00]
 │
 ├─ Sources:
 │      60. USB Audio Mono                      [vol: 1.00]
 │
 └─ Streams:

Video
"""


def fake(table):
    calls = []

    def run(argv, timeout=20):
        calls.append(argv)
        for key, res in table.items():
            if tuple(argv[:len(key)]) == key:
                return res
        return 1, "", "unknown"
    run.calls = calls
    return run


def test_bluetooth_devices_pairing_and_refusals():
    info = "Device AA:BB:CC:DD:EE:01 (public)\n\tAlias: Mando inalámbrico\n\tIcon: input-gaming\n\tPaired: yes\n\tConnected: yes\n\tBattery Percentage: 0x50 (80)\n"
    run = fake({("bluetoothctl", "devices"): (0, "Device AA:BB:CC:DD:EE:01 Wireless Controller\nDevice AA:BB:CC:DD:EE:02 Headset\n", ""),
                ("bluetoothctl", "info", "AA:BB:CC:DD:EE:01"): (0, info, ""),
                ("bluetoothctl", "info", "AA:BB:CC:DD:EE:02"): (0, "\tPaired: no\n\tConnected: no\n", ""),
                ("bluetoothctl", "--timeout"): (0, "", "")})
    d = C.bt_devices(run)["devices"]
    assert d[0] == {"mac": "AA:BB:CC:DD:EE:01", "name": "Mando inalámbrico", "icon": "input-gaming", "paired": True,
                    "connected": True, "battery": 80}
    assert d[1]["name"] == "Headset" and not d[1]["paired"]
    assert C.bt_action("pair", "AA:BB:CC:DD:EE:02", run) == {"ok": True}
    assert [c[3:] for c in run.calls if "--timeout" in c][-3:] == [["--agent", "NoInputNoOutput", "pair", "AA:BB:CC:DD:EE:02"],
                                                                     ["trust", "AA:BB:CC:DD:EE:02"], ["connect", "AA:BB:CC:DD:EE:02"]]
    for bad in (("pair", "aa:bb"), ("pair", "AA:BB:CC:DD:EE:02; reboot"), ("rm", "AA:BB:CC:DD:EE:02")):
        assert "error" in C.bt_action(*bad, run=run), bad
    assert "no disponible" in C.bt_devices(fake({("bluetoothctl",): (None, "", "bluetoothctl no está instalado")}))["error"]


def test_audio_outputs_volume_and_checks():
    run = fake({("wpctl", "status"): (0, WPCTL, ""), ("wpctl", "get-volume"): (0, "Volume: 0.60\n", ""),
                ("wpctl", "set-default"): (0, "", ""), ("wpctl", "set-volume"): (0, "", ""), ("wpctl", "set-mute"): (0, "", "")})
    a = C.audio_status(run)
    assert a["outputs"] == [{"id": 51, "name": "Navi 10 HDMI/DP Audio Digital Stereo (HDMI)", "default": True},
                            {"id": 52, "name": "USB Audio Analog Stereo", "default": False}] and a["volume"] == 0.6, a
    assert C.audio_default(52, run) == {"ok": True} and C.audio_volume(0.35, run) == {"ok": True}
    assert ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.35"] in run.calls
    for bad in (True, "52", -1, 10 ** 6):
        assert "error" in C.audio_default(bad, run)
    assert "error" in C.audio_volume(1.5, run) and "error" in C.audio_status(fake({}))


def test_network_status_wifi_list_and_connect():
    run = fake({("nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION"): (0, "enp1s0:ethernet:connected:Wired connection 1\nwlan0:wifi:disconnected:\nlo:loopback:unmanaged:\n", ""),
                ("nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY"): (0, " :Casa:82:WPA2\n:Casa:40:WPA2\n*:Oficina\\:2:60:WPA2 WPA3\n:Invitados:54:\n::30:WPA2\n", ""),
                ("nmcli", "device", "wifi", "connect"): (0, "Device 'wlan0' successfully activated", ""),
                ("nmcli", "device", "disconnect"): (0, "", "")})
    s = C.net_status(run)
    assert s["online"] and [d["type"] for d in s["devices"]] == ["ethernet", "wifi"]
    nets = C.wifi_list(run)["networks"]
    assert [n["ssid"] for n in nets] == ["Oficina:2", "Casa", "Invitados"] and nets[1]["signal"] == 82 and not nets[2]["secure"]
    assert C.wifi_connect("Casa", "secreta123", run) == {"ok": True}
    assert ["nmcli", "device", "wifi", "connect", "Casa", "password", "secreta123"] in run.calls
    assert "error" in C.wifi_connect("Casa", "corta", run) and "error" in C.wifi_connect("x" * 40, None, run)
    bad_pw = fake({("nmcli", "device", "wifi", "connect"): (4, "", "Error: Connection activation failed: Secrets were required, but not provided.")})
    assert C.wifi_connect("Casa", "incorrecta1", bad_pw) == {"error": "Contraseña incorrecta"}
    assert C.wifi_disconnect("wlan0", run) == {"ok": True} and "error" in C.wifi_disconnect("wlan0; reboot", run)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
