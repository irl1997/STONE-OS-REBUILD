#!/usr/bin/env bash
# Build the STONE OS (rebuild) image on your own Linux machine, the same way the build-image workflow does.
#   scripts/build-local.sh [--owner <github-user>] [--no-rechunk]
# Needs podman (and skopeo to pin the base digest; buildah and cosign to rechunk). Produces localhost/stone-os-rebuild:<version>.
# On a Mac: use the GitHub workflow (docs/CONSTRUIR.md); container builds of bootc images need Linux.
set -euo pipefail
cd "$(dirname "$0")/.."
owner="local"; rechunk=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --owner) owner="$2"; shift 2 ;;
        --no-rechunk) rechunk=0; shift ;;
        *) echo "unknown argument $1" >&2; exit 2 ;;
    esac
done
# shellcheck source=image/config/build.env
source image/config/build.env
sha="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
version=""; channel=""
eval "$(scripts/release-info.sh "$(git describe --exact-match --tags 2>/dev/null || echo local)" "${sha}" --shell)"
base="${BASE_IMAGE}:${BASE_TAG}"
digest="${BASE_DIGEST:-}"
if [[ -z "${digest}" ]] && command -v skopeo >/dev/null; then
    digest="$(skopeo inspect --format '{{.Digest}}' "docker://${base}")"
fi
from="${base}${digest:+@${digest}}"
echo "Building STONE OS ${version} (${channel}) from ${from}"
podman build --pull=newer \
    --build-arg "BASE_IMAGE=${from}" --build-arg "BASE_DIGEST=${digest}" \
    --build-arg "STONE_COMMIT=${sha}" --build-arg "STONE_CHANNEL=${channel}" \
    --build-arg "STONE_BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --label "org.opencontainers.image.version=${version}" \
    --label "org.opencontainers.image.source=https://github.com/${owner}/${IMAGE_NAME}" \
    --tag "localhost/${IMAGE_NAME}:${version}" --file image/Containerfile .
if [[ "${rechunk}" == 1 ]]; then
    scripts/rechunk.sh "localhost/${IMAGE_NAME}:${version}"
fi
echo "Done: localhost/${IMAGE_NAME}:${version}"
