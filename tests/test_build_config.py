"""F0 build configuration: the decisions of docs/fases/F0_PLAN.md hold in the files that build the image.

    python3 tests/test_build_config.py     (or: pytest tests/test_build_config.py)
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need, read_env_file, load_yaml, run_module  # noqa: E402

ENV = read_env_file(os.path.join(REPO, "image", "config", "build.env"))
PINNED_GOVERNOR = "v0.4.14-1.20260619120402457887.update.deps.3.g14080b4.fc44"
MEASURED_BASE = "sha256:278941ea67603e24e24ff18e8c418b91f2f326fffd3d24edcff9779f36fbdf4e"


def _read(*parts):
    with open(os.path.join(REPO, *parts)) as f:
        return f.read()


def test_image_name_is_not_the_rc23_one():
    # F0-A: a console following ghcr.io/<owner>/stone-os must never receive a rebuild image.
    assert ENV["IMAGE_NAME"] == "stone-os-rebuild", ENV["IMAGE_NAME"]


def test_base_is_pinned_to_the_measured_digest():
    assert ENV["BASE_IMAGE"] == "ghcr.io/ublue-os/bazzite-deck" and ENV["BASE_TAG"] == "stable-44"
    assert ENV["BASE_DIGEST"] == MEASURED_BASE
    default = re.search(r"^ARG BASE_IMAGE=(\S+)$", _read("image", "Containerfile"), re.M).group(1)
    assert default == f"{ENV['BASE_IMAGE']}:{ENV['BASE_TAG']}@{ENV['BASE_DIGEST']}", default


def test_governor_is_pinned_to_the_measured_version():
    # R-03: the version of every board measurement; v0.4.15 (rc23) is not adopted.
    assert ENV["GOVERNOR_VERSION"] == PINNED_GOVERNOR
    assert ENV["GOVERNOR_COPR"] == "filippor/bazzite"
    build = _read("image", "build_files", "build.sh")
    assert 'dnf5 -y install "cyan-skillfish-governor-smu-${GOVERNOR_VERSION}"' in build
    assert '/ctx/governor-contract.sh "${GOVERNOR_VERSION}"' in build
    assert 'GOVERNOR_VERSION="${GOVERNOR_VERSION:-}"' not in build, "the pin must not fall back to 'latest'"


def test_reference_hardware_is_recorded_not_used_as_a_limit():
    assert ENV["STONE_REFERENCE_CPU_CORES"] == "8" and ENV["STONE_REFERENCE_GPU_CU"] == "40"
    build = _read("image", "build_files", "build.sh")
    assert "STONE_REFERENCE_CPU_CORES" in build and "STONE_REFERENCE_GPU_CU" in build


def test_reference_hardware_matches_the_board_profile():
    prof = load_yaml(os.path.join(REPO, "hardware", "bc250.yaml"))
    assert prof["reference"]["cpu_cores"]["value"] == int(ENV["STONE_REFERENCE_CPU_CORES"])
    assert prof["reference"]["gpu_compute_units"]["value"] == int(ENV["STONE_REFERENCE_GPU_CU"])
    assert PINNED_GOVERNOR in prof["governor"]["package"]["value"]


def test_40_cu_module_is_required():
    # D-16/D-17: without the module the reference console would boot with 24 CU.
    build = _read("image", "build_files", "build.sh")
    assert '[[ "${CU40_STATUS}" == ok ]] || { echo "ERROR: 40 CU module not built' in build
    assert 'echo "ERROR: stone-cu-verify not built"; exit 1' in build
    assert "systemctl enable stone-cu40-guard.service" in build


def test_steam_game_mode_is_the_interface():
    # D-34: Bazzite's automatic session stays; STONE writes no session of its own.
    build = _read("image", "build_files", "build.sh")
    assert "sddm.conf.d" not in build and "User=" not in build
    tree = []
    for root, _, files in os.walk(os.path.join(REPO, "system")):
        tree += [os.path.relpath(os.path.join(root, f), REPO) for f in files]
    for gone in ("stone-home", "stone-session", "gamescope-session-stone", "sessions.d/stone"):
        assert not [p for p in tree if gone in p], (gone, tree)
    assert "cp -a /ctx/services/stoned/stoned /usr/lib/stone/stoned" in build
    assert "systemctl enable stoned-recover.service stoned.service" in build
    assert "systemctl enable stone-console-setup.service stone-blackbox.service" in build


def test_console_pieces_are_pinned_and_checked():
    env = _read("image", "config", "build.env")
    assert re.search(r"^DECKY_VERSION=v\d+\.\d+\.\d+$", env, re.M)
    assert re.search(r"^DECKY_SHA256=[0-9a-f]{64}$", env, re.M)
    sha = re.search(r"^CSS_LOADER_SHA256=([0-9a-f]{64})$", env, re.M).group(1)
    assert re.search(rf"^CSS_LOADER_URL=https://\S+/{sha}\.zip$", env, re.M)
    build = _read("image", "build_files", "build.sh")
    assert 'echo "${DECKY_SHA256}  ${CONSOLE}/PluginLoader" | sha256sum -c -' in build
    assert 'echo "${CSS_LOADER_SHA256}  /tmp/css-loader.zip" | sha256sum -c -' in build
    container = _read("image", "Containerfile")
    assert "npm ci" in container and "npm run typecheck" in container and "from=plugin" in container
    assert '"root"' in _read("plugins", "stone", "plugin.json")


def test_no_sleep_and_no_hhd():
    build = _read("image", "build_files", "build.sh")
    assert "systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target" in build
    assert 'systemctl mask "${unit}"' in build
    conf = _read("system", "usr", "lib", "systemd", "sleep.conf.d", "50-stone-no-sleep.conf")
    for key in ("AllowSuspend=no", "AllowHibernation=no", "AllowHybridSleep=no", "AllowSuspendThenHibernate=no"):
        assert key in conf, key


def test_version_is_valid():
    v = _read("VERSION").strip()
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?", v), v


def test_executable_bits():
    for rel in ("image/build_files/build.sh", "image/build_files/check-kernel.sh", "image/build_files/governor-config.py",
                "image/build_files/governor-contract.sh", "image/build_files/cu40/build-amdgpu.sh",
                "image/build_files/cu40/patch-gfx10.py", "system/usr/bin/stone-cu40", "system/usr/libexec/stone/stone-console-setup", "scripts/validate.sh",
                "scripts/test-all.sh", "scripts/release-info.sh", "scripts/build-local.sh", "scripts/build-iso-local.sh"):
        need(os.path.exists(os.path.join(REPO, rel)), f"{rel} not written yet")
        assert os.access(os.path.join(REPO, rel), os.X_OK), rel


def test_rechunk_uses_signed_chunkah_pinned_by_digest():
    # D-32: stable layers, so console updates download only what changed
    assert re.fullmatch(r"quay\.io/coreos/chunkah:[\w.-]+@sha256:[0-9a-f]{64}", ENV["CHUNKAH_IMAGE"])
    script = _read("scripts", "rechunk.sh")
    assert "cosign verify" in script and "coreos/chunkah/" in script and "--prune /sysroot/" in script
    # 1.0.0-rc4 on the board: stale labels made the installer fail; the build now imports the image like it
    assert '"ostree.final-diffid", "ostree.commit"' in script
    assert script.index("ostree container image pull") > script.index('podman tag "${id}"')
    workflow = _read(".github", "workflows", "build-image.yml")
    assert 'scripts/rechunk.sh "localhost/${IMAGE_NAME}:build"' in workflow
    assert "build-chunked-oci" not in workflow + _read("scripts", "build-local.sh")
    assert workflow.index("Install cosign") < workflow.index("scripts/rechunk.sh")


if __name__ == "__main__":
    sys.exit(run_module(globals()))

