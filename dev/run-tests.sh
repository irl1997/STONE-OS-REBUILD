#!/usr/bin/env bash
# Run scripts/validate.sh and scripts/test-all.sh inside the development container (Fedora 44).
# Both always run (one failing does not hide the other); the exit status fails if either fails.
#   dev/run-tests.sh
# Needs podman or docker. The repository is mounted read only; the tests write only to /tmp.
set -euo pipefail
cd "$(dirname "$0")/.."
engine="$(command -v podman || command -v docker || true)"
[[ -n "${engine}" ]] || { echo "podman or docker is needed (see docs/CONSTRUIR.md)" >&2; exit 2; }
"${engine}" build -t localhost/stone-os-rebuild-dev -f dev/Containerfile dev
# shellcheck disable=SC2016  # $rc is expanded by the container's bash, not here
"${engine}" run --rm -v "$(pwd):/src:ro" localhost/stone-os-rebuild-dev \
    bash -c 'rc=0; scripts/validate.sh || rc=1; scripts/test-all.sh || rc=1; exit $rc'
