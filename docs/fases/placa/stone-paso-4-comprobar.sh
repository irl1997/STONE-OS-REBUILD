#!/usr/bin/env bash
# STONE · paso 4 · Comprobaciones tras el primer arranque de 0.3.0-dev.1. SOLO LEE.
# Escribe el informe en la carpeta desde la que se ejecuta (el pendrive) y dice si se puede seguir.
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
# digest-esperado.txt (next to this script, written by Claude after checking the release's signature)
EXPECTED="$(tr -d '[:space:]' < "${here}/digest-esperado.txt" 2>/dev/null || true)"
[[ "${EXPECTED}" == sha256:* ]] || { echo "PARA: falta digest-esperado.txt junto a este script. No he cambiado nada. Avisa a Claude."; exit 1; }
out="$(pwd)/stone-f2-comprobacion-$(date +%Y%m%d-%H%M%S).txt"
section() { echo; echo "### $1"; shift; timeout 30 "$@" 2>&1; echo "[exit $?]"; }
{
    section "bootc status" bootc status
    section "ostree admin status" ostree admin status
    section "stone-release" cat /usr/lib/stone-release
    section "cmdline" cat /proc/cmdline
    section "stoned activo" systemctl is-active stoned
    section "stonectl status" stonectl status
    section "stone-cu40 status" stone-cu40 status
    section "stone-session status" stone-session status
    section "stone-session boot" stone-session boot
    section "systemd-analyze time" systemd-analyze time
    section "errores de este arranque" journalctl -b -p err --no-pager -n 200
} > "${out}"

fail=0
check() { if eval "$2"; then echo "  OK    $1"; else echo "  FALLO $1"; fail=1; fi; }
echo "Comprobaciones (informe: ${out})"
booted="$(bootc status --format=json 2>/dev/null | python3 -c 'import sys,json; b=json.load(sys.stdin)["status"]["booted"]["image"]; print(b["image"]["image"], b["imageDigest"])' 2>/dev/null)"
check "arrancada STONE OS 0.3.0-dev.1" '[[ "${booted}" == *stone-os-rebuild:0.3.0-dev.1* ]]'
check "es la imagen firmada" '[[ "${booted}" == *"${EXPECTED}"* ]]'
check "fase F2" 'grep -q "^STONE_PHASE=\"F2\"" /usr/lib/stone-release'
check "stoned en marcha" '[ "$(systemctl is-active stoned)" = active ]'
check "stoned responde" 'timeout 30 stonectl status >/dev/null 2>&1'
check "rc23 sigue fijada como versión anterior" 'ostree admin status | grep -q "Pinned: yes"'
echo
if [ "${fail}" = 0 ]; then
    echo "TODO BIEN: sigue con el paso 5."
else
    echo "PARA: algo no cuadra. No sigas con el paso 5. Lleva el pendrive al Mac y avisa a Claude."
fi
exit "${fail}"
