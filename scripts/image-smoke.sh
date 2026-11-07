#!/usr/bin/env bash
# STONE OS image smoke test (D-31): runs INSIDE the freshly built image (CI, build-image.yml) and
# fails the build when something STONE needs on the console is missing. Nothing is started; only
# files, packages, enabled units and Python imports are checked.
#   podman run --rm -v ./scripts/image-smoke.sh:/smoke.sh:ro --entrypoint bash <image> /smoke.sh
set -uo pipefail
fail=0
ok() { echo "PASS  $1"; }
bad() { echo "FAIL  $1"; fail=1; }
warn() { echo "WARN  $1"; }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }

# Programs (required: STONE cannot work without them)
for b in stone-home stone-session stonectl stoned stone-doctor stone-cu40 stone-game \
         gamescope steam pkexec systemctl bootc rpm-ostree journalctl bluetoothctl wpctl nmcli flatpak python3; do
    check "program $b" "command -v $b"
done
check "chromium" "command -v chromium-browser || command -v chromium"
[ -x /usr/share/gamescope-session-plus/gamescope-session-plus ] && ok "gamescope-session-plus" || bad "gamescope-session-plus"

# STONE files
for f in /usr/lib/stone-release /usr/share/stone-home/index.html /usr/share/gamescope-session-plus/sessions.d/stone \
         /usr/share/wayland-sessions/gamescope-session-stone.desktop /etc/sddm.conf.d/zz-stone-session.conf \
         /usr/libexec/stone/stone-session-select /usr/libexec/stone/stone-session-guard /usr/libexec/stone/stone-blackbox \
         /usr/share/polkit-1/actions/org.stonemachine.performance.policy /usr/share/polkit-1/actions/org.stonemachine.session.policy \
         /usr/share/polkit-1/actions/org.stonemachine.cu40.policy /usr/share/polkit-1/rules.d/50-stone.rules \
         /usr/share/dbus-1/system.d/org.stonemachine.Performance1.conf /usr/share/plymouth/themes/stone/stone.plymouth \
         /usr/share/applications/stone-volver.desktop; do
    check "file $f" "test -s $f"
done
check "STONE session is the automatic one" "grep -q '^Session=gamescope-session-stone.desktop' /etc/sddm.conf.d/zz-stone-session.conf"

# Enabled units
for u in stoned.service stoned-recover.service stone-cu40-guard.service stone-session-guard.service \
         stone-blackbox.service cyan-skillfish-governor-smu.service; do
    check "enabled $u" "systemctl is-enabled $u"
done

# Python: every STONE module imports with the system Python and the image's own libraries
python3 -I - <<'PY' && ok "python imports (stone_home, stoned, stone_display, stone_games, gi, Xlib, evdev)" || bad "python imports"
import sys
sys.path[0:0] = ["/usr/lib/stone"]
import importlib, pkgutil
mods = []
for pkg in ("stone_home", "stoned", "stone_display", "stone_games"):
    p = importlib.import_module(pkg)
    for m in pkgutil.iter_modules(p.__path__):
        if m.name in ("app", "chromium") or m.name.startswith("_"):
            continue                                   # need a display to import cleanly
        mods.append(f"{pkg}.{m.name}")
for m in mods:
    importlib.import_module(m)
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("WebKit", "6.0")
from gi.repository import Gio, GLib  # noqa: F401
import Xlib, evdev  # noqa: F401
print(f"{len(mods)} modules imported")
PY

# stone-doctor runs (in a container most readings are "unknown": it must still answer, as JSON)
check "stone-doctor --json answers" "stone-doctor --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d[\"checks\"]'"

# Optional pieces: their feature says "no disponible" without them
ls /usr/share/vulkan/implicit_layer.d/ 2>/dev/null | grep -qi basalt && ok "vkBasalt (STONE IMAGE)" || warn "vkBasalt missing: STONE IMAGE looks unavailable"
command -v mangohud >/dev/null && ok "MangoHud (measurements)" || warn "MangoHud missing: OPTIMIZAR cannot measure"

echo
if [ "$fail" = 0 ]; then echo "IMAGE SMOKE: PASS"; else echo "IMAGE SMOKE: FAIL"; fi
exit "$fail"
