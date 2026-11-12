"""STONE HEALTH (health.py), stone-doctor and the Crash Black Box (blackbox.py), with fake /proc,
/sys, systemctl and journalctl. Pure Python: runs anywhere.

    python3 tests/test_health.py     (or: pytest tests/test_health.py)
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import blackbox as BB  # noqa: E402
from stone_home import health as H  # noqa: E402


def _tree(files):
    root = tempfile.mkdtemp(prefix="stone-health-")
    for rel, text in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    return root


def test_cpu_and_memory_readings_and_unknowns():
    r = _tree({"proc/cpuinfo": "processor\t: 0\nmodel name\t: AMD Custom APU 0405\n",
               "sys/devices/system/cpu/online": "0-15\n",
               "proc/meminfo": "MemTotal:       16000000 kB\nMemAvailable:    9000000 kB\n"})
    try:
        assert H.cpu(os.path.join(r, "proc"), os.path.join(r, "sys")) == {"model": "AMD Custom APU 0405", "threads": 16}
        assert H.memory(os.path.join(r, "proc"))["total"] == 16000000 * 1024
        assert H.cpu(os.path.join(r, "none"), os.path.join(r, "none")) == {"model": None, "threads": None}
        assert H.memory(os.path.join(r, "none")) is None
    finally:
        shutil.rmtree(r)


def fake_run(states, journal="", rc=0):
    def run(argv, timeout=10):
        if argv[:2] == ["systemctl", "is-active"]:
            st = states.get(argv[2], "inactive")
            return (0 if st == "active" else 3), st + "\n"
        if argv[0] == "journalctl":
            return rc, journal
        return None, ""
    return run


def test_doctor_marks_missing_required_services_as_failures():
    run = fake_run({"stoned.service": "active", "cyan-skillfish-governor-smu.service": "failed"},
                   journal="amdgpu 0000:01:00.0: ring gfx timeout\nsome other error\n")
    snap = {"cpu": {"threads": 16, "model": "x"}, "memory": {"total": 16 * 2**30}, "storage": [{"path": "/", "total": 500 * 2**30, "free": 10 * 2**30}],
            "services": H.services(run), "gpu_errors": H.gpu_errors(run), "blackbox": [{"clean": False}, {"clean": True}]}
    checks = {(c[1]): c for c in H.doctor(snap)}
    assert checks["Regulador de GPU"][0] == "fail" and checks["Servicio de rendimiento (stoned)"][0] == "ok"
    assert checks["Guardia de arranque"][0] == "ok"                      # oneshot: inactive after boot is fine
    assert checks["Disco /"][0] == "warn" and "poco espacio" in checks["Disco /"][2]
    assert checks["GPU"][0] == "warn" and "1 errores" in checks["GPU"][2]
    assert checks["Caja negra"][0] == "warn"
    assert H.gpu_errors(fake_run({}, rc=None)) is None


def test_stone_doctor_exit_code_and_json():
    real = H.snapshot
    H.snapshot = lambda run=None: {"cpu": {"threads": 16}, "memory": None, "storage": [], "services": [], "gpu_errors": [], "blackbox": []}
    try:
        assert H.main([]) == 0 and H.main(["--json"]) == 0
        H.snapshot = lambda run=None: {"services": [{"unit": "stoned.service", "label": "stoned", "state": "failed", "required": True}]}
        assert H.main([]) == 1
    finally:
        H.snapshot = real


def test_blackbox_keeps_the_previous_boot_once_and_rotates():
    d = tempfile.mkdtemp(prefix="stone-bb-")
    boots = {"-1": "a" * 32}

    def run(argv, timeout=30):
        if argv[:2] == ["journalctl", "--list-boots"]:
            return 0, f" -2 {'b' * 32} Thu 2026-11-05\n -1 {boots['-1']} Fri 2026-11-06\n  0 {'c' * 32} Sat 2026-11-07\n"
        if "-p" in argv:
            return 0, "kernel: amdgpu: ring timeout\n-- No entries --\n"
        return 0, "systemd[1]: Reached target System Power Off.\n" if boots["-1"].startswith("a") else "kernel: something\n"
    try:
        t = [1800000000]
        assert BB.record(run, d, now=lambda: t[0]) == "clean"
        assert BB.record(run, d, now=lambda: t[0]) == "already"
        meta = json.load(open(os.path.join(d, [n for n in os.listdir(d) if n.endswith(".json")][0])))
        assert meta == {"boot_id": "a" * 32, "time": 1800000000, "clean": True, "errors": 1}
        for i in range(12):
            boots["-1"] = f"{i:02d}" + "d" * 30
            t[0] += 100
            assert BB.record(run, d, now=lambda: t[0]) == "not-clean"
        assert len([n for n in os.listdir(d) if n.endswith(".json")]) == BB.KEEP
        assert len([n for n in os.listdir(d) if n.endswith(".log")]) == BB.KEEP
        assert [b["clean"] for b in H.blackbox(d)][:1] == [False]
        assert BB.record(lambda a, timeout=30: (1, ""), d) is None
    finally:
        shutil.rmtree(d)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
