#!/usr/bin/env bash
# STONE MACHINE - read-only diagnostic of the AMD BC-250 (see PROCEDIMIENTO_DIAGNOSTICO_BC250.md).
#
# READ ONLY. This script never: changes BIOS/firmware, frequencies or voltages, enables or
# disables CPU cores or CU, installs or removes packages, starts/stops/enables services, edits
# configuration, or runs a load/stress test. Every command below only queries and prints.
#
# Output: one folder ~/stone-diag-<date>/ with one text file per section, plus SUMMARY.txt.
# Serial numbers, MAC addresses and IP addresses are not collected.
#
# Run from Desktop Mode (Konsole) or SSH, as the console user (not root). sudo is asked once
# and used ONLY for read-only queries: dmidecode (firmware tables), journalctl -k (kernel log),
# `stone-cu40 status` (its kernel CU count) and reading /var/lib/stone (stoned's state, 0700).
# busctl runs with --auto-start=no, so no D-Bus query can start a service. Run while Game
# Mode/Steam is open for section 11.
set -u
umask 077

OUT="${HOME}/stone-diag-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
SUDO_OK=0

# run <file> <title> <command...>: print the command and its output (stdout+stderr) to <file>.
run() {
    local file="$OUT/$1" title="$2"; shift 2
    {
        echo "### ${title}"
        echo "\$ $*"
        if command -v "$1" >/dev/null 2>&1; then
            timeout 30 "$@" 2>&1
            echo "[exit $?]"
        else
            echo "[no disponible: $1 no está instalado; no se instala nada]"
        fi
        echo
    } >>"$file"
}

# runsh <file> <title> <shell snippet>: same, for short read-only pipelines.
runsh() {
    local file="$OUT/$1" title="$2" snippet="$3"
    { echo "### ${title}"; echo "\$ ${snippet}"; timeout 30 bash -c "$snippet" 2>&1; echo "[exit $?]"; echo; } >>"$file"
}

# rsudo: only the three read-only uses described above; skipped if sudo was not granted.
rsudo() {
    local file="$1" title="$2"; shift 2
    if [ "$SUDO_OK" = 1 ]; then run "$file" "$title" sudo -n "$@"; else
        { echo "### ${title}"; echo "[omitido: sin sudo]"; echo; } >>"$OUT/$file"; fi
}

echo "STONE diagnostic (solo lectura) -> $OUT"
echo "Se pedirá la contraseña de sudo una vez (dmidecode, registro del kernel, estado de stoned)."
if sudo -v; then SUDO_OK=1; else echo "Sin sudo: esas secciones se omiten."; fi

# 01 - System identity and installed image
F=01-sistema.txt
run   $F "STONE release"                cat /usr/lib/stone-release
run   $F "os-release"                   cat /etc/os-release
run   $F "Kernel"                       uname -r
run   $F "Kernel command line"          cat /proc/cmdline
run   $F "Deployments (rpm-ostree)"     rpm-ostree status
run   $F "Deployments (JSON)"           rpm-ostree status --json
run   $F "bootc status"                 bootc status
run   $F "Secure Boot"                  mokutil --sb-state
runsh $F "UEFI boot"                    '[ -d /sys/firmware/efi ] && echo UEFI || echo BIOS/legacy'

# 02 - CPU: how many cores are really active (P-03)
F=02-cpu.txt
run   $F "lscpu"                        lscpu
run   $F "nproc"                        nproc
runsh $F "Logical CPUs in /proc/cpuinfo" 'grep -c ^processor /proc/cpuinfo; grep -m1 "model name" /proc/cpuinfo'
runsh $F "CPU topology (possible/present/online/offline)" 'for f in possible present online offline; do printf "%s: " $f; cat /sys/devices/system/cpu/$f 2>/dev/null || echo -; done'
runsh $F "Cores per package (unique core_id)" 'cat /sys/devices/system/cpu/cpu*/topology/core_id 2>/dev/null | sort -un | wc -l'
runsh $F "CPU frequency interface" 'ls /sys/devices/system/cpu/cpu0/cpufreq 2>/dev/null || echo "sin cpufreq (esperado en la BC-250)"; grep -m3 MHz /proc/cpuinfo'
rsudo $F "SMBIOS processor (core count / enabled)" bash -c 'dmidecode -t processor | grep -E "Socket Designation|Version|Core Count|Core Enabled|Thread Count|Max Speed|Current Speed"'

