#!/usr/bin/env bash
# Build the STONE OS (rebuild) installer ISO locally (Linux, rootful podman), like build-installer.yml.
#   scripts/build-iso-local.sh <image-ref-to-install> [<update-ref>]
# Example: scripts/build-iso-local.sh ghcr.io/<owner>/stone-os-rebuild:0.2.0-dev.1 ghcr.io/<owner>/stone-os-rebuild:dev
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=image/config/build.env
source image/config/build.env
image="${1:?image reference to install}"; update="${2:-$1}"
out="$(pwd)/output"; mkdir -p "${out}"
cfg="$(mktemp)"; trap 'rm -f "${cfg}"' EXIT
sed -e "s|@UPDATE_REF@|${update}|g" -e "s|@IMAGE_REF@|${image}|g" image/disk_config/iso.toml > "${cfg}"
sudo podman pull "${image}"
sudo podman run --rm -it --privileged --pull=newer --net=host \
    --security-opt label=type:unconfined_t \
    -v "${cfg}:/config.toml:ro" -v "${out}:/output" \
    -v /var/lib/containers/storage:/var/lib/containers/storage \
    "${BIB_IMAGE}" --type anaconda-iso --rootfs btrfs --use-librepo=True "${image}"
iso="$(find "${out}" -name '*.iso' | head -n1)"
version="$(tr -d '[:space:]' < VERSION)"
mv "${iso}" "${out}/${IMAGE_NAME}-${version}-x86_64.iso"
(cd "${out}" && sha256sum "${IMAGE_NAME}-${version}-x86_64.iso" > SHA256SUMS)
echo "ISO: ${out}/${IMAGE_NAME}-${version}-x86_64.iso"
