#!/usr/bin/bash
# STONE: build-time contract of the GPU governor package (R-03).
#
#   governor-contract.sh <expected version-release> <output file>
#
# Strict (fails the build):
#   * the installed cyan-skillfish-governor-smu is exactly the pinned version-release,
#   * its systemd unit and its configuration file are where STONE expects them.
# Recorded (never guessed, written to <output file> and shown in the build log):
#   * the package's D-Bus files and the D-Bus names, object paths and methods found as strings in
#     its binaries. A future version is compared against this record before it is adopted.
# The governor cannot run inside a container build (it needs the BC-250's SMU), so the live
# D-Bus interface is checked on the board (HARDWARE_VALIDATION test 0, busctl introspect).
set -euo pipefail

expected="${1:?expected version-release}"
out="${2:?output file}"
pkg=cyan-skillfish-governor-smu

installed="$(rpm -q --qf '%{VERSION}-%{RELEASE}' "${pkg}")" \
    || { echo "ERROR (governor contract): ${pkg} is not installed"; exit 1; }
[[ "${installed}" == "${expected}" ]] \
    || { echo "ERROR (governor contract): installed ${installed}, pinned ${expected}"; exit 1; }

unit=/usr/lib/systemd/system/${pkg}.service
conf=/etc/${pkg}/config.toml
[[ -f "${unit}" ]] || { echo "ERROR (governor contract): ${unit} missing"; exit 1; }
[[ -f "${conf}" ]] || { echo "ERROR (governor contract): ${conf} missing"; exit 1; }

mkdir -p "$(dirname "${out}")"
{
    echo "# cyan-skillfish-governor-smu build-time contract record (STONE F0)"
    echo "version=${installed}"
    echo "unit=${unit}"
    echo "config=${conf}"
    echo "# D-Bus files shipped by the package"
    rpm -ql "${pkg}" | grep -iE 'dbus|polkit' || echo "(none)"
    echo "# Strings found in the package's executables (names, paths, methods)"
    while read -r f; do
        [[ -f "${f}" && -x "${f}" ]] || continue
        echo "## ${f}"
        grep -aoE 'com\.cyanskillfish\.[A-Za-z0-9_.]+|/com/cyanskillfish/[A-Za-z0-9_/]+|\bSet(Range|LoadTarget|TemperatureThresholds|FixedFrequency|TestMode)\b' "${f}" 2>/dev/null \
            | sort -u || true
    done < <(rpm -ql "${pkg}")
} > "${out}"
cat "${out}"
echo "governor contract: ${pkg} ${installed} (pinned) OK"
