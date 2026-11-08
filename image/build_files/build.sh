#!/usr/bin/bash
# STONE OS (rebuild): customisation of the Bazzite (bazzite-deck) image for STONE MACHINE.
# Runs inside the container build (image/Containerfile). Any error stops the build: an image that
# would boot without a critical STONE layer is never produced.
#
# F0 (docs/fases/F0_PLAN.md): STONE files, kernel check, pinned GPU governor, no sleep, Handheld
# Daemon off, BC-250 40 CU module and boot guard, Plymouth, provenance.
# F1: stoned (STONE System Service) with its recovery, units, D-Bus and polkit policy.
# D-34: Steam Game Mode is the interface, with the STONE theme and plugin on Decky Loader.
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

### 6c. The console: Steam Game Mode with the STONE theme and plugin (D-34)
## Bazzite's own automatic session stays. Decky Loader, CSS Loader, the theme and the plugin are
## carried in /usr/share/stone/console (pinned by SHA-256) and put in the user's home by
## stone-console-setup.service, because a home directory cannot be part of the image.
test -x /usr/bin/steam || { echo "ERROR: /usr/bin/steam missing"; exit 1; }
compgen -G "/usr/share/wayland-sessions/gamescope-session*.desktop" || { echo "ERROR: Bazzite's Steam session missing"; exit 1; }
CONSOLE=/usr/share/stone/console
mkdir -p "${CONSOLE}/plugins/STONE" "${CONSOLE}/themes"
curl --fail --location --retry 3 --output "${CONSOLE}/PluginLoader" \
    "https://github.com/SteamDeckHomebrew/decky-loader/releases/download/${DECKY_VERSION}/PluginLoader"
echo "${DECKY_SHA256}  ${CONSOLE}/PluginLoader" | sha256sum -c -
chmod 755 "${CONSOLE}/PluginLoader"
curl --fail --location --retry 3 --output /tmp/css-loader.zip "${CSS_LOADER_URL}"
echo "${CSS_LOADER_SHA256}  /tmp/css-loader.zip" | sha256sum -c -
python3 -c "import shutil, sys; shutil.unpack_archive('/tmp/css-loader.zip', sys.argv[1], 'zip')" "${CONSOLE}/plugins"
test -s "${CONSOLE}/plugins/SDH-CssLoader/plugin.json" || { echo "ERROR: CSS Loader's folder changed name"; exit 1; }
cp -a /ctx/themes/STONE "${CONSOLE}/themes/STONE"
for f in plugin.json package.json main.py README.md; do cp "/plugin/${f}" "${CONSOLE}/plugins/STONE/${f}"; done
mkdir -p "${CONSOLE}/plugins/STONE/dist"
cp /plugin/dist/index.js "${CONSOLE}/plugins/STONE/dist/index.js"
test -s "${CONSOLE}/plugins/STONE/dist/index.js" || { echo "ERROR: the STONE plugin was not built"; exit 1; }
test -s "${CONSOLE}/stone-startup.webm" || { echo "ERROR: STONE's startup movie missing"; exit 1; }
printf '{"decky":"%s","css_loader":"%s","plugin":"%s","theme":"%s"}\n' \
    "${DECKY_VERSION}" "${CSS_LOADER_VERSION}" "${STONE_VERSION}" "${STONE_VERSION}" > "${CONSOLE}/manifest.json"
python3 -m compileall -q /usr/lib/stone/stone_console_setup.py
systemctl enable stone-console-setup.service stone-blackbox.service

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
    echo "STONE_DECKY=\"${DECKY_VERSION}\""
    echo "STONE_CSS_LOADER=\"${CSS_LOADER_VERSION}\""
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

echo "STONE OS ${STONE_VERSION}: build completed."
