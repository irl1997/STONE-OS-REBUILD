#!/usr/bin/env bash
# STONE · paso 3 · Cambia a STONE OS (rebuild) 0.3.0-dev.1 sin borrar nada (bootc switch).
# CAMBIA la imagen del próximo arranque. La actual queda como versión anterior en el menú de arranque.
# /home (juegos, partidas, ajustes) no se toca. Vuelta atrás: sudo bootc rollback y reiniciar.
set -euo pipefail
IMAGE="ghcr.io/irl1997/stone-os-rebuild:0.3.0-dev.1"
here="$(cd "$(dirname "$0")" && pwd)"
# digest-esperado.txt (next to this script, written by Claude after checking the release's signature)
EXPECTED="$(tr -d '[:space:]' < "${here}/digest-esperado.txt" 2>/dev/null || true)"
[[ "${EXPECTED}" == sha256:* ]] || { echo "PARA: falta digest-esperado.txt junto a este script. No he cambiado nada. Avisa a Claude."; exit 1; }
echo "Se va a preparar: ${IMAGE}"
echo "Digest firmado que debe llegar: ${EXPECTED}"
echo "Hace falta internet. Tarda entre 10 y 40 minutos. No apagues la consola mientras tanto."
read -r -p "Escribe SI (en mayúsculas) y pulsa Intro para empezar: " answer
[ "${answer}" = "SI" ] || { echo "No has escrito SI: no he cambiado nada."; exit 0; }
sudo bootc switch "${IMAGE}"
got="$(sudo bootc status --format=json | python3 -c 'import sys,json; s=json.load(sys.stdin)["status"]; st=s.get("staged") or {}; print(((st.get("image") or {}).get("imageDigest")) or "")')"
echo
echo "Preparada: ${got:-ninguna}"
if [ "${got}" = "${EXPECTED}" ]; then
    echo "LISTO: es la imagen firmada. Reinicia con:  systemctl reboot"
else
    echo "PARA: la imagen preparada no es la firmada (${EXPECTED}). NO reinicies."
    echo "Deshazlo con:  sudo bootc rollback   (o simplemente no reinicies) y avisa a Claude con una foto."
    exit 1
fi
