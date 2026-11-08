#!/usr/bin/env bash
# STONE OS image smoke test (D-31): runs INSIDE the freshly built image (CI, build-image.yml) and
# fails the build when something STONE needs on the console is missing. Nothing is started; only
# files, packages, enabled units and Python imports are checked.
#   podman run --rm -v ./scripts/image-smoke.sh:/smoke.sh:ro --entrypoint bash <image> /smoke.sh
set -uo pipefail
fail=0
ok() { echo "PASS  $1"; }
bad() { echo "FAIL  $1"; fail=1; }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }

# Programs (required: STONE cannot work without them)
for b in stonectl stoned stone-doctor stone-cu40 gamescope steam systemctl bootc rpm-ostree journalctl python3; do
    check "program $b" "command -v $b"
done
check "gamescope-session-plus" "test -x /usr/share/gamescope-session-plus/gamescope-session-plus"

# STONE files
for f in /usr/lib/stone-release /usr/libexec/stone/stone-console-setup /usr/libexec/stone/stone-blackbox \
         /usr/share/polkit-1/actions/org.stonemachine.performance.policy /usr/share/polkit-1/rules.d/50-stone.rules \
         /usr/share/dbus-1/system.d/org.stonemachine.Performance1.conf /usr/share/plymouth/themes/stone/stone.plymouth \
         /usr/share/stone/console/manifest.json /usr/share/stone/console/PluginLoader /usr/share/stone/console/stone-startup.webm \
         /usr/share/stone/console/plugins/STONE/plugin.json /usr/share/stone/console/plugins/STONE/main.py \
         /usr/share/stone/console/plugins/STONE/dist/index.js /usr/share/stone/console/plugins/SDH-CssLoader/plugin.json \
         /usr/share/stone/console/themes/STONE/theme.json; do
    check "file $f" "test -s $f"
done
check "Bazzite's Steam session" "compgen -G '/usr/share/wayland-sessions/gamescope-session*.desktop'"
check "no STONE session left" "! test -e /etc/sddm.conf.d/zz-stone-session.conf"

# Enabled units
for u in stoned.service stoned-recover.service stone-cu40-guard.service stone-console-setup.service \
         stone-blackbox.service cyan-skillfish-governor-smu.service; do
    check "enabled $u" "systemctl is-enabled $u"
done

# Python: every STONE module imports with the system Python and the image's own libraries
if python3 -I - <<'PY'; then ok "python imports (stoned, stone_console_setup, gi)"; else bad "python imports"; fi
import sys
sys.path[0:0] = ["/usr/lib/stone"]
import importlib, pkgutil
mods = []
p = importlib.import_module("stoned")
for m in pkgutil.iter_modules(p.__path__):
    if not m.name.startswith("_"):
        mods.append(f"stoned.{m.name}")
mods.append("stone_console_setup")
for m in mods:
    importlib.import_module(m)
from gi.repository import Gio, GLib  # noqa: F401
print(f"{len(mods)} modules imported")
PY

# stone-doctor runs (in a container most readings are "unknown": it must still answer, as JSON)
check "stone-doctor --json answers" "stone-doctor --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d[\"checks\"]'"

echo
if [ "$fail" = 0 ]; then echo "IMAGE SMOKE: PASS"; else echo "IMAGE SMOKE: FAIL"; fi
exit "$fail"
