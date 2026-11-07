"""STONE MACHINE reference configuration (D-16): what the console is meant to be, against what it is.

The image records the reference in /usr/lib/stone-release (STONE_REFERENCE_CPU_CORES,
STONE_REFERENCE_GPU_CU). Every start of stoned reads what this boot really has:

  cpu_cores   physical cores online: unique (package, core_id) pairs of the online CPUs
  gpu_cu      40 when amdgpu runs the BC-250 40 CU option in this boot, 24 otherwise

Nothing here is a limit and nothing is written. When the detected configuration differs from the
reference, or cannot be read, stoned says so (GetCapabilities "configuration") and refuses what
depends on it: CUSTOM slots, stability tests and calibration (T-PERF-01). Factory profiles stay
available. An image without a reference (older images) imposes nothing.
"""

import os


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _cpu_list(text):
    """"0-3,6,8-9" -> [0, 1, 2, 3, 6, 8, 9]."""
    out = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.partition("-")
        try:
            a = int(lo)
            b = int(hi) if hi else a
        except ValueError:
            return []
        out.extend(range(a, b + 1))
    return out


def detected_cores(root="/"):
    """Physical cores online in this boot, or None when the topology cannot be read."""
    base = os.path.join(root, "sys/devices/system/cpu")
    cpus = _cpu_list(_read(os.path.join(base, "online")))
    if not cpus:
        return None
    cores = set()
    for n in cpus:
        topo = os.path.join(base, f"cpu{n}", "topology")
        core = _read(os.path.join(topo, "core_id"))
        if core is None:
            return None
        cores.add((_read(os.path.join(topo, "physical_package_id")) or "0", core))
    return len(cores)


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def check(caps, release, root="/"):
    """{"reference", "detected", "matches", "reasons"}; matches is None when the image has no reference."""
    ref = {"cpu_cores": _int(release.get("STONE_REFERENCE_CPU_CORES")),
           "gpu_cu": _int(release.get("STONE_REFERENCE_GPU_CU"))}
    cu40 = caps.get("cu40") or {}
    detected = {"cpu_cores": detected_cores(root),
                "gpu_cu": (40 if cu40.get("active") else 24) if caps.get("board") else None}
    if ref["cpu_cores"] is None and ref["gpu_cu"] is None:
        return {"reference": None, "detected": detected, "matches": None, "reasons": []}
    reasons = []
    for key, label in (("cpu_cores", "CPU cores"), ("gpu_cu", "GPU compute units")):
        want, have = ref[key], detected[key]
        if want is None:
            continue
        if have is None:
            reasons.append(f"{label}: not readable (reference {want})")
        elif have != want:
            reasons.append(f"{label}: {have} detected, reference {want}")
    return {"reference": ref, "detected": detected, "matches": not reasons, "reasons": reasons}
