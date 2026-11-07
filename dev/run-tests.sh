#!/usr/bin/env bash
# Run scripts/validate.sh and scripts/test-all.sh inside the development container (Fedora 44).
#   dev/run-tests.sh
# Needs podman or docker. The repository is mounted read only; the tests write only to /tmp.
set -euo pipefail
cd "$(dirname "$0")/.."
engine="$(command -v podman || command -v docker || true)"
[[ -n "${engine}" ]] || { echo "podman or docker is needed (see docs/CONSTRUIR.md)" >&2; exit 2; }
"${engine}" build -t localhost/stone-os-rebuild-dev -f dev/Containerfile dev
"${engine}" run --rm -v "$(pwd):/src:ro" localhost/stone-os-rebuild-dev \
    bash -c 'scripts/validate.sh && scripts/test-all.sh'
