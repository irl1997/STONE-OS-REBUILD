#!/usr/bin/env bash
# STONE · paso 2 · Fija la versión arrancada ahora (rc23) para que no se borre nunca.
# CAMBIA solo una marca de ostree. Se quita con: sudo ostree admin pin --unpin <índice>
# No toca BIOS, firmware, frecuencias, núcleos, CU, paquetes ni servicios.
set -euo pipefail
st="$(ostree admin status)"
echo "$st"
echo
# Deployment lines start with "* " (the booted one) or two spaces and a name; details are indented more.
n="$(printf '%s\n' "$st" | grep -E '^(\* |  )[^ ]' | grep -n '^\*' | cut -d: -f1 || true)"
if [ -z "$n" ]; then
    echo "PARA: no encuentro la versión arrancada. No he cambiado nada. Avisa a Claude con una foto de esta pantalla."
    exit 1
fi
idx=$((n - 1))
echo "La versión arrancada es la número ${idx} de la lista. Se fija ahora (pide la contraseña)."
sudo ostree admin pin "${idx}"
echo
after="$(ostree admin status)"
echo "$after"
if printf '%s\n' "$after" | awk '/^\* /{b=1; next} /^(  )[^ ]/{b=0} b && /Pinned: yes/{f=1} END{exit !f}'; then
    echo
    echo "LISTO: la versión arrancada queda fijada (Pinned: yes). Sigue con el paso 3."
else
    echo
    echo "PARA: no veo «Pinned: yes» en la versión arrancada. Avisa a Claude con una foto de esta pantalla."
    exit 1
fi
