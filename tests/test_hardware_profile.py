"""hardware/bc250.yaml and hardware/validation/matrix.yaml: every fact has its origin and state,
and no board test is marked PASS without a recorded run on the BC-250 (D-08, D-18).

    python3 tests/test_hardware_profile.py     (or: pytest tests/test_hardware_profile.py)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, load_yaml, run_module  # noqa: E402

PROFILE = os.path.join(REPO, "hardware", "bc250.yaml")
MATRIX = os.path.join(REPO, "hardware", "validation", "matrix.yaml")
STATES = {"owner-confirmed", "observed", "documented", "inherited", "unknown", "verified"}
STATUSES = {"NOT TESTED", "PASS", "FAIL", "BLOCKED"}
KINDS = {"P", "S+V"}
PHASES = {f"F{n}" for n in range(10)}


def _facts(node, path=()):
    """Every leaf fact {value, source, state} of the profile, with its path."""
    if isinstance(node, dict) and "state" in node:
        yield path, node
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("schema", "board"):
                continue
            yield from _facts(v, path + (k,))


def test_every_fact_has_value_source_and_state():
    facts = list(_facts(load_yaml(PROFILE)))
    assert len(facts) > 20, len(facts)
    for path, f in facts:
        assert set(f) == {"value", "source", "state"}, (path, f)
        assert f["state"] in STATES, (path, f["state"])
        assert str(f["source"]).strip(), path


def test_nothing_is_verified_yet():
    # No HARDWARE_VALIDATION row has passed on the board: nothing can claim "verified".
    for path, f in _facts(load_yaml(PROFILE)):
        assert f["state"] != "verified", path


def test_reference_configuration():
    ref = load_yaml(PROFILE)["reference"]
    assert ref["cpu_cores"]["value"] == 8 and ref["cpu_cores"]["state"] == "owner-confirmed"
    assert ref["gpu_compute_units"]["value"] == 40 and ref["gpu_compute_units"]["state"] == "owner-confirmed"


def test_inherited_constants_are_labelled():
    # D-18: rc23 numbers kept in code are listed as inherited, never as STONE design limits.
    inh = load_yaml(PROFILE)["inherited_constants"]
    for name, f in inh.items():
        assert f["state"] == "inherited", name
    with open(os.path.join(REPO, "system", "usr", "lib", "stone", "stone_cu40.py")) as fh:
        code = fh.read()
    for const, key in (("CEILING_MHZ = ", "cu40_baseline_ceiling_mhz"), ("TEST_STOP_C = ", "cu40_test_stop_c"),
                       ("ENABLE_MAX_IDLE_C = ", "cu40_enable_max_idle_c")):
        value = int(code.split(const, 1)[1].split()[0])
        assert inh[key]["value"] == value, (key, value)


def test_matrix_entries_are_well_formed_and_unique():
    tests = load_yaml(MATRIX)["tests"]
    ids = [t["id"] for t in tests]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for n in range(30):
        assert str(n) in ids, f"rc23 board test {n} missing"
    for t in tests:
        assert set(t) == {"id", "title", "phase", "kind", "status", "runs", "observed"}, t
        assert t["kind"] in KINDS and t["status"] in STATUSES and t["phase"] in PHASES, t


def test_no_pass_without_a_board_run():
    for t in load_yaml(MATRIX)["tests"]:
        if t["status"] in ("PASS", "FAIL"):
            assert t["runs"], f"{t['id']}: {t['status']} without a recorded run"
            for r in t["runs"]:
                assert {"date", "image", "result"} <= set(r) and r["image"].startswith("sha256:"), (t["id"], r)
        if t["status"] == "PASS":
            assert t["runs"][-1]["result"] == "PASS", t["id"]


if __name__ == "__main__":
    sys.exit(run_module(globals()))