# 03 - Firmware / BIOS and memory
F=03-firmware-memoria.txt
runsh $F "BIOS (sysfs, no root)"        'for f in bios_vendor bios_version bios_date bios_release board_vendor board_name board_version; do printf "%s: " $f; cat /sys/class/dmi/id/$f 2>/dev/null || echo -; done'
rsudo $F "SMBIOS BIOS"                  bash -c 'dmidecode -t bios | grep -vE "Serial|UUID"'
rsudo $F "SMBIOS memory"                bash -c 'dmidecode -t memory | grep -E "Maximum Capacity|Size:|Type:|Speed:" | grep -v "No Module"'
run   $F "Memory"                       free -h
runsh $F "Memory (meminfo)"             'grep -E "MemTotal|MemAvailable|SwapTotal" /proc/meminfo'
runsh $F "GPU VRAM/GTT carve-out (UMA)" 'for d in /sys/class/drm/card[0-9]*/device; do echo "$d"; for f in mem_info_vram_total mem_info_vis_vram_total mem_info_gtt_total; do printf "  %s: " $f; cat $d/$f 2>/dev/null || echo -; done; done'

# 04 - GPU, driver and compute units (P-03)
F=04-gpu-cu.txt
runsh $F "GPU PCI ids"                  'lspci -nn | grep -iE "vga|display|3d"'
runsh $F "GPU driver in use"            'lspci -nnk | grep -iA3 -E "vga|display"'
runsh $F "amdgpu 40 CU parameter (this boot)" 'cat /sys/module/amdgpu/parameters/bc250_cc_write_mode 2>/dev/null || echo "sin parámetro: amdgpu de Bazzite (sin opción 40 CU)"'
runsh $F "amdgpu module file and parameters" 'modinfo -F filename amdgpu; modinfo -F vermagic amdgpu; modinfo -F parm amdgpu | grep -i bc250 || echo "sin bc250_cc_write_mode"'
run   $F "STONE 40 CU status"           stone-cu40 status
rsudo $F "STONE 40 CU status (with kernel CU count)" stone-cu40 status
rsudo $F "Kernel log: amdgpu (this boot)" bash -c 'journalctl -k -b --no-pager | grep -iE "amdgpu|drm|cu |active_cu|gfx10" | head -n 200'
rsudo $F "Kernel log: amdgpu errors (previous boot)" bash -c 'journalctl -k -b -1 --no-pager 2>/dev/null | grep -iE "amdgpu.*(error|fault|timeout|hang|reset)" | tail -n 50'
runsh $F "GPU clocks/levels (known unreliable on BC-250)" 'for d in /sys/class/drm/card[0-9]*/device; do echo "$d"; cat $d/pp_dpm_sclk 2>/dev/null; printf "gpu_busy_percent: "; cat $d/gpu_busy_percent 2>/dev/null || echo -; done'
runsh $F "gpu_metrics activity bytes (0x1c)" 'for f in /sys/class/drm/card[0-9]*/device/gpu_metrics; do echo "$f"; od -An -tx1 -j 28 -N 2 "$f" 2>/dev/null; done'
run   $F "Vulkan devices (summary)"     vulkaninfo --summary

# 05 - GPU governor (cyan-skillfish-governor-smu) (P-01, P-02, P-08)
F=05-regulador.txt
run   $F "Package version"              rpm -q cyan-skillfish-governor-smu
run   $F "Service"                      systemctl status cyan-skillfish-governor-smu --no-pager
run   $F "Config file"                  cat /etc/cyan-skillfish-governor-smu/config.toml
run   $F "D-Bus: main object"           busctl --system --auto-start=no introspect com.cyanskillfish.Governor /com/cyanskillfish/Governor
for r in Current Allowed Initial; do
run   $F "D-Bus: Range/$r"              busctl --system --auto-start=no introspect com.cyanskillfish.Governor "/com/cyanskillfish/Governor/Range/$r"
done
run   $F "Governor log (this boot)"     journalctl -u cyan-skillfish-governor-smu -b --no-pager -n 200

