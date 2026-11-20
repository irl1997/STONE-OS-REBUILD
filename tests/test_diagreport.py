"""The diagnostic report (stone_home/diagreport.py): what it gathers, that nothing personal is in it,
and the phone downloading it (phonedrop.Drop.offer). Pure Python, temporary folders only.

    python3 tests/test_diagreport.py     (or: pytest tests/test_diagreport.py)
"""

import http.client
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import diagreport as D, phonedrop as P  # noqa: E402

PRIVATE = ("ana.perez@gmail.com", "76561198012345678", "hunter2", "eyJhbGciOi", "192.168.1.57", "a4:b1:c2:d3:e4:f5")


def fake_run(argv, timeout=20):
    name = " ".join(argv)
    if argv[0] == "journalctl" and "--user" in argv:
        return ("2026-11-14T10:00 stone-home[1]: [stone] steam: its own window wanted in front (store)\n"
                "2026-11-14T10:01 steam[2]: Logged in as ana.perez@gmail.com steamid 76561198012345678\n"
                "2026-11-14T10:02 steam[2]: login password=hunter2\n"
                "2026-11-14T10:03 stone-home[1]: Traceback (most recent call last):\n"
                "2026-11-14T10:03 nm[3]: wlan0 a4:b1:c2:d3:e4:f5 got 192.168.1.57 Authorization: Bearer eyJhbGciOi\n")
    if "-1" in argv:
        return "2026-11-13T22:00 kernel: amdgpu: GPU reset begin!\n"
    if argv[:2] == ["systemctl", "--failed"]:
        return "  UNIT LOAD ACTIVE SUB\n● cyan-skillfish-governor-smu.service loaded failed failed GPU governor\n"
    return f"output of {name}\n"


def test_nothing_personal_is_written():
    # a secret is recognised by what names it (password=, token, Authorization...): such lines go whole
    text = ("signed in as ana.perez@gmail.com, account 76561198012345678\nlogin password=hunter2\n"
            "Authorization: Bearer eyJhbGciOi\nwlan0 a4:b1:c2:d3:e4:f5 got 192.168.1.57\nnormal line\n")
    out = D.redact(text)
    for p in PRIVATE:
        assert p not in out, p
    assert "192.168.1.x" in out and "a4:b1:c2:xx:xx:xx" in out and "[correo]" in out and "[cuenta de Steam]" in out
    assert "normal line" in out and out.count("[línea omitida") == 2                    # password= and Authorization


def test_the_report_gathers_logs_and_says_what_it_found():
    t = tempfile.mkdtemp(prefix="stone-diag-")
    try:
        home = os.path.join(t, "home")
        logs = os.path.join(home, ".local", "share", "Steam", "logs")
        os.makedirs(logs)
        with open(os.path.join(logs, "console_log.txt"), "w") as f:
            f.write("[2026-11-14] Startup - updater built\nSteam account 76561198012345678 ana.perez@gmail.com\n")
        st = os.path.join(home, ".local", "state", "stone")
        os.makedirs(st)
        with open(os.path.join(st, "home.log"), "w") as f:
            f.write("[stone] steam: its own window wanted in front (store)\n[stone] launch 620: error AppError_51\n")
        with open(os.path.join(st, "game-graphics.json"), "w") as f:
            json.dump({"620": {"original": "", "applied": "X=1 %command%"}}, f)
        tree = {"Apps": {n.split(".")[1]: "f1" for n in D.STEAM_NEEDS if n.startswith("Apps.") and n != "Apps.TerminateApp"},
                "Installs": {n.split(".")[1]: "f1" for n in D.STEAM_NEEDS if n.startswith("Installs.")},
                "Downloads": {"EnableAllDownloads": "f2", "ResumeAppUpdate": "f2"}}
        live = {"steam_probe": [{"title": "x", "has_steamclient": False}, {"title": "SharedJSContext", "has_steamclient": True, "tree": tree}],
                "health": [["ok", "CPU", "12 hilos"], ["fail", "Regulador de GPU", "parado"]], "net": {"ssid": "Casa de Ana"}}
        r = D.build(out_dir=os.path.join(t, "out"), live=live, run=fake_run, home=home, now=lambda: 1794600000)
        s = r["summary"]
        assert s["steam_functions"]["missing"] == ["Apps.TerminateApp"] and s["steam_functions"]["page"] == "SharedJSContext"
        assert s["errors"] >= 1 and s["previous_boot_errors"] == 1 and s["failed_services"] == ["cyan-skillfish-governor-smu.service"]
        assert any("TerminateApp" in f for f in s["findings"]) and any("Regulador de GPU" in f for f in s["findings"])
        with zipfile.ZipFile(r["path"]) as z:
            names = z.namelist()
            assert names[0] == "resumen.txt" and "stone-home.txt" in names and "steam-console_log.txt" in names
            assert "stone-home-app.txt" in names                                     # STONE Home's own log (home.log)
            assert "estado/game-graphics.json" in names and "vivo.json" in names and "arranque-anterior.txt" in names
            everything = "".join(z.read(n).decode("utf-8") for n in names)
        for p in PRIVATE:
            assert p not in everything, p
        assert "GPU reset" in everything and "Traceback" in everything
        assert r["name"].startswith("stone-informe-") and os.path.getsize(r["path"]) == r["size"]
        assert D.steam_functions([])["missing"] is None                                   # Steam not answering
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_the_bc250s_start_up_messages_and_others_warnings_are_not_counted():
    # the first report from the console counted 159 errors (121 were STONE's blind calls to Steam, the
    # rest Steam's and the base image's own) and 147 for a previous boot that ended well
    text = ("kernel: amdgpu 0000:01:00.0: [drm] *ERROR* dal_irq_service_dummy_ack: called for non-implemented irq source\n"
            "kernel: RDSEED is not reliable on this platform; disabling.\n"
            "steam[1]: [1114/214329.332883:ERROR:context.cc(107)] The browser_subprocess_path directory is not absolute\n"
            "steamos-manager[2]: WARN Failed to load orca configuration\n"
            "stone-session: gamescope focus: ERROR window gone\n"
            "steam[1]: RaiseJSException: Method call failed: Storage.GetJSON requires 2 arguments; only 1 given\n"
            "kernel: amdgpu: GPU reset begin!\n")
    n, rows = D._errors(text)
    assert n == 3 and any("stone-session" in r for r in rows) and any("RaiseJSException" in r for r in rows) and any("GPU reset" in r for r in rows), rows


