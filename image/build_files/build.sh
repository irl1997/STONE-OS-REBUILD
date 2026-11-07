#!/usr/bin/bash
# STONE OS (rebuild): customisation of the Bazzite (bazzite-deck) image for STONE MACHINE.
# Runs inside the container build (image/Containerfile). Any error stops the build: an image that
# would boot without a critical STONE layer is never produced.
#
# F0 (docs/fases/F0_PLAN.md): STONE files, kernel check, pinned GPU governor, no sleep, Handheld
# Daemon off, BC-250 40 CU module and boot guard, Plymouth, provenance.
# F1: stoned (STONE System Service) with its recovery, units, D-Bus and polkit policy.
# F2: STONE Home, STONE DISPLAY and STONE OPTIMIZED (ported, D-27) and the STONE session (M24).
# The other modules arrive in later phases; this image declares them absent.
set -ouex pipefail

# shellcheck source=/dev/null
source /ctx/build.env

STONE_VERSION="$(tr -d '[:space:]' < /ctx/VERSION)"
[[ "${STONE_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?$ ]] || { echo "ERROR: VERSION '${STONE_VERSION}' is not X.Y.Z[-pre]"; exit 1; }

### 1. STONE system files (40 CU tool and boot guard, no-sleep config, Plymouth theme)
cp -avf /ctx/system_files/. /

### 2. Kernel check
## BC-250 community documentation reports GPU driver failures on 6.15.0-6.15.6 and
## 6.17.8-6.17.10. If the base ever ships one of those, the build fails.
/ctx/check-kernel.sh

### 3. BC-250 GPU governor, pinned (R-03)
## The version every board measurement used. The COPR is enabled only for this install.
[[ -n "${GOVERNOR_VERSION}" ]] || { echo "ERROR: GOVERNOR_VERSION is empty (R-03 requires a pinned governor)"; exit 1; }
dnf5 -y copr enable "${GOVERNOR_COPR}"
dnf5 -y install "cyan-skillfish-governor-smu-${GOVERNOR_VERSION}"
dnf5 -y copr disable "${GOVERNOR_COPR}"
systemctl enable cyan-skillfish-governor-smu.service
/ctx/governor-contract.sh "${GOVERNOR_VERSION}" /usr/lib/stone/governor-contract.txt
## The package's own configuration, with one change: its D-Bus interface enabled (used by stoned
## from F1). Voltage curve, range and thermal threshold stay exactly as the package ships them.
GOV_INFO="$(/ctx/governor-config.py /etc/cyan-skillfish-governor-smu/config.toml)"
echo "${GOV_INFO}"

### 4. No sleep, not even from Steam
## The BC-250 does not come back from s2idle. sleep.conf.d forbids it in systemd; Steam Game Mode
## has its own idle suspend, which asks for the same targets. Masked, every request is refused.
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

### 5. Handheld Daemon: not for a desktop console (associated with micro-stutter on the BC-250)
for unit in hhd.service hhd@.service; do
    if [ -e "/usr/lib/systemd/system/${unit}" ]; then
        systemctl mask "${unit}"
    fi
done

### 6. BC-250 40 CU (reference configuration, D-16; mechanism kept as in rc23, D-17)
## amdgpu rebuilt in the Containerfile's cu40 stage for this exact kernel. With
## amdgpu.bc250_cc_write_mode unset or 0 it behaves as Bazzite's module; the console's kernel
## argument selects 40 CU. Unlike rc23, a missing module FAILS the build: an image without it
## would boot the reference console with 24 CU.
CU40_STATUS="$(cat /cu40/status 2>/dev/null || echo 'unavailable: builder stage gave no result')"
[[ "${CU40_STATUS}" == ok ]] || { echo "ERROR: 40 CU module not built (${CU40_STATUS})"; exit 1; }
KVER40="$(cat /cu40/kver)"
MODDIR="/usr/lib/modules/${KVER40}"
test -d "${MODDIR}" || { echo "ERROR: 40 CU module built for ${KVER40}, which is not this image's kernel"; exit 1; }
origs=( "${MODDIR}"/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko* )
[[ ${#origs[@]} -eq 1 && -f "${origs[0]}" ]] || { echo "ERROR: Bazzite's amdgpu module not found (or several)"; exit 1; }
orig="${origs[0]}"
[[ "$(modinfo -F vermagic "${orig}")" == "$(modinfo -F vermagic /cu40/amdgpu.ko)" ]] \
    || { echo "ERROR: 40 CU module vermagic differs from Bazzite's amdgpu"; exit 1; }
tmp40="$(mktemp -d)"
cp /cu40/amdgpu.ko "${tmp40}/amdgpu.ko"
case "${orig}" in
    *.ko.xz)  xz --check=crc32 --lzma2=dict=1MiB -f "${tmp40}/amdgpu.ko"; new40="${tmp40}/amdgpu.ko.xz" ;;
    *.ko.zst) zstd -q --rm -f "${tmp40}/amdgpu.ko"; new40="${tmp40}/amdgpu.ko.zst" ;;
    *.ko)     new40="${tmp40}/amdgpu.ko" ;;
    *)        echo "ERROR: unknown module compression: ${orig}"; exit 1 ;;
esac
install -m644 "${new40}" "${orig}"
rm -rf "${tmp40}"
modinfo -F parm "${orig}" > /tmp/amdgpu-parm
grep -q '^bc250_cc_write_mode:' /tmp/amdgpu-parm || { echo "ERROR: installed amdgpu has no bc250_cc_write_mode"; exit 1; }
depmod -a "${KVER40}"
CU40_SOURCE="$(cat /cu40/source)"
echo "40 CU: amdgpu replaced (${CU40_SOURCE})"
## stone-cu-verify: the compute correctness test stone-cu40 uses. Required with 40 CU.
[[ -x /cu40/stone-cu-verify && -s /cu40/stone-cu-verify.spv ]] || { echo "ERROR: stone-cu-verify not built"; exit 1; }
install -Dm755 /cu40/stone-cu-verify /usr/libexec/stone/stone-cu-verify
install -Dm644 /cu40/stone-cu-verify.spv /usr/libexec/stone/stone-cu-verify.spv
python3 -m compileall -q /usr/lib/stone
systemctl enable stone-cu40-guard.service

### 6b. STONE System Service (stoned), F1
## Unprivileged service (user `stoned`, sysusers.d) that talks to the governor over D-Bus.
## Source: services/stoned (R-10), installed where the launchers expect it.
mkdir -p /usr/lib/stone
cp -a /ctx/services/stoned/stoned /usr/lib/stone/stoned
python3 -c "import gi; gi.require_version('Gio', '2.0'); from gi.repository import Gio" \
    || dnf5 -y install python3-gobject
python3 -c "import gi; gi.require_version('Gio', '2.0'); from gi.repository import Gio" \
    || { echo "ERROR: python3-gobject missing; stoned cannot run"; exit 1; }
## Stability test workload (vkmark). Without it stoned reports the test as unsupported.
dnf5 -y install --skip-unavailable vkmark
command -v vkmark >/dev/null 2>&1 || echo "WARNING: vkmark not available; no stability test on this image"
python3 -m compileall -q /usr/lib/stone/stoned
systemctl enable stoned-recover.service stoned.service

### 6c. STONE Home, STONE DISPLAY, STONE OPTIMIZED: user side, ported from rc23 (F2, D-27)
## Python packages next to stoned; the page, fonts, artwork and boot movie; the built-in game profiles.
cp -a /ctx/apps/stone-home/stone_home /usr/lib/stone/stone_home
cp -a /ctx/modules/display/stone_display /usr/lib/stone/stone_display
cp -a /ctx/modules/games/stone_games /usr/lib/stone/stone_games
mkdir -p /usr/share/stone-home /usr/share/stone/game-profiles
cp -a /ctx/apps/stone-home/ui/. /usr/share/stone-home/
cp -a /ctx/modules/games/game-profiles/. /usr/share/stone/game-profiles/
## Both engines stay until board test 26 passes (R-02, D-06): Chromium draws on the GPU; the
## GTK 4 + WebKitGTK 6 shell is the software fallback. The build fails without either.
dnf5 -y install webkitgtk6.0 gtk4 gobject-introspection chromium   # cairo-1.0 typelib: GTK from Python
python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('WebKit', '6.0'); from gi.repository import Gtk, WebKit" \
    || { echo "ERROR: WebKitGTK 6 / GTK 4 bindings missing; STONE Home fallback cannot run"; exit 1; }
CHROMIUM_BIN=""
for c in /usr/bin/chromium-browser /usr/bin/chromium; do [ -x "$c" ] && CHROMIUM_BIN="$c" && break; done
test -n "${CHROMIUM_BIN}" || { echo "ERROR: chromium not installed; STONE Home would have no GPU drawing"; exit 1; }
"${CHROMIUM_BIN}" --version || echo "WARNING: ${CHROMIUM_BIN} --version failed in the build container (root, no display)"
python3 -c "import gi; gi.require_version('GUdev', '1.0'); from gi.repository import GUdev" \
    || dnf5 -y install --skip-unavailable libgudev
python3 -c "import gi; gi.require_version('GUdev', '1.0'); from gi.repository import GUdev" \
    || echo "WARNING: GUdev not available; STONE DISPLAY will not see display hotplug events"
python3 -m compileall -q /usr/lib/stone/stone_home /usr/lib/stone/stone_display /usr/lib/stone/stone_games
## Built-in game profiles pass the same checks as at run time.
python3 -c "
import glob, json, sys
sys.path.insert(0, '/usr/lib/stone')
from stone_games import schema
for p in glob.glob('/usr/share/stone/game-profiles/steam/*.json'):
    schema.clean_profile(json.load(open(p)), 'builtin')
" || { echo "ERROR: a built-in STONE game profile is invalid"; exit 1; }
command -v mangohud >/dev/null 2>&1 || ls /usr/lib64/mangohud/libMangoHud*.so >/dev/null 2>&1 \
    || echo "WARNING: MangoHud not found; STONE OPTIMIZED cannot measure games on this image"
test -x /usr/libexec/stone-home || { echo "ERROR: /usr/libexec/stone-home missing"; exit 1; }
test -x /usr/bin/steam || { echo "ERROR: /usr/bin/steam missing; STONE Home launches games through Steam"; exit 1; }
for f in index.html icon.png fonts/jost-latin-300-normal.woff2 grid/capsule.png boot/stone-startup.webm; do
    test -s "/usr/share/stone-home/${f}" || { echo "ERROR: STONE Home file missing: ${f}"; exit 1; }
done

### 6d. STONE session (M24, D-21): gamescope-session-plus@stone, the console's automatic session
## (D-29, "llegar y jugar"). `sudo stone-session default off` goes back to Bazzite's Game Mode; the
## boot guard does it by itself after two STONE boots that never reach "Home operable".
test -x /usr/share/gamescope-session-plus/gamescope-session-plus \
    || { echo "ERROR: gamescope-session-plus not found; the STONE session cannot run"; exit 1; }
test -e /usr/lib/systemd/user/gamescope-session-plus@.service \
    || { echo "ERROR: gamescope-session-plus@.service not found"; exit 1; }
test -s /usr/share/gamescope-session-plus/sessions.d/stone || { echo "ERROR: sessions.d/stone missing"; exit 1; }
## Gamescope focus (Home as the main interface, the game in front) is written with python-xlib.
python3 -c "import Xlib" 2>/dev/null || dnf5 -y install python3-xlib
python3 -c "import Xlib" || { echo "ERROR: python3-xlib missing; the STONE session cannot keep Gamescope's focus"; exit 1; }
## The guide button during a game (Home in front, plan B of V-13) is read with python-evdev.
python3 -c "import evdev" 2>/dev/null || dnf5 -y install python3-evdev
python3 -c "import evdev" || { echo "ERROR: python3-evdev missing; the guide button cannot bring STONE Home back"; exit 1; }
## The automatic session: an /etc drop-in that sorts after Bazzite's zz-holo-autologin.conf (SDDM
## reads /etc/sddm.conf.d in name order, the last file wins). /etc in the image is the default of a
## new installation; on an existing one ostree keeps a removed file removed (`default off` holds).
mkdir -p /etc/sddm.conf.d
printf '%s\n' "# STONE OS: the STONE session is the automatic session (D-29)." \
    "# Back to Bazzite's Game Mode: sudo stone-session default off" \
    "[Autologin]" "Session=gamescope-session-stone.desktop" > /etc/sddm.conf.d/zz-stone-session.conf
test -x /usr/libexec/stone/stone-session-select && test -x /usr/libexec/stone/stone-session-guard \
    || { echo "ERROR: STONE session helpers missing"; exit 1; }
systemctl enable stone-session-guard.service stone-blackbox.service
command -v pkexec >/dev/null || { echo "ERROR: pkexec missing; Escritorio / Volver a STONE cannot switch sessions"; exit 1; }
ls /usr/share/wayland-sessions/plasma.desktop /usr/share/wayland-sessions/plasmawayland.desktop 2>/dev/null \
    || echo "WARNING: no Plasma session file; Escritorio will look for gnome.desktop"
test -s /usr/share/gamescope-session-plus/sessions.d/steam \
    || echo "WARNING: sessions.d/steam not found; the STONE session runs without Steam's Gamescope settings"
ls /usr/share/gamescope-session-plus/sessions.d/ /usr/share/wayland-sessions/

### 7. STONE boot screen (Plymouth script theme; the base does not ship the script plugin)
dnf5 -y install plymouth-plugin-script
test -e /usr/lib64/plymouth/script.so || { echo "ERROR: Plymouth script plugin missing"; exit 1; }
plymouth-set-default-theme stone
## The theme must be inside the initramfs to be seen at boot.
KVER="$(find /usr/lib/modules -mindepth 1 -maxdepth 1 -printf '%f\n' | sort | head -n1)"
dracut --no-hostonly --kver "${KVER}" --reproducible --zstd -v --add ostree \
    -f "/usr/lib/modules/${KVER}/initramfs.img"

### 8. Identity and provenance: /usr/lib/stone-release (Bazzite's os-release is left alone)
# First match only (multilib packages answer once per architecture); "not-installed" if absent.
rpmver() { local v; v="$(rpm -q --qf '%{VERSION}-%{RELEASE}\n' "$@" 2>/dev/null | grep -v 'not installed' | head -n1 || true)"; echo "${v:-not-installed}"; }
rpmfile() { local v; v="$(rpm -qf --qf '%{NAME} %{VERSION}-%{RELEASE}\n' "$1" 2>/dev/null | grep -v 'not owned\|No such\|not installed' | head -n1 || true)"; echo "${v:-not-installed}"; }
{
    echo "STONE_NAME=\"STONE OS\""
    echo "STONE_VERSION=\"${STONE_VERSION}\""
    echo "STONE_PHASE=\"F2\""
    echo "STONE_MODULES_ABSENT=\"connect downloads emulation desktop\""
    echo "STONE_SESSION_DEFAULT=\"on (sudo stone-session default off)\""
    echo "STONE_CHANNEL=\"${STONE_CHANNEL:-dev}\""
    echo "STONE_COMMIT=\"${STONE_COMMIT:-unknown}\""
    echo "STONE_BUILD_DATE=\"${STONE_BUILD_DATE:-unknown}\""
    echo "STONE_HARDWARE=\"AMD BC-250\""
    echo "STONE_REFERENCE_CPU_CORES=\"${STONE_REFERENCE_CPU_CORES}\""
    echo "STONE_REFERENCE_GPU_CU=\"${STONE_REFERENCE_GPU_CU}\""
    echo "STONE_BASE_IMAGE=\"${BASE_IMAGE:-unknown}\""
    echo "STONE_BASE_DIGEST=\"${BASE_DIGEST:-unknown}\""
    echo "STONE_BAZZITE_VERSION=\"$(. /usr/lib/os-release && echo "${VERSION_ID:-}${VERSION:+ (${VERSION})}")\""
    echo "STONE_KERNEL=\"${KVER}\""
    echo "STONE_MESA=\"$(rpmver mesa-vulkan-drivers)\""
    echo "STONE_GAMESCOPE=\"$(rpmfile /usr/bin/gamescope)\""
    echo "STONE_CU40=\"${CU40_STATUS}\""
    echo "STONE_CU40_SOURCE=\"${CU40_SOURCE}\""
    echo "STONE_GOVERNOR_VERSION=\"$(rpmver cyan-skillfish-governor-smu)\""
    echo "STONE_GOVERNOR_PINNED=\"${GOVERNOR_VERSION}\""
    echo "${GOV_INFO}" | sed -n 's/^STONE_GOV_\([A-Z_]*\)=\(.*\)$/STONE_GOV_\1="\2"/p'
} > /usr/lib/stone-release
cat /usr/lib/stone-release

echo "STONE OS ${STONE_VERSION} (F2): build completed."