# 06 - STONE services and state
F=06-stone.txt
run   $F "System units"                 systemctl status stoned stoned-recover stone-cu40-guard --no-pager
runsh $F "Enabled state"                'for u in stoned stoned-recover stone-cu40-guard cyan-skillfish-governor-smu; do printf "%s: " $u; systemctl is-enabled $u 2>&1; done'
run   $F "User units"                   systemctl --user status stone-home-register stone-home-autostart --no-pager
run   $F "stonectl status"              stonectl status
run   $F "stonectl status (JSON)"       stonectl --json status
run   $F "stonectl calibration"         stonectl calibration
rsudo $F "stoned state directory"       ls -la /var/lib/stone /var/lib/stone/flags
rsudo $F "stoned state (calibration, slots, safe mode)" cat /var/lib/stone/state.json
rsudo $F "stoned workload log (last lines)" tail -n 80 /var/lib/stone/workload.log
run   $F "stoned log (this boot)"       journalctl -u stoned -u stoned-recover -b --no-pager -n 300
run   $F "stoned log (previous boot)"   journalctl -u stoned -u stoned-recover -b -1 --no-pager -n 150
run   $F "Polkit rules from STONE"      cat /usr/share/polkit-1/rules.d/50-stone.rules
run   $F "stoned sandbox score"         systemd-analyze security stoned --no-pager

# 07 - Sleep / suspend (must be blocked)
F=07-reposo.txt
runsh $F "Sleep targets"                'for t in sleep suspend hibernate hybrid-sleep suspend-then-hibernate; do printf "%s.target: " $t; systemctl is-enabled $t.target 2>&1; done'
run   $F "sleep.conf.d"                 cat /usr/lib/systemd/sleep.conf.d/50-stone-no-sleep.conf

# 08 - Sensors, fan, watchdog (P-12, P-13)
F=08-sensores.txt
runsh $F "hwmon devices and readings"   'for h in /sys/class/hwmon/hwmon*; do echo "$h: $(cat $h/name 2>/dev/null)"; for f in $h/temp*_input $h/temp*_label $h/fan*_input $h/power1_average $h/in*_input; do [ -r "$f" ] && echo "  $(basename $f): $(cat $f 2>/dev/null)"; done; done'
run   $F "lm_sensors (if installed)"    sensors
runsh $F "Hardware watchdog"            'ls -l /dev/watchdog* 2>/dev/null || echo "sin /dev/watchdog"; for w in /sys/class/watchdog/*; do [ -d "$w" ] && echo "$w: $(cat $w/identity 2>/dev/null)"; done; lsmod | grep -iE "sp5100|wdt" || echo "sin módulo sp5100_tco cargado"'

# 09 - Display and video connection (P-05, P-06, P-07); EDID serials are never printed
F=09-pantalla.txt
runsh $F "DRM connectors"               'for c in /sys/class/drm/card[0-9]*-*; do [ -f "$c/status" ] || continue; echo "$(basename $c): $(cat $c/status) enabled=$(cat $c/enabled 2>/dev/null)"; [ "$(cat $c/status)" = connected ] && head -n 15 $c/modes; done'
run   $F "STONE DISPLAY model (JSON, sin números de serie)" stonectl display --json
run   $F "STONE DISPLAY summary"        stonectl display

# 10 - Storage, network, USB, Bluetooth, controllers (STONE CONNECT / DOWNLOADS); no MACs, no IPs
F=10-conectividad.txt
run   $F "Disks"                        lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,TRAN
run   $F "Free space"                   df -h /var /var/home /sysroot
run   $F "Network devices (no MAC/IP)"  nmcli -t -f DEVICE,TYPE,STATE device
run   $F "USB devices"                  lsusb
run   $F "Radio switches"               rfkill list
runsh $F "Bluetooth service state"      'systemctl is-enabled bluetooth 2>&1; systemctl is-active bluetooth 2>&1'
runsh $F "Bluetooth adapters (BlueZ, only if already running)" 'if systemctl is-active -q bluetooth; then busctl --system --auto-start=no tree org.bluez; else echo "bluetooth no está activo: no se consulta (no se arranca nada)"; fi'
runsh $F "Input devices (names)"        'grep -E "^N: Name" /proc/bus/input/devices'
runsh $F "Controllers by id"            'ls -1 /dev/input/by-id 2>/dev/null || echo -'