def test_the_phone_downloads_only_the_report_offered():
    t = tempfile.mkdtemp(prefix="stone-diag-")
    d = P.Drop(lambda n, data: None, base=os.path.join(t, "Emulation"))
    try:
        rep = os.path.join(t, "stone-informe-x.zip")
        with open(rep, "wb") as f:
            f.write(b"PK\x03\x04 report")
        info = d.start(host="127.0.0.1")
        assert info["download"] is None
        info = d.offer(rep)
        u = urllib.parse.urlparse(info["download"])
        c = http.client.HTTPConnection(u.hostname, u.port, timeout=10)
        c.request("GET", u.path)
        resp = c.getresponse()
        body = resp.read()
        assert resp.status == 200 and body == b"PK\x03\x04 report" and "stone-informe-x.zip" in resp.getheader("Content-Disposition")
        c.request("GET", u.path.replace("informe", "../../etc/passwd"))
        assert c.getresponse().status == 404
        c.close()
    finally:
        d.stop()
        shutil.rmtree(t, ignore_errors=True)
    assert d.offered is None


def test_the_report_keeps_what_the_display_said_about_sound_without_its_serial():
    """3.1.0-rc12 (board, 20-11-2026): no sound and HDR gone; the EDID and the ELD say why."""
    t = tempfile.mkdtemp(prefix="stone-edid-")
    try:
        drm = os.path.join(t, "sys", "class", "drm", "card0-DP-1")
        os.makedirs(drm)
        edid = bytearray(256)
        edid[0:8] = bytes([0, 255, 255, 255, 255, 255, 255, 0])
        edid[12:16] = b"\x12\x34\x56\x78"                        # serial in the header
        edid[54:59] = bytes([0, 0, 0, 0xFF, 0]); edid[59:72] = b"SERIAL123456\n"
        edid[126] = 1
        with open(os.path.join(drm, "edid"), "wb") as f:
            f.write(bytes(edid))
        with open(os.path.join(drm, "status"), "w") as f:
            f.write("connected\n")
        os.makedirs(os.path.join(t, "sys", "class", "drm", "card0-DP-2"))
        with open(os.path.join(t, "sys", "class", "drm", "card0-DP-2", "status"), "w") as f:
            f.write("disconnected\n")
        snd = os.path.join(t, "proc", "asound", "card0")
        os.makedirs(snd)
        with open(os.path.join(snd, "eld#0.0"), "w") as f:
            f.write("monitor_present\t\t0\neld_valid\t\t0\n")
        text = D._edids_text(t)
        assert "card0-DP-1: 256 bytes, 2 bloque(s), 1 extensión(es)" in text and "DP-2" not in text
        assert "12345678" not in text and b"SERIAL123456".hex() not in text and "00ffffffffffff00" in text
        assert "eld#0.0" in D._elds_text(t) and "monitor_present" in D._elds_text(t)
        assert "ninguna pantalla" in D._edids_text(os.path.join(t, "nada"))
    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
