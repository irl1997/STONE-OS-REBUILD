#!/usr/bin/env bash
# STONE · paso 6 · Recoge lo que dejó la sesión STONE para analizarlo en el Mac. SOLO LEE.
# Copia a la carpeta desde la que se ejecuta (el pendrive).
set -uo pipefail
dir="$(pwd)/stone-f2-sesion-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${dir}"
state="${XDG_STATE_HOME:-$HOME/.local/state}/stone"
for f in session.log session.json boot-metrics.jsonl; do
    [ -f "${state}/${f}" ] && cp "${state}/${f}" "${dir}/"
done
{ stone-session status; echo; stone-session boot; } > "${dir}/stone-session.txt" 2>&1
stonectl status > "${dir}/stonectl-status.txt" 2>&1
bootc status > "${dir}/bootc-status.txt" 2>&1
# The previous boots are the ones that ran the STONE session.
for b in -1 -2 -3 -4 -5 -6; do
    journalctl --user -b "${b}" --no-pager 2>/dev/null | tail -n 4000 > "${dir}/journal-user-boot${b}.txt"
done
ls -l "${dir}"
echo
echo "LISTO: lleva el pendrive al Mac."
