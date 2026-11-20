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


def _image(path, at_bytes):
    """A small file with bytes at given offsets (a disc image's markers)."""
    size = max(o + len(b) for o, b in at_bytes) + 16
    buf = bytearray(size)
    for o, b in at_bytes:
        buf[o:o + len(b)] = b
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(bytes(buf))
    return path


def _iso9660(path, names):
    """A minimal ISO 9660 image whose root folder holds `names`."""
    pvd = bytearray(2048)
    pvd[0:6] = b"\x01CD001"
    rec = bytearray(34)
    rec[0] = 34
    rec[2:6] = (20).to_bytes(4, "little")
    rec[10:14] = (2048).to_bytes(4, "little")
    pvd[156:190] = rec
    root = bytearray()
    for n in names:
        nb = n.encode()
        r = bytearray(33 + len(nb) + (1 - len(nb) % 2))
        r[0] = len(r)
        r[32] = len(nb)
        r[33:33 + len(nb)] = nb
        root += r
    return _image(path, [(0x8000, bytes(pvd)), (20 * 2048, bytes(root))])


def test_loose_disc_images_are_recognised_by_what_is_inside():
    """rc12: a loose .iso/.rvz/.gcz at the top of the drive was left there; its console is read from it."""
    t = tempfile.mkdtemp(prefix="stone-usb-")
    try:
        d = os.path.join(t, "drive")
        _image(os.path.join(d, "Zelda TP.iso"), [(0x1C, bytes.fromhex("c2339f3d"))])
        _image(os.path.join(d, "Mario Galaxy.iso"), [(0x18, bytes.fromhex("5d1c9ea3"))])
        _image(os.path.join(d, "Metroid.rvz"), [(0, b"RVZ\x01"), (0x48, (1).to_bytes(4, "big"))])
        _image(os.path.join(d, "Smash.gcz"), [(0, (0xB10BC001).to_bytes(4, "little")), (4, (1).to_bytes(4, "little"))])
        _image(os.path.join(d, "Halo.iso"), [(0x10000, b"MICROSOFT*XBOX*MEDIA")])
        _iso9660(os.path.join(d, "God of War.iso"), [".", "..", "SYSTEM.CNF;1", "SLUS_206.47;1"])
        _iso9660(os.path.join(d, "Patapon.iso"), ["PSP_GAME", "UMD_DATA.BIN;1"])
        _iso9660(os.path.join(d, "datos.iso"), ["README.TXT;1"])                     # a data disc: left alone
        got = sorted((g["system"], g["name"]) for g in U.scan_volume(d)["games"])
        assert got == [("gc", "Metroid"), ("gc", "Zelda TP"), ("ps2", "God of War"), ("psp", "Patapon"),
                       ("wii", "Mario Galaxy"), ("wii", "Smash"), ("xbox", "Halo")], got
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_games_of_several_files_are_copied_whole_and_found_on_the_console():
    """rc12: a .cue/.bin, a Dreamcast .gdi with its tracks and a game in its own folder; their parts are
    never games of their own, and the console's library finds each one once."""
    from stone_home import roms as R
    t = tempfile.mkdtemp(prefix="stone-usb-")
    try:
        d = os.path.join(t, "drive")
        _put(d, "dreamcast/Shenmue/Shenmue.gdi")
        with open(os.path.join(d, "dreamcast", "Shenmue", "Shenmue.gdi"), "w") as f:
            f.write('3\n1 0 4 2352 track01.bin 0\n2 600 0 2352 "track 02.raw" 0\n3 45000 4 2352 track03.bin 0\n')
        for n, z in (("track01.bin", 700), ("track 02.raw", 300), ("track03.bin", 9000)):
            _put(d, f"dreamcast/Shenmue/{n}", z)
        with open(_put(d, "ps2/Ico (USA).cue"), "w") as f:
            f.write('FILE "Ico (USA).bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
        _put(d, "ps2/Ico (USA).bin", 4000)
        _put(d, "ps2/Okami/Okami.iso", 5000)
        _put(d, "ps2/Okami/portada.jpg", 50)
        v = U.scan_volume(d)
        got = sorted((g["system"], g["name"], len(g["files"])) for g in v["games"])
        assert got == [("dreamcast", "Shenmue", 4), ("ps2", "Ico", 2), ("ps2", "Okami", 2)], got
        base = os.path.join(t, "Emulation")
        r = U.copy(v, lambda *a: None, base=base)
        assert r["copied"] == 3 and r["error"] is None and r["bytes"] == sum(g["size"] for g in v["games"]), r
        assert os.path.getsize(os.path.join(base, "roms", "dreamcast", "Shenmue", "track 02.raw")) == 300
        assert os.path.exists(os.path.join(base, "roms", "ps2", "Okami", "portada.jpg"))
        dc = R.games_in(os.path.join(base, "roms", "dreamcast"), "dreamcast")
        ps2 = R.games_in(os.path.join(base, "roms", "ps2"), "ps2")
        assert [(g["name"], os.path.basename(g["path"])) for g in dc] == [("Shenmue", "Shenmue.gdi")], dc
        assert [(g["name"], os.path.basename(g["path"])) for g in ps2] == [("Ico", "Ico (USA).bin"), ("Okami", "Okami.iso")], ps2
        assert U.copy(U.scan_volume(d), lambda *a: None, base=base)["skipped"] == 3            # already there
        # a half-copied file a power cut left is cleared before copying
        open(os.path.join(base, "roms", "ps2", "Ico (USA).bin" + R.PART_SUFFIX), "w").close()
        assert U.leftovers(base) == 1
        # a sheet never reaches outside its folder
        with open(os.path.join(d, "ps2", "malo.cue"), "w") as f:
            f.write('FILE "../../etc/passwd" BINARY\n')
        assert R.sheet_files(os.path.join(d, "ps2", "malo.cue")) == []
    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run_module(globals()))