# 11 - Steam, STONE Home, Game Mode (run with Game Mode open)
F=11-steam-home.txt
run   $F "STONE Home session status"    stone-home-session status
run   $F "STONE Home diagnostic"        stone-home-session diag
runsh $F "Game Mode processes"          'ps -eo pid,etimes,args | grep -E "gamescope|steamwebhelper|SteamLaunch|stone-home|chromium" | grep -v grep | cut -c1-300'
runsh $F "Session variant"              'systemctl --user list-units "gamescope-session-plus@*" --no-pager --no-legend'
runsh $F "STONE Home prefs"             'cat ~/.config/stone/home.json 2>/dev/null || echo -; cat ~/.config/stone/home.env 2>/dev/null || echo "(sin home.env)"; cat ~/.config/environment.d/90-stone-display.conf 2>/dev/null || echo "(sin set-output experimental)"'
runsh $F "STONE user state files"       'ls -la ~/.local/state/stone ~/.local/share/stone 2>/dev/null; ls -la ~/.local/share/stone/components 2>/dev/null || echo "(sin componentes descargados)"'
runsh $F "STONE Home log (last 120 lines)" 'tail -n 120 ~/.local/state/stone/home.log 2>/dev/null || echo -'

# 12 - Installed software relevant to STONE (engines, workloads, desktop session)
F=12-software.txt
run   $F "Key packages"                 rpm -q chromium webkitgtk6.0 gtk4 vkmark mangohud python3-gobject plymouth-plugin-script libgudev gamescope steam
run   $F "User Flatpaks"                flatpak list --user --columns=application,version
runsh $F "Desktop sessions available"   'ls /usr/share/wayland-sessions /usr/share/xsessions 2>/dev/null; command -v steamos-session-select || echo "sin steamos-session-select"'
runsh $F "Plymouth theme"               'plymouth-set-default-theme 2>/dev/null || echo -'

# Summary of the answers this session is meant to give
{
    echo "STONE MACHINE - diagnóstico de solo lectura - $(date -Is)"
    echo
    echo "STONE_VERSION / regulador / kernel:"
    grep -E "STONE_VERSION|STONE_GOVERNOR_VERSION|STONE_KERNEL|STONE_CU40=" /usr/lib/stone-release 2>/dev/null
    echo "Regulador instalado: $(rpm -q cyan-skillfish-governor-smu 2>&1)"
    echo "Imagen arrancada: $(rpm-ostree status --json 2>/dev/null | python3 -c 'import json,sys; d=[x for x in json.load(sys.stdin)["deployments"] if x.get("booted")][0]; print(d.get("container-image-reference"), d.get("container-image-reference-digest") or d.get("checksum"))' 2>/dev/null)"
    echo "CPU lógicas: $(nproc)  · núcleos (core_id únicos): $(cat /sys/devices/system/cpu/cpu*/topology/core_id 2>/dev/null | sort -un | wc -l)  · online: $(cat /sys/devices/system/cpu/online)"
    echo "40 CU en este arranque (bc250_cc_write_mode): $(cat /sys/module/amdgpu/parameters/bc250_cc_write_mode 2>/dev/null || echo 'sin opción')"
    echo "BIOS: $(cat /sys/class/dmi/id/bios_vendor 2>/dev/null) $(cat /sys/class/dmi/id/bios_version 2>/dev/null) $(cat /sys/class/dmi/id/bios_date 2>/dev/null)"
    echo "GPU: $(lspci -nn | grep -iE 'vga|display' | head -n1)"
    echo "Conectores conectados: $(for c in /sys/class/drm/card[0-9]*-*; do [ "$(cat $c/status 2>/dev/null)" = connected ] && printf '%s ' "$(basename $c)"; done)"
    echo
    echo "Archivos: $(ls "$OUT" | tr '\n' ' ')"
} >"$OUT/SUMMARY.txt" 2>&1

[ "$SUDO_OK" = 1 ] && sudo -k
echo "Listo. Revisa $OUT antes de compartirlo."
