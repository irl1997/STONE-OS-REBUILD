#!/usr/bin/env bash
# Re-split a built image into stable layers with chunkah (D-32), in place:
#   scripts/rechunk.sh localhost/stone-os-rebuild:build
# chunkah puts each package's files in the same layer build after build, so a console updating from
# the previous image downloads only the layers that changed. rpm-ostree's build-chunked-oci (used up
# to 1.0.0-rc2) packed files differently on every build: rc1 -> rc2 was a ~7 GB download.
# Same steps as Bazzite's build.py: verify chunkah's signature, empty /run and /tmp, chunk, reload.
# Needs podman, buildah and cosign (Linux; the build-image workflow runs it).
set -euo pipefail
cd "$(dirname "$0")/.."
img="${1:?usage: scripts/rechunk.sh <local image ref>}"
# shellcheck source=image/config/build.env
source image/config/build.env

podman pull "${CHUNKAH_IMAGE}"
ref="$(podman image inspect --format '{{index .RepoDigests 0}}' "${CHUNKAH_IMAGE}")"
cosign verify --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    --certificate-identity-regexp '^https://github\.com/coreos/chunkah/' "${ref}" > /dev/null
echo "chunkah signature verified: ${ref}"

# /run and /tmp emptied (the directories themselves stay): nothing there belongs in the image
# shellcheck disable=SC2016  # expanded by the inner bash, on purpose
buildah unshare bash -euo pipefail -c '
    c="$(buildah from "$1")"; m="$(buildah mount "$c")"
    find "$m/run" "$m/tmp" -mindepth 1 -delete
    buildah umount "$c"; buildah commit --identity-label=false --rm "$c" "$1"' bash "${img}"

work="$(mktemp -d)"; trap 'rm -rf "${work}"' EXIT
podman image inspect "${img}" > "${work}/config.json"
mkdir "${work}/out"
podman run --rm --pull=never \
    --mount=type=image,src="${img}",target=/chunkah \
    --volume "${work}/config.json:/chunkah-config.json:ro,Z" \
    --volume "${work}/out:/run/out:Z" \
    "${ref}" build --max-layers "${CHUNKAH_MAX_LAYERS}" --prune /sysroot/ \
    --config /chunkah-config.json --output oci:/run/out/chunked
podman rmi -f "${img}"
id="$(podman pull -q "oci:${work}/out/chunked")"
podman tag "${id}" "${img}"
echo "${img}: $(podman image inspect --format '{{len .RootFS.Layers}}' "${img}") layers"
