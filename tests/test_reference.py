"""stoned/reference.py: detected CPU cores and GPU CU against the image's reference (D-16, T-PERF-01).

Pure Python (no D-Bus): runs on any machine.

    python3 tests/test_reference.py     (or: pytest tests/test_reference.py)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "services", "stoned"))
from stoned import reference as REF  # noqa: E402

RELEASE = {"STONE_REFERENCE_CPU_CORES": "8", "STONE_REFERENCE_GPU_CU": "40"}
BOARD_40 = {"board": True, "cu40": {"available": True, "active": True}}


def _root(cores, threads=2, online=None, missing_core_id=False):
    root = tempfile.mkdtemp(prefix="stone-ref-")
    base = os.path.join(root, "sys/devices/system/cpu")
    os.makedirs(base)
    n = cores * threads
    with open(os.path.join(base, "online"), "w") as f:
        f.write((online or f"0-{n - 1}") + "\n")
    for i in range(n):
        d = os.path.join(base, f"cpu{i}", "topology")
        os.makedirs(d)
        if not (missing_core_id and i == 0):
            with open(os.path.join(d, "core_id"), "w") as f:
                f.write(f"{i % cores}\n")
    return root


def test_counts_physical_cores_not_threads():
    root = _root(8, threads=2)
    try:
        assert REF.detected_cores(root) == 8
    finally:
        shutil.rmtree(root)


def test_offline_cpus_do_not_count():
    root = _root(8, threads=2, online="0-5,8-13")      # cores 6 and 7 offline on both threads
    try:
        assert REF.detected_cores(root) == 6
    finally:
        shutil.rmtree(root)


def test_unreadable_topology_is_none():
    root = _root(8, missing_core_id=True)
    try:
        assert REF.detected_cores(root) is None
    finally:
        shutil.rmtree(root)
    assert REF.detected_cores("/nonexistent-root") is None


def test_reference_configuration_matches():
    root = _root(8)
    try:
        r = REF.check(BOARD_40, RELEASE, root)
        assert r["matches"] is True and r["reasons"] == [] and r["detected"] == {"cpu_cores": 8, "gpu_cu": 40}, r
    finally:
        shutil.rmtree(root)


def test_mismatch_lists_every_reason():
    root = _root(6)
    try:
        r = REF.check({"board": True, "cu40": {"available": True, "active": False}}, RELEASE, root)
        assert r["matches"] is False, r
        assert "CPU cores: 6 detected, reference 8" in r["reasons"]
        assert "GPU compute units: 24 detected, reference 40" in r["reasons"]
    finally:
        shutil.rmtree(root)


def test_unknown_counts_as_mismatch():
    r = REF.check({"board": False}, RELEASE, "/nonexistent-root")
    assert r["matches"] is False and len(r["reasons"]) == 2 and all("not readable" in x for x in r["reasons"]), r


def test_no_reference_in_the_image_imposes_nothing():
    r = REF.check(BOARD_40, {"STONE_GOVERNOR_VERSION": "x"}, "/nonexistent-root")
    assert r["matches"] is None and r["reference"] is None and r["reasons"] == [], r


if __name__ == "__main__":
    sys.exit(run_module(globals()))
