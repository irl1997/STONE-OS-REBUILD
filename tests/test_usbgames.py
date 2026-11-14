"""Games from a USB drive (stone_home/usbgames.py): found on the drive the ways people and other
emulation tools lay them out, copied to ~/Emulation/roms. Pure Python, temporary folders only.

    python3 tests/test_usbgames.py     (or: pytest tests/test_usbgames.py)
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import usbgames as U  # noqa: E402


def _put(root, rel, size=10):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b"x" * size)
    return p


def test_games_are_found_in_system_folders_and_by_their_own_extension():
    t = tempfile.mkdtemp(prefix="stone-usb-")
    try:
        drive = os.path.join(t, "media", "stone", "JUEGOS")
        _put(drive, "PS2/Shadow of the Colossus.iso")
        _put(drive, "PS2/notas.txt")
        _put(drive, "roms/gba/Metroid Fusion.gba")
        _put(drive, "Emulation/roms/Nintendo Switch/Zelda/Zelda.nsp")        # a game in its own folder
        _put(drive, "Pokemon Emerald.gba")                                  # loose, but .gba is only GBA
        _put(drive, "suelto.iso")                                           # loose .iso: which console? left alone
        _put(drive, ".Trashes/oculto.gba")
        v = U.scan_volume(drive)
        got = sorted((g["system"], g["name"]) for g in v["games"])
        assert got == [("gba", "Metroid Fusion"), ("gba", "Pokemon Emerald"), ("ps2", "Shadow of the Colossus"), ("switch", "Zelda")], got
        assert v["bytes"] == 40 and v["label"] == "JUEGOS"
        assert U.volumes(os.path.join(t, "media"), ismount=lambda p: p == drive) == [drive]
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_copy_to_the_console_once_with_space_kept_and_cancel():
    t = tempfile.mkdtemp(prefix="stone-usb-")
    try:
        drive = os.path.join(t, "drive")
        _put(drive, "ps2/Juego.iso", 5000)
        _put(drive, "gba/Otro.gba", 300)
        base = os.path.join(t, "Emulation")
        seen = []
        r = U.copy(U.scan_volume(drive), lambda n, total, name: seen.append((n, total, name)), base=base)
        assert r == {"copied": 2, "skipped": 0, "bytes": 5300, "error": None}, r
        assert os.path.getsize(os.path.join(base, "roms", "ps2", "Juego.iso")) == 5000 and seen[-1][:2] == (5300, 5300)
        assert not [n for n in os.listdir(os.path.join(base, "roms", "ps2")) if n.endswith(".stone-part")]
        r = U.copy(U.scan_volume(drive), lambda *a: None, base=base)
        assert r["copied"] == 0 and r["skipped"] == 2                       # already on the console
        _put(drive, "ps2/Nuevo.iso", 100)
        r = U.copy(U.scan_volume(drive), lambda *a: None, base=base, cancel=lambda: True)
        assert r["copied"] == 0 and not os.path.exists(os.path.join(base, "roms", "ps2", "Nuevo.iso"))
        old = U.shutil.disk_usage
        U.shutil.disk_usage = lambda p: type("D", (), {"free": 2 * 2**30 + 50})()
        try:
            r = U.copy(U.scan_volume(drive), lambda *a: None, base=base)
            assert r["copied"] == 0 and r["error"].startswith("No hay espacio"), r
        finally:
            U.shutil.disk_usage = old
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_only_removable_partitions_with_a_file_system_are_mounted():
    tree = {"blockdevices": [
        {"path": "/dev/nvme0n1", "type": "disk", "hotplug": False, "rm": False, "children": [
            {"path": "/dev/nvme0n1p3", "fstype": "btrfs", "mountpoint": None, "hotplug": False, "rm": False, "type": "part"}]},
        {"path": "/dev/sda", "type": "disk", "hotplug": True, "rm": True, "children": [
            {"path": "/dev/sda1", "fstype": "exfat", "mountpoint": None, "hotplug": True, "rm": True, "type": "part"},
            {"path": "/dev/sda2", "fstype": "exfat", "mountpoint": "/run/media/stone/X", "hotplug": True, "rm": True, "type": "part"},
            {"path": "/dev/sda3", "fstype": None, "mountpoint": None, "hotplug": True, "rm": True, "type": "part"}]}]}
    calls = []

    def run(argv, timeout=30):
        calls.append(argv)
        return (0, json.dumps(tree)) if argv[0] == "lsblk" else (0, "")
    assert U.mount_removable(run) == ["/dev/sda1"]
    assert ["udisksctl", "mount", "-b", "/dev/sda1", "--no-user-interaction"] in calls and len(calls) == 2


if __name__ == "__main__":
    sys.exit(run_module(globals()))
